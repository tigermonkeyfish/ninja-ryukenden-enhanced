"""Stage entries in a palette mode (evidence b): enter each listed stage as
Level Select does (start_stage, first update), step FRAMES frames and check,
every frame, every VCE entry against the RAM palette: GB DMG = the table value
(index 256 may hold the mapped border), Original = the RAM word. Reports
the frames with mismatches; saves the last frame's screenshot for SHOT stages.
usage: stagestarts.py ROM FLAGS FRAMES STAGES(comma) [SHOTS_DIR SHOT_STAGES(comma) TAG]"""
import json
import sys
from pathlib import Path

from gbtools import Session, cv, ram_palette, vce_words
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts'))
from palette_tables import gb_dmg_table  # noqa: E402

GB = gb_dmg_table()


def main():
    rom, flags, frames = sys.argv[1], int(sys.argv[2], 0), int(sys.argv[3])
    stages = [int(s) for s in sys.argv[4].split(',')]
    shots = Path(sys.argv[5]) if len(sys.argv) > 5 else None
    shot_stages = {int(s) for s in sys.argv[6].split(',')} if len(sys.argv) > 6 else set()
    tag = sys.argv[7] if len(sys.argv) > 7 else hex(flags)
    f = (lambda c: GB[c & 0x1ff]) if flags & 0x18 == 0x10 else (lambda c: c)
    for stage in stages:
        bad_frames = []
        with Session(rom, flags) as g:
            cv.start_stage(g, stage)
            for n in range(frames):
                g.checked_step(1)
                ram = g.read(0, 0x2000)
                vce, pal = vce_words(g.read(0, 1024, area=8)), ram_palette(ram)
                border = f(ram[0x281] | ram[0x282] << 8)
                bad = [i for i in range(512) if vce[i] != f(pal[i]) and not (i == 256 and vce[i] == border)]
                if bad:
                    bad_frames.append((n, len(bad), ram[0x260]))
                last = [(i, hex(pal[i]), hex(vce[i])) for i in bad[:8]]
            if shots and stage in shot_stages:
                shots.mkdir(parents=True, exist_ok=True)
                name = cv.STAGE_NAMES[stage]
                (shots / f'start-{name}-{tag}.png').write_bytes(g.screenshot())
        print(json.dumps({'stage': cv.STAGE_NAMES[stage], 'flags': flags, 'frames': frames,
                          'count': len(bad_frames), 'last_frame_bad': last,
                          'mismatch_frames': bad_frames[:20]}), flush=True)


if __name__ == '__main__':
    main()
