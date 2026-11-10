"""Compare two screenshots: differing pixel count, the rows they span, and
optionally a side-by-side image (A | B | difference mask) for evidence.
usage: pngdiff.py A.png B.png [OUT.png]"""
import sys
from PIL import Image, ImageChops

a, b = Image.open(sys.argv[1]).convert('RGB'), Image.open(sys.argv[2]).convert('RGB')
d = ImageChops.difference(a, b).convert('L').point(lambda v: 255 if v else 0)
box = d.getbbox()
count = sum(1 for v in d.getdata() if v)
print(f'{count} pixels differ; bbox {box}')
if len(sys.argv) > 3:
    w, h = a.size
    out = Image.new('RGB', (3 * w, h))
    out.paste(a, (0, 0))
    out.paste(b, (w, 0))
    out.paste(d.convert('RGB'), (2 * w, 0))
    out.resize((6 * w, 2 * h), Image.NEAREST).save(sys.argv[3])
