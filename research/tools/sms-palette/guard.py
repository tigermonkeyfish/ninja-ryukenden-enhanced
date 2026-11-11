"""Stack low-water mark (as ../gb-palette/guard.py, for the SMS build's layout:
$2104 is the palette module's state, so the watched margin is $2105-$213F).
At the first update, fill $2105 up to the stack pointer with $A5;
replay RUN with $2100 = FLAGS; at each MENU frame open the menu (Select),
force a full palette re-queue while it is open (the queue written as $F394
does, so the vblank upload runs its longest path under the menu's deepest
stack), close it (Select) and go on. Reports the lowest byte that changed.
The menu openings change the replay after them; this is a stack test only.
usage: guard.py ROM RUN FLAGS|orig MENU_FRAMES(comma)"""
import json
import sys

from smstools import Session, cv, load_run

rom, run_name = sys.argv[1], sys.argv[2]
flags = None if sys.argv[3] == 'orig' else int(sys.argv[3], 0)
menus = [int(x) for x in sys.argv[4].split(',')] if len(sys.argv) > 4 and sys.argv[4] else []
run = load_run(run_name)
inputs = [set(b) for c, b in run['segments'] for _ in range(c)] + [set()] * 60
with Session(rom, flags) as g:
    cv.start_stage(g, run['stage'])
    sp0 = int(g.call('get_huc6280_status')['S'], 16)
    g.write(0x105, bytes([0xA5]) * (0x100 + sp0 - 0x105 + 1))
    opened = 0
    for f, buttons in enumerate(inputs):
        if f in menus:
            g.press({'select'})
            g.checked_step(2)
            g.press(set())
            g.checked_step(10)
            if g.read(0x101, 1)[0] is not None:
                opened += 1
            g.write(0x260, bytes([1, 0, 0, 0, 0, 0, 0, 0, 0, 4]))
            g.write(0x271, bytes([0]))
            g.write(0x279, bytes([0]))
            g.checked_step(10)
            g.press({'select'})
            g.checked_step(2)
            g.press(set())
            g.checked_step(10)
        g.press(buttons)
        g.checked_step(1)
    page = g.read(0x100, 0x100)
low = next((0x2100 + i for i in range(5, 0x100) if page[i] != 0xA5), None)
print(json.dumps({'run': run_name, 'flags': sys.argv[3], 'sp_at_first_update': f'$21{sp0:02X}',
                  'menus': len(menus), 'low_water': f'${low:04X}' if low else None,
                  'above_margin_top_2140': (low - 0x2140) if low else None}))
