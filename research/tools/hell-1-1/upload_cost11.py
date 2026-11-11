"""research/tools/hell-palette/upload_cost.py with the visible stage written
($2E5F) after each case's state load, so the same 1-1 hook state measures
HELL's override loop (STAGE 0, 1-1) and the plain loop (STAGE 3, 2-2): per
synthetic queue the VCE writes in the vblank, the last one in lines after
the vblank interrupt and the median master clocks between writes. Also a
queue of colours that are all the key ($094 at entries 0-127), to time the
override hit.
usage: upload_cost11.py ROM FLAGS STAGE   (GB_WORK: seed.state, original.pce)"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'hell-palette'))
import upload_cost as uc  # noqa: E402

STAGE = int(sys.argv[3], 0)
KEYS = 'mapped 128, all $094'
base = uc.measure


def measure(g, state, queue, keys=False):
    real_load = g.call

    def call(name, args=None):
        result = real_load(name, args) if args is not None else real_load(name)
        if name == 'load_state_file':
            g.write(0xe5f, bytes([STAGE]))
            if keys:
                g.write(0x286, b'\x94\x00' * 128)
        return result
    g.call = call
    try:
        return base(g, state, queue)
    finally:
        g.call = real_load


uc.CASES[KEYS] = [(0, 128)]
uc.measure = lambda g, state, queue: measure(g, state, queue, keys=queue is uc.CASES[KEYS])
sys.argv = sys.argv[:3]
print('visible stage', STAGE, flush=True)
uc.main()
