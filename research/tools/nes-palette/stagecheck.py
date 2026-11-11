"""Evidence b (stage loads): every Level Select entry in Original mode and in
NES mode, one fresh session each from the shared start state. Counts the
frames from the main-loop hook to the first update ($8457; the load's
length), then steps FRAMES frames and records the gameplay fields and the
sprite table per frame. At the last frame, the RAM palette: every entry of
the stage's colour set that Original mode still holds at its set value
must hold the NES value in NES mode (the 3-2 variant in 3-2), the HUD
entries $F1-$F7 the NES HUD, sprite row 0 Ryu's NES palette, and 1-1 row 1 /
2-2 rows 13-14 the NES Enhanced palettes. Entries that Original mode itself
no longer holds at the set value (the game animates or rewrites them) are
listed separately with what each mode shows.
usage: stagecheck.py ROM FRAMES OUT.json [stages,..] [SHOTS_DIR shot_stages,..]"""
import hashlib
import json
import sys
from pathlib import Path

from ntools import NES, Session, cv, ram_palette

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts'))
import nes_palette as NP  # noqa: E402

FIELDS = {'ryu': (0xe9e, 0xeb8), 'timer': (0xeda, 0xede), 'cam': (0x20f, 0x211), 'area': (0xe60, 0xe61),
          'stage': (0xe5f, 0xe60), 'health': (0xead, 0xeae)}


TAIL = 60                    # palette compared over the last TAIL frames


def expected(original):
    data = NP.load()
    lay = NP.layout(data)
    import struct
    orig_sets = {}
    for s in range(NP.SETS):
        addr, count = struct.unpack_from('<HH', original, NP.SET_TABLE + 4 * s)
        orig_sets[s] = NP.unpack(original[NP.SET_TABLE + addr - 0x6000:], count)
    enh = {}
    for mod in ('stage11', 'stage22'):
        for label, (merged, nes) in NP.enhanced_palettes(mod, original).items():
            enh[label] = (merged, nes)
    return lay, orig_sets, enh


def load_and_trace(rom, flags, stage, frames):
    with Session(rom, flags) as g:
        cpu = g.call('get_huc6280_status')
        saved = {k: int(cpu[k], 16) for k in ('X', 'Y', 'P', 'S')}
        g.write(0x241, bytes([stage]))
        g.write(0x247, bytes([cv.NEXT_SEQUENCE[stage], 0]))
        g.write(0xe65, bytes(22))
        g.write(0xead, bytes([16]))
        sp = saved['S']
        g.write(0x100 + sp - 1, bytes([0xf2, 0x83]))
        g.reg('S', sp - 2)
        g.reg('A', stage)
        g.reg('PC', 0x8244)
        g.call('set_breakpoint', {'address': '23f3', 'memory_area': 'rom', 'execute': True})
        g.call('set_breakpoint', {'address': '2457', 'memory_area': 'rom', 'execute': True})
        load = 0
        while True:
            if g.step(1) is not None:
                load += 1
                continue
            pc = g.call('get_huc6280_status')['PC']
            if pc == '83F3':
                for k in ('X', 'Y', 'P'):
                    g.reg(k, saved[k])
                g.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'})
                continue
            if pc == '8457':
                break
            raise RuntimeError(f'unexpected stop {pc}')
        g.call('remove_breakpoint', {'address': '2457', 'memory_area': 'rom'})
        entered = Path(g.logdir) / 'entered.state'
        g.call('save_state_file', {'file_path': str(entered)})
        g.call('load_state_file', {'file_path': str(entered)})
        # cv.start_stage's tripwire: the first step must cover one update.
        before = g.read(0xeda, 1)[0]
        g.checked_step(1)
        after = g.read(0xeda, 1)[0]
        g.call('load_state_file', {'file_path': str(entered)})
        if (before - after) & 0xff != 1:
            raise cv.StepError(f'the first step covered {(before - after) & 0xff} updates')
        trace, palettes = [], []
        for n in range(frames):
            g.checked_step(1)
            ram = g.read(0, 0x2000)
            trace.append({k: ram[a:b].hex() for k, (a, b) in FIELDS.items()} |
                         {'sat': hashlib.sha1(g.read(0, 512, area=6)).hexdigest()[:16]})
            if n >= frames - TAIL:
                palettes.append(ram_palette(ram))
        return load, trace, palettes, g.screenshot()


