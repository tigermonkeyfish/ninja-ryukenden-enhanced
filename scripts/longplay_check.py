#!/usr/bin/env python3
"""Cold-start replay check of research/longplay/full.json (emulator evidence only).

One fresh headless Geargrafx session: power-on with the given mode's backup-RAM
image (status SETTINGS LOADED, menu never opened), the title left with Run
(longplay_lib.boot_to_first_update), then the whole recording replayed as one
continuous input list, no re-syncing. At each stage marker it checks that the
stage begins exactly there (one frame before: still the previous stage or its
transition; at the marker: the stage byte of that stage, area 0, gameplay), and
at the end that the ending is reached (the file's `end` record). Prints one line
per stage with the frame it starts and PASS/FAIL.

    LD_LIBRARY_PATH=/workspace/build/toolchain/sdl3/lib \
      python3 scripts/longplay_check.py --mode original
"""
import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comparison_video import STAGE_NAMES                                     # noqa: E402
from longplay_lib import EMULATOR, ROM, MODE_BITS, Game, boot_to_first_update  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def info(game):
    r = game.read(0, 0x1100)
    return {'master': r[0x240], 'm2': r[0x241], 'stage': r[0xe5f], 'area': r[0xe60],
            'x': r[0xe9e] | r[0xe9f] << 8, 'y': r[0xea0], 'health': r[0xead], 'lives': r[0xeaf],
            'boss': r[0x1035]}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--mode', default='original', choices=sorted(MODE_BITS))
    ap.add_argument('--file', type=Path, default=ROOT / 'research/longplay/full.json')
    ap.add_argument('--rom', type=Path, default=ROM)
    a = ap.parse_args()
    run = json.loads(a.file.read_text())
    segs = run['segments']
    total = sum(n for n, _ in segs)
    # frames at which to look: a window before each stage marker (stepped one
    # frame at a time, to find the first frame of that stage) and the marker
    WINDOW = 400
    checks = {}
    for s in run['stages']:
        for fr in range(max(0, s['start_frame'] - WINDOW), s['start_frame']):
            checks.setdefault(fr, []).append(('scan', s))
        checks.setdefault(s['start_frame'], []).append(('start', s))
    end = run.get('end')
    if end:
        checks.setdefault(end['frame'], []).append(('end', end))
    tail = run.get('tail')
    if tail:
        checks.setdefault(total, []).append(('end', {'frame': total, 'state': tail}))
    first = {}
    ok = True
    t0 = time.time()
    work = Path(tempfile.mkdtemp(prefix='longplay-check-', dir='/workspace/build/longplay'))
    with Game(EMULATOR, work) as game:
        status = boot_to_first_update(game, a.rom, a.mode, work / 'entered.state')
        print(f'mode {a.mode}: boot {status}', flush=True)
        frame = 0
        marks = sorted(checks)
        mi = 0

        def look():
            nonlocal mi, ok
            while mi < len(marks) and marks[mi] <= frame:
                if marks[mi] == frame:
                    cur = info(game)
                    for kind, s in checks[frame]:
                        here = 'name' in s and cur['stage'] == STAGE_NAMES.index(s['name']) and cur['master'] == 0
                        if kind == 'scan':
                            if here and s['name'] not in first:
                                first[s['name']] = frame
                        elif kind == 'start':
                            good = here and cur['area'] == 0
                            f0 = first.get(s['name'], frame)
                            print(f'{"PASS" if good else "FAIL"} {s["name"]:5s} gameplay from frame {f0:6d} '
                                  f'({(f0 + status["boot_frames"]) / 60:7.1f} s from power-on; marker {frame}) {cur}',
                                  flush=True)
                            ok &= good
                        else:
                            good = all(cur.get(k) == v for k, v in s['state'].items())
                            print(f'{"PASS" if good else "FAIL"} end reached at frame {frame}: {cur} '
                                  f'(expected {s["state"]})', flush=True)
                            ok &= good
                mi += 1

        look()
        for n, buttons in segs:
            game.press(set(buttons))
            while n > 0:
                step = min(n, 500)
                if mi < len(marks):
                    step = min(step, marks[mi] - frame)
                game.checked_step(step)
                frame += step
                n -= step
                look()
        last = info(game)
    print(f'replayed {total} frames (+{status["boot_frames"]} boot) in {time.time() - t0:.0f} s; final {last}')
    if not end:
        print('NOTE: the file has no end record yet (recording unfinished)')
    print('RESULT', 'PASS' if ok else 'FAIL')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
