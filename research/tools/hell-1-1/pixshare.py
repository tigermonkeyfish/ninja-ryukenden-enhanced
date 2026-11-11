"""Share of pixels that differ between two builds over a stored run in one
mode (research reference): both ROMs replayed in lockstep (two fresh
sessions from the shared start state), every STEP-th frame's screenshots
compared pixel by pixel. Reports, over the frames compared, the mean and
largest share of differing pixels (of the whole 256 x 242 picture and of
the playfield, rows 51 and below: the HUD is above), per area ($2E60) as
well, and the frames where nothing differs.
usage: pixshare.py ROM_A ROM_B RUN FLAGS [STEP]   (GB_WORK: seed.state, original.pce)"""
import io
import json
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'gb-palette'))
from gbtools import Session, cv, load_run  # noqa: E402

TOP = 51


def pixels(png):
    im = Image.open(io.BytesIO(png)).convert('RGB')
    return im.size, im.tobytes()


def main():
    rom_a, rom_b, name, flags = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4], 0)
    step = int(sys.argv[5]) if len(sys.argv) > 5 else 1
    run = load_run(name)
    inputs = [b for c, b in run['segments'] for _ in range(c)]
    rows, by_area = [], {}
    with Session(rom_a, flags) as a, Session(rom_b, flags) as b:
        cv.start_stage(a, run['stage'])
        cv.start_stage(b, run['stage'])
        for f, buttons in enumerate(inputs):
            a.press(set(buttons))
            b.press(set(buttons))
            a.checked_step(1)
            b.checked_step(1)
            if f % step:
                continue
            ram = a.read(0, 0x2000)
            if ram[0x240]:
                continue
            (w, h), pa = pixels(a.screenshot())
            _, pb = pixels(b.screenshot())
            diff = [k for k in range(0, len(pa), 3) if pa[k:k + 3] != pb[k:k + 3]]
            field = sum(1 for k in diff if k // 3 // w >= TOP)
            share, fshare = len(diff) / (w * h), field / (w * (h - TOP))
            rows.append((f, share, fshare))
            by_area.setdefault(ram[0xe60], []).append(fshare)
    summary = {'run': name, 'flags': flags, 'frames_compared': len(rows),
               'mean_share': round(100 * sum(r[1] for r in rows) / len(rows), 3),
               'max_share': round(100 * max(r[1] for r in rows), 3),
               'mean_playfield_share': round(100 * sum(r[2] for r in rows) / len(rows), 3),
               'max_playfield_share': round(100 * max(r[2] for r in rows), 3),
               'max_at': max(rows, key=lambda r: r[2])[0],
               'frames_identical': sum(1 for r in rows if r[1] == 0),
               'playfield_share_by_area': {k: [round(100 * sum(v) / len(v), 3), round(100 * max(v), 3), len(v)]
                                           for k, v in sorted(by_area.items())}}
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    main()
