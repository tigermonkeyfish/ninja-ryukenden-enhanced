"""Compare instruction streams (interrupt part and main-loop part separately) of two builds.
Usage: div2.py TAGA ROMA TAGB ROMB STATEFRAME FIRST LAST [skip_patch]"""
import sys
import numpy as np
from prof import trace, irq_mask
ta, ra, tb, rb, sf, first, last = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], *map(int, sys.argv[5:8])
S = '/workspace/build/longplay-drift/states'
A, ea, _ = trace(ra, f'{S}/{ta}-{sf}.state', sf, first, last)
B, eb, _ = trace(rb, f'{S}/{tb}-{sf}.state', sf, first, last)


def norm(X):
    # drop the wait loops and patch-only code (bank 0 >= $FE00, RAM code, patch banks >= $40, trampolines)
    pc, bank = X['pc'], X['bank']
    w = ((bank == 0) & (pc >= 0xFD67) & (pc <= 0xFD6F)) | ((pc >= 0x37C0) & (pc <= 0x37FF))
    patch = ((bank == 0) & (pc >= 0xFE00)) | (bank >= 0x40)
    return ~w & ~patch


for label, sel in (('interrupt', True), ('main', False)):
    ma = (irq_mask(A) == sel) & norm(A)
    mb = (irq_mask(B) == sel) & norm(B)
    a, b = A[ma], B[mb]
    ka = (a['bank'].astype(np.int64) << 16) | a['pc']
    kb = (b['bank'].astype(np.int64) << 16) | b['pc']
    n = min(len(ka), len(kb))
    d = np.nonzero(ka[:n] != kb[:n])[0]
    print(label, 'instructions', len(ka), len(kb))
    if len(d):
        i = d[0]
        print(' first divergence at', i, 'frame', a['frame'][i], b['frame'][i])
        for j in range(max(0, i - 30), min(n, i + 4)):
            print(f"  {a['frame'][j]} {a['bank'][j]:02X}:{a['pc'][j]:04X} {int(a['clk'][j])%358995:6d} | {b['frame'][j]} {b['bank'][j]:02X}:{b['pc'][j]:04X} {int(b['clk'][j])%358995:6d}")
