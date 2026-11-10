"""trace / ident replays of a stored run with an optional Fire Wheel grant.

survey.py trace ROM RUN FLAGS GRANT N OUT.json
survey.py ident ROM RUN FLAGS GRANT FRAME
FLAGS: 'orig' for the unmodified game, else the $2100 value. GRANT: -1 for none.
"""
import json
import sys
from fw import *
import os
GRANT_ROUTINE = int(os.environ.get('GRANT_ROUTINE', 'a919'), 16)


def replay(game, rom, run, flags, grant, n, on_frame=None, before_frame=None):
    inputs = frames_of(run)
    begin(game, rom, run['stage'], flags)
    log = []
    for f in range(n):
        held = inputs[f] if f < len(inputs) else set()
        if f == grant:
            game.press(set())
            call_native(game, GRANT_ROUTINE)
        game.press(held)
        if before_frame and before_frame(game, f):
            return log
        game.checked_step(1)
        s = sample(game)
        s['f'] = f
        r = game.read(0xee0, 20)
        s['types'] = r.hex()
        log.append(s)
    return log


def events(log):
    out = []
    for p, s in zip(log, log[1:]):
        if s['health'] < p['health'] or s['lives'] != p['lives']:
            out.append({'f': s['f'], 'health': (p['health'], s['health']), 'lives': (p['lives'], s['lives']),
                        'y': s['y'], 'wheel': s['wheel'], 'eff': s['eff'], 'timer': s['timer']})
    return out


def main():
    mode, rom, runname, flags, grant = sys.argv[1:6]
    flags = None if flags == 'orig' else int(flags, 0)
    grant = int(grant)
    run = json.loads((RUNS / f'{runname}.json').read_text())
    if mode == 'trace':
        n, out = int(sys.argv[6]), sys.argv[7]
        with session('trace') as game:
            log = replay(game, rom, run, flags, grant, n)
        Path(out).write_text(json.dumps(log))
        for e in events(log):
            print(json.dumps(e))
    else:
        frame = int(sys.argv[6])
        hits = []

        def before(game, f):
            if f < frame - 1:
                return False
            for site in ('41c8', '41d0'):
                game.call('set_breakpoint', {'address': site, 'memory_area': 'rom', 'execute': True})
            for _ in range(3):
                if game.step(1) is None:
                    slot = game.read(0xedf, 1)[0]
                    r = game.read(0, 0x2000)
                    hits.append({'frame_near': f, 'slot': slot, 'type': r[0xee0 + slot],
                                 'z36': r[0x36], 'z37': r[0x37], 'health': r[0xead],
                                 'ryu_y': r[0xea0], 'enemy_y': r[0xf58 + slot],
                                 'enemy_x': r[0xf1c + slot] | r[0xf30 + slot] << 8,
                                 'ryu_x': r[0xe9e] | r[0xe9f] << 8, 'eff': r[0x110e:0x1113].hex(),
                                 'types': r[0xee0:0xef4].hex()})
                    break
            return True
        with session('ident') as game:
            replay(game, rom, run, flags, grant, frame + 2, before_frame=before)
        print(json.dumps(hits))


if __name__ == '__main__':
    main()
