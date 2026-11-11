"""Print the palette queue, lock and $2100 after each of the first FRAMES
frames of a stored run (or from frame START). usage: qwatch.py ROM RUN FLAGS FRAMES [START]"""
import sys

from gbtools import Session, cv, load_run, queue

rom, run_name, flags, frames = sys.argv[1], sys.argv[2], int(sys.argv[3], 0), int(sys.argv[4])
start = int(sys.argv[5]) if len(sys.argv) > 5 else 0
if run_name.isdigit():                       # a Level Select entry, no input
    run, inputs = {'stage': int(run_name)}, [set()] * (start + frames)
else:
    run = load_run(run_name)
    inputs = [set(b) for c, b in run['segments'] for _ in range(c)] + [set()] * 60
with Session(rom, flags) as g:
    cv.start_stage(g, run['stage'])
    for f in range(start + frames):
        g.press(inputs[f])
        g.checked_step(1)
        if f >= start:
            ram = g.read(0, 0x300)
            vce = g.read(4, 6, area=8)
            print(f, queue(ram), 'lock', ram[0x283], 'opts', hex(ram[0x100]), 'ram', ram[0x28a:0x290].hex(), 'vce', vce.hex())
