"""Free-ROM audit (../gb-palette/freewatch.py with a palette mode): a
read/execute watch over ROM file offsets LO-HI (inclusive) while replaying a
stored run (fresh session, shared start state, $2100 = FLAGS from the
environment, default 0) or a cold boot through the title to 600 updates of
1-1 (RUN = boot). Reports every stop (PC and MPRs). Run it on the build
before the change: the range must never be touched; on the new build in the
mode that uses the range it is the positive control (the first access stops
the watch, so only the first stops are meaningful).
usage: [FLAGS=0xb8] freewatch.py ROM RUN LO HI [LO HI ...]"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

import os

from smstools import Session, cv, load_run
from gbtools import EMU, WORK

rom, run_name = sys.argv[1], sys.argv[2]
spans = list(zip(sys.argv[3::2], sys.argv[4::2]))
stops = []


def watch(g):
    for lo, hi in spans:
        g.call('set_breakpoint_range', {'start_address': lo, 'end_address': hi, 'memory_area': 'rom',
                                        'read': True, 'execute': True})


def step(g):
    if g.step(1) is None:
        st = g.call('get_huc6280_status')
        stops.append({'pc': st['PC'], 'mpr': [m['value'] for m in st['MPR']]})
        return False
    return True


frames = 0
if run_name == 'boot':
    work = Path(tempfile.mkdtemp(prefix='fw-', dir=WORK))
    try:
        with cv.Game(EMU, work) as g:
            g.call('load_media', {'file_path': str(Path(rom).resolve())})
            g.call('debug_pause')
            watch(g)
            after = None
            while frames < 8000 and len(stops) < 20:
                gameplay = g.read(0x240, 1)[0] == 0 and frames > 60
                g.press({'run'} if frames % 20 < 2 and not gameplay else set())
                if gameplay and after is None:
                    after = frames
                if after is not None and frames > after + 600:
                    break
                if step(g):
                    frames += 1
    finally:
        shutil.rmtree(work, ignore_errors=True)
else:
    run = load_run(run_name)
    with Session(rom, int(os.environ.get('FLAGS', '0'), 0)) as g:
        cv.start_stage(g, run['stage'])
        watch(g)
        for count, buttons in run['segments'] + [[60, []]]:
            g.press(set(buttons))
            for _ in range(count):
                while not step(g) and len(stops) < 20:
                    pass
                frames += 1
            if len(stops) >= 20:
                break
print(json.dumps({'run': run_name, 'spans': spans, 'frames': frames, 'stops': len(stops), 'first': stops[:3]}))
