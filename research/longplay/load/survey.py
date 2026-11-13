"""Survey of stage loads and area changes from lx.py runs (load-exact; diagnostic, emulator only).

    survey.py A.npz [B.npz ...]

Events: every call of the native background initialization ($80AB, bank 1) from the stage load
(bank 1 $82CD) or the area change (bank 1 $85B4). For each event, the main-loop update that
contains it and the updates around it: vblanks inside each update (= frames lost by it), and
the clocks from its wait call to the next vblank interrupt (the margin). A load is its own
update; an area change's transition spans several. Printed per event: frame, stage/area,
the event update's vblanks / margin, the window's vblank pattern and its smallest margin.
"""
import sys
import numpy as np
STAGES = ['1-1', '1-2', '2-1', '2-2', '2-3', '3-1', '3-2', '3-3', '4-1', '4-2', '4-3', '4-4', '5-1', '5-2', '5-3',
          '5-4', '6-1', '6-2', '6-3', '6-4A', '6-4B', '6-4C']
BEFORE, AFTER = 4, 8


def load(p):
    d = np.load(p)
    h = d['hits']
    h = h[np.argsort(h['clk'], kind='stable')]
    names = list(d['names'])
    e = {n: h[h['which'] == i] for i, n in enumerate(names)}
    return d, e


def updates(e):
    s = e['upd']['clk'].astype(np.int64)
    w = e['wait']['clk'].astype(np.int64)
    v = e['vbl']['clk'].astype(np.int64)
    iw = np.searchsorted(w, s)
    keep = iw < len(w)
    s, iw = s[keep], iw[keep]
    sf = e['upd']['frame'][keep]
    end = w[iw]
    nv = np.searchsorted(v, end) - np.searchsorted(v, s)
    iv = np.searchsorted(v, end)
    margin = np.where(iv < len(v), v[np.minimum(iv, len(v) - 1)] - end, -1)
    return s, sf, end, nv, margin


def events(path):
    d, e = load(path)
    s, sf, end, nv, margin = updates(e)
    out = []
    for kind in ('load', 'area'):
        for hclk, hf in zip(e[kind]['clk'].astype(np.int64), e[kind]['frame']):
            k = int(np.searchsorted(s, hclk, side='right') - 1)
            if k < 0:
                continue
            lo, hi = max(0, k - BEFORE), min(len(s), k + AFTER + 1)
            f = int(hf)
            out.append(dict(kind=kind, frame=f, upd_frame=int(sf[k]), stage=STAGES[d['stg'][f]] if d['stg'][f] < 22 else d['stg'][f],
                            area=int(d['are'][min(f + 1, len(d['are']) - 1)]), nv=int(nv[k]), margin=int(margin[k]),
                            work=int(end[k] - s[k]),
                            window=[int(x) for x in nv[lo:hi]], wmargin=[int(x) for x in margin[lo:hi]],
                            pos=k - lo))
    loads = {x['upd_frame'] for x in out if x['kind'] == 'load'}
    out = [x for x in out if x['kind'] == 'load' or x['upd_frame'] not in loads]
    out.sort(key=lambda x: x['frame'])
    return out


def show(path):
    ev = events(path)
    print(path)
    for x in ev:
        w = ''.join(str(min(n, 9)) if i != x['pos'] else f'[{n}]' for i, n in enumerate(x['window']))
        print(f"  {x['kind']:4s} {x['frame']:6d} {x['stage']:>4s} a{x['area']} upd {x['upd_frame']:6d} "
              f"work {x['work']:8d} vbl {x['nv']:2d} left {x['margin']:7d} | window {w} min left "
              f"{min(m for m in x['wmargin'] if m >= 0):7d}")
    return ev


if __name__ == '__main__':
    for p in sys.argv[1:]:
        show(p)
