"""Diagnosis for stagecheck: which gameplay fields differ in the first frames
after a stage entry between two (rom, flags) sessions.
usage: firstframes.py STAGE FRAMES ROM_A FLAGS_A ROM_B FLAGS_B"""
import sys

from stagecheck import load_and_trace

stage, frames = int(sys.argv[1]), int(sys.argv[2])
a = load_and_trace(sys.argv[3], int(sys.argv[4], 0), stage, frames)
b = load_and_trace(sys.argv[5], int(sys.argv[6], 0), stage, frames)
print('load frames', a[0], b[0])
for n, (x, y) in enumerate(zip(a[1], b[1])):
    d = {k: (x[k], y[k]) for k in x if x[k] != y[k]}
    if d:
        print(n, d)
