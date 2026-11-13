"""start-pos: the start window of every event, defined by the camera (capture.py output, A = unmodified).

    startwin.py DIR_A DIR_B OUT.json

Per event: the dark run (from EV-1 on, the frames whose playfield, rows 60-229, has under 10 percent
non-black pixels: a load's black and an area change's transition; sprites and the HUD may show), the
first visible frame (the first frame after it; for 1-1, the first non-black frame), the camera then,
the first frame the camera ($220F) differs from it ("first move") and the first frame the render
camera $2E4B/$2E4C changes; start window = first visible .. first move - 1 (to the end of the capture
when the camera does not move). Reports whether the dark run and every start-window frame are
pixel-identical, whether the frames before the dark run (the old area) are, and the first differing
frame at or after first visible.
"""
import json, sys
from pathlib import Path
import numpy as np
from capture import EVENTS

da, db, outp = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
res = {}
for ev in EVENTS:
    a, b = np.load(da / f'ev-{ev}.npz'), np.load(db / f'ev-{ev}.npz')
    ma, mb = a['meta'], b['meta']
    frames = [int(x) for x in ma[:, 0]]
    dark = [float((a[f'img{f}'][60:230].max(axis=2) > 0).mean()) < 0.10 for f in frames]
    if ev == 1:
        vis = next(i for i, f in enumerate(frames) if a[f'img{f}'].any())
        d0 = 0
    else:
        i0 = max(0, frames.index(ev) - 1)
        d = next((i for i in range(i0, len(frames)) if dark[i]), None)
        d0 = d
        vis = next((i for i in range(d, len(frames)) if not dark[i]), None) if d is not None else None
    if vis is None:
        res[ev] = {'event': ev, 'error': 'no visible frame'}
        continue
    c0 = int(ma[vis][1])
    mv = next((i for i in range(vis, len(frames)) if ma[i][1] != c0), None)
    r0 = tuple(ma[vis][2:4])
    rmv = next((i for i in range(vis, len(frames)) if tuple(ma[i][2:4]) != r0), None)
    end = mv if mv is not None else len(frames)
    same = [np.array_equal(a[f'img{f}'], b[f'img{f}']) for f in frames]
    ram_same = bool((ma[:, 1:9] == mb[:, 1:9]).all())
    first_diff = next((frames[i] for i in range(vis, len(frames)) if not same[i]), None)
    res[ev] = {'event': ev, 'stage': int(ma[vis][7]), 'area': int(ma[vis][8]), 'first_visible': frames[vis],
               'camera': c0, 'first_move': frames[mv] if mv is not None else None,
               'first_render_move': frames[rmv] if rmv is not None else None,
               'window_frames': end - vis, 'window_identical': all(same[vis:end]),
               'dark_from': frames[d0], 'dark_identical': all(same[d0:vis]),
               'old_area_identical': all(same[:d0]), 'first_diff_from_visible': first_diff,
               'ram_equal': ram_same}
    print(json.dumps(res[ev]), flush=True)
Path(outp).write_text(json.dumps(res, indent=1))
