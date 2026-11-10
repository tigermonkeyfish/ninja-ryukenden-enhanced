"""Unit test of the wheel box in place: in 1-1 with a wheel, at the gameplay
loop, set Ryu's position, call nes_effect_box ($DC00, A = 5) by a synthetic
JSR and read the effect box $2EC7-$2ECC. Option on: NES box; option off: the
native box ($AABD/$95D6 from the wheel's own fields).
boxtest.py ROM FLAGS"""
import json
import sys
from fw import *

rom, flags = sys.argv[1], int(sys.argv[2], 0)
cases = [(500, 120), (8, 120), (9, 120), (0x1ff, 30), (300, 24), (300, 25), (300, 0), (0x0103, 247)]
res = []
with session('boxtest') as game:
    begin(game, rom, 0, flags)
    call_native(game, 0xa6a6)
    r = game.read(0, 0x2000)
    slot = next(i for i in range(5) if r[0x110e + i] == 5)
    for x, y in cases:
        game.write(0x110d, bytes([slot]))
        game.write(0xe9e, bytes([x & 255, x >> 8, y]))
        # the native box reads the wheel's own fields; place them as its handler does
        game.write(0x111d + slot, bytes([x & 255]))
        game.write(0x1122 + slot, bytes([x >> 8]))
        game.write(0x1131 + slot, bytes([(y + 3) & 255]))
        call_here(game, 0xdc00, a=5)
        b = game.read(0xec7, 6)
        got = {'left': b[0] | b[1] << 8, 'top': b[2], 'right': b[3] | b[4] << 8, 'bottom': b[5]}
        want = {'left': (x - 9) & 0xffff, 'top': max(y - 25, 0), 'right': x + 12, 'bottom': y}
        res.append({'x': x, 'feet': y, 'box': got, 'nes_expected': want, 'matches_nes': got == want})
print(json.dumps({'rom': Path(rom).name, 'flags': flags, 'cases': res}, indent=0))
