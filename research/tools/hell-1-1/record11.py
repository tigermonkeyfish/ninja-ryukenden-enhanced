"""Replay one stored comparison run and log per frame what
research/tools/sms-palette/record.py logs (the same fields and format, so
its analyse.py compares these recordings with the all-palettes build's),
with HELL's VCE expectation per visible stage: in HELL gameplay entries
0-239 are due for hell_stage_table($2E5F) (1-1's override of $094), not the
global table; every other mode as smstools.expected.
usage: record.py ROM RUN OUT.json FLAGS [SHOTS_DIR FRAME,FRAME,...]
(GB_WORK: seed.state, original.pce)"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'sms-palette'))
import record as base  # noqa: E402
from smstools import HELL_MAPPED, SMS64, Session, cv, expected, h, load_run, mode_due, queue, ram_palette, vce_words  # noqa: E402,F401
from palette_tables import hell_stage_table  # noqa: E402

STAGE_TABLES = {s: hell_stage_table(s) for s in range(22)}


def expected_at(mode, pal, border, stage):
    if mode != 0x18:
        return expected(mode, pal, border)
    table = STAGE_TABLES.get(stage, STAGE_TABLES[1])
    words = list(pal)
    words[256] = border
    return [table[c & 0x1ff] if i < HELL_MAPPED else c & 0x1ff for i, c in enumerate(words)]


def bad_entries(vce, pal, border, mode, stage):
    want = expected_at(mode, pal, border, stage)
    alt = expected_at(mode, pal, pal[256], stage)[256]
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
                        'nonsms': sum(1 for c in vce if c & 0x1ff not in SMS64),
                        'pix': base.channel_values(png),
                        'q': ents, 'qn': qn, 'lock': ram[0x283],
                        'ovr': [i for i in range(240) if ram[0x240] == 0 and pal[i] & 0x1ff == 0x094],
                        'bad': base.ranges(bad_entries(vce, pal, border, mode, ram[0xe5f]))})
                    n += 1
        return trace

    trace = cv.retried(once)
    Path(out).write_text(json.dumps(trace))
    worst = max((sum(b - a + 1 for a, b in e['bad']) for e in trace), default=0)
    print(Path(rom).name, run_name, sys.argv[4], len(trace), 'frames;',
          sum(1 for e in trace if e['bad']), 'frames with VCE entries not yet due; most at once', worst, flush=True)


if __name__ == '__main__':
    main()
