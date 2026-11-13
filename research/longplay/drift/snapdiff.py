"""RAM at the start of each update (bank 0 $E06C) in two builds, frame by frame.
Usage: snapdiff.py TAGA ROMA TAGB ROMB STATEFRAME LAST [ADDR...]"""
import sys
import numpy as np
from tracer import T, inputs
INP = inputs()
ta, ra, tb, rb, sf, last = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5]), int(sys.argv[6])
S = '/workspace/build/longplay-drift/states'
EXCL = [(0x2100, 0x2200), (0x2257, 0x225B), (0x2260, 0x2284), (0x2286, 0x2A86), (0x37C0, 0x37FE), (0x3C00, 0x4000)]


def run(tag, rom):
    t = T(rom); t.load(f'{S}/{tag}-{sf}.state')
    out = {}
    for f in range(sf + 1, last + 1):
        t.press(INP[f - 1]); r, c = t.snap(0, 0xE06C)
        if r is not None:
            out[f] = r
    return out
A = run(ta, ra); B = run(tb, rb)
mask = np.ones(0x2000, bool)
for a, b in EXCL:
    mask[a - 0x2000:b - 0x2000] = False
mask[0x50:0x52] = False; mask[0x1227] = False
prev = None
for f in sorted(set(A) & set(B)):
    x, y = A[f], B[f]
    d = np.nonzero((x != y) & mask)[0]
    key = tuple(d)
    if key != prev:
        print(f, x[0], y[0], ' '.join(f'${0x2000 + j:04X}:{x[j]}/{y[j]}' for j in d[:40]))
        prev = key
print('frames only in A', sorted(set(A) - set(B))[:10], 'only in B', sorted(set(B) - set(A))[:10])
