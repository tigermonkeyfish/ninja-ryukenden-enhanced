"""2-D shift between Enhanced and native background pixels within changed cells."""
import sys, json
from analyze import R, ROWS, load, sample_rows
stage, names = sys.argv[1], sys.argv[2:]
orun = {s['name']: s for s in json.loads((R/'orig'/stage/'run.json').read_text())['samples']}
erun = {s['name']: s for s in json.loads((R/'enh'/stage/'run.json').read_text())['samples']}
for name in names:
    ro, re = orun[name], erun[name]; rc = ro['render_camera']
    so, se = sample_rows(load('orig', stage, ro), rc), sample_rows(load('enh', stage, re), rc)
    H = ROWS * 8
    O = [[so[y // 8][0][x][y % 8] for x in range(256)] for y in range(H)]
    E = [[se[y // 8][0][x][y % 8] for x in range(256)] for y in range(H)]
    M = [[(so[y // 8][2][x] != se[y // 8][2][x]) or (so[y // 8][0][x] != se[y // 8][0][x]) for x in range(256)] for y in range(H)]
    # cell-level mask
    best = []
    for dy in range(-16, 17):
        for dx in range(-16, 17):
            a = t = 0
            for y in range(0, H, 2):
                yy = y + dy
                if not 0 <= yy < H: continue
                for x in range(0, 256, 2):
                    xx = x + dx
                    if 0 <= xx < 256 and M[y][x] and M[yy][xx]:
                        t += 1; a += E[y][x] == O[yy][xx]
            if t > 100: best.append((a / t, dx, dy, t))
    best.sort(reverse=True)
    print(name, 'cam', ro['camera'], best[:4])
