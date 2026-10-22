"""Classify screenshot differences outside background cells (foreground/sprite/HUD integrity)."""
import json, sys
from collections import Counter
from multiprocessing import Pool
from analyze import R, ROWS, SCREEN_Y0, load, sample_rows
from core import png_decode
from vdc import words, tile_rows

def job(stage):
    orun = json.loads((R/'orig'/stage/'run.json').read_text())['samples']
    erun = json.loads((R/'enh'/stage/'run.json').read_text())['samples']
    cats = Counter(); examples = []
    for ro, re in zip(orun, erun):
        if ro['png_sha256'] == re['png_sha256']:
            cats['identical_screenshot'] += 1; continue
        rc = ro['render_camera']
        bo, be = load('orig', stage, ro), load('enh', stage, re)
        so, se = sample_rows(bo, rc), sample_rows(be, rc)
        _, _, imo = png_decode((R/'orig'/stage/'samples'/f"{ro['name']}.png").read_bytes())
        _, _, ime = png_decode((R/'enh'/stage/'samples'/f"{re['name']}.png").read_bytes())
        sato = (R/'orig'/stage/'samples'/f"{ro['name']}.sat").read_bytes()
        sate = (R/'enh'/stage/'samples'/f"{re['name']}.sat").read_bytes()
        palsame = bo.pal == be.pal
        kinds = Counter()
        for sy in range(len(imo)):
            for x in range(256):
                if imo[sy][x] == ime[sy][x]: continue
                if sy < SCREEN_Y0:
                    kinds['hud'] += 1; continue
                cy = (sy - SCREEN_Y0) // 8
                if cy >= ROWS: kinds['below'] += 1; continue
                wo, we = so[cy][2][x], se[cy][2][x]
                if wo != we: continue                       # patched background cell
                if so[cy][0][x] != se[cy][0][x]:
                    kinds['animated_tile_or_palette'] += 1; continue   # same word, decoded pixels differ
                kinds['other(sprite/raster)'] += 1
        cat = 'bg_only' if not kinds else '+'.join(sorted(kinds))
        cats[cat] += 1
        if 'other(sprite/raster)' in kinds and len(examples) < 6:
            examples.append({'name': ro['name'], 'kinds': dict(kinds), 'sat_same': sato == sate, 'pal_same': palsame})
    return stage, dict(cats), examples

if __name__ == '__main__':
    stages = sorted(p.name for p in (R/'orig').iterdir() if (p/'run.json').exists())
    allres = {}
    with Pool(8) as p:
        for stage, cats, ex in p.imap_unordered(job, stages):
            allres[stage] = {'categories': cats, 'examples': ex}
            print(stage, cats, ex[:3], flush=True)
    (R/'report'/'integrity.json').write_text(json.dumps(allres, indent=1))
