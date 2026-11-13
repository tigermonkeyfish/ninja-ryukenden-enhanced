"""Cost by bank/page of the longest main-loop segment (between two vblank waits) in FIRST..LAST.
Usage: segprof.py FIRST LAST STATEFRAME TAG:ROM ..."""
import sys
import numpy as np
from prof import trace, irq_mask, costs
first, last, sf = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
res = {}
for spec in sys.argv[4:]:
    tag, rom = spec.split(':')
    A, e, _ = trace(rom, f'/workspace/build/longplay-drift/states/{tag}-{sf}.state', sf, first, last)
    c = costs(A, e); irq = irq_mask(A)
    pc, bank = A['pc'], A['bank']
    w = ((bank == 0) & (pc >= 0xFD67) & (pc <= 0xFD6F)) | ((pc >= 0x37C0) & (pc <= 0x37DD) & (bank == 0xF8))
    # segments of non-wait main instructions
    seg = np.cumsum(w)
    best = None
    for s in np.unique(seg):
        m = (seg == s) & ~w & ~irq
        tot = c[m].sum()
        if best is None or tot > best[0]:
            best = (tot, m, s)
    tot, m, s = best
    key = np.where(bank >= 0x40, bank.astype(int) * 256, bank.astype(int) * 256 + (pc >> 8))
    ks, inv = np.unique(key[m], return_inverse=True)
    sums = np.bincount(inv, weights=c[m])
    res[tag] = dict(zip(ks.tolist(), sums.astype(int).tolist()))
    idx = np.nonzero(m)[0]
    print(tag, 'longest segment', int(tot), 'frames', A['frame'][idx[0]], A['frame'][idx[-1]],
          'irq clocks inside', int(c[(seg == s) & irq].sum()))
tags = list(res)
keys = sorted(set().union(*[set(r) for r in res.values()]))
for k in keys:
    vals = [res[t].get(k, 0) for t in tags]
    if max(vals) - min(vals) > 3000:
        nm = f'bank {k >> 8:02X}' if (k >> 8) >= 0x40 else f'{k >> 8:02X}:{k & 0xff:02X}xx'
        print(f'  {nm:12s}', ' | '.join(str(v) for v in vals))
