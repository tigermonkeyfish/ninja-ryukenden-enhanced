"""Compare lx.py runs frame by frame against the first (load-exact; diagnostic, emulator only).

    cmp7.py REF.npz OTHER.npz ...

Per run: first frame where the update counter, master flags, stage or area differ from REF and how
many frames differ; stage starts (first gameplay frame of each stage), area changes (frames where
$2E60 changes in gameplay), the ending cinema's first frame (master 1, scene $2241 = 14) and whether all equal REF's.
"""
import sys
import numpy as np
STAGES = ['1-1', '1-2', '2-1', '2-2', '2-3', '3-1', '3-2', '3-3', '4-1', '4-2', '4-3', '4-4', '5-1', '5-2', '5-3',
          '5-4', '6-1', '6-2', '6-3', '6-4A', '6-4B', '6-4C']


def marks(d):
    stg, mas, are = d['stg'], d['mas'], d['are']
    st = {}
    for i, name in enumerate(STAGES):
        f = np.nonzero((stg == i) & (mas == 0))[0]
        f = f[f > 0]
        st[name] = int(f[0]) if len(f) else None
    ch = np.nonzero((np.diff(are.astype(int)) != 0) & (mas[1:] == 0) & (mas[:-1] == 0))[0] + 1
    end = np.nonzero((mas == 1) & (d['m2'] == 14))[0]
    return st, [int(x) for x in ch], int(end[0]) if len(end) else None


def main(ref, others):
    R = np.load(ref)
    rs, ra, re_ = marks(R)
    print(ref, 'stage starts', ' '.join(f'{k}:{v}' for k, v in rs.items()))
    print('  area changes', len(ra), 'ending', re_)
    for p in others:
        D = np.load(p)
        out = []
        for k in ('cnt', 'mas', 'm2', 'stg', 'are'):
            n = min(len(R[k]), len(D[k]))
            d = np.nonzero(R[k][:n] != D[k][:n])[0]
            out.append(f'{k} first diff {int(d[0]) if len(d) else None} ({len(d)} frames)')
        s, a, e = marks(D)
        print(p, '; '.join(out))
        print(f'  stage starts equal {s == rs}; area changes equal {a == ra} ({len(a)}); ending {e} (ref {re_})')
        if s != rs:
            print('   differing starts', {k: (rs[k], s[k]) for k in rs if rs[k] != s[k]})
        if a != ra:
            n = min(len(a), len(ra)); i = next((j for j in range(n) if a[j] != ra[j]), n)
            print('   first differing area change', i, ra[i:i + 3], a[i:i + 3])


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2:])
