"""Pause test (frame stepping): 1-1, wheel at update 30, Run pressed at frame
100 (pause) and again at 300 (resume); the wheel counter per frame.
pause.py ROM FLAGS"""
import json
import sys
from fw import *

rom, flags = sys.argv[1], int(sys.argv[2], 0)
out = []
with session('pause') as game:
    begin(game, rom, 0, flags)
    for f in range(400):
        if f == 30:
            call_native(game, 0xa6a6)
        game.press({'run'} if f in (100, 101, 300, 301) else set())
        game.step(1)
        r = game.read(0, 0x2000)
        slot = next((i for i in range(5) if r[0x110e + i] == 5), None)
        out.append((f, None if slot is None else r[0x1127 + slot] | r[0x1136 + slot] << 8, r[0xeda], r[0x117a]))
print(json.dumps({'rom': Path(rom).name, 'flags': flags,
                  'samples': [o for o in out if o[0] in (95, 99, 100, 105, 150, 200, 299, 300, 305, 310, 320, 399)]}))
