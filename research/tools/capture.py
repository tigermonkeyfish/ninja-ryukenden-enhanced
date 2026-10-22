#!/usr/bin/env python3
"""Capture matched background sweeps for one ROM (raw original or Enhanced).

Interventions (identical for both ROMs, all debugger-only, none in the output ROM):
  * Level Select reproduced by debugger writes at $83F3 (see core.jump_to_stage).
  * ROM-buffer NOP of the player-driven `jsr $E341` at bank 1 $925E (same bytes in
    both ROMs), as in the project's historical camera sweeps, so only the forced
    scroll moves the camera.
  * At each gameplay update ($8457, bank 1): Ryu X = camera+128, Ryu Y = $60,
    health = $10, then a synthetic call to the native camera scroll $E341 with
    $220E = +/-4. Registers A/X/Y/P/S are restored before the update continues.
  * Area changes use the native forward area transition at $8490.
"""
import argparse
import hashlib
import json
import sys
import time
import zlib

from core import (ENHANCED, ORIGINAL, PARALLAX, STAGE_NAMES, Path, Session,
                  boot_to_gameplay, jump_to_stage, run_to_hook)

STEP = 4          # camera pixels per forced update
SAMPLE_EVERY = 8  # updates between samples (32 px)


class Sweeper:
    def __init__(self, s, out, label):
        self.s, self.out, self.label = s, out, label
        self.records = []

    def wait_bp(self, pc='8457', polls=20000):
        for _ in range(polls):
            st = self.s.status()
            if st['paused']:
                if st['pc'] != pc:
                    raise RuntimeError(f'unexpected stop {st}')
                return st
        raise TimeoutError(pc)

    def next_update(self):
        """From PC=$8457, execute this update and stop at the next one."""
        self.s.call('debug_step_into')
        self.s.call('debug_continue')
        self.wait_bp()

    def forced_scroll(self, delta):
        s = self.s
        cpu = s.cpu()
        assert cpu['PC'] == '8457', cpu
        sp = int(cpu['S'], 16)
        saved = {k: int(cpu[k], 16) for k in ('A', 'X', 'Y', 'P')}
        cam = int.from_bytes(s.read(0x20f, 2), 'little')
        x = cam + 128
        s.write(0xe9e, bytes([x & 255, x >> 8, 0x60]))
        s.write(0xead, b'\x10')
        s.write(0x20e, bytes([delta & 255]))
        s.write(0x100 + sp - 1, bytes([0x56, 0x84]))
        s.reg('S', sp - 2)
        s.reg('PC', 0xe341)
        s.call('debug_continue')
        self.wait_bp()
        cpu = s.cpu()
        assert int(cpu['S'], 16) == sp, cpu
        for k, v in saved.items():
            s.reg(k, v)

    def sample(self, kind, index, sub):
        s = self.s
        regs = {r[0]: int(r[1], 16) for r in s.call('get_huc6270_registers')['registers']}
        ram = s.read(0, 0x2000)
        vram = s.read(0, 0x10000, area=4)
        pal = s.read(0, 1024, area=8)
        sat = s.read(0, 512, area=6)
        png = s.screenshot_png()
        name = f'{sub}-{kind}-{index:04}'
        d = self.out / 'samples'
        (d / f'{name}.png').write_bytes(png)
        (d / f'{name}.vram.z').write_bytes(zlib.compress(vram, 6))
        (d / f'{name}.ram.z').write_bytes(zlib.compress(ram, 6))
        (d / f'{name}.pal').write_bytes(pal)
        (d / f'{name}.sat').write_bytes(sat)
        rec = {
            'name': name, 'kind': kind, 'index': index, 'subarea': sub,
            'camera': int.from_bytes(ram[0x20f:0x211], 'little'),
            'render_camera': int.from_bytes(ram[0xe4b:0xe4d], 'little'),
            'stage': ram[0xe5f], 'subarea_ram': ram[0xe60], 'master': ram[0x240:0x249].hex(),
            'pages': ram[0x237], 'geometry': ram[0x251:0x257].hex(),
            'options': ram[0x100], 'mwr': regs[9], 'png_sha256': hashlib.sha256(png).hexdigest(),
        }
        self.records.append(rec)
        return rec

    def sweep_area(self, sub, log):
        s = self.s
        ram = s.read(0, 0x2000)
        pages = ram[0x237]
        max_cam = max(0, pages * 256 - 256)
        c0 = int.from_bytes(ram[0x20f:0x211], 'little')
        rec = self.sample('entry', 0, sub)
        log(f'{self.label} sub {sub}: entry cam {c0} pages {pages} max {max_cam} '
            f'stage {rec["stage"]} sub_ram {rec["subarea_ram"]}')
        if max_cam == 0:
            # Non-horizontal area: a few natural updates only.
            for i in range(1, 4):
                for _ in range(SAMPLE_EVERY):
                    self.next_update()
                self.sample('static', i, sub)
            return
        first = 1 if c0 <= max_cam // 2 else -1
        for kind, direction in (('fwd', first), ('rev', -first)):
            i, stuck, last = 0, 0, None
            while True:
                cam = int.from_bytes(s.read(0x20f, 2), 'little')
                target = max_cam if direction > 0 else 0
                remaining = abs(target - cam)
                if remaining == 0 or stuck > 4:
                    self.sample(kind, i + 1, sub)
                    break
                delta = direction * min(STEP, remaining)
                self.forced_scroll(delta)
                self.next_update()
                i += 1
                cam2 = int.from_bytes(s.read(0x20f, 2), 'little')
                stuck = stuck + 1 if cam2 == last else 0
                last = cam2
                if i % SAMPLE_EVERY == 0:
                    self.sample(kind, i, sub)
                if i > 6000:
                    raise RuntimeError('sweep did not terminate')
            log(f'{self.label} sub {sub}: {kind} done at cam {cam} after {i} updates')

    def next_area(self):
        """Native forward area transition ($8490), as the historical captures did."""
        s = self.s
        before = s.read(0, 0x2000)
        s.reg('PC', 0x8490)
        s.call('remove_breakpoint', {'address': '2457', 'memory_area': 'rom'})
        s.step(150)
        s.call('set_breakpoint', {'address': '2457', 'memory_area': 'rom', 'execute': True})
        s.call('debug_continue')
        self.wait_bp(polls=40000)
        after = s.read(0, 0x2000)
        return before, after


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('rom', choices=['orig', 'enh'])
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--stages', type=int, nargs='*', default=PARALLAX)
    ap.add_argument('--max-areas', type=int, default=8)
    ap.add_argument('--rom-file', type=Path, help='Override the ROM for this label')
    ap.add_argument('--options', type=int, help='Write the patch option bytes $2100/$2101 before stage jumps')
    args = ap.parse_args()
    rom = args.rom_file or (ORIGINAL if args.rom == 'orig' else ENHANCED)
    root = args.out / args.rom
    root.mkdir(parents=True, exist_ok=True)
    logf = (root / 'capture.log').open('a')

    def log(msg):
        line = f'{time.strftime("%H:%M:%S")} {msg}'
        print(line, flush=True)
        logf.write(line + '\n')
        logf.flush()

    with Session(root) as s:
        hook_state = (root / 'hook.state').resolve()
        boot_to_gameplay(s, rom, log)
        s.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'})
        s.step(120)
        s.call('set_breakpoint', {'address': '23f3', 'memory_area': 'rom', 'execute': True})
        run_to_hook(s)
        if args.options is not None:
            s.write(0x100, bytes([args.options, args.options]))
            log(f'options $2100/$2101 = {args.options:02x}')
        s.call('save_state_file', {'file_path': str(hook_state)})
        for stage in args.stages:
            out = root / f'{stage:02}-{STAGE_NAMES[stage]}'
            (out / 'samples').mkdir(parents=True, exist_ok=True)
            s.call('load_state_file', {'file_path': str(hook_state)})
            s.write(0x325e, bytes([0xea] * 3), area=3)
            s.call('set_breakpoint', {'address': '23f3', 'memory_area': 'rom', 'execute': True})
            jump_to_stage(s, stage)
            s.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'})
            s.step(90)
            s.call('set_breakpoint', {'address': '2457', 'memory_area': 'rom', 'execute': True})
            s.call('debug_continue')
            sw = Sweeper(s, out, f'{args.rom} {STAGE_NAMES[stage]}')
            sw.wait_bp(polls=40000)
            areas = []
            for sub in range(args.max_areas):
                ram = s.read(0, 0x2000)
                if ram[0xe5f] != stage or ram[0x240] != 0:
                    log(f'left stage: stage {ram[0xe5f]} master {ram[0x240:0x242].hex()}')
                    break
                areas.append({'subarea': sub, 'subarea_ram': ram[0xe60],
                              'camera_entry': int.from_bytes(ram[0x20f:0x211], 'little'),
                              'pages': ram[0x237], 'geometry': ram[0x251:0x257].hex()})
                sw.sweep_area(sub, log)
                s.call('save_state_file', {'file_path': str((out / f'area{sub}-end.state').resolve())})
                before, after = sw.next_area()
                if after[0xe60] == before[0xe60] and after[0xe5f] == before[0xe5f]:
                    log(f'area index did not advance ({after[0xe60]}); stopping')
                    break
            s.call('remove_breakpoint', {'address': '2457', 'memory_area': 'rom'})
            (out / 'run.json').write_text(json.dumps({
                'rom': str(rom), 'rom_sha256': hashlib.sha256(rom.read_bytes()).hexdigest(),
                'stage': stage, 'stage_name': STAGE_NAMES[stage], 'areas': areas,
                'step_px': STEP, 'sample_every_updates': SAMPLE_EVERY,
                'samples': sw.records, 'interventions': __doc__,
            }, indent=1) + '\n')
            log(f'{STAGE_NAMES[stage]} complete: {len(sw.records)} samples, {len(areas)} areas')


if __name__ == '__main__':
    main()
