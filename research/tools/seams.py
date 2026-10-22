#!/usr/bin/env python3
"""Seam detection in Enhanced textures.

A join is a texture position u where the adjacent column pair (E[u], E[u+1])
never occurs side by side anywhere in the same native row. A join flagged in
several rows at once forms a vertical seam. For each seam the number of
samples in which it was actually on screen (inside background-changed cells)
is counted, and a 4x crop of the Enhanced texture around it is written next to
the native backdrop for visual review.
"""
import json
import sys
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import stitch  # noqa: E402
from analyze import R, ROWS  # noqa: E402
from compose import agreement, native_offsets, pano_from  # noqa: E402
from core import png_encode  # noqa: E402

OUT = R / 'report' / 'seams'


def job(arg):
    stage, sub = arg
    data = stitch.collect(stage, sub, ('fwd', 'rev', 'entry', 'static'))
    rows = [r for r in range(ROWS) if any(any(d['flags'][r]) for d in data)]
    if not rows:
        return stage, sub, None
    no = native_offsets(data, rows)
    keep = [k for k, o in enumerate(no) if o is not None]
    nd, noo = [data[k] for k in keep], [no[k] for k in keep]
    epanos, npanos, models = {}, {}, {}
    for r in rows:
        _, nc = agreement(nd, 'orig', r, noo)
        m1 = [d['camera'] // 8 for d in data]
        a1, c1 = agreement(data, 'enh', r, m1)
        a0, c0 = agreement(data, 'enh', r, [0] * len(data))
        ec, models[r] = (c1, m1) if (a1 or 0) >= (a0 or 0) else (c0, [0] * len(data))
        npanos[r] = pano_from(nc)
        epanos[r] = pano_from(ec)
    lo = min(epanos[r][1] for r in rows if epanos[r][0])
    hi = max(epanos[r][1] + len(epanos[r][0]) for r in rows if epanos[r][0])
    fails = defaultdict(list)
    for r in rows:
        pn, _ = npanos[r]
        pe, elo = epanos[r]
        pairs = {(pn[v], pn[v + 1]) for v in range(len(pn) - 1)
                 if pn[v] is not None and pn[v + 1] is not None}
        for i in range(len(pe) - 1):
            a, b = pe[i], pe[i + 1]
            if a is None or b is None:
                continue
            if (a, b) not in pairs:
                fails[elo + i].append(r)
    # cluster
    seams = []
    for u in sorted(fails):
        rs = fails[u]
        if len(rs) < 2:
            continue
        if seams and u - seams[-1]['u1'] <= 2:
            seams[-1]['u1'] = u
            seams[-1]['rows'] = sorted(set(seams[-1]['rows']) | set(rs))
        else:
            seams.append({'u0': u, 'u1': u, 'rows': sorted(rs)})
    # on-screen visibility (Enhanced offset model per row)
    for s in seams:
        vis = []
        for k, d in enumerate(data):
            shown = 0
            for r in s['rows']:
                x = s['u0'] - models[r][k]
                if 0 <= x < 255 and d['flags'][r][x] and d['flags'][r][x + 1]:
                    shown += 1
            if shown >= 2:
                vis.append(d['name'])
        s['visible_samples'] = len(vis)
        s['example'] = vis[len(vis) // 2] if vis else None
    OUT.mkdir(parents=True, exist_ok=True)
    for n, s in enumerate(seams):
        if not s['visible_samples']:
            continue
        r0, r1 = max(min(s['rows']) - 2, rows[0]), min(max(s['rows']) + 2, rows[-1])
        img = []
        for r in range(r0, r1 + 1):
            if r not in epanos:
                continue
            pe, elo = epanos[r]
            for y in range(8):
                line = []
                for u in range(s['u0'] - 40, s['u1'] + 41):
                    i = u - elo
                    c = pe[i] if 0 <= i < len(pe) else None
                    p = c[y] if c is not None else (50, 50, 50)
                    if u == s['u0'] + 1 and y < 2 and r == r0:
                        p = (255, 0, 0)
                    line.append(p)
                img.append(line)
        big = []
        for line in img:
            l2 = [p for p in line for _ in range(4)]
            big.extend([l2] * 4)
        name = f'{stage}-a{sub}-seam{n}-u{s["u0"]}.png'
        (OUT / name).write_bytes(png_encode(big))
        s['image'] = name
    return stage, sub, {'seams': seams, 'texture_span': [lo, hi]}


if __name__ == '__main__':
    jobs = []
    for d in sorted((R / 'orig').iterdir()):
        if (d / 'run.json').exists() and (len(sys.argv) == 1 or d.name in sys.argv[1:]):
            for a in json.loads((d / 'run.json').read_text())['areas']:
                jobs.append((d.name, a['subarea']))
    results = {}
    with Pool(8) as pool:
        for stage, sub, res in pool.imap_unordered(job, jobs):
            if res is None:
                continue
            results[f'{stage}/a{sub}'] = res
            vis = [s for s in res['seams'] if s['visible_samples']]
            print(stage, sub, 'seams', len(res['seams']), 'visible', len(vis),
                  [(s['u0'], s['u1'], len(s['rows']), s['visible_samples']) for s in vis][:12], flush=True)
    (R / 'report' / 'seams.json').write_text(json.dumps(results, indent=1) + '\n')
