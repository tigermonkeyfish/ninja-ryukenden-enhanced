#!/usr/bin/env python3
"""Diagnostic triptych: native | Enhanced | Enhanced with unmatched windows marked."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from core import png_decode, png_encode  # noqa: E402
from analyze import K, R, SCREEN_Y0  # noqa: E402


def triptych(stage, name, out, scale=2, analysis=None):
    a = analysis or json.loads((R / 'analysis' / f'{stage}.json').read_text())
    fails = a['fails'].get(name, [])
    ps = next(p for p in a['per_sample'] if p['name'] == name)
    _, _, imo = png_decode((R / 'orig' / stage / 'samples' / f'{name}.png').read_bytes())
    _, _, ime = png_decode((R / 'enh' / stage / 'samples' / f'{name}.png').read_bytes())
    mark = [[False] * 256 for _ in imo]
    for cy, x in fails:
        for yy in range(8):
            sy = SCREEN_Y0 + cy * 8 + yy
            for xx in range(x, min(256, x + K)):
                mark[sy][xx] = True
    third = []
    for sy, row in enumerate(ime):
        line = []
        for x, p in enumerate(row):
            if mark[sy][x]:
                line.append(((p[0] + 255 * 2) // 3, p[1] // 3, (p[2] + 255 * 2) // 3))
            else:
                g = (p[0] + p[1] + p[2]) // 3
                line.append((g // 2 + p[0] // 2, g // 2 + p[1] // 2, g // 2 + p[2] // 2))
        third.append(line)
    gap = [(40, 40, 40)] * 4
    rows = []
    for sy in range(len(imo)):
        row = imo[sy] + gap + ime[sy] + gap + third[sy]
        row = [p for p in row for _ in range(scale)]
        rows.extend([row] * scale)
    Path(out).write_bytes(png_encode(rows))
    return len(fails)


if __name__ == '__main__':
    stage = sys.argv[1]
    outdir = Path(sys.argv[2])
    outdir.mkdir(parents=True, exist_ok=True)
    a = json.loads((R / 'analysis' / f'{stage}.json').read_text())
    for name in sys.argv[3:]:
        n = triptych(stage, name, outdir / f'{stage}-{name}.png', analysis=a)
        print(name, n)
