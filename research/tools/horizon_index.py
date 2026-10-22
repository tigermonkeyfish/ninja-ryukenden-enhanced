"""Exact horizon alignment at round starts: native column vs Enhanced loop index per screen tile."""
import json, sys, struct
from collections import Counter
from pathlib import Path
import local
sys.path.insert(0, str(local.SCRIPTS))
import analyze, stitch
from analyze import R
import castle_horizon as ch
base = local.ENHANCED.read_bytes()
words = struct.unpack('<782H', base[0x7bf58:0x7bf58 + 1564])
rom = Path(sys.argv[1]).read_bytes()
stages = sys.argv[2:]
MAPS = {'14-5-3': 0x7c * 0x2000 + 0x400, '15-5-4': 0x7c * 0x2000 + 0x400, '16-6-1': 0x66 * 0x2000 + 0x400}
SKYMAPS = {'14-5-3': 0x7c * 0x2000 + 0x400, '15-5-4': 0x7c * 0x2000 + 0x400, '16-6-1': 0x44 * 0x2000 + 0x400}
for stage in stages:
    m = rom[MAPS[stage]:MAPS[stage] + 23 * 64]
    run = json.loads((R / 'orig' / stage / 'run.json').read_text())
    erun = json.loads((R / 'enh' / stage / 'run.json').read_text())
    for a in run['areas']:
        sub = a['subarea']
        pairs = [(o, e) for o, e in zip(run['samples'], erun['samples']) if o['subarea'] == sub and o['kind'] == 'entry']
        if not pairs: continue
        o, e = pairs[0]
        rc = o['render_camera']
        so = analyze.sample_rows(stitch.load('orig', stage, o), rc)
        se = analyze.sample_rows(stitch.load('enh', stage, e), rc)
        sm = rom[SKYMAPS[stage]:SKYMAPS[stage] + 23 * 64]
        for label, rows, mm in (('sky', range(0, 14), sm), ('horizon', range(14, 23), m)):
            offs = Counter()
            for x in range(0, 256, 8):
                ncols = None; ecols = None
                for r in rows:
                    wo, we = so[r][2][x], se[r][2][x]
                    if (wo >> 12) >= 2 or (we >> 12) >= 2: continue
                    nc = {c for c in range(34) if words[r * 34 + c] == wo}
                    eu = {u for u in range(45) if mm[r * 64 + u] == (we & 0xff)}
                    ncols = nc if ncols is None else ncols & nc
                    ecols = eu if ecols is None else ecols & eu
                if ncols and ecols and len(ncols) == 1 and len(ecols) == 1:
                    offs[(next(iter(ncols)) - next(iter(ecols))) % 45] += 1
            print(stage, 'area', sub, 'camera', o['camera'], label, 'native-minus-enhanced column offsets:', offs.most_common(3))
