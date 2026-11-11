"""(f) Compare SMS screenshots with the owner's mock-up operation (research
reference, not a maintained tool): for each pair DIR/<name>-sms.png and
DIR/<name>-original.png (shots.py, the same frame of the same replay), map
every pixel of the Original picture through candidate A's per-channel
quantisation (sms.json: the emulator's 8-bit value for each PC Engine level
read off the pictures themselves) and count the pixels where the SMS picture
differs. The mock-up sheets were made the same way from captured frames, so
0 differing pixels means the build shows what the mock-up operation gives
for that frame.
usage: mockcompare.py DIR"""
import sys
from pathlib import Path

from PIL import Image

from smstools import SMS  # noqa: F401  (the table this compares against is sms.json's)
from palette_tables import load_sms, sms_channel

d = Path(sys.argv[1])
sms_levels, pce = load_sms()
pairs = sorted(p for p in d.glob('*-sms.png') if (d / p.name.replace('-sms.png', '-original.png')).exists())
values = sorted({v for p in pairs for img in (Image.open(d / p.name.replace('-sms.png', '-original.png')).convert('RGB'),)
                 for _, rgb in img.getcolors(1 << 16) for v in rgb})
if len(values) != 8:
    raise SystemExit(f'expected the 8 channel values of levels 0-7, found {values}')
to_level = {v: i for i, v in enumerate(values)}
quant = {v: values[sms_channel(to_level[v], sms_levels, pce)] for v in values}
total = 0
for p in pairs:
    sms = Image.open(p).convert('RGB')
    orig = Image.open(d / p.name.replace('-sms.png', '-original.png')).convert('RGB')
    want = orig.point(lambda v: quant.get(v, v))
    a, b = list(sms.getdata()), list(want.getdata())
    diff = sum(1 for x, y in zip(a, b) if x != y)
    total += diff
    print(f'{p.name}: {diff} of {len(a)} pixels differ from candidate A applied to the Original picture')
print('channel values', values, '-> SMS', sorted(set(quant.values())), '; total differing pixels', total)
