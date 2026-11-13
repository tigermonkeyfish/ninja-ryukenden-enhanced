"""start-align: per-event table rows (JSON) from capture windows: visible-start frame, diffs from there, shift analysis."""
import json
import numpy as np
from pathlib import Path
from compare import pack, best_shift, runs
from capture import EVENTS
da, db = Path('/workspace/build/start-align/cap-unmod'), Path('/workspace/build/start-align/cap-new')
rows = {}
for ev in EVENTS:
    a = np.load(da / f'ev-{ev}.npz'); b = np.load(db / f'ev-{ev}.npz')
    m = a['meta']; mb = b['meta']; fr = [int(x) for x in m[:, 0]]
    s = np.array([a[f'img{f}'].astype(np.int64).sum() for f in fr]); mx = s.max()
    dark = [i for i, v in enumerate(s) if v < 0.5 * mx]
    # loads: first non-black frame of the load (window starts in the old/black part); area changes: the window
    # starts in the old area, then a short dark run (the transition), the new area's first frame follows it
    kind = 'area' if (dark and len(dark) < 20) else 'load'
    if kind == 'area':
        j = dark[0]
        while j < len(fr) and s[j] < 0.5 * mx: j += 1
        nb = j
    else:
        nb = next(i for i, v in enumerate(s) if v > 0)
    diff = [i for i in range(len(fr)) if not np.array_equal(a[f'img{fr[i]}'], b[f'img{fr[i]}'])]
    post = [i for i in diff if i >= nb]
    pre = [i for i in diff if i < nb]
    # frames to full brightness (>=99% of max)
    fb = next((i for i, v in enumerate(s) if v >= 0.99 * s[nb:].max() and i >= nb), nb)
    r = dict(event=ev, kind=kind, first_visible=fr[nb], full_bright=fr[fb], cam=int(m[nb, 1]), area_after=int(m[nb, 8]), stage=int(m[nb, 7]),
             n_pre_diff=len(pre), pre_runs=runs([fr[i] for i in pre]), n_post_diff=len(post), post_runs=runs([fr[i] for i in post]),
             n_frames_from_visible=len(fr) - nb, regs_equal=bool((m[:, 1:7] == mb[:, 1:7]).all()),
             regs_visible=m[nb, 1:7].tolist(), regs_visible_b=mb[nb, 1:7].tolist())
    # window check: first visible + 8 frames after full bright covered?
    r['covers_fb_plus8'] = bool(fb + 8 < len(fr))
    smp = []
    for i in sorted(set(post[:3] + post[-1:] + [p for p in post if p in (nb, nb + 1, nb + 8, fb, fb + 8)])):
        A, B = a[f'img{fr[i]}'], b[f'img{fr[i]}']
        D = (A != B).any(axis=2); ys, xs = np.nonzero(D)
        (dx, dy), mt, rs, nn = best_shift(pack(A), pack(B), D)
        smp.append(dict(frame=fr[i], npix=int(D.sum()), bbox=[int(ys.min()), int(ys.max()), int(xs.min()), int(xs.max())], shift=[dx, dy], resid_frac=round(rs / D.sum(), 3), amb=nn))
    r['post_samples'] = smp
    rows[ev] = r
    from PIL import Image
    Path('/workspace/build/start-align/mismatch').mkdir(exist_ok=True)
    for tag, idx in (('post-first', post[:1]), ('post-vis8', [p for p in post if p >= nb + 8][:1])):
        for i in idx:
            A, B = a[f'img{fr[i]}'], b[f'img{fr[i]}']
            D = (A != B).any(axis=2)
            dimg = np.where(D[:, :, None], np.array([255, 0, 255], np.uint8), A // 3).astype(np.uint8)
            sep = np.full((A.shape[0], 4, 3), 255, np.uint8)
            Image.fromarray(np.hstack([A, sep, B, sep, dimg])).save(f'/workspace/build/start-align/mismatch/ev{ev}-{tag}-f{fr[i]}.png')
    print(ev, kind, 'vis', fr[nb], 'fb', fr[fb], 'pre', len(pre), 'post', len(post), r['post_runs'][:4], 'regs=', r['regs_equal'], flush=True)
Path('/workspace/build/start-align/rows.json').write_text(json.dumps(rows, indent=1))
