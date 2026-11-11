"""Level Select entries in HELL with the per-stage override (research
reference; research/tools/hell-palette/stagestarts.py with the expectation
of record11.py): enter each listed stage as Level Select does, step FRAMES
frames and check every frame every VCE entry against what HELL is due for
the RAM palette in the visible stage ($2E5F: 1-1's override of $094; the
global table elsewhere; raw colours in cinemas). Reports the frames with
entries not yet due, the frame from which all match, and how many due frames
hold colour $094 below entry 240 (and so show the override in 1-1, the
table's crimson elsewhere).
usage: stagestarts11.py ROM FLAGS FRAMES STAGES(comma|all)   (GB_WORK: seed.state, original.pce)"""
import json
import sys

from record11 import Session, bad_entries, cv, mode_due, ram_palette, vce_words


def main():
    rom, flags, frames = sys.argv[1], int(sys.argv[2], 0), int(sys.argv[3])
    stages = list(range(22)) if sys.argv[4] == 'all' else [int(s) for s in sys.argv[4].split(',')]
    for stage in stages:
        bad_frames, with_key = [], 0
        with Session(rom, flags) as g:
            cv.start_stage(g, stage)
            for n in range(frames):
                g.checked_step(1)
                ram = g.read(0, 0x2000)
                vce, pal = vce_words(g.read(0, 1024, area=8)), ram_palette(ram)
                border = ram[0x281] | ram[0x282] << 8
                mode = mode_due(flags) if ram[0x240] == 0 else 0
                bad = bad_entries(vce, pal, border, mode, ram[0xe5f])
                if bad:
                    bad_frames.append((n, len(bad), ram[0x260]))
                elif any(pal[i] & 0x1ff == 0x094 for i in range(240)):
                    with_key += 1
        settled = (bad_frames[-1][0] + 1) if bad_frames else 0
        print(json.dumps({'stage': cv.STAGE_NAMES[stage], 'flags': flags, 'frames': frames,
                          'frames_not_due': len(bad_frames), 'all_due_from_frame': settled,
                          'due_frames_with_094': with_key, 'not_due_frames': bad_frames[:8]}), flush=True)


if __name__ == '__main__':
    main()
