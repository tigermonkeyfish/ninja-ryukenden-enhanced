"""Save the screenshots (and VCE dumps) of chosen frames of a stored run.
usage: capture.py ROM RUN FLAGS|orig OUTDIR TAG FRAME[,FRAME...]"""
import sys
from pathlib import Path

from gbtools import Session, cv, load_run

rom, run_name, flags, out, tag = sys.argv[1:6]
frames = sorted(int(x) for x in sys.argv[6].split(','))
run = load_run(run_name)
inputs = [set(b) for c, b in run['segments'] for _ in range(c)] + [set()] * 60
out = Path(out)
out.mkdir(parents=True, exist_ok=True)
with Session(rom, None if flags == 'orig' else int(flags, 0)) as g:
    cv.start_stage(g, run['stage'])
    for f in range(frames[-1] + 1):
        g.press(inputs[f])
        g.checked_step(1)
        if f in frames:
            (out / f'{run_name}-{f:05d}-{tag}.png').write_bytes(g.screenshot())
            (out / f'{run_name}-{f:05d}-{tag}.vce').write_bytes(g.read(0, 1024, area=8))
print('saved', len(frames))
