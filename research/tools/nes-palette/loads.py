"""Every palette load the game makes: execute breakpoints on the set loader
$F211 (A = set), the sprite palette loader $F1C0 (A = palette, X = sprite
row) and the HUD colour writer (bank 1 $83C3), with the stage $2E5F, area
$2E60, master state $2240 and MPR3 at each call. Modes: `stages` enters every
Level Select entry and steps FRAMES frames; `runs` replays stored runs.
usage: loads.py ROM FLAGS stages FRAMES [stage,..] | loads.py ROM FLAGS runs [name,..]"""
import collections
import json
import sys

from ntools import RUN_NAMES, Session, cv, enter_stage, load_run, step_frame

STOPS = ('1211', '11c0', '23c3')
NAMES = {'F211': 'set', 'F1C0': 'sprite', '83C3': 'hud'}


def main():
    rom, flags, mode = sys.argv[1], int(sys.argv[2], 0), sys.argv[3]
    log = []
    frame = [0]
    where = ['load']

    def on_stop(g, st):
        cpu = g.call('get_huc6280_status')
        ram = g.read(0x240, 1) + g.read(0xe5f, 2)
        log.append({'at': where[0], 'frame': frame[0], 'what': NAMES.get(cpu['PC'], cpu['PC']),
                    'a': int(cpu['A'], 16), 'x': int(cpu['X'], 16), 'state': ram[0], 'stage': ram[1], 'area': ram[2],
                    'mpr3': cpu['MPR'][3]['value'] if isinstance(cpu['MPR'][3], dict) else cpu['MPR'][3]})

    if mode == 'stages':
        frames = int(sys.argv[4])
        stages = [int(s) for s in sys.argv[5].split(',')] if len(sys.argv) > 5 else range(22)
        for stage in stages:
            with Session(rom, flags) as g:
                where[0], frame[0] = f'ls{stage}', -1
                enter_stage(g, stage, on_stop, STOPS)
                for a in STOPS:
                    g.call('set_breakpoint', {'address': a, 'memory_area': 'rom', 'execute': True})
                for n in range(frames):
                    frame[0] = n
                    step_frame(g, on_stop)
    else:
        names = sys.argv[4].split(',') if len(sys.argv) > 4 else RUN_NAMES
        for name in names:
            run = load_run(name)
            with Session(rom, flags) as g:
                where[0], frame[0] = name, -1
                enter_stage(g, run['stage'], on_stop, STOPS)
                for a in STOPS:
                    g.call('set_breakpoint', {'address': a, 'memory_area': 'rom', 'execute': True})
                n = 0
                for count, buttons in run['segments'] + [[60, []]]:
                    g.press(set(buttons))
                    for _ in range(count):
                        frame[0] = n
                        step_frame(g, on_stop)
                        n += 1
    summary = collections.Counter((e['at'], e['what'], e['a'], e['x'] if e['what'] == 'sprite' else 0, e['stage'], e['state'])
                                  for e in log)
    for k, v in sorted(summary.items()):
        print(json.dumps({'at': k[0], 'what': k[1], 'a': k[2], 'x': k[3], 'stage': k[4], 'state': k[5], 'calls': v}))
    print(json.dumps({'log': log}))


if __name__ == '__main__':
    main()
