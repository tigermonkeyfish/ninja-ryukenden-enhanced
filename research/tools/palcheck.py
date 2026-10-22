"""Palette entries that differ between ROMs: value sets and whether visible cells use them."""
import sys, json
from collections import Counter, defaultdict
from analyze import R, ROWS
from vdc import words
import zlib
stage = sys.argv[1]
orun = json.loads((R/'orig'/stage/'run.json').read_text())['samples']
erun = json.loads((R/'enh'/stage/'run.json').read_text())['samples']
vals = defaultdict(lambda: (Counter(), Counter())); ndiff = Counter()
usage = defaultdict(Counter)   # palette -> where used (bg-changed vs same) per ROM
for ro, re in zip(orun, erun):
    po = words((R/'orig'/stage/'samples'/f"{ro['name']}.pal").read_bytes())
    pe = words((R/'enh'/stage/'samples'/f"{re['name']}.pal").read_bytes())
    vo = words(zlib.decompress((R/'orig'/stage/'samples'/f"{ro['name']}.vram.z").read_bytes())[:4096])
    ve = words(zlib.decompress((R/'enh'/stage/'samples'/f"{re['name']}.vram.z").read_bytes())[:4096])
    rc = ro['render_camera']
    for cy in range(ROWS):
        for cx in range(rc // 8, rc // 8 + 33):
            i = cy * 64 + cx % 64
            usage[vo[i] >> 12]['orig-same' if vo[i] == ve[i] else 'orig-changed'] += 1
            usage[ve[i] >> 12]['enh-same' if vo[i] == ve[i] else 'enh-changed'] += 1
    for i in range(256):
        if po[i] != pe[i]:
            ndiff[i] += 1
        vals[i][0][po[i]] += 1; vals[i][1][pe[i]] += 1
print(stage, 'samples', len(orun))
for i in sorted(ndiff):
    print(f'  pal {i//16:2}.{i%16:2}: differs in {ndiff[i]:3} samples; native values {dict(vals[i][0])}; enh values {dict(vals[i][1])}')
for p in sorted({i // 16 for i in ndiff}):
    print(f'  palette {p} usage (visible cells):', dict(usage[p]))
