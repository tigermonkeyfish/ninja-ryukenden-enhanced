"""start-align: per differing event, the frame the area byte changes and shift analysis at frames around it."""
import json, sys
import numpy as np
from pathlib import Path
from compare import pack, best_shift, runs
from capture import EVENTS
da, db = Path('/workspace/build/start-align/cap-unmod'), Path('/workspace/build/start-align/cap-new')
res = {}
for ev in EVENTS:
    a = np.load(da / f'ev-{ev}.npz'); b = np.load(db / f'ev-{ev}.npz')
    m = a['meta']; fr = m[:, 0].tolist()
    ar = m[:, 8]; st = m[:, 7]
    ch = [int(fr[i]) for i in range(1, len(fr)) if ar[i] != ar[i-1] or st[i] != st[i-1]]
    diff = [f for f in fr if not np.array_equal(a[f'img{f}'], b[f'img{f}'])]
    r = dict(event=ev, flips=ch, ndiff=len(diff), diff_runs=runs(diff))
    if diff:
        # shift analysis, only for differing frames; summarize by distinct (dx,dy) with residual share
        out = []
        for f in diff[::max(1, len(diff)//10)] + [diff[0]]:
            A, B = a[f'img{f}'], b[f'img{f}']
            D = (A != B).any(axis=2)
            (dx, dy), mt, rs, nn = best_shift(pack(A), pack(B), D)
            ys, xs = np.nonzero(D)
            out.append((f, int(D.sum()), (int(ys.min()), int(ys.max()), int(xs.min()), int(xs.max())), (dx, dy), round(rs / D.sum(), 2)))
        r['samples'] = out
    res[ev] = r
    print(ev, 'flip', ch, 'ndiff', len(diff), runs(diff)[:5])
Path('/workspace/build/start-align/flip.json').write_text(json.dumps(res, default=str, indent=1))
