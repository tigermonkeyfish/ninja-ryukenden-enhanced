#!/usr/bin/env python3
"""Missing/extra scenery check: colour content of the visible background per sample.

For each matched sample, histograms of decoded background pixels inside
tile-number-changed cells are compared (total variation distance, 0..1).
Parallax shifts change which part of the art is visible, so moderate values
are expected; large values flag scenes where one ROM shows content (e.g. a
mountain) that the other replaces with something else (e.g. flat sky).
"""
import json, sys
from collections import Counter
from multiprocessing import Pool
from analyze import R, ROWS, load, sample_rows

def job(stage):
    orun = json.loads((R/'orig'/stage/'run.json').read_text())['samples']
    erun = json.loads((R/'enh'/stage/'run.json').read_text())['samples']
    out = []
    for ro, re in zip(orun, erun):
        rc = ro['render_camera']
        so, se = sample_rows(load('orig', stage, ro), rc), sample_rows(load('enh', stage, re), rc)
        ho, he = Counter(), Counter()
        for cy in range(ROWS):
            co, cells, wo = so[cy]; ce, _, we = se[cy]
            for x in range(256):
                if wo[x] != we[x]:
                    for y in range(8):
                        ho[co[x][y]] += 1; he[ce[x][y]] += 1
        n = sum(ho.values())
        if n < 512:
            continue
        tv = 0.5 * sum(abs(ho[c] / n - he[c] / n) for c in set(ho) | set(he))
        # colours present (>=1% of pixels) in native but (almost) absent in Enhanced
        missing = sorted(((ho[c] / n, c) for c in ho if ho[c] / n >= 0.01 and he[c] / n < 0.1 * ho[c] / n), reverse=True)
        out.append({'name': ro['name'], 'camera': ro['camera'], 'subarea': ro['subarea'], 'pixels': n,
                    'tv': round(tv, 3), 'missing_colours': [[round(f, 3), list(c)] for f, c in missing[:5]],
                    'distinct_native': len([c for c in ho if ho[c] / n >= 0.005]),
                    'distinct_enh': len([c for c in he if he[c] / n >= 0.005])})
    return stage, out

if __name__ == '__main__':
    stages = sorted(p.name for p in (R/'orig').iterdir() if (p/'run.json').exists())
    allres = {}
    with Pool(8) as pool:
        for stage, out in pool.imap_unordered(job, stages):
            allres[stage] = out
            tvs = sorted(o['tv'] for o in out)
            worst = sorted(out, key=lambda o: -o['tv'])[:4]
            print(stage, 'samples', len(out), 'median tv', tvs[len(tvs)//2] if tvs else None,
                  'max', tvs[-1] if tvs else None, '| worst:', [(w['name'], w['tv'], w['distinct_native'], w['distinct_enh']) for w in worst], flush=True)
    (R/'report'/'content.json').write_text(json.dumps(allres, indent=1))
