"""Print the palette queue, lock and $2100 after each of the first FRAMES
frames of a stored run (or from frame START). usage: qwatch.py ROM RUN FLAGS FRAMES [START]"""
import sys

from gbtools import Session, cv, load_run, queue

rom, run_name, flags, frames = sys.argv[1], sys.argv[2], int(sys.argv[3], 0), int(sys.argv[4])
start = int(sys.argv[5]) if len(sys.argv) > 5 else 0
run = load_run(run_name)
inputs = [set(b) for c, b in run['segments'] for _ in range(c)] + [set()] * 60
with Session(rom, flags) as g:
    cv.start_stage(g, run['stage'])
    for f in range(start + frames):
        g.press(inputs[f])
        g.checked_step(1)
        if f >= start:
            ram = g.read(0, 0x300)
            print(f, queue(ram), 'lock', ram[0x283], 'opts', hex(ram[0x100]))
