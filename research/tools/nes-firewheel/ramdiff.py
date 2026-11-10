"""Replay a stored run on two Enhanced ROMs (rec2 method, options FLAGS) and
list the RAM bytes (outside comparison_video.OWNED) that differ, per frame.
ramdiff.py ROM_A ROM_B RUN FLAGS"""
import collections
import json
import sys
import shutil
import tempfile
from pathlib import Path
from fw import *
sys.path.insert(0, str(WT / "scripts"))
import comparison_video as cv  # noqa: E402

rom_a, rom_b, runname, flags = sys.argv[1:5]
run = json.loads((RUNS / f'{runname}.json').read_text())


def rams(rom):
    out = []
    work = Path(tempfile.mkdtemp(prefix='ramdiff-', dir=OUT / 'logs'))
    try:
        with cv.Game(EMU, work) as game:
            cv.start_point(game, rom, seed(), True)
            game.write(0x100, bytes([int(flags, 0)] * 2))
            cv.start_stage(game, run['stage'])
            for count, buttons in run['segments'] + [[60, []]]:
                game.press(set(buttons))
                for _ in range(count):
                    game.checked_step(1)
                    out.append(game.read(0, 0x2000))
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return out


a, b = rams(rom_a), rams(rom_b)
byaddr = collections.defaultdict(list)
for f, (x, y) in enumerate(zip(a, b)):
    for i in range(0x2000):
        if x[i] != y[i] and i not in cv.OWNED:
            byaddr[0x2000 + i].append(f)
print(json.dumps({'run': runname, 'frames': len(a), 'differing': {f'${k:04x}': v[:8] for k, v in sorted(byaddr.items())}}))
