"""Interrupt handler entries and their lengths over frames, plus main-loop wait entries.
Usage: irqlist.py FIRST LAST STATEFRAME TAG:ROM ..."""
import sys
import numpy as np
from prof import trace, irq_mask, costs
first, last, sf = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
for spec in sys.argv[4:]:
    tag, rom = spec.split(':')
    A, e, _ = trace(rom, f'/workspace/build/longplay-drift/states/{tag}-{sf}.state', sf, first, last)
    c = costs(A, e); irq = irq_mask(A)
    pc, bank, clk = A['pc'], A['bank'], A['clk'].astype(np.int64)
    print('==', tag)
    i = 0; n = len(A)
    while i < n:
        if bank[i] == 0 and pc[i] in (0xFCD7, 0xFCD3):
            j = i
            while j < n and irq[j]:
                j += 1
            kind = 'vbl' if np.any((bank[i:j] == 0) & (pc[i:j] == 0xFCEC)) else 'rcr/other'
            print(f'  {A["frame"][i]} irq {kind} at {clk[i]} len {int(c[i:j].sum())}')
            i = j; continue
        if (bank[i] == 0 and pc[i] in (0xE06C, 0xE061)):
            print(f'  {A["frame"][i]} main {pc[i]:04X} at {clk[i]}')
        i += 1
