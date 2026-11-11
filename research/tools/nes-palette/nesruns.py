"""Evidence b/d (stored runs in NES mode): replay each stored run in Original
mode and in NES mode ($2100 = $08), plus FRAMES_AFTER frames with no input
(the stage end, a cinema where there is one, the next stage's start), one
fresh session each. Per frame:

- gameplay: Ryu, timer, camera, area, stage, lives, health, master state and
  the sprite table must be identical in both modes (no frame added or
  dropped, same play);
- colours (gameplay frames, $2240 = 0): every managed RAM palette entry (the
  colour set of the stage shown, the 3-2 variant in 3-2, the HUD entries
  $F1-$F7, Ryu's sprite row 0, the 1-1 / 2-2 Enhanced rows) that Original
  mode holds at its full original value must hold the full NES value in NES
  mode; where Original mode is fading (every channel at or below the full
  value), NES mode must be at or below the NES value too (a flash of an
  original colour is a brighter channel). Entries the game animates (given
  per stage in ANIMATED, a JSON of stage name -> indices; build it from
  stagecheck.py's game_written lists) are left out. A mismatch in a frame
  that ends with the palette lock $2283 held (a load unpacking: nothing is
  uploaded, the picture cannot show it) is counted apart as mid-update;
- cinemas and the title ($2240 != 0): picture, VCE and RAM palette identical
  in both modes (original colours).
usage: nesruns.py ROM OUT.json FRAMES_AFTER ANIMATED.json [runs,..]"""
import hashlib
import json
import struct
import sys
from pathlib import Path

from ntools import NES, RUN_NAMES, Session, cv, load_run, ram_palette

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts'))
import nes_palette as NP  # noqa: E402

FIELDS = {'ryu': (0xe9e, 0xeb8), 'timer': (0xeda, 0xede), 'cam': (0x20f, 0x211), 'area': (0xe60, 0xe61),
          'stage': (0xe5f, 0xe60), 'lives': (0xeaf, 0xeb0), 'health': (0xead, 0xeae), 'master': (0x240, 0x241)}


def h(b):
    return hashlib.sha1(b).hexdigest()[:16]


def replay(rom, flags, run, after):
    inputs = [b for c, b in run['segments'] for _ in range(c)] + [[]] * after
    out = []
    with Session(rom, flags) as g:
        cv.start_stage(g, run['stage'])
        for buttons in inputs:
            g.press(set(buttons))
            g.checked_step(1)
            ram = g.read(0, 0x2000)
            fr = {k: ram[a:b].hex() for k, (a, b) in FIELDS.items()}
            fr['sat'] = h(g.read(0, 512, area=6))
            fr['lock'] = ram[0x283]
            fr['pal'] = ram_palette(ram)
            if ram[0x240]:
                fr['png'] = h(g.screenshot())
                fr['vce'] = h(g.read(0, 1024, area=8))
            out.append(fr)
    return out


def managed(stage, data, lay, orig_sets, enh):
    """{index: [(original full, NES full), ...]} for a stage."""
    s = NP.STAGE_SET[stage]
    base = orig_sets[s]
    nes = lay['variants'][stage][1] if stage in lay['variants'] else lay['sets'][s]
    m = {i: [(base[i], nes[i])] for i in range(len(base)) if i % 16 or i == 0}
    hud = data['shared']['hud']['entries']
    for k in range(7):
        m[0xf1 + k] = [(int(hud[k]['pce'], 16), lay['hud'][k])]
    ryu = data['shared']['sprites'][0]
    for k in range(1, 16):
        m[256 + k] = [(int(ryu['entries'][k]['pce'], 16), dict(lay['sprites'])[96][k])]
    rows = {0: [('extra_palette_nes', 1)], 3: [('palette13_nes', 13), ('palette14_nes', 14)]}.get(stage, [])
    for label, row in rows:
        mo, ne = enh[label]
        for k in range(1, 16):
            m.setdefault(16 * row + k, []).append((mo[k], ne[k]))
    return m


def channels(c):
    return (c >> 6) & 7, (c >> 3) & 7, c & 7


