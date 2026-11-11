"""Brightness of the stages the dark lift is for, from real captures
(cap.py / capall.sh), measured as the dark-colour survey and the dark-lift
study did (research reference, not a maintained tool; needs numpy, Pillow).

Per mode and stage, the mean over the stage's captures of: mean CIE L* of
the playfield (screenshot rows 50-241), the share of it below L* 10 and
below L* 20, and the distinct colours shown. Two readings of each capture:
- 'entries': the index picture (which VCE entry each pixel shows) with the
  captured VCE, L* per 9-bit colour (the study's method: its predictions
  are this reading of the hell-1-1 captures with the new tables);
- 'picture': the screenshot's own RGB (the survey's nums.py).
4-1 also gets the trunk/fill separation over the frames that show the
parallax (f250-f1450): L* of VCE entry $03B (the trunk) minus entry $000
(the fill behind it), the pixel-weighted L* of the trunk and bark entries
($036, $038-$03B) minus the fill, and dE76 between $03B and the fill; and
the survey's par.py figures for the parallax rows (palettes 0 and 3).
usage: measure.py CAP [BEFORE_CAP] [--json OUT]
  CAP: this build's captures; BEFORE_CAP: the same captures of the build
  before (the survey's, build/dark-survey/cap), printed beside them."""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts'))
import nes_palette as NP  # noqa: E402

MODES = ['original', 'nes-a', 'nes-b', 'gb-dmg', 'hell', 'sms']
Y0, Y1 = 50, 242
TRUNK = (0x03B, 0x03A, 0x036, 0x039, 0x038)
STAGES = [
    ('4-1', [f'4-1-f{f}' for f in (250, 700, 1150, 1450, 1750)]),
    ('5-1 area 0', [f'ls12-a0-{t}' for t in ('start', 'hold')]),
    ('6-2 areas 0-4', [f'ls17-a{a}-{t}' for a in range(5) for t in ('start', 'hold')]),
    ('6-2 area 0', [f'ls17-a0-{t}' for t in ('start', 'hold')]),
    ('6-4A', [f'ls19-f{f}' for f in (60, 200, 400, 700)]),
    ('6-4B', [f'ls20-f{f}' for f in (60, 200, 400, 700)]),
    ('6-4C', [f'ls21-f{f}' for f in (60, 200, 400, 700)]),
]
_L = np.array([NP.lightness(c) for c in range(512)])
_rgb = {}


def entries(path):
    q = np.array(Image.open(path).convert('RGB')).astype(int)
    q = np.round(q * 7 / 255).astype(int)
    return (q[..., 1] << 6) | (q[..., 0] << 3) | q[..., 2]


def vce(path):
    d = Path(path).read_bytes()
    return np.array([(d[2 * i] | d[2 * i + 1] << 8) & 0x1ff for i in range(512)])


def picture_l(path):
    a = np.array(Image.open(path).convert('RGB'))[Y0:Y1]
    u, inv = np.unique(a.reshape(-1, 3), axis=0, return_inverse=True)
    lu = np.array([_rgb.setdefault(tuple(int(v) for v in p), NP.lab(tuple(int(v) for v in p))[0]) for p in u])
    return lu[inv.reshape(-1)]


def capture(cap, name, mode):
    base = Path(cap) / f'{name}-{mode}'
    e = entries(str(base) + '-index.png')[Y0:Y1]
    v = vce(str(base) + '.vce')
    light = _L[v[e]]
    pic = picture_l(str(base) + '.png')
    out = {'entries': (light.mean(), (light < 10).mean() * 100, (light < 20).mean() * 100, len(np.unique(v[e]))),
           'picture': (pic.mean(), (pic < 10).mean() * 100, (pic < 20).mean() * 100)}
    fill = _L[v[0]]
    m = np.isin(e, TRUNK)
    a, b = NP.lab(NP.rgb8(int(v[0x3B]))), NP.lab(NP.rgb8(int(v[0])))
    out['sep'] = (_L[v[0x3B]] - fill, (light[m].mean() - fill) if m.any() else float('nan'),
                  sum((x - y) ** 2 for x, y in zip(a, b)) ** .5, int(v[0]), int(v[0x3B]))
    par = np.isin((e >> 4) & 31, (0, 3))
    out['par'] = (par.mean() * 100, light[par].mean() if par.any() else float('nan'),
                  light[~par].mean(), (light[par] < 10).mean() * 100 if par.any() else float('nan'),
                  (light[par] < 20).mean() * 100 if par.any() else float('nan'))
    return out


def stage(cap, names, mode):
    caps = [capture(cap, n, mode) for n in names]
    row = {k: [float(np.mean([c[k][i] for c in caps])) for i in range(len(caps[0][k]))] for k in ('entries', 'picture')}
    row['sep'] = [float(np.mean([c['sep'][i] for c in caps[:4]])) for i in range(3)] + list(caps[0]['sep'][3:])
    row['par'] = [float(np.nanmean([c['par'][i] for c in caps[:4]])) for i in range(5)]
    return row


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    out = sys.argv[sys.argv.index('--json') + 1] if '--json' in sys.argv else None
    if out:
        args.remove(out)
    caps = [('after', args[0])] + ([('before', args[1])] if len(args) > 1 else [])
    result = {}
    cell = lambda r: '%.1f/%.0f/%.0f/%.0f' % tuple(r['entries'])
    pict = lambda r: '%.1f/%.0f/%.0f' % tuple(r['picture'])
    print('cells: mean L* / % below L* 10 / % below L* 20 [/ distinct colours], playfield rows 50-241, mean over the captures')
    for mode in MODES:
        print(f'\n== {mode}')
        for name, names in STAGES:
            rows = {tag: stage(cap, names, mode) for tag, cap in caps}
            result.setdefault(mode, {})[name] = rows
            print(f'{name:14s} ' + ' | '.join(f'{tag}: entries {cell(r)}  picture {pict(r)}' for tag, r in rows.items()))
            if name == '4-1':
                for tag, r in rows.items():
                    s, p = r['sep'], r['par']
                    print(f'   {tag}: trunk $03B - fill dL* {s[0]:.1f}, trunk pixels - fill dL* {s[1]:.1f}, dE76 {s[2]:.1f}; '
                          f'fill {s[3]:03X} trunk {s[4]:03X}; parallax rows {p[0]:.0f}% of the playfield, mean L* {p[1]:.1f} '
                          f'(rest {p[2]:.1f}), {p[3]:.0f}% below 10, {p[4]:.0f}% below 20')
    if out:
        Path(out).write_text(json.dumps(result, indent=1))


if __name__ == '__main__':
    main()
