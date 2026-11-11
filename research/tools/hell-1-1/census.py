"""Where a colour is used (research reference, not a maintained tool): replay
stored runs ('run:NAME') or Level Select entries ('ls:INDEX:FRAMES', holding
right) and, every STEP frames in gameplay ($2240 = 0), list the background
VCE entries (0-239) whose RAM palette colour is COLOUR, by visible stage
($2E5F). Prints one JSON line per source: {stage: {entry: samples}}.
usage: census.py ROM FLAGS COLOUR STEP SOURCE...   (GB_WORK: seed.state, original.pce)"""
import json
import sys

sys.path.insert(0, __file__.rsplit('/', 2)[0] + '/hell-palette')
from helltools import Session, cv, load_run, ram_palette  # noqa: E402


def scan(g, frames, step, colour, out, buttons=None):
    for n in range(frames):
        g.checked_step(1)
        if n % step:
            continue
        ram = g.read(0, 0x2000)
        if ram[0x240]:
            continue
        pal = ram_palette(ram)
        st = cv.STAGE_NAMES[ram[0xe5f]] if ram[0xe5f] < 22 else str(ram[0xe5f])
        for i in range(240):
            if pal[i] & 0x1ff == colour:
                d = out.setdefault(st, {})
                d[i] = d.get(i, 0) + 1


def main():
    rom, flags, colour, step = sys.argv[1], int(sys.argv[2], 0), int(sys.argv[3], 16), int(sys.argv[4])
    for src in sys.argv[5:]:
        out = {}
        kind, *rest = src.split(':')
        with Session(rom, flags) as g:
            if kind == 'run':
                run = load_run(rest[0])
                cv.start_stage(g, run['stage'])
                for count, buttons in run['segments']:
                    g.press(set(buttons))
                    scan(g, count, step, colour, out)
            else:
                cv.start_stage(g, int(rest[0]))
                g.press({'right'})
                scan(g, int(rest[1]), step, colour, out)
        print(json.dumps({'source': src, 'colour': f'{colour:03X}', 'by_stage': out}), flush=True)


if __name__ == '__main__':
    main()
