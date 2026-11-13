"""Per-frame RAM differences between two builds from saved states.
Usage: ramdiff.py TAGA ROMA TAGB ROMB STATEFRAME LAST"""
import sys
import numpy as np
from tracer import T, inputs
INP = inputs()
ta, ra, tb, rb, sf, last = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5]), int(sys.argv[6])
S = '/workspace/build/longplay-drift/states'
EXCL = [(0x2100, 0x2200), (0x2257, 0x225B), (0x2260, 0x2284), (0x2286, 0x2A86), (0x37C0, 0x37FE), (0x3C00, 0x4000)]


def run(tag, rom):
    t = T(rom); t.load(f'{S}/{tag}-{sf}.state')
    out = []
    for f in range(sf + 1, last + 1):
        t.press(INP[f - 1]); t.step(1)
        out.append(np.frombuffer(bytes(t.ram), np.uint8).copy())
    return out
A = run(ta, ra); B = run(tb, rb)
mask = np.ones(0x2000, bool)
for a, b in EXCL:
    mask[a - 0x2000:b - 0x2000] = False
prev = None
for i, (x, y) in enumerate(zip(A, B)):
    d = np.nonzero((x != y) & mask)[0]
    key = tuple(d)
    if key != prev:
        print(sf + 1 + i, ' '.join(f'${0x2000 + j:04X}:{x[j]}/{y[j]}' for j in d[:40]))
        prev = key
