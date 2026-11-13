"""Compare pe_run outputs (palette-exact; diagnostic). Usage:
    pe_cmp.py vblank A.npz B.npz [LAST]   per-vblank palette path cost ($FD13 -> $FD16) frame by frame
    pe_cmp.py frames A.npz B.npz          first frame where counters / stage / fingerprints differ
    pe_cmp.py lost A.npz LAST_FRAME       lost updates (vblanks inside updates) for updates started before LAST_FRAME
    pe_cmp.py starts A.npz                first gameplay frame of each stage
    pe_cmp.py writes A.npz                writers of the watched RAM range (bank:pc, count, frames)
"""
import sys, collections
import numpy as np
STAGES = ['1-1', '1-2', '2-1', '2-2', '2-3', '3-1', '3-2', '3-3', '4-1', '4-2', '4-3', '4-4', '5-1', '5-2', '5-3',
          '5-4', '6-1', '6-2', '6-3', '6-4A', '6-4B', '6-4C']


def ev(d):
    h = d['hits']
    names = list(d['names'])
    h = h[np.argsort(h['clk'], kind='stable')]
    return {n: h[h['which'] == i] for i, n in enumerate(names)}


def pal_costs(d):
    """frame -> list of (start clock, cost) of the palette path calls in that frame step."""
    e = ev(d)
    s, t = e['pal'], e['pal_end']
    j = np.searchsorted(t['clk'], s['clk'])
    out = collections.defaultdict(list)
    for k in range(len(s)):
        if j[k] < len(t):
            out[int(s['frame'][k])].append((int(s['clk'][k]), int(t['clk'][j[k]] - s['clk'][k])))
    return out


def vblank(a, b, last=None):
    A, B = pal_costs(a), pal_costs(b)
    frames = sorted(set(A) & set(B))
    if last:
        frames = [f for f in frames if f <= last]
    diff = collections.Counter()
    shown = 0
    n = 0
    for f in frames:
        if len(A[f]) != len(B[f]):
            diff['count'] += 1
            continue
        for (ca, xa), (cb, xb) in zip(A[f], B[f]):
            n += 1
            diff[xb - xa] += 1
            if xb != xa and shown < 10:
                print(f'  frame {f}: {xa} vs {xb} clocks')
                shown += 1
    print(f'vblanks compared {n} in {len(frames)} frames; cost difference (B - A, clocks) -> count: {dict(diff)}')
    allc = collections.Counter(x for f in frames for _, x in B[f])
    print('B cost distribution (top 8):', allc.most_common(8))


def frames(a, b):
    for k in ('cnt', 'stg', 'are', 'mas', 'm2', 'core', 'wide'):
        x, y = a[k], b[k]
        n = min(len(x), len(y))
        d = np.nonzero(x[:n] != y[:n])[0]
        print(f'{k:5s} first difference at frame {int(d[0]) if len(d) else None} ({len(d)} frames differ of {n})')


def updates(d):
    e = ev(d)
    s, sf = e['upd']['clk'].astype(np.int64), e['upd']['frame']
    w, v = e['wait']['clk'].astype(np.int64), e['vbl']['clk'].astype(np.int64)
    iw = np.searchsorted(w, s)
    keep = iw < len(w)
    s, sf, iw = s[keep], sf[keep], iw[keep]
    end = w[iw]
    nv = np.searchsorted(v, end) - np.searchsorted(v, s)
    iv = np.searchsorted(v, end)
    margin = np.where(iv < len(v), v[np.minimum(iv, len(v) - 1)] - end, -1)
    return sf, nv, margin


def lost(d, last):
    sf, nv, margin = updates(d)
    m = sf < last
    print(f'updates {int(m.sum())} started before frame {last}; lost (vblanks inside updates) {int(nv[m].sum())}; '
          f'updates spanning a vblank {int((nv[m] > 0).sum())}')
    close = np.argsort(np.where(m & (nv == 0), margin, 1 << 40))[:5]
    print('closest calls (frame, clocks before the vblank):', [(int(sf[i]), int(margin[i])) for i in close])


def starts(d):
    stg, mas = d['stg'], d['mas']
    out = []
    for i, name in enumerate(STAGES):
        f = np.nonzero((stg == i) & (mas == 0))[0]
        f = f[f > 0]
        out.append((name, int(f[0]) if len(f) else None))
    print(' '.join(f'{n}:{f}' for n, f in out))
    return out


def writes(d):
    a = d['acc']
    c = collections.Counter((int(x['bank']), int(x['pc'])) for x in a)
    for (b, pc), k in sorted(c.items()):
        fr = a['frame'][(a['bank'] == b) & (a['pc'] == pc)]
        offs = a['off'][(a['bank'] == b) & (a['pc'] == pc)]
        print(f'  {b:02X}:{pc:04X} {k:7d} writes, frames {int(fr.min())}..{int(fr.max())}, '
              f'RAM ${0x2000 + int(offs.min()):04X}-${0x2000 + int(offs.max()):04X}')


if __name__ == '__main__':
    cmd = sys.argv[1]
    L = lambda p: np.load(p)
    if cmd == 'vblank':
        vblank(L(sys.argv[2]), L(sys.argv[3]), int(sys.argv[4]) if len(sys.argv) > 4 else None)
    elif cmd == 'frames':
        frames(L(sys.argv[2]), L(sys.argv[3]))
    elif cmd == 'lost':
        lost(L(sys.argv[2]), int(sys.argv[3]))
    elif cmd == 'starts':
        starts(L(sys.argv[2]))
    elif cmd == 'writes':
        writes(L(sys.argv[2]))
