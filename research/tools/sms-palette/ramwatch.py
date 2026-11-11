"""Free-RAM audit (as ../gb-palette/freewatch.py, for CPU addresses): a
read/write watch over CPU addresses LO-HI (hex, inclusive, cpu_addr) while
replaying a stored run (fresh session, shared start state) or from power-on
through the title to 600 updates of 1-1 (RUN = boot, pressing Run). Reports
every stop (PC, MPRs, S and the watched bytes then) and the bytes at the
end. Run it on the build before the change: only the reset's RAM clear may
touch the range.
usage: ramwatch.py ROM RUN LO HI [LO HI ...]   (e.g. 2104 2104)"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

from smstools import Session, cv, load_run
from gbtools import EMU, WORK

rom, run_name = sys.argv[1], sys.argv[2]
spans = [(int(lo, 16), int(hi, 16)) for lo, hi in zip(sys.argv[3::2], sys.argv[4::2])]
stops = []


def watched(g):
    return [g.read(lo - 0x2000, hi - lo + 1).hex() for lo, hi in spans]


def watch(g):
    for lo, hi in spans:
        g.call('set_breakpoint_range', {'start_address': f'{lo:04x}', 'end_address': f'{hi:04x}',
                                        'memory_area': 'cpu_addr', 'read': True, 'write': True})


def step(g):
    if g.step(1) is None:
        st = g.call('get_huc6280_status')
        stops.append({'pc': st.get('PC'), 'mpr': [m['value'] for m in st.get('MPR', [])],
                      's': st.get('S', st.get('SP')), 'bytes': watched(g)})
        return False
    return True


frames, end = 0, None
if run_name == 'boot':
    work = Path(tempfile.mkdtemp(prefix='rw-', dir=WORK))
    try:
        with cv.Game(EMU, work) as g:
            g.call('load_media', {'file_path': str(Path(rom).resolve())})
            g.call('debug_pause')
            watch(g)
            after = None
            while frames < 8000 and len(stops) < 40:
                gameplay = g.read(0x240, 1)[0] == 0 and frames > 60
                g.press({'run'} if frames % 20 < 2 and not gameplay else set())
                if gameplay and after is None:
                    after = frames
                if after is not None and frames > after + 600:
                    break
                if step(g):
                    frames += 1
            end = watched(g)
    finally:
        shutil.rmtree(work, ignore_errors=True)
else:
    run = load_run(run_name)
    with Session(rom, 0) as g:
        cv.start_stage(g, run['stage'])
        watch(g)
        for count, buttons in run['segments'] + [[60, []]]:
            g.press(set(buttons))
            for _ in range(count):
                while not step(g) and len(stops) < 40:
                    pass
                frames += 1
            if len(stops) >= 40:
                break
        end = watched(g)
print(json.dumps({'run': run_name, 'spans': [f'{lo:04X}-{hi:04X}' for lo, hi in spans], 'frames': frames,
                  'stops': len(stops), 'first': stops[:4], 'end': end}))
