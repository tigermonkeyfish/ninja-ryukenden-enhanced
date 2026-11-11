"""HELL pictures of captured frames under several hell.json files (research
reference, not a maintained tool; needs numpy and Pillow). A capture (cap.py:
NAME-MODE.png, -index.png, .ram, .vce) is redrawn from its index picture
(which VCE entry each pixel shows) and its RAM palette: entries below
`mapped_entries` through the table of each hell.json (with the stage's
override), the rest as captured. Per capture a strip: the pictures side by
side, and under them the places where the colours of PAIR touch, enlarged;
and the share of the playfield that differs between the first table and
each other one.
usage: hellmock.py OUT PAIR LABEL=hell.json[,LABEL=hell.json...] CAPTURE...
  PAIR: two colours, e.g. 049,092 (the zooms; '-' for none)
  CAPTURE: path without the -MODE suffix parts, e.g. cap/ls12-a0-start-hell
           (stage number from 'lsN-' names, else 255)"""
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts'))
import palette_tables as PT  # noqa: E402

out, pair = Path(sys.argv[1]), sys.argv[2]
tables = [(l, Path(p)) for l, p in (x.split('=') for x in sys.argv[3].split(','))]
caps = sys.argv[4:]
out.mkdir(parents=True, exist_ok=True)
RGB = np.array([[((c >> 3) & 7) * 255 // 7, ((c >> 6) & 7) * 255 // 7, (c & 7) * 255 // 7] for c in range(512)],
               dtype=np.uint8)
RUN_STAGE = {'1-1': 0, '2-2': 3, '3-1': 5, '3-2': 6, '4-1': 8, '4-2': 9, '5-2': 13, '5-3': 14, '5-4': 15,
             '6-1': 16, '6-3': 18}


def stage_of(name):
    m = re.match(r'ls(\d+)-', name)
    if m:
        return int(m.group(1))
    return RUN_STAGE.get(name.split('-f')[0], 255)


def draw(base, path):
    mapped = PT.load_hell(path)['mapped_entries']
    table = np.array(PT.hell_stage_table(stage_of(Path(base).name), path))
    ram = Path(base + '.ram').read_bytes()
    pal = np.array([(ram[2 * i] | ram[2 * i + 1] << 8) & 0x1ff for i in range(512)])
    vce = Path(base + '.vce').read_bytes()
    shown = np.array([(vce[2 * i] | vce[2 * i + 1] << 8) & 0x1ff for i in range(512)])
    q = np.round(np.array(Image.open(base + '-index.png').convert('RGB')).astype(int) * 7 / 255).astype(int)
    e = (q[..., 1] << 6) | (q[..., 0] << 3) | q[..., 2]
    words = np.where(e < mapped, table[pal[e]], shown[e])
    return e, pal[e], words


for base in caps:
    name = Path(base).name
    pics, first = [], None
    for label, path in tables:
        e, col, words = draw(base, path)
        pics.append((label, words))
        if first is None:
            first = words
        else:
            d = (words[50:242] != first[50:242])
            print(f'{name}: {label} differs from {tables[0][0]} in {d.mean() * 100:.2f}% of the playfield')
    h, w = first.shape
    zooms = []
    if pair != '-':
        a, b = (int(x, 16) for x in pair.split(','))
        bg = e < 240
        ma, mb = bg & (col == a), bg & (col == b)
        touch = np.zeros_like(ma)
        touch[:, :-1] |= (ma[:, :-1] & mb[:, 1:]) | (mb[:, :-1] & ma[:, 1:])
        touch[:-1] |= (ma[:-1] & mb[1:]) | (mb[:-1] & ma[1:])
        touch[:50] = False
        ys, xs = np.nonzero(touch)
        print(f'{name}: ${a:03X} {ma[50:242].mean() * 100:.2f}% and ${b:03X} {mb[50:242].mean() * 100:.2f}% of the '
              f'playfield, touching at {len(ys)} pixels')
        seen = []
        for y, x in sorted(zip(ys.tolist(), xs.tolist()), key=lambda p: -touch[max(0, p[0] - 16):p[0] + 16,
                                                                               max(0, p[1] - 16):p[1] + 16].sum()):
            if all(abs(y - sy) > 40 or abs(x - sx) > 40 for sy, sx in seen):
                seen.append((y, x))
            if len(seen) == 3:
                break
        zooms = [(max(0, min(h - 48, y - 24)), max(0, min(w - 48, x - 24))) for y, x in seen]
    sheet = Image.new('RGB', (len(pics) * (w + 8), h + 14 + (80 + 16 if zooms else 0)), (40, 40, 40))
    dr = ImageDraw.Draw(sheet)
    for k, (label, words) in enumerate(pics):
        img = Image.fromarray(RGB[words])
        sheet.paste(img, (k * (w + 8), 14))
        dr.text((k * (w + 8) + 2, 1), f'{label} {name}', fill=(255, 255, 255))
        for j, (y, x) in enumerate(zooms):
            crop = img.crop((x, y, x + 48, y + 48)).resize((80, 80), Image.NEAREST)
            sheet.paste(crop, (k * (w + 8) + j * (crop.width + 4), h + 22))
    sheet.save(out / f'{name}.png')
print('sheets in', out)
