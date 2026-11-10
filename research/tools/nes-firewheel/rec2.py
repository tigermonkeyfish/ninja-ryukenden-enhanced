"""scripts/comparison_video.py `record` without per-frame images on disk:
the same replay (start_point, start_stage, run segments + 60 tail frames,
checked one-frame steps) and the same trace fields, plus the SHA-1 of each
frame's screenshot. Options byte set to FLAGS for Enhanced ROMs.
rec2.py ROM RUN OUT.json FLAGS|orig"""
import hashlib
import json
import os
import sys
from pathlib import Path
import tempfile
import shutil

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts'))
import comparison_video as cv  # noqa: E402

EMU = os.environ['NG_EMULATOR']
SEED = Path(os.environ.get('NFW_WORK', 'build/nes-firewheel')).resolve() / 'seed.state'
rom, run, out, flags = sys.argv[1:5]
run = json.loads(Path(run).read_text())


def once():
    work = Path(tempfile.mkdtemp(prefix='rec2-', dir=str(Path(os.environ.get('NFW_WORK', 'build/nes-firewheel')).resolve() / 'logs')))
    trace, n = [], 0
    try:
        with cv.Game(EMU, work) as game:
            cv.start_point(game, rom, SEED, flags != 'orig')
            if flags != 'orig':
                game.write(0x100, bytes([int(flags, 0)] * 2))
            cv.start_stage(game, run['stage'])
            for count, buttons in run['segments'] + [[60, []]]:
                game.press(set(buttons))
                for _ in range(count):
                    game.checked_step(1)
                    shot = hashlib.sha1(game.screenshot()).hexdigest()[:16]
                    ram = game.read(0, 0x2000)
                    trace.append({
                        'f': n, 'ram': hashlib.sha1(bytes(b for k, b in enumerate(ram) if k not in cv.OWNED)).hexdigest()[:12],
                        'sat': hashlib.sha1(game.read(0, 512, area=6)).hexdigest()[:12],
                        'ryu': ram[0xe9e:0xeb8].hex(), 'timer': ram[0xeda:0xede].hex(),
                        'stage': ram[0xe5f], 'area': ram[0xe60], 'lives': ram[0xeaf],
                        'health': ram[0xead], 'cam': int.from_bytes(ram[0x20f:0x211], 'little'),
                        'master': ram[0x240], 'boss': ram[0x1035], 'png': shot})
                    n += 1
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return trace


trace = cv.retried(once)
Path(out).write_text(json.dumps(trace))
print(Path(rom).name, run['name'], flags, len(trace), 'frames')
