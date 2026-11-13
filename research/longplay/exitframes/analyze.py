"""exit-frames: per event and frame, picture difference and its cause (per-line scroll vs content).

    analyze.py DIR_A DIR_B [OUT.json]     (DIR_A = unmodified ROM's probe.py output, DIR_B = the build's)

Per frame: differing pixels, visible lines whose (latched BXR, BG Y offset) differ, the split's BYR
write ($FD3B) scanline/dot on both sides, the IRQ1 entry clock relative to the frame start, and the
first meta (RAM) difference. Visible line = vpos 14..255 = picture row vpos - 14.
"""
import json, sys
from pathlib import Path
import numpy as np


def byr(d, f):
    w = d['vw'][(d['vw']['frame'] == f) & (d['vw']['pc'] == 0xFD3B)]
    return [(int(x['vpos']), int(x['hpos'])) for x in w]


def lines(d, f):
    l = d['lr'][(d['lr']['frame'] == f) & (d['lr']['vpos'] >= 14) & (d['lr']['vpos'] < 256)]
    return {int(x['vpos']): (int(x['bxr']), int(x['by'])) for x in l}


def main():
    A, B = Path(sys.argv[1]), Path(sys.argv[2])
    res = {}
    for fa in sorted(A.glob('ev-*.npz'), key=lambda p: int(p.stem[3:])):
        ev = int(fa.stem[3:])
        a, b = np.load(fa), np.load(B / fa.name)
        ma, mb = a['meta'], b['meta']
        rows = []
        for i in range(len(ma)):
            f = int(ma[i, 0])
            ia, ib = a[f'img{f}'], b[f'img{f}']
            dm = (ia != ib).any(2)
            nd = int(dm.sum())
            la, lb = lines(a, f), lines(b, f)
            dl = sorted(v for v in la if la[v] != lb.get(v))
            ram = [k for k in range(1, 10) if ma[i, k] != mb[i, k]]
            r = dict(frame=f, px=nd, bright=int(ia.sum()) // 1000, scroll_lines=len(dl),
                     first_scroll_line=(dl[0] - 14) if dl else None, byr_a=byr(a, f), byr_b=byr(b, f), ram_diff=ram,
                     m2258=[int(ma[i, 10]), int(mb[i, 10])], e63=int(ma[i, 6]))
            if nd:
                ys, xs = np.nonzero(dm)
                r['bbox'] = [int(ys.min()), int(ys.max()), int(xs.min()), int(xs.max())]
                r['cause'] = 'scroll' if dl else 'content'
            rows.append(r)
        res[ev] = rows
    if len(sys.argv) > 3:
        Path(sys.argv[3]).write_text(json.dumps(res, indent=1))
    for ev, rows in res.items():
        print('event', ev)
        for r in rows:
            flag = '' if not r['px'] else r['cause']
            print('  %6d px=%6d %-7s sl=%3d first=%s byrA=%s byrB=%s ram=%s 2258=%s e63=%d bbox=%s' % (
                r['frame'], r['px'], flag, r['scroll_lines'], r['first_scroll_line'], r['byr_a'], r['byr_b'],
                r['ram_diff'], r['m2258'], r['e63'], r.get('bbox')))


if __name__ == '__main__':
    main()
