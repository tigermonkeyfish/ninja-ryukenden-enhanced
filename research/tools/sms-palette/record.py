"""Replay one stored comparison run (as research/tools/gb-palette/record.py:
start_point, start_stage, the run's segments + 60 tail frames, checked
one-frame steps) and log per frame: SHA-1 of the screenshot, of the VCE, of
the sprite table and of game RAM (outside comparison_video.OWNED), the
gameplay fields, $2100 and $2104 (the palette module's state since the SMS
build), the palette queue, and 'bad': the VCE entries that differ from what
the session's mode is due for the RAM palette (smstools.expected: Original
raw, GB DMG the GB table, HELL the HELL table below entry 240 and raw from
it, SMS the SMS table; entry 256 also matches the raw or mapped border
colour, as in gameplay the upload writes it after the queue). Cinema,
title and ending frames ($2240 != 0) are compared with raw colours. Also
per frame: 'nonsms', the VCE entries whose colour is not one of the 64 SMS
colours, and 'pix', the distinct 8-bit channel values in the screenshot
(what is on screen; analyse.py compares them with what the emulator shows
for PC Engine channel values 0, 2, 5 and 7).
usage: record.py ROM RUN OUT.json FLAGS [SHOTS_DIR FRAME,FRAME,...]"""
import io
import json
import sys
from pathlib import Path

from PIL import Image

from smstools import SMS64, Session, cv, expected, h, load_run, mode_due, queue, ram_palette, vce_words


def channel_values(png):
    """The distinct 8-bit channel values of a screenshot's pixels."""
    colours = Image.open(io.BytesIO(png)).convert('RGB').getcolors(1 << 16)
    return sorted({v for _, rgb in colours for v in rgb})


def ranges(idx):
    out = []
    for i in idx:
        if out and out[-1][1] == i - 1:
            out[-1][1] = i
        else:
            out.append([i, i])
    return out


def bad_entries(vce, pal, border, mode):
    want = expected(mode, pal, border)
    alt = expected(mode, pal, pal[256])[256]       # entry 256 as the queue left it, before the border
    return [i for i in range(512) if vce[i] != want[i] and not (i == 256 and vce[i] == alt)]


def main():
    rom, run_name, out = sys.argv[1:4]
    flags = int(sys.argv[4], 0)
    shots = Path(sys.argv[5]) if len(sys.argv) > 5 else None
    shot_frames = {int(x) for x in sys.argv[6].split(',')} if len(sys.argv) > 6 else set()
    run = load_run(run_name)

    def once():
        trace, n = [], 0
        with Session(rom, flags) as game:
            cv.start_stage(game, run['stage'])
            for count, buttons in run['segments'] + [[60, []]]:
                game.press(set(buttons))
                for _ in range(count):
                    game.checked_step(1)
                    png = game.screenshot()
                    if n in shot_frames:
                        shots.mkdir(parents=True, exist_ok=True)
                        (shots / f'{run_name}-{n:05d}.png').write_bytes(png)
                    ram = game.read(0, 0x2000)
                    vce_raw = game.read(0, 1024, area=8)
                    vce, pal = vce_words(vce_raw), ram_palette(ram)
                    border = ram[0x281] | ram[0x282] << 8
                    qn, ents = queue(ram)
                    mode = mode_due(flags) if ram[0x240] == 0 else 0
                    trace.append({
                        'f': n, 'png': h(png), 'vce': h(vce_raw),
                        'ram': h(bytes(b for k, b in enumerate(ram) if k not in cv.OWNED)),
                        'sat': h(game.read(0, 512, area=6)),
                        'ryu': ram[0xe9e:0xeb8].hex(), 'timer': ram[0xeda:0xede].hex(),
                        'stage': ram[0xe5f], 'area': ram[0xe60], 'lives': ram[0xeaf],
                        'health': ram[0xead], 'cam': int.from_bytes(ram[0x20f:0x211], 'little'),
                        'master': ram[0x240], 'boss': ram[0x1035], 'opts': ram[0x100], 'st': ram[0x104],
                        'nonsms': sum(1 for c in vce if c & 0x1ff not in SMS64), 'pix': channel_values(png),
                        'q': ents, 'qn': qn, 'lock': ram[0x283],
                        'bad': ranges(bad_entries(vce, pal, border, mode))})
                    n += 1
        return trace

    trace = cv.retried(once)
    Path(out).write_text(json.dumps(trace))
    worst = max((sum(b - a + 1 for a, b in e['bad']) for e in trace), default=0)
    print(Path(rom).name, run_name, sys.argv[4], len(trace), 'frames;',
          sum(1 for e in trace if e['bad']), 'frames with VCE entries not yet due; most at once', worst, flush=True)


if __name__ == '__main__':
    main()
