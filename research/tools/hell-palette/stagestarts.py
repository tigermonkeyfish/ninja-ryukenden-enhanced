"""Stage entries in a palette mode (evidence b; as research/tools/gb-palette/
stagestarts.py): enter each listed stage as Level Select does (start_stage,
first update), step FRAMES frames and check every frame every VCE entry
against what the mode is due for the RAM palette (helltools.expected; entry
256 may hold the border colour or the queue's colour, as in gameplay).
Reports the frames with entries not yet due and the frame from which all
match; saves the screenshot at SHOT_AT for the SHOT stages.
usage: stagestarts.py ROM FLAGS FRAMES STAGES(comma|all) [SHOTS_DIR SHOT_STAGES(comma) TAG SHOT_AT]"""
import json
import sys
from pathlib import Path

from helltools import Session, cv, expected, ram_palette, vce_words


def main():
    rom, flags, frames = sys.argv[1], int(sys.argv[2], 0), int(sys.argv[3])
    stages = list(range(22)) if sys.argv[4] == 'all' else [int(s) for s in sys.argv[4].split(',')]
    shots = Path(sys.argv[5]) if len(sys.argv) > 5 else None
    shot_stages = {int(s) for s in sys.argv[6].split(',')} if len(sys.argv) > 6 else set()
    tag = sys.argv[7] if len(sys.argv) > 7 else hex(flags)
    shot_at = int(sys.argv[8]) if len(sys.argv) > 8 else frames - 1
    for stage in stages:
        bad_frames = []
        with Session(rom, flags) as g:
            cv.start_stage(g, stage)
            for n in range(frames):
                g.checked_step(1)
                ram = g.read(0, 0x2000)
                vce, pal = vce_words(g.read(0, 1024, area=8)), ram_palette(ram)
                border = ram[0x281] | ram[0x282] << 8
                mode = flags & 0x18 if ram[0x240] == 0 else 0
                want = expected(mode, pal, border)
                alt = expected(mode, pal, pal[256])[256]
                bad = [i for i in range(512) if vce[i] != want[i] and not (i == 256 and vce[i] == alt)]
                if bad:
                    bad_frames.append((n, len(bad), ram[0x260]))
                if shots and stage in shot_stages and n == shot_at:
                    shots.mkdir(parents=True, exist_ok=True)
                    (shots / f'start-{cv.STAGE_NAMES[stage]}-{tag}.png').write_bytes(g.screenshot())
        settled = (bad_frames[-1][0] + 1) if bad_frames else 0
        print(json.dumps({'stage': cv.STAGE_NAMES[stage], 'flags': flags, 'frames': frames,
                          'frames_not_due': len(bad_frames), 'all_due_from_frame': settled,
                          'not_due_frames': bad_frames[:12]}), flush=True)


if __name__ == '__main__':
    main()
