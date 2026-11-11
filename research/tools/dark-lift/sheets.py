"""Contact sheets, the build before against the build after, same frames
(research reference, not a maintained tool; needs Pillow).
usage: sheets.py OUT BEFORE_CAP AFTER_CAP BEFORE_SHOTS AFTER_SHOTS
  *_CAP: cap.py captures (4-1, 5-1, 6-2); *_SHOTS: cap.py scout pictures of
  1-1 f600, 2-2 f400, 5-3 f3000. Per mode (SMS, HELL, NES-A, NES-B) three
  sheets of three rows, left the build before, right the build after, the
  224 visible lines at 2x."""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

out, cap0, cap1, shot0, shot1 = [Path(p) for p in sys.argv[1:6]]
out.mkdir(parents=True, exist_ok=True)
SHEETS = {
    '4-1': [('4-1 frame 250 (area 0)', 'c', '4-1-f250'), ('4-1 frame 1150 (area 0)', 'c', '4-1-f1150'),
            ('4-1 frame 1750 (area 1)', 'c', '4-1-f1750')],
    '5-1-6-2': [('5-1 area 0', 'c', 'ls12-a0-hold'), ('6-2 area 0', 'c', 'ls17-a0-hold'),
                ('6-2 area 2', 'c', 'ls17-a2-hold')],
    'regress': [('1-1 frame 600', 's', '1-1-f600'), ('2-2 frame 400', 's', '2-2-f400'),
                ('5-3 frame 3000', 's', '5-3-f3000')],
}
W, H, LBL = 512, 448, 16
for mode in ('sms', 'hell', 'nes-a', 'nes-b'):
    for sheet, rows in SHEETS.items():
        im = Image.new('RGB', (2 * W + 4, len(rows) * (H + LBL)), (24, 24, 24))
        d = ImageDraw.Draw(im)
        same = []
        for r, (title, where, name) in enumerate(rows):
            pics = []
            for k, (label, folder) in enumerate((('hell-1-1 build', cap0 if where == 'c' else shot0),
                                                 ('dark lift', cap1 if where == 'c' else shot1))):
                p = Image.open(folder / f'{name}-{mode}.png').convert('RGB')
                pics.append(p)
                im.paste(p.crop((0, 18, 256, 242)).resize((W, H), Image.NEAREST), (k * (W + 4), r * (H + LBL) + LBL))
                d.text((k * (W + 4) + 3, r * (H + LBL) + 2), f'{mode.upper()} {title}: {label}', fill=(255, 255, 255))
            a, b = pics[0].load(), pics[1].load()
            n = sum(1 for y in range(18, 242) for x in range(256) if a[x, y] != b[x, y])
            same.append(f'{title}: {100 * n / (224 * 256):.1f}% of the picture differs')
        im.save(out / f'sheet-{mode}-{sheet}.png')
        print(f'sheet-{mode}-{sheet}.png', '; '.join(same), flush=True)
