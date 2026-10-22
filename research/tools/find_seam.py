"""Find samples where an Enhanced texture coordinate is on screen and crop both screenshots."""
import sys, json
from pathlib import Path
import stitch
from compose import agreement, pano_from
from analyze import R, SCREEN_Y0
from core import png_decode, png_encode
stage, sub, row, u_seam = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
y0, y1 = int(sys.argv[5]), int(sys.argv[6])   # BAT rows for the crop
data = stitch.collect(stage, sub, ('fwd', 'rev'))
_, ec = agreement(data, 'enh', row, [d['camera'] // 8 for d in data])
pe, elo = pano_from(ec)
U = u_seam + elo                     # absolute texture coordinate
hits = []
for d in data:
    x = U - d['camera'] // 8
    if 40 <= x <= 216 and d['flags'][row][x]:
        hits.append((d['name'], d['camera'], x))
print('seam visible in', len(hits), 'samples:', hits[:10])
if hits:
    name, cam, x = hits[len(hits) // 2]
    imgs = []
    for w in ('orig', 'enh'):
        _, _, im = png_decode((R / w / stage / 'samples' / f'{name}.png').read_bytes())
        crop = [r[max(0, x - 48): x + 48] for r in im[SCREEN_Y0 + 8 * y0: SCREEN_Y0 + 8 * y1]]
        imgs.append(crop)
    rows = []
    for a, b in zip(*imgs):
        line = a + [(255, 255, 255)] * 2 + b
        line = [p for p in line for _ in range(4)]
        rows.extend([line] * 4)
    out = Path(f'viz/seam-{stage}-a{sub}-{name}.png'); out.write_bytes(png_encode(rows)); print('wrote', out, 'screen x', x)
