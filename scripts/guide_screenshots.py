#!/usr/bin/env python3
"""Make the screenshots for docs/OPTIONS.md from an Enhanced ROM.

Plays the ROM in headless Geargrafx with real button input: leaves the
splash, cycles the title screen's language, starts 1-1, opens the in-game
menu and changes each setting, checking the game's own bytes at each step.
Writes the few how-to images that scripts/audit_public.py allows
(GUIDE_IMAGES); nothing else from the emulator is kept.
"""
import argparse
from pathlib import Path
import subprocess
import tempfile

from audit_public import GUIDE_IMAGES
from comparison_video import Game

LANGUAGE = 0x1227          # $3227: 0 Japanese, 1 English, 2 Chinese
DRAFT = 0x0101             # $2101: menu settings before I applies them
TITLE_ROWS = (28, 88)      # logo and subtitle line
MENU_ROWS = (16, 19)       # the two menu lines that replace the score bar
SCREEN_ROWS = (18, 224)    # the visible display


def tap(game, buttons, hold=(), after=12):
    game.press(set(hold) | set(buttons))
    game.step(2)
    game.press(set(hold))
    game.step(after)


def expect(game, address, value, what):
    actual = game.read(address, 1)[0]
    if actual != value:
        raise RuntimeError(f'{what}: expected {value:#04x} at {address:#06x}, found {actual:#04x}')


def to_title(game):
    """Leave the splash and the intro with Run; stop on the title screen."""
    game.step(60)
    tap(game, {'run'}, after=1)
    previous, since = None, 0
    for _ in range(6000):
        master = game.read(0x240, 2)
        if master != previous:
            previous, since = master, 0
        if master == b'\x01\x00' and since in (400, 700, 1000):
            tap(game, {'run'}, after=1)
        if master == b'\x01\x01' and since == 150:
            return
        game.step(1)
        since += 1
    raise RuntimeError('Title screen not reached')


def to_gameplay(game):
    game.call('set_breakpoint', {'address': '23f3', 'memory_area': 'rom', 'execute': True})
    tap(game, {'run'}, after=1)
    for _ in range(8000):
        game.step(1)
        status = game.call('debug_get_status')
        if status.get('at_breakpoint') and status['pc'] == '83F3':
            break
    else:
        raise RuntimeError('Gameplay not reached')
    game.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'})
    game.step(150)


def capture(game, rom, shots):
    game.call('load_media', {'file_path': str(rom)})
    game.call('debug_pause')
    to_title(game)
    expect(game, LANGUAGE, 1, 'English by default')
    shots['english'] = game.screenshot()
    for name, value in (('chinese', 2), ('japanese', 0), (None, 1)):
        # Hold I + II and press Select: the original game's language switch.
        game.press({'I', 'II'})
        game.step(4)
        tap(game, {'select'}, hold={'I', 'II'}, after=4)
        game.press(set())
        game.step(40)
        expect(game, LANGUAGE, value, f'language after Select ({name or "english"})')
        if name:
            shots[name] = game.screenshot()
    to_gameplay(game)
    tap(game, {'select'}, after=30)
    expect(game, DRAFT, 0, 'menu opens on the defaults')
    shots['menu'] = game.screenshot()
    for _ in range(5):                       # 1-1 -> 1-2 -> 2-1 -> 2-2 -> 2-3 -> 3-1
        tap(game, {'right'}, after=8)
    shots['menu-stage'] = game.screenshot()
    tap(game, {'down'})
    tap(game, {'right'})
    expect(game, DRAFT, 1, 'parallax ORIGINAL')
    shots['menu-parallax'] = game.screenshot()
    tap(game, {'down'})
    tap(game, {'right'})
    expect(game, DRAFT, 3, 'NO DAMAGE ON')
    shots['menu-no-damage'] = game.screenshot()
    tap(game, {'II'}, after=30)
    expect(game, 0x0100, 0, 'II leaves the settings unchanged')


def ffmpeg(inputs, graph, out):
    command = ['ffmpeg', '-v', 'error', '-y']
    for path in inputs:
        command += ['-i', str(path)]
    subprocess.run(command + ['-filter_complex', graph, '-frames:v', '1', str(out)], check=True)


def compose(shots, work, out):
    paths = {}
    for name, png in shots.items():
        paths[name] = work / f'{name}.png'
        paths[name].write_bytes(png)
    out.mkdir(parents=True, exist_ok=True)
    top, height = TITLE_ROWS
    gap = 'pad=iw:ih+4:0:0:color=0x444444'
    ffmpeg([paths['english'], paths['chinese'], paths['japanese']],
           f'[0]crop=256:{height}:0:{top},{gap}[a];[1]crop=256:{height}:0:{top},{gap}[b];'
           f'[2]crop=256:{height}:0:{top}[c];[a][b][c]vstack=3,scale=iw*2:ih*2:flags=neighbor',
           out / 'title-languages.png')
    top, height = SCREEN_ROWS
    ffmpeg([paths['menu']], f'crop=256:{height}:0:{top},scale=iw*2:ih*2:flags=neighbor', out / 'menu.png')
    top, height = MENU_ROWS
    for name in ('menu-stage', 'menu-parallax', 'menu-no-damage'):
        ffmpeg([paths[name]], f'crop=256:{height}:0:{top},pad=iw:ih+2:0:0:black,scale=iw*3:ih*3:flags=neighbor',
               out / f'{name}.png')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--emulator', type=Path, required=True)
    parser.add_argument('--rom', type=Path, required=True, help='Enhanced ROM')
    parser.add_argument('--out', type=Path, default=Path(__file__).resolve().parents[1] / 'docs/images/options')
    args = parser.parse_args()
    shots = {}
    with tempfile.TemporaryDirectory(prefix='guide-screenshots-') as temp:
        work = Path(temp)
        with Game(args.emulator, work / 'log') as game:
            capture(game, args.rom.resolve(), shots)
        compose(shots, work, args.out)
    root = Path(__file__).resolve().parents[1]
    written = sorted(str(p.resolve().relative_to(root)) for p in args.out.glob('*.png'))
    if written != sorted(GUIDE_IMAGES):
        raise RuntimeError(f'Images differ from the allowed list: {written}')
    for name in written:
        print('wrote', name, (root / name).stat().st_size, 'bytes')


if __name__ == '__main__':
    main()
