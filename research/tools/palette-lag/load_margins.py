#!/usr/bin/env python3
"""Load margins from `palette_lag.py loadtime` logs: per Level Select stage
load, ORIGINAL's sound-command and first-update margin to the next vblank,
and each mode's delay (and whether it lands after another vblank).
usage: load_margins.py LOG [LOG ...]"""
import re
import sys

P = 358995
for path in sys.argv[1:]:
    rows = {}
    for line in open(path):
        m = re.match(r'stage\s+(\d+) (\S+(?: dmg)?)\s+(.*)', line)
        if not m:
            continue
        cells = re.findall(r'([sf]) vblank (\d+) \+(\d+)(?: \(([+-]\d+)\))?', m.group(3))
        rows.setdefault(int(m.group(1)), {})[m.group(2)] = [(k, int(v), int(i), int(d or 0)) for k, v, i, d in cells]
    print(path)
    worst = {}
    flips = []
    for stage, modes in sorted(rows.items()):
        o = modes['original']
        margins = [P - i for k, v, i, d in o]
        line = f'  stage {stage:2d}: ORIGINAL margins ' + ', '.join(f'{k} {P - i}' for k, v, i, d in o)
        for mode, cells in modes.items():
            if mode == 'original':
                continue
            ds = [d for k, v, i, d in cells]
            worst[mode] = max(worst.get(mode, 0), max(ds) if ds else 0)
            for (k, v, i, d), (_, vo, io, _) in zip(cells, o):
                if v != vo:
                    flips.append((stage, mode, k, d))
        print(line)
    print('  worst delay per mode:', worst)
    print('  commands or first updates in another vblank than ORIGINAL:', flips or 'none')
