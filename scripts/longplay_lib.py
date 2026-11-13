"""Full-playthrough helpers: power-on with a backup-RAM mode to 1-1's first update.

Emulator evidence only (headless Geargrafx). The boot is the one palette_lag.py
e2e uses: power-on with backup RAM holding the settings entry for `mode`, the
title left with Run, the game's own start into 1-1, stop at 1-1's first update
($8457), save and reload that state so frame 0 is defined.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bram_image as bi                                              # noqa: E402
from comparison_video import Game                                    # noqa: E402

EMULATOR = Path('/workspace/build/toolchain/geargrafx/platforms/linux/geargrafx')
ROM = Path('/workspace/roms/Ninja Ryukenden - Enhanced v1.11-dev (apocalypse, reset 2, palette timing 2).pce')
MODE_BITS = {'original': 0x00, 'apocalypse': 0x18, 'nes-a': 0x08, 'nes-b': 0x28, 'sms': 0xb8, 'gb dmg': 0x10}
FIRST_UPDATE_ROM = 0x2457


def boot_to_first_update(game, rom, mode, entered):
    """Power on in `mode` (settings loaded from backup RAM) and stop at 1-1's first
    update; leaves the machine on a freshly reloaded state saved at `entered`.
    Returns status (opt byte, save status, boot frames)."""
    bram = bi.image([bi.settings_entry(options=MODE_BITS[mode])])
    game.power_on(rom, bram)
    previous, since, presses, pressed, title = None, 0, [200], False, False
    for frame in range(1, 20000):
        game.checked_step(1)
        since += 1
        master = bytes(game.read(0x240, 2))
        if master != previous:
            previous, since = master, 0
        if master == b'\x01\x01':
            title = True
        if master == b'\x01\x01' and since == 180 and not pressed:
            presses.append(frame)
            pressed = True
        if master in (b'\x00\x00', b'\x01\x00') and since % 300 == 150 and not title:
            presses.append(frame)
        for p in presses:
            if frame == p:
                game.call('controller_button', {'player': 1, 'button': 'run', 'action': 'press'})
            elif frame == p + 2:
                game.call('controller_button', {'player': 1, 'button': 'run', 'action': 'release'})
        if title and master[0] == 0 and frame > presses[-1] + 2:
            break
    else:
        raise RuntimeError('gameplay not reached')
    status = {'opt': game.read(0x100, 1)[0], 'save_status': game.read(0x105, 1)[0], 'boot_frames': frame}
    game.call('set_breakpoint', {'address': f'{FIRST_UPDATE_ROM:x}', 'memory_area': 'rom', 'execute': True})
    game.run_to('8457', polls=400000)
    game.call('remove_breakpoint', {'address': f'{FIRST_UPDATE_ROM:x}', 'memory_area': 'rom'})
    game.call('save_state_file', {'file_path': str(entered)})
    game.call('load_state_file', {'file_path': str(entered)})
    game.held = set()
    return status


def play_segments(game, segments, chunk=500):
    """Replay [frames, [buttons]] segments one frame step request at a time
    (the emulator caps a step at 1000 frames), checking every step."""
    for count, buttons in segments:
        game.press(set(buttons))
        while count > 0:
            n = min(count, chunk)
            game.checked_step(n)
            count -= n
