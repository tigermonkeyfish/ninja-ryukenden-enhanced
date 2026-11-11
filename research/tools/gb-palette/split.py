"""HUD-split timing: the CPU entry of the scanline interrupt (lines after the
vblank interrupt; the handler writes BYR a fixed time later) per vblank,
compared between two sets of timing_trace.py outputs.
usage: split.py DIR TAG_A TAG_B"""
import json
import sys
from pathlib import Path

from gbtools import RUN_NAMES

d, a, b = sys.argv[1:4]
for name in RUN_NAMES:
    A = json.loads((Path(d) / f'{a}-{name}.json').read_text())['vblanks']
    B = json.loads((Path(d) / f'{b}-{name}.json').read_text())['vblanks']
    pa = [w['cpu'] for w in A if w['cpu']]
    pb = [w['cpu'] for w in B if w['cpu']]
    diff = [i for i, (x, y) in enumerate(zip(A, B)) if x['cpu'] != y['cpu']]
    over = lambda p: sum(1 for c in p if c > 70.84)
    worst = max(((y['cpu'] or 0) - (x['cpu'] or 0), i) for i, (x, y) in enumerate(zip(A, B)))
    print(f'{name}: max {max(pa):.3f} / {max(pb):.3f}; entries after 70.84: {over(pa)} / {over(pb)}; '
          f'vblanks that differ: {len(diff)}; largest later entry in B: {worst[0]:+.3f} at {worst[1]}')
