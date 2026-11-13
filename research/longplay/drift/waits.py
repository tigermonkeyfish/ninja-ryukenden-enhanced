"""Segments between vblank waits: for each wait entry, the caller, the clock phase, the CPU clocks
since the previous wait returned, and the vblank it waits for. Usage: waits.py FIRST LAST STATEFRAME TAG:ROM ..."""
import sys
import numpy as np
from prof import trace, irq_mask, costs
first, last, sf = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
for spec in sys.argv[4:]:
    tag, rom = spec.split(':')
    A, e, _ = trace(rom, f'/workspace/build/longplay-drift/states/{tag}-{sf}.state', sf, first, last)
    c = costs(A, e); irq = irq_mask(A)
    pc, bank = A['pc'], A['bank']
    entry = np.nonzero(((bank == 0) & (pc == 0xFD67)) | ((pc == 0x37C0) & (bank == 0xF8)))[0]
    exitp = np.nonzero(((bank == 0) & (pc == 0xFD6F)) | ((pc == 0x37C8) & (bank == 0xF8)))[0]
    vbl = A['clk'][np.nonzero((bank == 0) & (pc == 0xFCEC))[0]].astype(np.int64)
    print('==', tag)
    prev_exit = 0
    for i in entry:
        # caller: the instruction before the jsr target
        j = i - 1
        while j > 0 and irq[j]:
            j -= 1
        clk = int(A['clk'][i])
        busy = int(c[prev_exit:i][~irq[prev_exit:i]].sum())
        nv = vbl[vbl > clk]
        ex = exitp[exitp > i]
        print(f"  frame {A['frame'][i]} wait from {bank[j]:02X}:{pc[j]:04X} phase-to-next-vbl {int(nv[0]) - clk if len(nv) else None} busy-since-last-wait {busy}")
        prev_exit = int(ex[0]) if len(ex) else len(A)
