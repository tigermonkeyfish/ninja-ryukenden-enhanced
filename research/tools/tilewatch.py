"""Track the pixel pattern of the tiles behind same-word/different-pixel cells across samples."""
import sys, json, hashlib
from collections import Counter
from analyze import R, ROWS, load, sample_rows
from vdc import tile_rows
stage, sub = sys.argv[1], int(sys.argv[2])
orun = json.loads((R/'orig'/stage/'run.json').read_text())['samples']
erun = json.loads((R/'enh'/stage/'run.json').read_text())['samples']
pairs = [(a, b) for a, b in zip(orun, erun) if a['subarea'] == sub]
words = Counter()
for ro, re in pairs[:6]:
    bo, be = load('orig', stage, ro), load('enh', stage, re)
    rc = ro['render_camera']
    for cy in range(ROWS):
        for cx in range(rc // 8, rc // 8 + 33):
            wo, we = bo.cell_word(cx, cy), be.cell_word(cx, cy)
            if wo == we and bo.cell_pixels(wo) != be.cell_pixels(we):
                words[wo] += 1
print('same-word/diff-pixel words', [hex(w) for w, _ in words.most_common(12)])
w0 = words.most_common(1)[0][0]
for ro, re in pairs[::4]:
    bo, be = load('orig', stage, ro), load('enh', stage, re)
    to = tile_rows(bo.vram, w0 & 0xfff); te = tile_rows(be.vram, w0 & 0xfff)
    ho = hashlib.md5(str(to).encode()).hexdigest()[:6]; he = hashlib.md5(str(te).encode()).hexdigest()[:6]
    vshift = [d for d in range(-7, 8) if all(te[y] == to[(y - d) % 8] for y in range(8))]
    print(ro['name'], ro['camera'], 'orig', ho, 'enh', he, 'enh = orig rolled down by', vshift)
