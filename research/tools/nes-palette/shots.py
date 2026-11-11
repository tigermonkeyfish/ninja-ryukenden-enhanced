"""Evidence f: screenshots in NES mode at frames of the stored runs, and the
popup opened there with the PALETTE row selected (NES shown).
usage: shots.py ROM OUT run:frame[:open] ..."""
import sys
from pathlib import Path

from ntools import NES, Session, cv, load_run

rom, out = sys.argv[1], Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)


def tap(g, b, after=4):
    g.press({b})
    g.checked_step(2)
    g.press(set())
    g.checked_step(after)


for spec in sys.argv[3:]:
    name, frame, *opt = spec.split(':')
    run = load_run(name)
    inputs = [b for c, b in run['segments'] for _ in range(c)]
    with Session(rom, NES) as g:
        g.write(0x1227, b'\x01')
        cv.start_stage(g, run['stage'])
        for f in range(int(frame)):
            g.press(set(inputs[f]))
            g.checked_step(1)
        g.press(set())
        g.checked_step(1)
        (out / f'nes-{name}-f{frame}.png').write_bytes(g.screenshot())
        if opt and opt[0] == 'open':
            tap(g, 'select', 12)
            for b in ('down', 'down', 'down', 'down'):
                tap(g, b)
            for k in range(2):          # the selected value blinks (16 frames on, 16 off)
                g.checked_step(16)
                (out / f'nes-{name}-f{frame}-menu-open-{k}.png').write_bytes(g.screenshot())
    print('shot', name, frame, flush=True)
