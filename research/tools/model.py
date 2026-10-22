#!/usr/bin/env python3
"""Test motion models: native static backdrop vs Enhanced offset = s*floor(C/8)."""
import sys, json
from collections import Counter, defaultdict
from multiprocessing import Pool
import stitch
from analyze import R, ROWS

def model_offsets(data, kind):
    if kind == 'static':
        return [0] * len(data)
    s = 1 if kind == 'pos8' else -1
    return [s * (d['camera'] // 8) for d in data]

def agreement(data, which, row, offs):
    cols = defaultdict(Counter)
    for k, d in enumerate(data):
        for x in range(256):
            if d['flags'][row][x]:
                cols[x + offs[k]][d[which][row][x]] += 1
    tot = sum(sum(c.values()) for c in cols.values())
    agree = sum(c.most_common(1)[0][1] for c in cols.values())
    return (agree / tot if tot else None), tot, cols

def job(arg):
    stage, sub = arg
    data = stitch.collect(stage, sub, ('fwd', 'rev'))
    out = {}
    for row in range(ROWS):
        if not any(any(d['flags'][row]) for d in data):
            continue
        res = {}
        for which in ('orig', 'enh'):
            best = None
            for kind in ('static', 'pos8', 'neg8'):
                a, tot, _ = agreement(data, which, row, model_offsets(data, kind))
                res.setdefault(which, {})[kind] = round(a, 4) if a is not None else None
        res['visible_px'] = tot
        out[row] = res
    return stage, sub, out

if __name__ == '__main__':
    jobs = []
    for d in sorted((R / 'orig').iterdir()):
        if (d / 'run.json').exists():
            for a in json.loads((d / 'run.json').read_text())['areas']:
                jobs.append((d.name, a['subarea']))
    results = {}
    with Pool(8) as pool:
        for stage, sub, out in pool.imap_unordered(job, jobs):
            results[f'{stage}/a{sub}'] = out
            print(stage, sub, flush=True)
            for row, r in out.items():
                print(f'   row {row:2} px {r["visible_px"]:6}  orig static {r["orig"]["static"]} pos8 {r["orig"]["pos8"]} neg8 {r["orig"]["neg8"]} | enh static {r["enh"]["static"]} pos8 {r["enh"]["pos8"]} neg8 {r["enh"]["neg8"]}', flush=True)
    (R / 'report' / 'motion-models.json').write_text(json.dumps(results, indent=1))
