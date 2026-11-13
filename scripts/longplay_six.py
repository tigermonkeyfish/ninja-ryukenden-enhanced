#!/usr/bin/env python3
"""Six-mode whole-recording replay with per-frame counters, gameplay fingerprints
and sub-frame clocks at marker frames (emulator evidence only).

    run:     one fresh headless Geargrafx session, power-on with MODE's backup-RAM
             image (menu never opened), the whole recording as one continuous
             input list (no re-syncing, no RAM writes). Every frame it reads the
             8 KiB of RAM and stores: the game-update counter delta ($2000),
             the master flags, stage, area, boss health, and two CRC32
             fingerprints (see CORE and WIDE below). In the frames listed in
             --windows it also arms execution breakpoints at the sound-driver
             command ($38:$4006) and the main-loop update ($2457 = CPU $8457) and
             records their master clocks (palette_lag.step_with_stops).
    compare: reads the six outputs and prints the tables.

    LD_LIBRARY_PATH=/workspace/build/toolchain/sdl3/lib \
      python3 scripts/longplay_six.py run --mode original --file F --out DIR [--windows W.json]
    python3 scripts/longplay_six.py compare DIR
"""
import argparse
import array
import json
import sys
import tempfile
import time
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comparison_video import STAGE_NAMES                                      # noqa: E402
from longplay_lib import EMULATOR, ROM, MODE_BITS, Game, boot_to_first_update, FIRST_UPDATE_ROM  # noqa: E402
import palette_lag as pl                                                      # noqa: E402

MODES = ['original', 'apocalypse', 'nes-a', 'nes-b', 'sms', 'gb dmg']
FRAME = 358995
CLOCK_HZ = 21477270

# RAM offsets (CPU address - $2000).
# CORE: the gameplay state the game itself keeps, no palette or conversion data:
#   counter $2000; master flags $2240-41; camera/pages $220F-10,$2237; stage/area
#   $2E5F-60; Ryu block $2E9E-$2EB7; score/timer $2ED0-$2EDD; boss/enemy/object
#   slots $2F00-$30FF (first enemy slot $2F1C, boss health $3035).
CORE = [(0x000, 0x001), (0x240, 0x242), (0x20f, 0x211), (0x237, 0x238), (0xe5f, 0xe61),
        (0xe9e, 0xeb8), (0xed0, 0xede), (0xf00, 0x1100)]
# WIDE: all of RAM except the palette/conversion/mode areas and the stack page:
#   $2100-$21FF (options byte $2100, palette state $2104, save status $2105, stack
#   and its margin: depth/contents differ with the palette worker's code path),
#   $2260-$2283 palette upload queue/border/lock, $2286-$2A85 RAM palette + backup,
#   $37C0-$37FD WAITR + palette timing + worker scratch, $3C00-$3FFF SHADOW.
EXCLUDED = [(0x100, 0x200), (0x260, 0x284), (0x286, 0xa86), (0x17c0, 0x17fe), (0x1c00, 0x2000)]
WIDE = []
_p = 0
for a, b in EXCLUDED:
    if a > _p:
        WIDE.append((_p, a))
    _p = b
if _p < 0x2000:
    WIDE.append((_p, 0x2000))


def fp(ram, ranges):
    c = 0
    for a, b in ranges:
        c = zlib.crc32(ram[a:b], c)
    return c


def expand(run):
    inputs = []
    for n, buttons in run['segments']:
        inputs += [frozenset(buttons)] * n
    return inputs


