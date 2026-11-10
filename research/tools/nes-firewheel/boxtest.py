"""Unit test of the wheel box in place: in 1-1 with a wheel, at the gameplay
loop, set Ryu's position, call nes_effect_box (A = 5) by a synthetic JSR and read
the effect box $2EC7-$2ECC. The routine's address is taken from the build
(effect_box_address). Option on: NES box; option off: the
native box ($AABD/$95D6 from the wheel's own fields).
boxtest.py ROM FLAGS"""
import json
import sys
from fw import *


def effect_box_address(rom):
    """nes_effect_box is not at a fixed number the probe may assume ($DC00 is
    the protection rule): read it from the operand of the hook `jsr
    nes_effect_box` that src/nes-firewheel/main.asm places at $AA8A in bank 2
    (ROM offset 2 * $2000 + $0A8A, headerless build)."""
    data = Path(rom).read_bytes()
    base = len(data) % 0x2000          # copier header, if any
    at = base + 2 * 0x2000 + 0x0A8A
    if data[at] != 0x20:
        raise SystemExit(f'{rom}: no JSR at $AA8A (not a Firewheel build?)')
    return data[at + 1] | data[at + 2] << 8


rom, flags = sys.argv[1], int(sys.argv[2], 0)
cases = [(500, 120), (8, 120), (9, 120), (0x1ff, 30), (300, 24), (300, 25), (300, 0), (0x0103, 247)]
res = []
box_routine = effect_box_address(rom)
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
        call_here(game, box_routine, a=5)
        b = game.read(0xec7, 6)
        got = {'left': b[0] | b[1] << 8, 'top': b[2], 'right': b[3] | b[4] << 8, 'bottom': b[5]}
        want = {'left': (x - 9) & 0xffff, 'top': max(y - 25, 0), 'right': x + 12, 'bottom': y}
        res.append({'x': x, 'feet': y, 'box': got, 'nes_expected': want, 'matches_nes': got == want})
print(json.dumps({'rom': Path(rom).name, 'flags': flags, 'routine': f'${box_routine:04X}', 'cases': res}, indent=0))
