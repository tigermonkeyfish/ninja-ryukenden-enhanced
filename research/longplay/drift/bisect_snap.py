"""Bisect the hit index of BANK:PC in FRAME at which RAM first differs between two builds.
Usage: bisect_snap.py TAGA ROMA TAGB ROMB STATEFRAME FRAME BANK PC MAXHITS"""
import sys
import numpy as np
from tracer import T, inputs
INP = inputs()
ta, ra, tb, rb, sf, fr = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5]), int(sys.argv[6])
bank, pc, mx = int(sys.argv[7], 16), int(sys.argv[8], 16), int(sys.argv[9])
S = '/workspace/build/longplay-drift/states'
IGN = np.zeros(0x2000, bool); IGN[0x100:0x200] = True; IGN[0x17c0:0x1800] = True; IGN[0x105] = True
cores = {ta: T(ra), tb: T(rb)}


def snap(tag, n):
    t = cores[tag]
    # each T() reloads its ROM only at creation; reload ROM by re-init when switching
    t.lib.gx_init(str({'v110': '/workspace/roms/Ninja Ryukenden - Enhanced v1.10.pce'}.get(tag, '')).encode()) if False else None
    t.load(f'{S}/{tag}-{sf}.state')
    for f in range(sf + 1, fr):
        t.press(INP[f - 1]); t.step(1)
    t.press(INP[fr - 1]); t.lib.gx_set_snap_nth(n)
    return t.snap(bank, pc)[0]


def diff(n):
    from roms import ROMS
    out = []
    for tag, rom in ((ta, ra), (tb, rb)):
        t = cores[tag]; t.lib.gx_init(ROMS[rom].encode()); out.append(snap(tag, n))
    a, b = out
    return [j for j in np.nonzero((a != b) & ~IGN)[0]], a, b
lo, hi = 1, mx
assert not diff(lo)[0], 'differs already at first hit'
while hi - lo > 1:
    mid = (lo + hi) // 2
    if diff(mid)[0]:
        hi = mid
    else:
        lo = mid
d, a, b = diff(hi)
print('equal at hit', lo, 'differs at hit', hi, ' '.join(f'${0x2000 + j:04X}:{a[j]}/{b[j]}' for j in d))
