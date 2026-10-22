"""Timer sub-counter for the first frames after each stage entry (from the
first gameplay update). usage: cadence.py ROM LABEL"""
import json, sys
from pathlib import Path
import local
sys.path.insert(0, str(local.SCRIPTS))
import comparison_video as cv
G = str(local.EMULATOR)
rom, label = sys.argv[1], sys.argv[2]
S = local.WORK / f'cadence-{label}'; S.mkdir(exist_ok=True)
out = {}
# One fresh session per stage, from a start state made in a session of its own
# (docs/pc-engine/LESSONS.md, "A session that cold-booted is not a clean replay
# session"). ROM is the original: Enhanced needs the original's start state.
seed = cv.make_seed(G, rom, S / 'seed.state')
for st in (0, 3, 5, 6, 8, 9, 13, 14, 15, 16, 18):
    with cv.Game(G, S) as g:
        cv.start_point(g, rom, seed)
        cv.start_stage(g, st)
        ticks = []
        for k in range(20):
            g.step(1); ticks.append(g.read(0xeda, 1)[0])
    out[cv.STAGE_NAMES[st]] = ticks
    print(label, cv.STAGE_NAMES[st], ticks, flush=True)
(S / 'result.json').write_text(json.dumps(out))
