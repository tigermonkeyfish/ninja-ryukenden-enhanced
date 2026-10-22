"""Frames from power-on and from the title press to the first 1-1 gameplay update,
with real Run presses only (plus forced English for the original-English case)."""
import json, sys
from pathlib import Path
import local
sys.path.insert(0, str(local.SCRIPTS))
import comparison_video as cv
G = str(local.EMULATOR)
S = Path(sys.argv[1])
ORIG = str(local.ORIGINAL)
ENH = str(local.ENHANCED)
def measure(label, rom, english, style):
    with cv.Game(G, S / f'st-{label}-{style}') as g:
        g.call('load_media', {'file_path': rom}); g.call('debug_pause')
        if english:
            g.call('set_breakpoint', {'address': '8022', 'memory_area': 'rom', 'execute': True})
        events, prior, title_press, last_press, f = [], None, None, None, 0
        scene_start = 0
        while f < 30000:
            r = g.read(0x240, 2); key = tuple(r)
            if key != prior:
                events.append((f, key)); scene_start = f; prior = key
                if key[0] == 0: break
            # Run presses: mash = 2 frames every 20 anywhere; minimal = only while scene 0
            # (splash/intro/title) and scene 1 (as the cinema audit needs).
            in_scene = f - scene_start
            press = (style == 'mash' or key in ((1, 0), (1, 1)) or f < 600) and (f % 20 < 2)
            if press and f % 20 == 0: last_press = f
            g.press({'run'} if press else set())
            g.step(1)
            if english:
                st = g.call('debug_get_status')
                if st['paused'] and st['pc'] == '8022':
                    g.write(0x1227, b'\x01'); g.call('remove_breakpoint', {'address': '8022', 'memory_area': 'rom'}); english = False
            f += 1
        # first gameplay update after the master state turns to gameplay
        g.press(set())
        g.call('set_breakpoint', {'address': '2457', 'memory_area': 'rom', 'execute': True})
        n = 0
        while True:
            g.step(1); n += 1
            st = g.call('debug_get_status')
            if st['pc'] == '8457': break
        lang = g.read(0x1227, 1)[0]
        gameplay = f + n
        title_to_play = None
        for (fa, ka), (fb, kb) in zip(events, events[1:]):
            if ka == (1, 0) and kb != (1, 0):
                title_to_play = gameplay - fb
        return {'events': events, 'first_gameplay_frame': gameplay, 'scene0_end_to_gameplay': title_to_play, 'language': lang}
out = {}
for style in ('minimal', 'mash'):
    for label, rom, eng in (('original-japanese', ORIG, False), ('original-english', ORIG, True), ('enhanced', ENH, False)):
        out[f'{label}/{style}'] = r = measure(label, rom, eng, style)
        print(label, style, r, flush=True)
json.dump(out, open(S / 'starttiming.json', 'w'), indent=1)
