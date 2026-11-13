"""Per-update table from a watch run: start, end, next vblank, margin (master clocks)."""
import numpy as np
from pathlib import Path
W = Path('/workspace/build/longplay-drift/watch')
FRAME = 358995


def load(tag):
    d = np.load(W / f'{tag}.npz')
    h = d['hits']
    names = list(d['names'])
    o = np.argsort(h['clk'], kind='stable')
    h = h[o]
    ev = {n: h[h['which'] == i] for i, n in enumerate(names)}
    return d, ev


def updates(tag):
    d, ev = load(tag)
    s = ev['upd']['clk'].astype(np.int64)
    sf = ev['upd']['frame']
    w = ev['wait']['clk'].astype(np.int64)
    v = ev['vbl']['clk'].astype(np.int64)
    iw = np.searchsorted(w, s)
    keep = iw < len(w)
    s, sf, iw = s[keep], sf[keep], iw[keep]
    e = w[iw]
    iv = np.searchsorted(v, s)
    ok = iv < len(v)
    vn = np.where(ok, v[np.minimum(iv, len(v) - 1)], -1)
    # vblanks passed during the update = number of vblanks between s and e
    nv = np.searchsorted(v, e) - iv
    # the vblank that started the update (last before s)
    vp = v[np.maximum(iv - 1, 0)]
    return dict(start=s, frame=sf, end=e, vnext=vn, margin=vn - e, nvbl=nv, vprev=vp,
                dur=e - s, delay=s - vp, fend=d['fend'].astype(np.int64), cnt=d['cnt'], ev=ev)
