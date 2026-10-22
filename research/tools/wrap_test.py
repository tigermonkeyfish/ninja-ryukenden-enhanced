"""Is each Enhanced row the native backdrop wrapped at period P (default 256)?"""
import json, sys
from multiprocessing import Pool
from collections import Counter, defaultdict
import stitch
from analyze import R, ROWS
from compose import native_offsets, agreement, pano_from

def job(arg):
    stage, sub = arg
    data = stitch.collect(stage, sub, ('fwd', 'rev', 'entry', 'static'))
    rows = [r for r in range(ROWS) if any(any(d['flags'][r]) for d in data)]
    if not rows: return stage, sub, None
    no = native_offsets(data, rows)
    keep = [k for k, o in enumerate(no) if o is not None]
    nd = [data[k] for k in keep]; noo = [no[k] for k in keep]
    out = {}
    for r in rows:
        _, nc = agreement(nd, 'orig', r, noo)
        e1 = agreement(data, 'enh', r, [d['camera'] // 8 for d in data])
        e0 = agreement(data, 'enh', r, [0] * len(data))
        ec = e1[1] if (e1[0] or 0) >= (e0[0] or 0) else e0[1]
        pn, nlo = pano_from(nc); pe, elo = pano_from(ec)
        known_e = [(u, c) for u, c in enumerate(pe) if c is not None]
        res = {}
        for P in (256, 200):
            best = None
            for d in range(P):
                a = t = 0
                for u, c in known_e:
                    v = (u + d) % P
                    if v < len(pn) and pn[v] is not None:
                        t += 1; a += pn[v] == c
                if t and (best is None or a / t > best[1]):
                    best = (d, a / t, t)
            res[P] = best
        out[r] = {'P256': round(res[256][1], 3) if res[256] else None, 'P200': round(res[200][1], 3) if res[200] else None,
                  'tested': res[256][2] if res[256] else 0}
    return stage, sub, out

if __name__ == '__main__':
    jobs = []
    for d in sorted((R/'orig').iterdir()):
        if (d/'run.json').exists():
            for a in json.loads((d/'run.json').read_text())['areas']: jobs.append((d.name, a['subarea']))
    allr = {}
    with Pool(8) as p:
        for stage, sub, out in p.imap_unordered(job, jobs):
            if out is None: continue
            allr[f'{stage}/a{sub}'] = out
    for k in sorted(allr):
        o = allr[k]
        s256 = [v['P256'] for v in o.values() if v['P256'] is not None]
        s200 = [v['P200'] for v in o.values() if v['P200'] is not None]
        print(k, 'rows', len(o), 'wrap256 min/median', min(s256), sorted(s256)[len(s256)//2], '| wrap200 min/median', min(s200), sorted(s200)[len(s200)//2],
              '| rows <0.97 @256:', [r for r, v in o.items() if (v['P256'] or 0) < 0.97])
    (R/'report'/'wrap-test.json').write_text(json.dumps(allr, indent=1))