def run_mode(a):
    run = json.loads(a.file.read_text())
    inputs = expand(run)
    total = len(inputs)
    windows = set(json.loads(a.windows.read_text())) if a.windows else set()
    out = a.out
    out.mkdir(parents=True, exist_ok=True)
    tag = a.mode.replace(' ', '')
    work = Path(tempfile.mkdtemp(prefix='longplay-six-', dir='/workspace/build/longplay'))
    tmp = work / 'clock.state'
    cnt, mas, m2s, stg, are, bos = (array.array('B') for _ in range(6))
    core, wide = array.array('I'), array.array('I')
    hits = []          # (frame, pc, clock) inside windows
    ends = {}          # frame -> clock of the frame end (windows only)
    t0 = time.time()
    with Game(EMULATOR, work) as game:
        status = boot_to_first_update(game, a.rom, a.mode, work / 'entered.state')
        entered = pl.master_clock(game, tmp)
        game.frame_end = None
        game.leftover = False
        prev = game.read(0, 0x2000)
        in_window = False
        for f in range(1, total + 1):
            game.press(set(inputs[f - 1]))
            want = f in windows
            if want and not in_window:
                game.stop_areas = {'4006': ('rom', pl.MUSIC_ENTRY), '8457': ('rom', FIRST_UPDATE_ROM)}
                for _, (area, addr) in game.stop_areas.items():
                    game.call('set_breakpoint', {'address': f'{addr:x}', 'memory_area': area, 'execute': True})
                game.frame_end = None
                game.leftover = False
                in_window = True
            if in_window:
                def on_stop(pc, clock, f=f):
                    hits.append((f, pc, clock))
                    return False
                pl.step_with_stops(game, tmp, f, on_stop)
                ends[f] = game.frame_end
                if f + 1 not in windows:
                    for _, (area, addr) in game.stop_areas.items():
                        game.call('remove_breakpoint', {'address': f'{addr:x}', 'memory_area': area})
                    # normalise after breakpoint stops (EMULATOR.md): save and reload
                    game.call('save_state_file', {'file_path': str(work / 'norm.state')})
                    game.call('load_state_file', {'file_path': str(work / 'norm.state')})
                    game.held = set()
                    game.press(set(inputs[f - 1]))
                    in_window = False
            else:
                game.checked_step(1)
            ram = game.read(0, 0x2000)
            cnt.append(ram[0])
            mas.append(ram[0x240]); m2s.append(ram[0x241])
            stg.append(ram[0xe5f]); are.append(ram[0xe60]); bos.append(ram[0x1035])
            core.append(fp(ram, CORE)); wide.append(fp(ram, WIDE))
            if f % 20000 == 0:
                print(f'{a.mode}: frame {f} ({time.time() - t0:.0f} s)', flush=True)
        final = game.read(0, 0x1100)
    for nm, arr in (('cnt', cnt), ('mas', mas), ('m2', m2s), ('stg', stg), ('are', are), ('bos', bos),
                    ('core', core), ('wide', wide)):
        (out / f'{tag}.{nm}.bin').write_bytes(arr.tobytes())
    (out / f'{tag}.clocks.json').write_text(json.dumps(
        {'mode': a.mode, 'status': status, 'entered_clock': entered, 'hits': hits,
         'frame_ends': {str(k): v for k, v in ends.items()}, 'total': total, 'seconds': round(time.time() - t0)}))
    # the checker's PASS/FAIL (same criteria as longplay_check.py)
    ok = True
    lines = []
    first = {}
    for f in range(0, total + 1):
        pass
    arrs = {'mas': mas, 'stg': stg, 'are': are, 'm2': m2s}
    for s in run['stages']:
        idx = STAGE_NAMES.index(s['name'])
        m = s['start_frame']
        f0 = next((f for f in range(max(1, m - 400), m + 1) if stg[f - 1] == idx and mas[f - 1] == 0), None)
        good = (m == 0) or (stg[m - 1] == idx and mas[m - 1] == 0 and are[m - 1] == 0)
        ok &= good
        lines.append(f'{"PASS" if good else "FAIL"} {s["name"]:5s} gameplay from frame {f0 if f0 else 0:6d} marker {m}')
    end = run.get('end')
    if end:
        good = all({'master': mas, 'm2': m2s}[k][end['frame'] - 1] == v for k, v in end['state'].items())
        ok &= good
        lines.append(f'{"PASS" if good else "FAIL"} end reached at frame {end["frame"]}: master {mas[end["frame"]-1]} m2 {m2s[end["frame"]-1]}')
    print('\n'.join(lines))
    print(f'replayed {total} frames (+{status["boot_frames"]} boot) in {time.time() - t0:.0f} s; status {status}; entered clock {entered}')
    print('RESULT', 'PASS' if ok else 'FAIL')
    (out / f'{tag}.result.txt').write_text('\n'.join(lines) + f'\nRESULT {"PASS" if ok else "FAIL"}\n')
    return 0 if ok else 1


def load(out, mode):
    tag = mode.replace(' ', '')
    d = {}
    for nm, code in (('cnt', 'B'), ('mas', 'B'), ('m2', 'B'), ('stg', 'B'), ('are', 'B'), ('bos', 'B'),
                     ('core', 'I'), ('wide', 'I')):
        arr = array.array(code)
        arr.frombytes((out / f'{tag}.{nm}.bin').read_bytes())
        d[nm] = arr
    d['clk'] = json.loads((out / f'{tag}.clocks.json').read_text())
    return d


def events(d):
    """Per mode: the frame (state after that many frames) of each named event."""
    mas, m2, stg, are, bos, cnt = d['mas'], d['m2'], d['stg'], d['are'], d['bos'], d['cnt']
    n = len(mas)
    ev = {}
    for f in range(1, n + 1):
        i = f - 1
        if stg[i] == 21 and mas[i] == 0 and '6-4C start' not in ev:
            ev['6-4C start'] = f
        if stg[i] == 21 and bos[i] > 0 and 'boss seen' not in ev:
            ev['boss seen'] = f
        if 'boss seen' in ev and stg[i] == 21 and bos[i] == 0 and 'boss hp 0' not in ev:
            ev['boss hp 0'] = f
        if stg[i] == 21 and are[i] == 1 and 'area 1' not in ev:
            ev['area 1'] = f
        if stg[i] == 21 and mas[i] != 0 and 'master leaves 0' not in ev:
            ev['master leaves 0'] = f
        if mas[i] == 1 and m2[i] == 14 and 'ending (1,14)' not in ev:
            ev['ending (1,14)'] = f
    if 'master leaves 0' in ev:
        ev['last gameplay frame (master 0)'] = ev['master leaves 0'] - 1
    ev['recording end'] = n
    return ev