def at_or_below(c, full):
    return all(x <= y for x, y in zip(channels(c), channels(full)))


def main():
    rom, out, after, animated = sys.argv[1], Path(sys.argv[2]), int(sys.argv[3]), json.loads(Path(sys.argv[4]).read_text())
    names = sys.argv[5].split(',') if len(sys.argv) > 5 else RUN_NAMES
    original = (Path(__import__('os').environ.get('NES_WORK', '/workspace/build/nes-palette')) / 'original.pce').read_bytes()
    original = original[512:] if len(original) % 8192 == 512 else original
    data = NP.load()
    lay = NP.layout(data)
    orig_sets = {}
    for s in range(NP.SETS):
        addr, count = struct.unpack_from('<HH', original, NP.SET_TABLE + 4 * s)
        orig_sets[s] = NP.unpack(original[NP.SET_TABLE + addr - 0x6000:], count)
    enh = {}
    for mod in ('stage11', 'stage22'):
        enh.update(NP.enhanced_palettes(mod, original))
    report = {}
    for name in names:
        run = load_run(name)
        a = cv.retried(replay, rom, 0, run, after)
        b = cv.retried(replay, rom, NES, run, after)
        gameplay = [f for f, (x, y) in enumerate(zip(a, b)) if any(x[k] != y[k] for k in list(FIELDS) + ['sat'])]
        cinema = [f for f, (x, y) in enumerate(zip(a, b)) if int(x['master'], 16) and
                  (x.get('png') != y.get('png') or x.get('vce') != y.get('vce') or x['pal'] != y['pal'])]
        full = fade = 0
        bad = []
        stages = set()
        for f, (x, y) in enumerate(zip(a, b)):
            if int(x['master'], 16):
                continue
            stage = int(x['stage'], 16)
            if stage >= 22:
                continue
            stages.add(cv.STAGE_NAMES[stage])
            skip = set(animated.get(cv.STAGE_NAMES[stage], []))
            for i, pairs in managed(stage, data, lay, orig_sets, enh).items():
                if i in skip:
                    continue
                ov, nv = x['pal'][i], y['pal'][i]
                hits = [p for p in pairs if ov == p[0]]
                if hits:
                    full += 1
                    # A full value that is also a fade step of a full value
                    # (black, while a fade ends) may be a step behind in NES mode.
                    fading = [p for p in pairs if ov != p[0] and at_or_below(ov, p[0])] + \
                        [p for p in hits if ov == 0]
                    if nv not in [p[1] for p in hits] and not any(at_or_below(nv, p[1]) for p in fading):
                        bad.append((f, i, f'{ov:03X}', f'{nv:03X}', 'full', bool(x['lock'] or y['lock'])))
                elif all(at_or_below(ov, p[0]) for p in pairs):
                    fade += 1
                    if not any(at_or_below(nv, p[1]) for p in pairs):
                        bad.append((f, i, f'{ov:03X}', f'{nv:03X}', 'fade', bool(x['lock'] or y['lock'])))
        cinema_frames = sum(1 for x in a if int(x['master'], 16))
        report[name] = {'frames': len(a), 'gameplay_differing': len(gameplay), 'gameplay_first': gameplay[:8],
                        'cinema_frames': cinema_frames, 'cinema_differing': len(cinema), 'cinema_first': cinema[:8],
                        'stages_seen': sorted(stages), 'full_checks': full, 'fade_checks': fade,
                        'colour_problems': sum(1 for p in bad if not p[5]), 'colour_first': [p for p in bad if not p[5]][:12],
                        'locked_mid_update': sum(1 for p in bad if p[5]), 'locked_first': [p for p in bad if p[5]][:6]}
        print(name, json.dumps(report[name]), flush=True)
    report['ok'] = all(not r['gameplay_differing'] and not r['cinema_differing'] and not r['colour_problems']
                       for r in report.values() if isinstance(r, dict))
    out.write_text(json.dumps(report, indent=1))
    print('nesruns', 'passed' if report['ok'] else 'FAILED')


if __name__ == '__main__':
    main()
