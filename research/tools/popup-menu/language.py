"""Language row: choose CHINESE / JAPANESE in the menu, Run (1-1
restarts), leave the stage by the native completion path ($8457 -> $8478)
until a cinema runs (1-1, then 1-2) and capture 1200 of its frames. Reference: the same Run with nothing changed and $3227
written by the debugger. The cinema's frames must match the reference with
the same language and differ from English.
usage: language.py ROM OUT"""
import os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
EMU = os.environ['GEARGRAFX']

import hashlib, json, sys, tempfile
from pathlib import Path
import check_menu as cm
from comparison_video import Game, start_point, start_stage
rom, out = sys.argv[1], Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
seed = Path(os.environ['NINJA_SEED_STATE'])  # comparison_video.make_seed on the original


def cinema(label, presses, poke=None, frames=4000, keep=1200):
    with Game(EMU, Path(tempfile.mkdtemp(dir=out))) as g:
        start_point(g, rom, seed, enhanced=True)
        g.write(0x1227, b'\x01')
        start_stage(g, 0)
        g.step(30)
        cm.menu_to(g, 5, presses)
        if poke is not None:
            g.write(0x1227, bytes([poke]))
        language = g.read(0x1227, 1)[0]
        hashes = []
        for attempt in range(6):
            # Leave the stage by the native completion path until a cinema runs.
            g.step(120)
            g.call('debug_run_to_cursor', {'address': '8457'})
            for _ in range(20000):
                st = g.call('debug_get_status')
                if st.get('paused'):
                    break
            assert st.get('paused') and st['pc'] == '8457', st
            g.reg('PC', 0x8478)
            for f in range(frames):
                g.checked_step(1)
                master = g.read(0x240, 1)[0]
                if master == 0 and hashes:
                    break
                if master != 1:
                    if master == 0 and f > 300 and g.read(0x240, 1)[0] == 0:
                        break               # gameplay again without a cinema
                    continue
                png = g.screenshot()
                hashes.append(hashlib.sha256(png).hexdigest()[:16])
                if len(hashes) in (300, 600):
                    (out / f'cinema-{label}-{len(hashes)}.png').write_bytes(png)
                if len(hashes) >= keep:
                    break
            if hashes:
                break
        return language, hashes


res = {}
for label, presses, poke in (('menu-chinese', ['left'], None), ('poke-chinese', [], 2),
                             ('menu-japanese', ['right'], None), ('poke-japanese', [], 0),
                             ('english', [], None)):
    lang, h = cinema(label, presses, poke)
    res[label] = {'language': lang, 'cinema_frames': len(h), 'sha': hashlib.sha256(''.join(h).encode()).hexdigest()[:16],
                  'hashes': h}
    print(label, lang, len(h), res[label]['sha'], flush=True)
ok = (res['menu-chinese']['hashes'] == res['poke-chinese']['hashes'] and res['menu-chinese']['language'] == 2
      and res['menu-japanese']['hashes'] == res['poke-japanese']['hashes'] and res['menu-japanese']['language'] == 0
      and res['english']['hashes'] != res['menu-chinese']['hashes'] and res['english']['hashes'] != res['menu-japanese']['hashes']
      and res['menu-chinese']['cinema_frames'] > 100)
for r in res.values():
    r.pop('hashes')
res['ok'] = ok
(out / 'language.json').write_text(json.dumps(res, indent=1))
print('language', 'passed' if ok else 'FAILED')
