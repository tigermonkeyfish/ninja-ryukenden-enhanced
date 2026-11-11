"""The first 1-1 update's frame when mashing Run from power-on, with settings
written by the debugger after the first frame (no backup RAM): which saved
settings move the boot by themselves, on any build.
usage: pokeboot.py ROM OPTIONS,LANGUAGE [OPTIONS,LANGUAGE ...]   (hex,decimal)"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts'))
from check_menu import FIRST_UPDATE  # noqa: E402
from comparison_video import Game  # noqa: E402


def boot(rom, options, language):
    with tempfile.TemporaryDirectory() as work, Game(os.environ['NG_EMULATOR'], work) as game:
        game.power_on(rom)
        game.call('set_breakpoint', {'address': FIRST_UPDATE, 'memory_area': 'rom', 'execute': True})
        for frame in range(3000):
            gameplay = game.read(0x240, 1)[0] == 0 and frame > 60
            game.press({'run'} if frame % 20 < 2 and not gameplay else set())
            game.step(1)
            if frame == 0:
                game.write(0x100, bytes([options]))
                game.write(0x1227, bytes([language]))
            if game.call('debug_get_status').get('pc') == '8457':
                return frame + 1


for pair in sys.argv[2:]:
    options, language = pair.split(',')
    print(Path(sys.argv[1]).name, pair, boot(sys.argv[1], int(options, 16), int(language)), flush=True)
