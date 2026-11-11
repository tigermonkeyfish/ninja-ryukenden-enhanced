"""Does the native pause (Run in gameplay) hold the music driver? (research
reference, not a maintained tool). 1-1 from the shared start state: 60
frames, Run pressed, 90 paused frames, Run again, 60 frames; per frame
whether the music driver's RAM (zero page $80-$8F, $3800-$3BFF) changed
and the pause flag candidates. Also, with MENU=1, the same around a
popup-menu opening (Select) held open for 90 frames.
usage: pausemusic.py ROM"""
import hashlib
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ.setdefault('GB_WORK', '/workspace/build/all-palettes')
sys.path.insert(0, str(HERE.parent / 'gb-palette'))
from gbtools import Session, cv  # noqa: E402


def music(g):
    return hashlib.sha1(g.read(0x80, 16) + g.read(0x1800, 0x400)).hexdigest()[:8]


rom = sys.argv[1]
button = 'select' if os.environ.get('MENU') == '1' else 'run'
with Session(rom, 0) as g:
    cv.start_stage(g, 0)
    g.step(60)
    seq = []
    last = music(g)
    for phase, frames, press in (('before', 20, None), ('paused', 90, button), ('after', 40, button)):
        changed = 0
        for k in range(frames):
            if press and k == 0:
                g.press({press})
            elif press and k == 2:
                g.press(set())
            g.step(1)
            m = music(g)
            changed += m != last
            last = m
        seq.append((phase, frames, changed))
    print(button, 'frames in which the music RAM changed:', seq)
