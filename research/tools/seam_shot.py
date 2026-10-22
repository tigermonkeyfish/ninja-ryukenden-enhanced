"""Crop real screenshots (native | Enhanced) around a detected seam for its example sample."""
import json, sys
from pathlib import Path
from analyze import R, SCREEN_Y0
from core import png_decode, png_encode
key, idx = sys.argv[1], int(sys.argv[2])
seams = json.loads((R/'report'/'seams.json').read_text())
s = seams[key]['seams'][idx]
stage, sub = key.split('/')
run = {x['name']: x for x in json.loads((R/'enh'/stage/'run.json').read_text())['samples']}
names = [n for n in run if n.startswith(sub[1:] + '-')]
out = []
for name in names:
    cam = run[name]['camera']
    x = s['u0'] + 1 - cam // 8
    if 24 <= x <= 232:
        out.append((name, x))
print(key, s['u0'], 'rows', s['rows'], 'candidate samples', out[:8])
pick = [o for o in out if o[0] == s['example']] or out[len(out)//2:len(out)//2+1]
name, x = pick[0]
r0, r1 = max(0, min(s['rows']) - 3), min(23, max(s['rows']) + 3)
crops = []
for w in ('orig', 'enh'):
    _, _, im = png_decode((R / w / stage / 'samples' / f'{name}.png').read_bytes())
    c = [list(r[max(0, x - 56): x + 56]) for r in im[SCREEN_Y0 + 8 * r0: SCREEN_Y0 + 8 * (r1 + 1)]]
    if w == 'enh':
        for r in c[:3]: r[min(56, x)] = (255, 0, 0)
    crops.append(c)
rows = []
for a, b in zip(*crops):
    line = a + [(255, 255, 255)] * 2 + b
    line = [p for p in line for _ in range(4)]
    rows.extend([line] * 4)
p = Path(f'viz/shot-{stage}-{sub}-u{s["u0"]}-{name}.png'); p.write_bytes(png_encode(rows)); print('wrote', p, 'sample', name, 'x', x)
