#!/usr/bin/env python3
"""NES palette timing probe (research): calls the native palette loaders
($F1C0 sprite palette A into sprite row X, $F211 colour set A) from a stub
in RAM with interrupts off, from one saved gameplay state, in Original,
NES-A and NES-B ($2100 = $00, $08, $28), with $2E5F (stage) and $2240
(master state) set per case, and reports the master clocks the call took
and the RAM palette and backup it left. Every NES case must take exactly
Original's clocks; with BASE given, the NES palettes must equal BASE's
(the build before the change) in the same case.
usage: nes_cycles.py ROM [BASE_ROM]"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts'))
from palette_lag import Game, EMULATOR, OUT, start_point, seed_state, master_clock  # noqa: E402

STUB = 0x3f00


def cases():
    for n in range(0, 160):
        for master in (0, 1):
            yield ('sprite', n, 6, master)
    for s in range(22):
        for stage in (0, 5, 6, 8):
            for master in (0, 1):
                yield ('set', s, stage, master)


def run(rom, label):
    out = {}
    log = OUT / 'work' / f'nes-cycles-{label}'
    tmp = log / 'clock.state'
    with Game(EMULATOR, log) as game:
        start_point(game, rom, seed_state(), True)
        base = log / 'base.state'
        game.call('save_state_file', {'file_path': str(base)})
        for kind, a, stage, master in cases():
            for bits in (0x00, 0x08, 0x28):
                game.call('load_state_file', {'file_path': str(base)})
                game.write(0x100, bytes([bits]))
                game.write(0xe5f, bytes([stage]))
                game.write(0x240, bytes([master]))
                game.write(0x260, b'\x00')            # empty queue
                game.write(0x283, b'\x00')            # unlocked
                loader = 0xf1c0 if kind == 'sprite' else 0xf211
                stub = bytes([0x78, 0xa9, a, 0xa2, 3, 0x20, loader & 0xff, loader >> 8, 0xea, 0x80, 0xfe])
                game.write(STUB - 0x2000, stub)
                game.reg('PC', STUB)
                for addr in (STUB + 5, STUB + 8):
                    game.call('set_breakpoint', {'address': f'{addr:x}', 'memory_area': 'cpu_addr', 'execute': True})
                game.run_to(f'{STUB + 5:04X}', polls=40000)
                t0 = master_clock(game, tmp)
                game.run_to(f'{STUB + 8:04X}', polls=40000)
                t1 = master_clock(game, tmp)
                for addr in (STUB + 5, STUB + 8):
                    game.call('remove_breakpoint', {'address': f'{addr:x}', 'memory_area': 'cpu_addr'})
                ram = game.read(0, 0x2000)
                out[f'{kind} {a} stage {stage} master {master} bits {bits:02x}'] = {
                    'clocks': t1 - t0, 'palette': hashlib.sha1(ram[0x286:0xa86]).hexdigest()[:12],
                    'zp': ram[0x15:0x30].hex(), 'queue': ram[0x260:0x281].hex()}
    return out


def main():
    rom = Path(sys.argv[1])
    res = run(rom, 'new')
    base = run(Path(sys.argv[2]), 'base') if len(sys.argv) > 2 else None
    (OUT / 'nes-cycles.json').write_text(json.dumps({'new': res, 'base': base}))
    bad_t, bad_p, n = [], [], 0
    for key, v in res.items():
        if key.endswith('bits 00'):
            continue
        n += 1
        o = res[key[:-2] + '00']
        if v['clocks'] != o['clocks']:
            bad_t.append((key, v['clocks'] - o['clocks']))
        if base and v['palette'] != base[key]['palette']:
            bad_p.append(key)
    worst = max((abs(d) for _, d in bad_t), default=0)
    print(f'{n} NES calls: {len(bad_t)} differ from Original in clocks (worst {worst}); first {bad_t[:6]}')
    if base:
        print(f'palette results differing from the base build: {len(bad_p)}; first {bad_p[:6]}')
        ot = [k for k in res if k.endswith('bits 00') and res[k]['clocks'] != base[k]['clocks']]
        op = [k for k in res if k.endswith('bits 00') and res[k]['palette'] != base[k]['palette']]
        print(f'Original calls differing from the base build: clocks {len(ot)}, palette {len(op)}')
        bt = [(k, base[k]['clocks'] - base[k[:-2] + '00']['clocks']) for k in base if not k.endswith('bits 00')]
        print('base build NES extra clocks: min', min(d for _, d in bt), 'max', max(d for _, d in bt))


if __name__ == '__main__':
    main()
