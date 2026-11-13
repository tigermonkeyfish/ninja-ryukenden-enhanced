"""start-pos: compare respawn.py runs (unmodified ROM A against build B), per scenario.

    respawn_cmp.py DIR_A DIR_B [PNGDIR]

Per scenario: whether the RAM sample is equal on every frame, the respawn's dark run (the last run
of frames whose playfield, rows 60-229, has under 10 percent non-black pixels; HUD and sprites may
show) and first visible frame (the frame after it), the first frame the camera changes after it,
whether the dark run and the start window (first visible .. camera change - 1) are pixel-identical,
the frames that differ, and the best backdrop shift (startalign compare.best_shift) per differing
frame from first visible (first 12 printed). PNGs (A | B | difference) of the first differing frame.
"""
import sys
from pathlib import Path
import numpy as np
from compare import best_shift

A_DIR, B_DIR = Path(sys.argv[1]), Path(sys.argv[2])
PNG = Path(sys.argv[3]) if len(sys.argv) > 3 else None


def lum(p):
    return ((p >> 16) & 255) + ((p >> 8) & 255) + (p & 255)


for fa in sorted(A_DIR.glob('*.npz')):
    A, B = np.load(fa), np.load(B_DIR / fa.name)
    ma, mb, ia, ib = A['meta'], B['meta'], A['imgs'], B['imgs']
    ram_eq = bool((ma == mb).all())
    dark = [float((ia[i][60:230] != 0).mean()) < 0.10 for i in range(len(ia))]
    # the respawn: the last dark run in the window
    runs, s = [], None
    for i, d in enumerate(dark):
        if d and s is None:
            s = i
        if not d and s is not None:
            runs.append((s, i - 1)); s = None
    vis = runs[-1][1] + 1 if runs else 0
    cam0 = ma[vis][1] if vis < len(ma) else None
    move = next((i for i in range(vis, len(ma)) if ma[i][1] != cam0), None)
    diff = [i for i in range(len(ia)) if not np.array_equal(ia[i], ib[i])]
    post = [i for i in diff if i >= vis]
    d0 = runs[-1][0] if runs else vis
    end = move if move is not None else len(ia)
    dark_eq = all(np.array_equal(ia[i], ib[i]) for i in range(d0, vis))
    win_eq = all(np.array_equal(ia[i], ib[i]) for i in range(vis, end))
    print(f'{fa.stem}: dark run identical {dark_eq}, start window ({end - vis} frames) identical {win_eq}')
    print(f'{fa.stem}: RAM equal {ram_eq}; dark runs {[(int(ma[a][0]), int(ma[b][0])) for a, b in runs]}; '
          f'first visible {int(ma[vis][0]) if vis < len(ma) else None} (stage {ma[vis][7]} area {ma[vis][8]} '
          f'cam {cam0}, lives {ma[vis][10]}); camera first changes at '
          f'{int(ma[move][0]) if move is not None else "never"}; identical frames from first visible: '
          f'{(post[0] - vis) if post else len(ia) - vis}; differing frames {len(diff)} '
          f'(before first visible {len(diff) - len(post)})')
    if not ram_eq:
        bad = [i for i in range(len(ma)) if not (ma[i] == mb[i]).all()]
        print('   RAM differs at', [int(ma[i][0]) for i in bad[:5]], ma[bad[0]].tolist(), mb[bad[0]].tolist())
    for i in post[:12]:
        D = ia[i] != ib[i]
        sh, m, res, amb = best_shift(ia[i], ib[i], D)
        ys, xs = np.nonzero(D)
        print(f'   f{int(ma[i][0])} cam {ma[i][1]} bxr {ma[i][2] | ma[i][3] << 8}: {int(D.sum())} px rows '
              f'{ys.min()}-{ys.max()} cols {xs.min()}-{xs.max()} build offset ({-sh[0]}, {-sh[1]}) residual {res}')
    if PNG and post:
        from PIL import Image
        PNG.mkdir(parents=True, exist_ok=True)
        i = post[0]
        def rgb(p):
            return np.stack([(p >> 16) & 255, (p >> 8) & 255, p & 255], -1).astype(np.uint8)
        d = rgb(ia[i]).copy() // 3
        d[ia[i] != ib[i]] = (255, 0, 255)
        Image.fromarray(np.concatenate([rgb(ia[i]), rgb(ib[i]), d], 1)).save(PNG / f'{fa.stem}-f{int(ma[i][0])}.png')
