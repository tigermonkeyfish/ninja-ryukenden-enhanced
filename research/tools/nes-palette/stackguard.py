"""Evidence e (stack): the stack's low-water mark in a mode. At the shared
start state (the main-loop hook in 1-1) the stack page below the stack
pointer down to $2104 (the watched margin starts below it) is filled with
$A5; then each listed stage is entered as Level Select does (its load, with
the NES loaders' deeper calls) and, for a stored run's stage, the run is
replayed (its area changes call the HUD routine). Reports the lowest byte
written. usage: stackguard.py ROM FLAGS [runs,..]"""
import json
import sys

from ntools import RUN_NAMES, Session, cv, load_run


def main():
    rom, flags = sys.argv[1], int(sys.argv[2], 0)
    names = sys.argv[3].split(',') if len(sys.argv) > 3 else RUN_NAMES
    out = {}
    for name in names:
        run = load_run(name)
        with Session(rom, flags) as g:
            s = int(g.call('get_huc6280_status')['S'], 16)
            g.write(0x104, b'\xa5' * (s - 0x04 + 1))
            cv.start_stage(g, run['stage'])
            for count, buttons in run['segments'] + [[60, []]]:
                g.press(set(buttons))
                g.checked_step(count)
            page = g.read(0x100, 0x100)
            low = next(i for i in range(4, 0x100) if page[i] != 0xa5)
            out[name] = f'${0x2100 + low:04X}'
            print(name, out[name], flush=True)
    print(json.dumps({'flags': flags, 'low_water': out, 'lowest': min(out.values())}))


if __name__ == '__main__':
    main()
