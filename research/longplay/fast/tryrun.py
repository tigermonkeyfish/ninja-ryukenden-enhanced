#!/usr/bin/env python3
"""Try a Level Select comparison run from a played-in stage start (diagnostic).

    tryrun.py STATE RUN.json [--offsets 0-6]
Loads STATE (the longplay at the stage's first gameplay frame), idles k frames,
plays the run's segments and reports how far it gets: frames until it ends the
stage (stage byte changes, master flags, or boss health back to 0), or where
it was lost (death, area went back) and the furthest area/x reached.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fastemu import Fast  # noqa: E402


def trial(f, state, segs, k):
    f.load(state)
    i0 = f.info()
    f.step(k, 0) if k else None
    fr, boss_seen, best = k, False, (0, 0)
    for n, b in segs:
        for _ in range(n):
            f.step(1, b)
            fr += 1
            i = f.info()
            boss_seen |= i['boss'] > 0
            best = max(best, (i['area'], i['x']))
            if i['stage'] != i0['stage'] or i['master'] != 0 or (boss_seen and i['boss'] == 0):
                return 'finished', fr, i, best
            if i['health'] == 0 or i['lives'] < i0['lives']:
                return 'died', fr, i, best
    return 'ran out', fr, f.info(), best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('state')
    ap.add_argument('run', type=Path)
    ap.add_argument('--offsets', default='0-6')
    a = ap.parse_args()
    lo, hi = map(int, a.offsets.split('-'))
    segs = json.loads(a.run.read_text())['segments']
    f = Fast()
    for k in range(lo, hi + 1):
        print(k, *trial(f, Path(a.state).read_bytes(), segs, k), flush=True)


if __name__ == '__main__':
    main()
