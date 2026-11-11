"""One check_menu exact_cycle at a frame of a stored run, findings printed
(research reference, not a maintained tool).
usage: onecycle.py ROM RUN FRAME [sweep]"""
import json
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ.setdefault('GB_WORK', '/workspace/build/all-palettes')
sys.path.insert(0, str(HERE.parents[2] / 'scripts'))
import check_menu as CM  # noqa: E402
from comparison_video import Game, start_point, start_stage, make_seed  # noqa: E402

rom, name, frame = sys.argv[1], sys.argv[2], int(sys.argv[3])
sweep = len(sys.argv) > 4
work = Path(tempfile.mkdtemp(prefix='one-', dir=os.environ['GB_WORK']))
seed = Path(os.environ['GB_WORK']) / 'menu-seed.state'
emu = os.environ['NG_EMULATOR']
if not seed.exists():
    make_seed(emu, Path(os.environ['GB_WORK']) / 'original.pce', seed)
run = json.loads((CM.RUNS / f'{name}.json').read_text())
inputs = [b for c, b in run['segments'] for _ in range(c)]
with Game(emu, work) as game:
    start_point(game, rom, seed, enhanced=True)
    start_stage(game, run['stage'])
    for buttons in inputs[:frame + 1]:
        game.press(set(buttons))
        game.step(1)
    if not CM.select_at_hook(game):
        raise SystemExit('no update saw Select')
    if sweep:
        found = CM.exact_cycle(game, work, actions=['down', 'right', 'down', 'right'], n=10, blink=False)
    else:
        found = CM.exact_cycle(game, work)
print(json.dumps(found, default=str)[:3000])
