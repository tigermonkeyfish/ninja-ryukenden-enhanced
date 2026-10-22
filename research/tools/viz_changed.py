"""native | Enhanced | Enhanced with background-changed cells tinted (cyan) and same-word/different-pixel cells (yellow)."""
import sys, json
from pathlib import Path
from core import png_decode, png_encode
from analyze import R, ROWS, SCREEN_Y0, load, sample_rows
stage, outdir = sys.argv[1], Path(sys.argv[2]); outdir.mkdir(exist_ok=True)
orun = {s['name']: s for s in json.loads((R/'orig'/stage/'run.json').read_text())['samples']}
erun = {s['name']: s for s in json.loads((R/'enh'/stage/'run.json').read_text())['samples']}
for name in sys.argv[3:]:
    ro, re = orun[name], erun[name]
    rc = ro['render_camera']
    so, se = sample_rows(load('orig', stage, ro), rc), sample_rows(load('enh', stage, re), rc)
    _, _, imo = png_decode((R/'orig'/stage/'samples'/f'{name}.png').read_bytes())
    _, _, ime = png_decode((R/'enh'/stage/'samples'/f'{name}.png').read_bytes())
    mark = {}
    for cy in range(ROWS):
        co, cells, wo = so[cy]; ce, _, we = se[cy]
        for x in range(256):
            if wo[x] != we[x]:
                mark[(cells[x], cy)] = 'c'
            elif co[x] != ce[x]:
                mark.setdefault((cells[x], cy), 'y')
    third = []
    for sy, row in enumerate(ime):
        line = []
        for x, p in enumerate(row):
            cy = (sy - SCREEN_Y0) // 8
            m = mark.get((((rc + x) % 512) // 8, cy)) if sy >= SCREEN_Y0 and cy < ROWS else None
            if m == 'c': line.append((p[0] // 3, (p[1] + 510) // 3, (p[2] + 510) // 3))
            elif m == 'y': line.append(((p[0] + 510) // 3, (p[1] + 510) // 3, p[2] // 3))
            else: line.append(p)
        third.append(line)
    gap = [(40, 40, 40)] * 4
    rows = []
    for sy in range(len(imo)):
        r = imo[sy] + gap + ime[sy] + gap + third[sy]
        r = [p for p in r for _ in range(2)]
        rows.extend([r, r])
    (outdir / f'chg-{stage}-{name}.png').write_bytes(png_encode(rows))
    print(name, 'changed-word cells', sum(1 for v in mark.values() if v == 'c'), 'same-word diff cells', sum(1 for v in mark.values() if v == 'y'))