def main():
    rom, frames, out = sys.argv[1], int(sys.argv[2]), Path(sys.argv[3])
    stages = [int(s) for s in sys.argv[4].split(',')] if len(sys.argv) > 4 and sys.argv[4] else range(22)
    shots = Path(sys.argv[5]) if len(sys.argv) > 5 else None
    shot_stages = {int(s) for s in sys.argv[6].split(',')} if len(sys.argv) > 6 else set()
    original = Path('/workspace/build/nes-palette/original.pce').read_bytes()
    original = original[512:] if len(original) % 8192 == 512 else original
    lay, orig_sets, enh = expected(original)
    report = {}
    for stage in stages:
        name = cv.STAGE_NAMES[stage]
        s = NP.STAGE_SET[stage]
        lo, tro, palo, _ = cv.retried(load_and_trace, rom, 0, stage, frames)
        ln, trn, paln, png = cv.retried(load_and_trace, rom, NES, stage, frames)
        if shots and stage in shot_stages:
            shots.mkdir(parents=True, exist_ok=True)
            (shots / f'nes-{name}-start.png').write_bytes(png)
        base = orig_sets[s]
        nes = lay['variants'][stage][1] if stage in lay['variants'] else lay['sets'][s]
        want = {}
        for i in range(len(base)):
            want[i] = (base[i], nes[i])
        for k in range(7):
            want[0xf1 + k] = (int(NP.load()['shared']['hud']['entries'][k]['pce'], 16), lay['hud'][k])
        if stage == 0:
            m, n = enh['extra_palette_nes']
            for k in range(1, 16):
                want[16 + k] = (m[k], n[k])
        if stage == 3:
            for label, row in (('palette13_nes', 13), ('palette14_nes', 14)):
                m, n = enh[label]
                for k in range(1, 16):
                    want[16 * row + k] = (m[k], n[k])
        for (p, cols) in lay['sprites']:
            ryu_orig = [int(x, 16) for x in NP.load()['shared']['sprites'][0]['pce']]
            for k in range(1, 16):
                want[256 + k] = (ryu_orig[k], cols[k])
        bad, game_written, changed = [], [], 0
        for i, (ov, nv) in sorted(want.items()):
            if i % 16 == 0 and i not in (0,):
                continue                     # colour 0 of a row shows entry 0 (unused)
            if any(p[i] != ov for p in palo):
                # Original mode itself shows another value in the last TAIL
                # frames: the game animates or rewrites this entry.
                game_written.append((i, f'{ov:03X}', sorted({f'{p[i]:03X}' for p in palo}),
                                     sorted({f'{p[i]:03X}' for p in paln}), f'{nv:03X}'))
                continue
            if any(p[i] != nv for p in paln):
                bad.append((i, f'{nv:03X}', sorted({f'{p[i]:03X}' for p in paln})))
            changed += ov != nv
        gameplay = [n for n, (a, b) in enumerate(zip(tro, trn)) if a != b]
        report[name] = {'set': s, 'variant': stage in lay['variants'], 'load_frames': [lo, ln],
                        'checked_entries': len(want) - len(game_written), 'entries_changed_by_nes': changed,
                        'mismatches': bad[:20], 'mismatch_count': len(bad),
                        'game_written': game_written, 'gameplay_differing_frames': gameplay[:10]}
        print(name, json.dumps({k: v for k, v in report[name].items() if k != 'game_written'}),
              'game-written', [g[0] for g in game_written], flush=True)
    report['ok'] = all(r['mismatch_count'] == 0 and not r['gameplay_differing_frames'] and
                       r['load_frames'][0] == r['load_frames'][1] for r in report.values() if isinstance(r, dict))
    out.write_text(json.dumps(report, indent=1))
    print('stagecheck', 'passed' if report['ok'] else 'FAILED')


if __name__ == '__main__':
    main()
