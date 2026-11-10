"""Replay one stored comparison run (comparison_video `record`: start_point,
start_stage, the run's segments + 60 tail frames, checked one-frame steps)
and log, per frame: SHA-1 of the screenshot, of the VCE (512 words) and of
game RAM (outside comparison_video.OWNED), the gameplay fields, the palette
queue, and how the VCE relates to the RAM palette $2286:
  'raw'  = VCE entries that differ from the RAM palette word,
  'gb'   = VCE entries that differ from the GB DMG table value of the RAM word
(index 256 is also compared with the border colour $2281/$2282, which the
upload writes there; an entry counts as matching if either agrees).
usage: record.py ROM RUN OUT.json FLAGS|orig [SHOTS_DIR FRAME,FRAME,...]"""
import json
import sys
from pathlib import Path

from gbtools import Session, cv, h, load_run, ram_palette, vce_words, queue

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts'))
from palette_tables import gb_dmg_table  # noqa: E402

GB = gb_dmg_table()


def diff(vce, pal, border, f=lambda c: c):
    bad = []
    for i in range(512):
        want = f(pal[i])
        if vce[i] != want and not (i == 256 and vce[i] == f(border)):
            bad.append(i)
    return bad


def ranges(idx):
    out = []
    for i in idx:
        if out and out[-1][1] == i - 1:
            out[-1][1] = i
        else:
            out.append([i, i])
    return out


def main():
    rom, run_name, out = sys.argv[1:4]
    flags = None if sys.argv[4] == 'orig' else int(sys.argv[4], 0)
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
                    trace.append({
                        'f': n, 'png': h(png), 'vce': h(vce_raw),
                        'ram': h(bytes(b for k, b in enumerate(ram) if k not in cv.OWNED)),
                        'sat': h(game.read(0, 512, area=6)),
                        'ryu': ram[0xe9e:0xeb8].hex(), 'timer': ram[0xeda:0xede].hex(),
                        'stage': ram[0xe5f], 'area': ram[0xe60], 'lives': ram[0xeaf],
                        'health': ram[0xead], 'cam': int.from_bytes(ram[0x20f:0x211], 'little'),
                        'master': ram[0x240], 'boss': ram[0x1035], 'opts': ram[0x100],
                        'q': ents, 'qn': qn, 'lock': ram[0x283],
                        'raw': ranges(diff(vce, pal, border)),
                        'gb': ranges(diff(vce, pal, border, lambda c: GB[c & 0x1ff]))})
                    n += 1
        return trace

    trace = cv.retried(once)
    Path(out).write_text(json.dumps(trace))
    print(Path(rom).name, run_name, sys.argv[4], len(trace), 'frames', flush=True)


if __name__ == '__main__':
    main()