def updates(d):
    """(updates, lag frames) from the counter deltas; a frame with no change is a lag frame."""
    c = d['cnt']
    upd = lag = multi = 0
    prev = None
    for v in c:
        if prev is not None:
            dd = (v - prev) & 255
            if dd == 0:
                lag += 1
            else:
                upd += dd
                multi += dd > 1
        prev = v
    return upd, lag, multi


def first_diff(a, b):
    for i in range(min(len(a), len(b))):
        if a[i] != b[i]:
            return i + 1
    return None if len(a) == len(b) else min(len(a), len(b)) + 1


def stops_in(d, f, pc):
    return [c for ff, p, c in d['clk']['hits'] if ff == f and p == pc]


def compare(a):
    out = a.out
    D = {m: load(out, m) for m in MODES}
    ref = D['original']
    evs = {m: events(D[m]) for m in MODES}
    print('## per mode: updates, lag frames, first divergence vs ORIGINAL (frame = state after that many frames)')
    print('mode | frames | game updates | lag frames | multi-update frames | first diff counter | first diff master/stage/area/boss | first diff CORE | first diff WIDE | boot frames | entered clock')
    for m in MODES:
        d = D[m]
        u, l, mu = updates(d)
        sig = lambda x: list(zip(x['mas'], x['m2'], x['stg'], x['are'], x['bos']))
        fd = first_diff(sig(d), sig(ref))
        print(f'{m} | {len(d["cnt"])} | {u} | {l} | {mu} | {first_diff(d["cnt"], ref["cnt"])} | {fd} | '
              f'{first_diff(d["core"], ref["core"])} | {first_diff(d["wide"], ref["wide"])} | '
              f'{d["clk"]["status"]["boot_frames"]} | {d["clk"]["entered_clock"]}')
    print('\n## events (frame per mode)')
    names = list(evs['original'])
    print('event | ' + ' | '.join(MODES))
    for nme in names:
        print(nme + ' | ' + ' | '.join(str(evs[m].get(nme)) for m in MODES))
    print('\n## sub-frame: first main-loop update ($8457) and first sound-driver call ($4006) clock in the event frame')
    ticks = lambda x: x
    for nme in names:
        row = []
        for m in MODES:
            f = evs[m].get(nme)
            if f is None:
                row.append('n/a'); continue
            for tag, pc in (('upd', '8457'), ('snd', '4006')):
                pass
            u = stops_in(D[m], f, '8457')
            s = stops_in(D[m], f, '4006')
            row.append((f, u[0] if u else None, u[-1] if u else None, s[0] if s else None))
        print(nme, row)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('run')
    r.add_argument('--mode', default='original', choices=sorted(MODE_BITS))
    r.add_argument('--file', type=Path, required=True)
    r.add_argument('--rom', type=Path, default=ROM)
    r.add_argument('--out', type=Path, required=True)
    r.add_argument('--windows', type=Path, help='JSON list of frames to step with breakpoints armed')
    w = sub.add_parser('windows', help='frames to measure with breakpoints, from a plain ORIGINAL run')
    w.add_argument('out', type=Path)
    w.add_argument('--file', type=Path, required=True)
    w.add_argument('dest', type=Path)
    c = sub.add_parser('compare')
    c.add_argument('out', type=Path)
    a = ap.parse_args()
    if a.cmd == 'run':
        return run_mode(a)
    if a.cmd == 'windows':
        d = load(a.out, 'original')
        run = json.loads(a.file.read_text())
        ws = set()
        for st in run['stages']:
            idx = STAGE_NAMES.index(st['name'])
            f0 = next((f for f in range(max(1, st['start_frame'] - 400), st['start_frame'] + 1)
                       if d['stg'][f - 1] == idx and d['mas'][f - 1] == 0), 1)
            for c in (f0, st['start_frame']):
                ws.update(range(max(1, c - 2), c + 4))
        for f in events(d).values():
            ws.update(range(max(1, f - 3), min(len(d['cnt']), f + 3) + 1))
        a.dest.write_text(json.dumps(sorted(ws)))
        print(len(ws), 'window frames')
        return 0
    return compare(a)


if __name__ == '__main__':
    sys.exit(main())
