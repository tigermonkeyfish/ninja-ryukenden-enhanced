#!/usr/bin/env python3
"""Horizontal tears: adjacent rows whose stacked columns never occur together natively."""
import json, sys
from multiprocessing import Pool
import stitch
from analyze import R, ROWS
from compose import agreement, native_offsets, pano_from

def job(arg):
    stage, sub = arg
    data = stitch.collect(stage, sub, ('fwd', 'rev', 'entry', 'static'))
    rows = [r for r in range(ROWS) if any(any(d['flags'][r]) for d in data)]
    if not rows: return stage, sub, None
    no = native_offsets(data, rows)
    keep = [k for k, o in enumerate(no) if o is not None]
    nd, noo = [data[k] for k in keep], [no[k] for k in keep]
    nat, enh, models = {}, {}, {}
    for r in rows:
        nat[r] = agreement(nd, 'orig', r, noo)[1]
        m1 = [d['camera'] // 8 for d in data]
        a1, c1 = agreement(data, 'enh', r, m1); a0, c0 = agreement(data, 'enh', r, [0] * len(data))
        enh[r], models[r] = (c1, m1) if (a1 or 0) >= (a0 or 0) else (c0, [0] * len(data))
    out = []
    for r in rows:
        s = r + 1
        if s not in nat or models[r] != models[s]: continue
        npairs = {(nat[r][u].most_common(1)[0][0], nat[s][u].most_common(1)[0][0]) for u in nat[r] if u in nat[s]}
        bad = []
        for u in sorted(set(enh[r]) & set(enh[s])):
            a, b = enh[r][u].most_common(1)[0][0], enh[s][u].most_common(1)[0][0]
            if (a, b) not in npairs:
                # only count if the boundary pixels actually differ from any native boundary with same top
                bad.append(u)
        spans = []
        for u in bad:
            if spans and u - spans[-1][1] <= 1: spans[-1][1] = u
            else: spans.append([u, u])
        tot = len(set(enh[r]) & set(enh[s]))
        if bad: out.append({'rows': [r, s], 'tear_columns': len(bad), 'columns_compared': tot, 'spans': spans[:20]})
    return stage, sub, out

if __name__ == '__main__':
    jobs = []
    for d in sorted((R/'orig').iterdir()):
        if (d/'run.json').exists() and (len(sys.argv) == 1 or d.name in sys.argv[1:]):
            for a in json.loads((d/'run.json').read_text())['areas']: jobs.append((d.name, a['subarea']))
    res = {}
    with Pool(8) as p:
        for stage, sub, out in p.imap_unordered(job, jobs):
            if out is None: continue
            res[f'{stage}/a{sub}'] = out
    for k in sorted(res):
        worst = sorted(res[k], key=lambda o: -o['tear_columns'] / max(o['columns_compared'], 1))[:4]
        print(k, [(o['rows'], o['tear_columns'], o['columns_compared']) for o in worst])
    (R/'report'/'vshear.json').write_text(json.dumps(res, indent=1))
