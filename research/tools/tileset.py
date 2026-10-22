"""For animated tiles (same BAT word, different pixels), are Enhanced frames a subset of native frames?"""
import sys, json, hashlib
from collections import Counter, defaultdict
from analyze import R, ROWS, load
from vdc import tile_rows
stage = sys.argv[1]
orun = json.loads((R/'orig'/stage/'run.json').read_text())['samples']
erun = json.loads((R/'enh'/stage/'run.json').read_text())['samples']
words = Counter()
pairs = list(zip(orun, erun))
cache = []
for ro, re in pairs:
    bo, be = load('orig', stage, ro), load('enh', stage, re)
    rc = ro['render_camera']
    cache.append((ro, bo, be))
    for cy in range(ROWS):
        for cx in range(rc // 8, rc // 8 + 33):
            wo, we = bo.cell_word(cx, cy), be.cell_word(cx, cy)
            if wo == we and bo.cell_pixels(wo) != be.cell_pixels(we):
                words[wo & 0xfff] += 1
print(stage, 'animated/same-word tiles:', {hex(t): n for t, n in words.most_common(20)})
for t in [t for t, _ in words.most_common(20)]:
    ho, he, mism = Counter(), Counter(), 0
    for ro, bo, be in cache:
        a = str(tile_rows(bo.vram, t)); b = str(tile_rows(be.vram, t))
        ho[a] += 1; he[b] += 1; mism += a != b
    extra = [h for h in he if h not in ho]
    print(f'  tile {t:#05x}: native frames {len(ho)}, enhanced frames {len(he)}, enhanced frames never seen natively {len(extra)} ({sum(he[h] for h in extra)} samples), samples differing {mism}/{len(cache)}')
