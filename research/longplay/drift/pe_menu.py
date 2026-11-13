"""Per-vblank palette path cost with the in-game menu open (palette-exact; diagnostic, emulator only).

Power-on in MODE (pe.W), the recording to frame START, then Select (2 frames), OPEN frames with
no input, Select (2 frames), AFTER frames; the clocks of $FD13 and $FD16 in every frame. Prints
the cost of each frame's palette path; compare two ROMs/modes with the same arguments.

    python3 pe_menu.py ROM MODE RECORDING [START] [OPEN] [AFTER]  ->  one line of costs per phase
"""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
from pe import W, inputs, BITS                                                  # noqa: E402

rom, mode, rec = sys.argv[1], sys.argv[2], sys.argv[3]
start = int(sys.argv[4]) if len(sys.argv) > 4 else 1500
opn = int(sys.argv[5]) if len(sys.argv) > 5 else 150
after = int(sys.argv[6]) if len(sys.argv) > 6 else 100
t = W(rom, None if mode == 'none' else mode)
t.boot()
inp = inputs(rec)
for f in range(1, start + 1):
    t.press(inp[f - 1]); t.step(1)
seq = [BITS['select']] * 2 + [0] * opn + [BITS['select']] * 2 + [0] * after
keys = [0xFD13, 0xFD16, 0xE061]
costs, menu_frames = [], 0
t.frame = 0
for f, b in enumerate(seq):
    _, h = t.run_w(1, np.array([b], np.uint8), keys)
    h = h[np.argsort(h['clk'], kind='stable')]
    s = h[h['which'] == 0]['clk']; e = h[h['which'] == 1]['clk']
    c = [int(e[e > x][0] - x) for x in s if (e > x).any()]
    costs.append(c)
opened = t.r(0x2240, 2)
flat = [x for c in costs for x in c]
print(mode, 'frames', len(seq), 'vblank palette paths', len(flat), 'costs (clocks):', ' '.join(map(str, flat)))
