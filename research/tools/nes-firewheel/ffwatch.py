"""Free-ROM audit: read/execute watch over ROM offsets LO-HI while replaying a
stored run on ROM (fresh session, shared start state), or a cold boot to the
first 1-1 update (RUN = boot). Reports every stop.
ffwatch.py ROM RUN LO HI"""
import json
import sys
from fw import *
sys.path.insert(0, str(WT / 'scripts'))
from comparison_video import boot  # noqa: E402

rom, runname, lo, hi = sys.argv[1:5]
stops = []


def watch(game):
    game.call('set_breakpoint_range', {'start_address': lo, 'end_address': hi, 'memory_area': 'rom',
                                       'read': True, 'execute': True})


def stepped(game, n):
    for _ in range(n):
        r = game.step(1)
        if r is None:
            st = game.call('get_huc6280_status')
            stops.append({'pc': st['PC'], 'mpr': [m['value'] for m in st['MPR']]})
            if len(stops) > 20:
                return False
    return True


with session('ffwatch') as game:
    if runname == 'boot':
        game.call('load_media', {'file_path': str(Path(rom).resolve())})
        game.call('debug_pause')
        watch(game)
        # Power-on, publisher screen, intro, title; Run 2 frames in every 20
        # until gameplay, then 600 more updates of 1-1 idle.
        frames, after = 0, None
        while frames < 8000:
            gameplay = game.read(0x240, 1)[0] == 0 and frames > 60
            game.press({'run'} if frames % 20 < 2 and not gameplay else set())
            if gameplay and after is None:
                after = frames
            if after is not None and frames > after + 600:
                break
            if not stepped(game, 1):
                break
            frames += 1
    else:
        run = json.loads((RUNS / f'{runname}.json').read_text())
        begin(game, rom, run['stage'], None)
        watch(game)
        n = 0
        for count, buttons in run['segments'] + [[60, []]]:
            game.press(set(buttons))
            if not stepped(game, count):
                break
            n += count
        frames = n
print(json.dumps({'run': runname, 'range': [lo, hi], 'updates': frames, 'stops': len(stops), 'first': stops[:3]}))
