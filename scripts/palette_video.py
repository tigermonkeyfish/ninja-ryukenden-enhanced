#!/usr/bin/env python3
"""Six-panel palette montage: one stage run, six palette modes, frame-synced.

Each panel is a fresh headless session that loads one saved start state,
chooses the stage, palette mode and NES Firewheel option through the in-game
menu (Select, rows, Run: the way a player does), stops at the stage's first
update, then replays the stored input. See docs/COMPARISON-VIDEOS.md.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

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
    way = palette_presses('original', mode, 'right')
    for b in way:
        press(game, b)
    # Every mode presses the same number of buttons, so the menu takes the
    # same frames and the game's counters agree in all six panels: to the
    # reset row (Left/Right do nothing there), padded to five presses.
    press(game, 'down')
    press(game, 'down')
    for _ in range(5 - len(way)):
        press(game, 'right')
    game.press({'run'})
    game.step(2)
    game.press(set())
    if not stop_at(game, FIRST_UPDATE, 600):
        raise RuntimeError('stage did not restart')
    entered = Path(game.logdir) / 'entered2.state'
    game.call('save_state_file', {'file_path': str(entered)})
    game.call('load_state_file', {'file_path': str(entered)})
    game.held = set()


def record(emulator, rom, seed, run, stage, mode, firewheel, out, windows, audio=None, inputs=None, tail=0, shots=True):
    """Replay run's input; save PNGs for frames inside `windows` ([(a, b)),
    half-open, in frames since the first update) and a per-frame trace."""
    out = Path(out)
    if out.exists():
        shutil.rmtree(out)
    (out / 'frames').mkdir(parents=True)
    last = max(b for _, b in windows) + tail
    if inputs is None:
        inputs = []
        for count, buttons in run['segments']:
            inputs += [frozenset(buttons)] * count
    inputs = list(inputs) + [frozenset()] * max(0, last - len(inputs))
    trace, offsets = [], {}
    if audio:
        # The private audio-capture build appends 16-bit stereo 44.1 kHz
        # samples per frame to this file (profile/video-tools).
        os.environ['NG_AUDIO_DUMP'] = str(audio)
        os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
        os.environ.setdefault('NG_DEBUGGER_FAST', '1')
        Path(audio).unlink(missing_ok=True)
    with Game(emulator, out) as game:
        start_point(game, rom, seed, True)
        enter_stage(game, stage, mode, firewheel)
        for n in range(last):
            if audio:
                offsets[n] = Path(audio).stat().st_size if Path(audio).exists() else 0
            game.press(set(inputs[n]))
            game.checked_step(1)
            ram = game.read(0, 0x2000)
            trace.append({
                'f': n, 'sat': hashlib.sha1(game.read(0, 512, area=6)).hexdigest()[:12],
                'ryu': ram[0xe9e:0xeb8].hex(), 'timer': ram[0xeda:0xede].hex(),
                'stage': ram[0xe5f], 'area': ram[0xe60], 'lives': ram[0xeaf], 'health': ram[0xead],
                'cam': int.from_bytes(ram[0x20f:0x211], 'little'), 'master': ram[0x240],
                'fx': ram[0x110e:0x1113].hex(), 'wheel': ram[0x117a], 'state': ram[0xeab],
                'opt': ram[0x100]})
            if shots and any(a <= n < b for a, b in windows):
                (out / 'frames' / f'{n:06d}.png').write_bytes(game.screenshot())
    (out / 'trace.json').write_text(json.dumps(trace))
    if audio:
        (out / 'audio-offsets.json').write_text(json.dumps(offsets))
    return trace


# ---------------------------------------------------------------- rendering

W, H = 1920, 1080
PW, PH = 512, 448                      # each panel: 256x224 at 2x, nearest neighbour
GAP = 40
LEFT = (W - (3 * PW + 2 * GAP)) // 2
ROW_Y = (120, 616)                     # panel tops; labels sit 40 px above
GOLD, WHITE, GREY = '0xf2d060', 'white', '0xc8c8d4'


def panel_xy(i):
    return LEFT + (i % 3) * (PW + GAP), ROW_Y[i // 3]


def compose_clip(frame_dirs, first, count, banner, sub, out, fonts, watermark, tmp):
    """Six panels (`frame_dirs`, in MODES order), frames first..first+count-1
    of each, into a lossless FFV1 clip with the banner, labels and watermark."""
    tmp = Path(tmp)
    tmp.mkdir(parents=True, exist_ok=True)
    bold, semi, reg = fonts

    def text(name, content, font, size, color, x, y):
        f = tmp / f'{name}.txt'
        f.write_text(content)
        return (f"drawtext=fontfile={font}:textfile={f}:fontsize={size}:fontcolor={color}:"
                f"x={x}:y={y}:shadowcolor=black@0.6:shadowx=2:shadowy=2")

    draw = [text('banner', banner, bold, 46, WHITE, '(w-text_w)/2', 14),
            text('sub', sub, reg, 26, GREY, '(w-text_w)/2', 62)] if False else \
           [text('banner', banner, bold, 50, GOLD, '(w-text_w)/2', 12)]
    graph = [f'color=c=black:s={W}x{H}:r=60[bg]']
    last = 'bg'
    for i, mode in enumerate(MODES):
        x, y = panel_xy(i)
        graph.append(f'[{i}:v]crop=256:224:0:18,scale={PW}:{PH}:flags=neighbor,setsar=1[p{i}]')
        graph.append(f'[{last}][p{i}]overlay={x}:{y}:shortest=1[o{i}]')
        last = f'o{i}'
        draw.append(text(f'l{i}', LABELS[mode], semi, 32, WHITE, f'{x}+({PW}-text_w)/2', y - 42))
    graph.append(f'[{len(MODES)}:v]scale=96:96:flags=lanczos,format=rgba,colorchannelmixer=aa=0.85[wm]')
    graph.append(f'[{last}][wm]overlay={W - 96 - 40}:{H - 96 - 40},format=gbrp,' + ','.join(draw) + '[v]')
    (tmp / 'graph.txt').write_text(';'.join(graph))
    cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y']
    for d in frame_dirs:
        cmd += ['-framerate', '60', '-start_number', str(first), '-i', str(Path(d) / 'frames' / '%06d.png')]
    cmd += ['-i', str(watermark), '-/filter_complex', str(tmp / 'graph.txt'), '-map', '[v]',
            '-frames:v', str(count), '-r', '60', '-c:v', 'ffv1', '-level', '3', str(out)]
    subprocess.run(cmd, check=True)


def end_card(out, banner, fonts, lines, tmp):
    """The trailer's end card: the channel banner with text lines drawn over
    it. `lines` are (text, font index, size, colour, y)."""
    tmp = Path(tmp)
    tmp.mkdir(parents=True, exist_ok=True)
    draw = []
    for i, (content, font, size, color, y) in enumerate(lines):
        f = tmp / f'e{i}.txt'
        f.write_text(content)
        draw.append(f"drawtext=fontfile={fonts[font]}:textfile={f}:fontsize={size}:fontcolor={color}:"
                    f"x=(w-text_w)/2:y={y}:shadowcolor=black@0.6:shadowx=3:shadowy=3")
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(banner),
                    '-vf', f'scale={W}:{H}:flags=lanczos,format=rgb24,' + ','.join(draw),
                    '-frames:v', '1', str(out)], check=True)
