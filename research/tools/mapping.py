#!/usr/bin/env python3
"""Map each Enhanced panorama column to the native panorama column it reproduces."""
import sys, json
from collections import defaultdict, Counter
import stitch
from analyze import K, ROWS

def column_map(pe, pn, k=8):
    """For each E column u, the set of native columns v with E[u:u+k] == N[v:v+k]."""
    hn = [hash(c) if c is not None else None for c in pn]
    idx = defaultdict(list)
    for v in range(len(pn) - k + 1):
        w = hn[v:v + k]
        if None not in w: idx[hash(tuple(w))].append(v)
    he = [hash(c) if c is not None else None for c in pe]
    cand = [set() for _ in pe]
    covered = [False] * len(pe)
    for u in range(len(pe) - k + 1):
        w = he[u:u + k]
        if None in w: continue
        for v in idx.get(hash(tuple(w)), ()):
            for j in range(k):
                cand[u + j].add(v + j)
                covered[u + j] = True
    return cand, covered

def segments(pe, pn, k=8):
    cand, covered = column_map(pe, pn, k)
    segs = []  # (u0, u1, delta or None)
    u = 0
    n = len(pe)
    while u < n:
        if pe[u] is None:
            u0 = u
            while u < n and pe[u] is None: u += 1
            segs.append((u0, u, 'hole')); continue
        if not cand[u]:
            u0 = u
            while u < n and pe[u] is not None and not cand[u]: u += 1
            segs.append((u0, u, 'new')); continue
        # choose delta that extends furthest
        best = None
        for v in cand[u]:
            d = v - u; e = u
            while e < n and (e + d) in cand[e]: e += 1
            if best is None or e > best[1]: best = (d, e)
        segs.append((u, best[1], best[0]))
        u = best[1]
    return segs

if __name__ == '__main__':
    stage, sub, kinds = sys.argv[1], int(sys.argv[2]), tuple(sys.argv[3].split(','))
    rows = [int(r) for r in sys.argv[4].split(',')] if len(sys.argv) > 4 else range(ROWS)
    data = stitch.collect(stage, sub, kinds)
    for r in rows:
        on = stitch.stitch(data, 'orig', r, max_shift=40)
        oe = stitch.stitch(data, 'enh', r, max_shift=40)
        pn, pe = on[1], oe[1]
        if not pe: continue
        segs = segments(pe, pn)
        new = sum(b - a for a, b, d in segs if d == 'new')
        desc = ' '.join(f'E[{a}:{b})' + ('=NEW' if d == 'new' else '=hole' if d == 'hole' else f'=N[{a+d}:{b+d})') for a, b, d in segs)
        print(f'row {r:2} Elen {len(pe)} Nlen {len(pn)} new {new}: {desc}')
