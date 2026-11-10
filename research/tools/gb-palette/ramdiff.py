"""RAM differences between two palette modes at given frames of a stored
run (palette RAM $2286-$2A85, the queue and zero page excluded).
usage: ramdiff.py ROM RUN FLAGS_A FLAGS_B FRAME[,FRAME...]"""
import sys

from gbtools import Session, cv, load_run

rom, run_name, fa, fb = sys.argv[1:5]
frames = [int(x) for x in sys.argv[5].split(',')]
run = load_run(run_name)
inputs = [set(b) for c, b in run['segments'] for _ in range(c)] + [set()] * 60


def dumps(flags):
    out = {}
    with Session(rom, int(flags, 0)) as g:
        cv.start_stage(g, run['stage'])
        for f in range(max(frames) + 1):
            g.press(inputs[f])
            g.checked_step(1)
            if f in frames:
                out[f] = g.read(0, 0x2000)
    return out


A, B = dumps(fa), dumps(fb)
skip = set(range(0x286, 0xa86)) | set(range(0x260, 0x284)) | set(range(0x100))
for f in frames:
    d = [i for i in range(0x2000) if A[f][i] != B[f][i] and i not in skip]
    print(f, len(d), ' '.join(f'${0x2000 + i:04X}:{A[f][i]:02x}/{B[f][i]:02x}' for i in d[:40]))
