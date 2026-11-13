"""start-align: the markdown event table from the capture windows (run after capture.py x2 and rows.py)."""
import numpy as np
from pathlib import Path
from compare import pack, best_shift, runs
from capture import EVENTS
LABEL = {1:'1-1 start',2846:'1-2 a0',10151:'2-1 a0',11343:'2-1 a1',12421:'2-1 a2',12546:'2-1 a3',13256:'2-2 a0',14030:'2-2 a1',14671:'2-2 a2',16547:'2-3 a0',27793:'3-1 a0',31416:'3-2 a0',34867:'3-3 a0',53302:'4-1 a0',55309:'4-1 a1',55429:'4-1 a2',57134:'4-2 a0',60369:'4-3 a0',60708:'4-3 a1',61795:'4-3 a2',63544:'4-3 a3',64436:'4-4 a0',70025:'5-1 a0',73278:'5-2 a0',74531:'5-2 a1',75459:'5-2 a2',76157:'5-2 a3',77219:'5-3 a0',77972:'5-3 a1',78669:'5-3 a2',79287:'5-3 a3',80296:'5-3 a4',80630:'5-3 a5',80887:'5-3 a6',82897:'5-4 a0',86521:'6-1 a0',88458:'6-2 a0',90754:'6-2 a1',91716:'6-2 a2',91820:'6-2 a3',92931:'6-2 a4',93822:'6-3 a0',94460:'6-3 a1',94579:'6-3 a2',96625:'6-3 a3',102317:'6-4A a0',106481:'6-4B a0',111242:'6-4C a0'}
da, db = Path('/workspace/build/start-align/cap-unmod'), Path('/workspace/build/start-align/cap-new')
out = ['| # | Event | Stage/area | Event frame | Camera at entry | First visible / full bright | Whole frame identical (start window) | Backdrop verdict (start window) | Notes (outside the start window) |', '|---|---|---|---|---|---|---|---|---|']
cnt = dict(same=0, shifted=0, differs=0)
verd = {}
for n, ev in enumerate(EVENTS, 1):
    a = np.load(da / f'ev-{ev}.npz'); b = np.load(db / f'ev-{ev}.npz')
    m = a['meta']; fr = [int(x) for x in m[:, 0]]
    s = np.array([a[f'img{f}'].astype(np.int64).sum() for f in fr]); mx = s.max()
    dark = [i for i, v in enumerate(s) if v < 0.5 * mx]
    area = bool(dark) and len(dark) < 20
    if area:
        j = dark[0]
        while j < len(fr) and s[j] < 0.5 * mx: j += 1
        nb = j
    else:
        nb = next(i for i, v in enumerate(s) if v > 0)
    fb = next((i for i, v in enumerate(s) if v >= 0.99 * s[nb:].max() and i >= nb), nb)
    end = min(len(fr) - 1, (nb if area else fb) + 8)
    diff = [i for i in range(len(fr)) if not np.array_equal(a[f'img{fr[i]}'], b[f'img{fr[i]}'])]
    st = [i for i in diff if nb <= i <= end]
    pre = [i for i in diff if i < nb and area]
    later = [i for i in diff if i > end]
    def shift_of(i):
        A, B = a[f'img{fr[i]}'], b[f'img{fr[i]}']; D = (A != B).any(axis=2); ys, xs = np.nonzero(D)
        (dx, dy), mt, rs, nn = best_shift(pack(A), pack(B), D)
        return D.sum(), (ys.min(), ys.max(), xs.min(), xs.max()), (-dx, -dy), rs / D.sum()
    if not st:
        v = 'identical'; ident = f'yes ({end - nb + 1} frames)'; cnt['same'] += 1
    else:
        sm = [shift_of(i) for i in (st[0], st[len(st) // 2], st[-1])]
        offs = sorted({x[2] for x in sm}); rf = max(x[3] for x in sm)
        npx, bb, o, r0 = sm[0]
        kind = 'tiny (not backdrop)' if npx <= 10 else ('shifted' if r0 <= 0.10 else 'content differs')
        cnt['same' if npx <= 10 and len(st) == len(st) and all((np.array(a[f'img{fr[i]}'] != b[f'img{fr[i]}']).any(axis=2).sum() <= 10) for i in st) else ('shifted' if kind == 'shifted' else 'differs')] += 1
        v = f'{kind}: build offset vs original (x,y) {", ".join(str(o_) for o_ in offs)}; residual {min(x[3] for x in sm):.0%}-{rf:.0%} of differing px; {len(st)}/{end-nb+1} frames differ, rows {bb[0]}-{bb[1]}, cols {bb[2]}-{bb[3]}'
        ident = f'no ({len(st)} of {end - nb + 1} frames differ)'
    note = []
    if pre:
        npx, bb, o, r0 = shift_of(pre[-1])
        note.append(f'last {len(pre)} frames of the old area before the transition black differ (build offset {o}, residual {r0:.0%}, {npx} px)')
    if later:
        note.append(f'{len(later)} later frames differ ({fr[later[0]]}..{fr[later[-1]]}, from {later[0]-nb} frames after the first visible one; the moving backdrop)')
    camera = int(m[nb, 1])
    out.append(f'| {n} | {"area change" if area else "load"} | {LABEL[ev]} | {ev} | {camera} | {fr[nb]} / {fr[fb]} | {ident} | {v} | {"; ".join(note) or "-"} |')
Path('/workspace/build/start-align/table.md').write_text('\n'.join(out) + '\n')
print(cnt)
