"""(h) Screenshots of the popup: stored runs at given frames, before and open;
GB DMG preview and after Run. usage: shots.py ROM OUT run:frame[:opts] ..."""
import os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
EMU = os.environ['GEARGRAFX']

import sys, json, tempfile
from pathlib import Path
import check_menu as cm
from comparison_video import Game, start_point, start_stage
rom, out = sys.argv[1], Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
seed = Path(os.environ['NINJA_SEED_STATE'])  # comparison_video.make_seed on the original


def tap(g, b, after=4):
    g.press({b}); g.checked_step(2); g.press(set()); g.checked_step(after)


for spec in sys.argv[3:]:
    name, frame, *opt = spec.split(':')
    opts = int(opt[0], 0) if opt else 0
    run = json.loads((cm.RUNS / f'{name}.json').read_text())
    inputs = [b for c, b in run['segments'] for _ in range(c)]
    tag = f'{name}-f{frame}' + ('-parallax-off' if opts & 1 else '')
    with Game(EMU, Path(tempfile.mkdtemp(dir=out))) as g:
        start_point(g, rom, seed, enhanced=True)
        g.write(0x1227, b'\x01')
        g.write(0x100, bytes([opts]))
        start_stage(g, run['stage'])
        for f in range(int(frame)):
            g.press(set(inputs[f])); g.checked_step(1)
        g.press(set()); g.checked_step(1)
        (out / f'{tag}-before.png').write_bytes(g.screenshot())
        tap(g, 'select', 12)
        (out / f'{tag}-open.png').write_bytes(g.screenshot())
        if 'gb' in spec or name in ('1-1',):
            for b in ('down', 'down', 'down', 'down'):
                tap(g, b)
            tap(g, 'right', 40)
            (out / f'{tag}-gb-preview.png').write_bytes(g.screenshot())
            g.press({'run'}); g.checked_step(2); g.press(set()); g.checked_step(200)
            tap(g, 'select', 12)
            (out / f'{tag}-gb-after-run-open.png').write_bytes(g.screenshot())
        print('shot', tag, flush=True)
