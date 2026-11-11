"""The stack's low-water mark of the reset loader and of the menu's save
(evidence for docs/validation/bram-save.md). At the routine's entry the
stack page from $2106 (the first byte of the watched margin since $2105
holds the save status) up to the stack pointer is filled with $A5; at its
return the lowest byte written is the deepest the routine reached.

- loader: from the reset trampoline ($FFE6) to the native init ($FCBE);
- save: in the open menu (Select in 1-1, one setting changed, Run) from the
  save's entry (bank $46 $4B03) to its return in the menu, on top of what
  the menu and the Select hook keep there.

usage: stackguard.py ROM
"""
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts'))
import bram_image as bi  # noqa: E402
from check_bram import ROWS, SAVE_ENTRY, boot, change, continue_to, open_menu  # noqa: E402
from comparison_video import Game  # noqa: E402

rom = sys.argv[1]
EMU = os.environ['NG_EMULATOR']
cases = bi.matrix()
FILL = 0x106


def measure(game, stop):
    s = int(game.call('get_huc6280_status')['S'], 16)
    game.write(FILL, b'\xa5' * (0x100 + s - FILL + 1))
    game.call('set_breakpoint', {'address': stop, 'memory_area': 'rom', 'execute': True})
    continue_to(game)
    page = game.read(FILL, 0x100 + s - FILL + 1)
    low = next((i for i, b in enumerate(page) if b != 0xa5), len(page))
    return {'entry_s': f'${0x2100 + s:04X}', 'lowest_written': f'${0x2000 + FILL + low:04X}',
            'bytes_used': 0x100 + s - FILL + 1 - low, 'status': bi.STATUS[game.read(0x105, 1)[0]]}


out = {'loader': {}, 'save': {}}
for name in ('absent', 'empty-8800', 'others-before', 'ours-bad-checksum', 'tiny-entries-ours-last', 'garbage'):
    with tempfile.TemporaryDirectory() as work, Game(EMU, work) as game:
        game.power_on(rom, cases[name])
        game.call('set_breakpoint', {'address': '1fe6', 'memory_area': 'rom', 'execute': True})
        assert continue_to(game) == 'FFE6'
        out['loader'][name] = measure(game, '1cbe')
        print('loader', name, out['loader'][name], flush=True)
call = Path(rom).read_bytes().index(bytes.fromhex('20034b'), 0x46 * 0x2000 + 0x400, 0x46 * 0x2000 + 0xb00)
for name in ('absent', 'others-only', 'others-before', 'blank-ff', 'blank-00-last-byte', 'tiny-entries-ours-last',
             'pointer-stale-high', 'full'):
    with tempfile.TemporaryDirectory() as work, Game(EMU, work) as game:
        boot(game, rom, cases[name], Path(work))
        assert open_menu(game) is not None
        change(game, ROWS['no damage'], ['right'])
        game.press({'run'})
        game.step(2)
        game.call('set_breakpoint', {'address': f'{SAVE_ENTRY:x}', 'memory_area': 'rom', 'execute': True})
        game.press(set())
        assert continue_to(game) == '4B03'
        out['save'][name] = measure(game, f'{call + 3:x}')
        print('save', name, out['save'][name], flush=True)
lowest = min(int(v['lowest_written'][1:], 16) for part in out.values() for v in part.values())
print(json.dumps({'lowest_written': f'${lowest:04X}', 'margin_from_2140': lowest - 0x2140}))
