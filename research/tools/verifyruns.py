"""Replay run files on the original from the canonical start; report where each ends."""
import json, sys
from pathlib import Path
import local
sys.path.insert(0, str(local.SCRIPTS))
import comparison_video as cv
G = str(local.EMULATOR)
S = local.WORK
seed = cv.make_seed(G, local.ORIGINAL, S / 'verifyruns' / 'seed.state')
for path in sys.argv[1:]:
    run = json.loads(Path(path).read_text())
    with cv.Game(G, S / 'verifyruns') as g:          # a fresh session per run
        cv.start_point(g, local.ORIGINAL, seed)
        cv.start_stage(g, run['stage'])
        for n, b in run['segments']:
            g.press(set(b)); g.step(n)
        g.press(set()); g.step(30)
        r = g.read(0, 0x1000)
        master = g.read(0x240, 1)[0]
        ok = r[0xe5f] != run['stage'] or master != 0 or (run['stage'] == 15 and g.read(0x1035, 1)[0] == 0)
        print(Path(path).stem, 'ends: stage', cv.STAGE_NAMES[r[0xe5f]], 'area', r[0xe60], 'master', master, 'health', r[0xead], 'lives', r[0xeaf], '->', 'FINISHES' if ok else 'DOES NOT FINISH', flush=True)
