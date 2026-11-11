"""Diagnosis: a stored run in two modes; for frames FIRST..LAST print the
stage, area, master state, palette lock, chosen RAM palette entries, whether
the picture is uniform (blank) and whether the two pictures are equal.
usage: peek.py ROM RUN FLAGS_A FLAGS_B FIRST LAST index,index,..[ SHOTS_DIR]"""
import sys
from pathlib import Path

from ntools import Session, cv, load_run, ram_palette

rom, name, fa, fb, first, last = sys.argv[1], sys.argv[2], int(sys.argv[3], 0), int(sys.argv[4], 0), \
    int(sys.argv[5]), int(sys.argv[6])
idx = [int(i) for i in sys.argv[7].split(',')]
shots = Path(sys.argv[8]) if len(sys.argv) > 8 else None
run = load_run(name)
inputs = [b for c, b in run['segments'] for _ in range(c)] + [[]] * 900


def go(flags):
    rows = {}
    with Session(rom, flags) as g:
        cv.start_stage(g, run['stage'])
        for f, b in enumerate(inputs[:last + 1]):
            g.press(set(b))
            g.checked_step(1)
            if f >= first:
                ram = g.read(0, 0x2000)
                png = g.screenshot()
                if shots:
                    shots.mkdir(parents=True, exist_ok=True)
                    (shots / f'{name}-{flags:#04x}-{f}.png').write_bytes(png)
                pal = ram_palette(ram)
                rows[f] = (ram[0xe5f], ram[0xe60], ram[0x240], ram[0x283], [f'{pal[i]:03X}' for i in idx], png)
    return rows


a, b = go(fa), go(fb)
for f in sorted(a):
    x, y = a[f], b[f]
    print(f, 'stage/area/master/lock', x[:4], y[:4], x[4], y[4], 'same picture' if x[5] == y[5] else 'PICTURE DIFFERS')
