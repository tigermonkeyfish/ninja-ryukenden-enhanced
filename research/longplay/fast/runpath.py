#!/usr/bin/env python3
"""Record the path of a Level Select comparison run (headless, original ROM).

    runpath.py STAGE OUT.json [--every 8]
Enters STAGE through the Level Select writes (comparison_video.start_stage) on
the original ROM, plays research/comparison-runs/STAGE.json and writes
[frame, area, x, y, health, stage, motion state $2EAA] every N frames plus every area change. The path is
used as beam waypoints for the played-in stage (the run itself does not replay
there: enemies and the frame phase differ). Diagnostic; emulator evidence only.
"""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from comparison_video import STAGE_NAMES, Game, make_seed, start_point, start_stage  # noqa: E402
from longplay_lib import EMULATOR                                                    # noqa: E402

ORIGINAL = Path('/workspace/DO_NOT_COMMIT_ROMS/Ninja Ryukenden (J).pce')


def main():
    stage, out = sys.argv[1], Path(sys.argv[2])
    every = int(sys.argv[sys.argv.index('--every') + 1]) if '--every' in sys.argv else 8
    run = json.loads((ROOT / f'research/comparison-runs/{stage}.json').read_text())
    work = Path(tempfile.mkdtemp(prefix='runpath-', dir='/workspace/build/longplay'))
    seed = work / 'seed.state'
    make_seed(EMULATOR, ORIGINAL, seed)
    path = []
    with Game(EMULATOR, work) as g:
        start_point(g, ORIGINAL, seed)
        start_stage(g, STAGE_NAMES.index(stage))
        fr, last_area = 0, None
        for n, b in run['segments']:
            g.press(set(b))
            for _ in range(n):
                g.step(1)
                fr += 1
                r = g.read(0xe5f, 0x60)
                area, x, y, hp = r[1], r[0x3f] | r[0x40] << 8, r[0x41], r[0x4e]
                if fr % every == 0 or area != last_area:
                    path.append([fr, area, x, y, hp, r[0], r[0x4b]])
                    last_area = area
    out.write_text(json.dumps({'stage': stage, 'path': path}))
    print(stage, len(path), path[-1])


if __name__ == '__main__':
    main()
