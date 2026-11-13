"""start-align: compare the event windows captured by capture.py (unmodified ROM A against build B).

    compare.py DIR_A DIR_B REPORT.json [PNGDIR]

Per event: frames compared, frames whole-picture identical, first non-black frame, brightness-full frame,
differing frame ranges; per differing frame the region of difference (rows, columns) and the best shift
(dx, dy) of B's picture that makes A's differing pixels match (|dx|,|dy| <= 16), with the residual.
"""
import json, sys
from pathlib import Path
import numpy as np
from capture import EVENTS, PRE  # noqa: E402
from PIL import Image

R = 16


def pack(a):
    return (a[:, :, 0].astype(np.int32) << 16) | (a[:, :, 1].astype(np.int32) << 8) | a[:, :, 2]


def best_shift(A, B, D):
    """Shift (dx, dy) of B (content moved right/down) maximizing equality with A on mask D."""
    h, w = A.shape
    sc = {}
    ys, xs = np.nonzero(D)
    n = len(ys)
    if n == 0:
        return (0, 0), 0, 0, 1
    # restrict to the bounding box of D for speed
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    Ab = A[y0:y1, x0:x1]; Db = D[y0:y1, x0:x1]
    Bp = np.pad(B, R, mode='edge')
    for dy in range(-R, R + 1):
        for dx in range(-R, R + 1):
            # B'(x, y) = B(x - dx, y - dy)
            sub = Bp[R + y0 - dy:R + y1 - dy, R + x0 - dx:R + x1 - dx]
            sc[(dx, dy)] = int(((sub == Ab) & Db).sum())
    best = max(sc.items(), key=lambda kv: (kv[1], -abs(kv[0][0]) - abs(kv[0][1])))
    top = best[1]
    near = [k for k, v in sc.items() if v >= top - max(1, n // 200)]
    return best[0], top, n - top, len(near)


def runs(x):
    r = []
    for v in x:
        if r and v == r[-1][1] + 1:
            r[-1][1] = v
        else:
            r.append([v, v])
    return [a if a == b else f'{a}-{b}' for a, b in r]


def main():
    da, db, rep = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    png = Path(sys.argv[4]) if len(sys.argv) > 4 else None
    out = {}
    for ev in EVENTS:
        a = np.load(da / f'ev-{ev}.npz'); b = np.load(db / f'ev-{ev}.npz')
        ma, mb = a['meta'], b['meta']
        frames = [int(x) for x in ma[:, 0]]
        info = dict(frame=ev, stage=int(mb[0, 7]), area=int(mb[-1, 8]), nframes=len(frames))
        bright = []
        diff = []
        shapes = []
        for f in frames:
            A, B = a[f'img{f}'], b[f'img{f}']
            bright.append(int(A.astype(np.int64).sum()))
            if A.shape != B.shape:
                diff.append(f); shapes.append(f); continue
            if not np.array_equal(A, B):
                diff.append(f)
        nz = [f for f, s in zip(frames, bright) if s > 0]
        info['first_nonblack'] = nz[0] if nz else None
        mx = max(bright)
        info['full_bright'] = next((f for f, s in zip(frames, bright) if s >= 0.99 * mx), None)
        info['n_diff'] = len(diff)
        info['diff_runs'] = runs(diff)
        info['shape_mismatch'] = runs(shapes)
        # first-visible / first-full-bright frame comparison
        info['first_nonblack_equal'] = info['first_nonblack'] not in diff if nz else None
        info['full_bright_equal'] = info['full_bright'] not in diff
        # camera / scroll registers per frame: differences
        cam_diff = [int(x) for x, y in zip(ma[:, 0], (ma[:, 1:6] != mb[:, 1:6]).any(axis=1)) if y]
        info['cam_scroll_diff_runs'] = runs(cam_diff)
        info['cam_at_entry'] = int(ma[PRE_IDX(frames, ev), 1])
        info['reg_first_visible'] = {'A': ma[frames.index(nz[0]), 1:7].tolist(), 'B': mb[frames.index(nz[0]), 1:7].tolist()} if nz else None
        # region + shift on representative differing frames
        reps = []
        dd = [f for f in diff if f not in shapes]
        if dd:
            pick = sorted(set([dd[0], dd[-1]] + [f for f in dd if f >= (info['full_bright'] or 0)][:2] + dd[::max(1, len(dd) // 8)]))
            for f in pick:
                A, B = a[f'img{f}'], b[f'img{f}']
                D = (A != B).any(axis=2)
                ys, xs = np.nonzero(D)
                PA, PB = pack(A), pack(B)
                (dx, dy), match, resid, nnear = best_shift(PA, PB, D)
                reps.append(dict(frame=f, npix=int(D.sum()), rows=[int(ys.min()), int(ys.max())], cols=[int(xs.min()), int(xs.max())],
                                 shift=[dx, dy], matched=match, residual=resid, ambiguous_shifts=nnear))
        info['reps'] = reps
        out[ev] = info
        if dd and png:
            png.mkdir(parents=True, exist_ok=True)
            for tag, f in (('first', dd[0]), ('bright', next((x for x in dd if x >= (info['full_bright'] or 0)), dd[-1]))):
                if tag == 'bright' and f == dd[0]:
                    continue
                A, B = a[f'img{f}'], b[f'img{f}']
                D = (A != B).any(axis=2)
                dimg = np.where(D[:, :, None], np.array([255, 0, 255], np.uint8), (A // 3)).astype(np.uint8)
                sep = np.full((A.shape[0], 4, 3), 255, np.uint8)
                Image.fromarray(np.hstack([A, sep, B, sep, dimg])).save(png / f'ev{ev}-s{info["stage"]}a{info["area"]}-{tag}-f{f}.png')
        print(ev, info['stage'], info['area'], 'ndiff', len(diff), '/', len(frames), info['diff_runs'][:6], flush=True)
    Path(rep).write_text(json.dumps(out, indent=1))


def PRE_IDX(frames, ev):
    return frames.index(ev) if ev in frames else 0


if __name__ == '__main__':
    main()
