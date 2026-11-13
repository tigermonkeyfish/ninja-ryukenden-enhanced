"""RAM of two builds at the first hit of BANK:PC in frame FRAME (from state at STATEFRAME).
Usage: snapat.py TAGA ROMA TAGB ROMB STATEFRAME FRAME BANK PC"""
import sys
import numpy as np
from tracer import T, inputs
INP = inputs()
ta, ra, tb, rb, sf, fr = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5]), int(sys.argv[6])
bank, pc = int(sys.argv[7], 16), int(sys.argv[8], 16)
nth = int(sys.argv[9]) if len(sys.argv) > 9 else 1
S = '/workspace/build/longplay-drift/states'
res = {}
for tag, rom in ((ta, ra), (tb, rb)):
    t = T(rom); t.load(f'{S}/{tag}-{sf}.state')
    for f in range(sf + 1, fr):
        t.press(INP[f - 1]); t.step(1)
    t.press(INP[fr - 1])
    t.lib.gx_set_snap_nth(nth)
    res[tag] = t.snap(bank, pc)
(a, ca), (b, cb) = res[ta], res[tb]
print('clock', ca, cb, cb - ca)
d = np.nonzero(a != b)[0]
print(' '.join(f'${0x2000 + j:04X}:{a[j]}/{b[j]}' for j in d if not (0x1c0 <= j < 0x200) and not (0x17c0 <= j < 0x1800)))
