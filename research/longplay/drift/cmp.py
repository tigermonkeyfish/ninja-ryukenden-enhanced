"""Side-by-side per-update view of two or more watch runs around a frame.
Usage: cmp.py FRAME_FROM FRAME_TO TAG...  (rows = updates started in that frame range of the first tag,
aligned by update count since the entered state)"""
import sys
import numpy as np
from upd import updates, FRAME
a, b = int(sys.argv[1]), int(sys.argv[2])
tags = sys.argv[3:]
U = {t: updates(t) for t in tags}
ref = U[tags[0]]
idx = np.nonzero((ref['frame'] >= a) & (ref['frame'] <= b))[0]
print('k | ' + ' | '.join(f'{t}: frame, start-phase, dur, margin, nvbl, music' for t in tags))
for k in idx:
    row = [str(k)]
    for t in tags:
        u = U[t]
        if k >= len(u['start']):
            row.append('-'); continue
        s = u['start'][k]
        mus = u['ev']['music']['clk'].astype(np.int64)
        m = mus[(mus >= s) & (mus < u['end'][k])]
        ph = (s - u['vprev'][k])
        row.append(f"{u['frame'][k]}, +{ph}, {u['dur'][k]}, {u['margin'][k]}, {u['nvbl'][k]}, {list(m - s) if len(m) else ''}")
    print(' | '.join(row))
