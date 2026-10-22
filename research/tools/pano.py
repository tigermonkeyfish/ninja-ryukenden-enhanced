#!/usr/bin/env python3
"""Render stitched native vs Enhanced background panoramas for one stage area."""
import sys, json
from pathlib import Path
from collections import Counter
import stitch
from analyze import K, ROWS
from core import png_encode

HOLE = None
def native_windows(pano):
    s = set()
    hs = [hash(c) if c is not HOLE else None for c in pano]
    for i in range(len(pano) - K + 1):
        w = hs[i:i + K]
        if None not in w: s.add(hash(tuple(w)))
    return s

def render(stage, sub, kinds, out, scale=2, rows=None):
    data = stitch.collect(stage, sub, kinds)
    rows = rows or [r for r in range(ROWS) if sum(sum(s['flags'][r]) for s in data) > 0]
    panos = {'orig': {}, 'enh': {}}
    info = {}
    for which in ('orig', 'enh'):
        for r in rows:
            offs, pano, steps, lo = stitch.stitch(data, which, r, max_shift=40)
            panos[which][r] = (pano, lo, offs)
    # Common origin: align rows by their own lo so each row starts at its first seen column.
    rowinfo = {}
    img = []
    W = max(len(panos[w][r][0]) for w in panos for r in rows)
    sep = [(255, 255, 255)] * W
    for which in ('orig', 'enh'):
        for r in rows:
            pano, lo, offs = panos[which][r]
            nat = native_windows(panos['orig'][r][0])
            bad = [False] * len(pano)
            hs = [hash(c) if c is not HOLE else None for c in pano]
            unmatched = 0; tot = 0
            for i in range(len(pano) - K + 1):
                w = hs[i:i + K]
                if None in w: continue
                tot += 1
                if hash(tuple(w)) not in nat:
                    unmatched += 1
                    for j in range(i, i + K): bad[j] = True
            rowinfo[(which, r)] = {'len': len(pano), 'holes': sum(1 for c in pano if c is HOLE),
                                   'period': stitch.period(pano) if pano else None,
                                   'unmatched_windows': unmatched, 'windows': tot,
                                   'offset_total': offs[-1]}
            for y in range(8):
                line = []
                for u in range(W):
                    c = pano[u] if u < len(pano) else HOLE
                    if c is HOLE:
                        line.append((70, 70, 70) if (u // 4 + y // 4) % 2 else (40, 40, 40))
                    else:
                        p = c[y]
                        if which == 'enh' and bad[u] and y in (0, 7):
                            p = (255, 0, 255)
                        line.append(p)
                img.append(line)
        img.extend([sep] * 2)
    big = []
    for line in img:
        l2 = [p for p in line for _ in range(scale)]
        big.extend([l2] * scale)
    Path(out).write_bytes(png_encode(big))
    return rowinfo

if __name__ == '__main__':
    stage, sub = sys.argv[1], int(sys.argv[2])
    kinds = tuple(sys.argv[3].split(','))
    info = render(stage, sub, kinds, sys.argv[4])
    for k, v in sorted(info.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        print(k, v)
