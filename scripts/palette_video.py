#!/usr/bin/env python3
"""Six-panel palette montage: one stage run, six palette modes, frame-synced.

Each panel is a fresh headless session that loads one saved start state,
chooses the stage, palette mode and NES Firewheel option through the in-game
menu (Select, rows, Run: the way a player does), stops at the stage's first
update, then replays the stored input. See docs/COMPARISON-VIDEOS.md.
"""
import hashlib
import json
from pathlib import Path
import shutil

from comparison_video import Game, start_point, start_stage, make_seed, StepError
from check_menu import press, stop_at, FIRST_UPDATE, palette_presses, MODE

MODES = ['original', 'apocalypse', 'sms', 'nes-a', 'nes-b', 'gb dmg']
LABELS = {'original': 'ORIGINAL', 'apocalypse': 'APOCALYPSE', 'sms': 'SMS',
          'nes-a': 'NES-A', 'nes-b': 'NES-B', 'gb dmg': 'GB DMG'}


def enter_stage(game, stage, mode, firewheel):
    """From the loaded 1-1 state: play 1-1 briefly, then open the menu and
    Run into `stage` with the palette `mode` and the NES Firewheel setting."""
    game.write(0x1227, b'\x01')                     # English, as Enhanced's reset default
    start_stage(game, 0)
    game.step(30)
    press(game, 'select', after=6)
    for _ in range(stage):
        press(game, 'right')                        # STAGE row
    for _ in range(3):
        press(game, 'down')                         # to NES FIREWHEEL
    if firewheel:
        press(game, 'right')
    press(game, 'down')                             # PALETTE
    for b in palette_presses('original', mode, 'right'):
        press(game, b)
    game.press({'run'})
    game.step(2)
    game.press(set())
    if not stop_at(game, FIRST_UPDATE, 600):
        raise RuntimeError('stage did not restart')
    entered = Path(game.logdir) / 'entered2.state'
    game.call('save_state_file', {'file_path': str(entered)})
    game.call('load_state_file', {'file_path': str(entered)})
    game.held = set()


def record(emulator, rom, seed, run, stage, mode, firewheel, out, windows, trace_all=True):
    """Replay run's input; save PNGs for frames inside `windows` ([(a, b)),
    half-open, in frames since the first update) and a per-frame trace."""
    out = Path(out)
    if out.exists():
        shutil.rmtree(out)
    (out / 'frames').mkdir(parents=True)
    last = max(b for _, b in windows)
    inputs = []
    for count, buttons in run['segments']:
        inputs += [frozenset(buttons)] * count
    inputs += [frozenset()] * max(0, last - len(inputs))
    trace = []
    with Game(emulator, out) as game:
        start_point(game, rom, seed, True)
        enter_stage(game, stage, mode, firewheel)
        for n in range(last):
            game.press(set(inputs[n]))
            game.checked_step(1)
            ram = game.read(0, 0x2000)
            trace.append({
                'f': n, 'sat': hashlib.sha1(game.read(0, 512, area=6)).hexdigest()[:12],
                'ryu': ram[0xe9e:0xeb8].hex(), 'timer': ram[0xeda:0xede].hex(),
                'stage': ram[0xe5f], 'area': ram[0xe60], 'lives': ram[0xeaf], 'health': ram[0xead],
                'cam': int.from_bytes(ram[0x20f:0x211], 'little'), 'master': ram[0x240],
                'fx': ram[0x10e:0x113].hex(), 'wheel': ram[0x117a], 'state': ram[0xeab],
                'opt': ram[0x100]})
            if any(a <= n < b for a, b in windows):
                (out / 'frames' / f'{n:06d}.png').write_bytes(game.screenshot())
    (out / 'trace.json').write_text(json.dumps(trace))
    return trace
