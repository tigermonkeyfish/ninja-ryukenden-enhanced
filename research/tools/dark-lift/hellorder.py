"""Lightness order of the HELL table (research reference, not a maintained
tool; needs numpy and Pillow for the captures).

The HELL mode recolours each colour from its family's ramp
(palette_tables.hell_family). A ramp that is not monotonic can show a lighter
input darker than a darker input of the same family; where both colours shade
one tile, its shading is reversed. This probe

1. lists, per family, every pair of colours of which the lighter input
   (CIE L* of the colour itself) maps to a colour at least MIN L* darker than
   the darker input's (an inversion), and
2. with capture folders (cap.py: NAME-MODE-index.png, .ram), finds where
   both colours of an inversion are on screen in the same background palette
   row: the pixels of each and the number of 4-neighbour pixel pairs in
   which the two touch.

usage: hellorder.py [--hell hell.json] [--min L] [--mode hell] [--pairs] [--sms] [CAP...]
  --pairs: list every inversion (default: per family counts and the greys).
  --sms: the SMS table instead (sms.json; every VCE entry), with the fade's
         order: a pair is inverted when one colour has every channel at least
         the other's (a fade step of it, or a lighter shade of one hue) and is
         shown at least MIN L* darker; captures of mode sms."""
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts'))
import nes_palette as NP  # noqa: E402
import palette_tables as PT  # noqa: E402

args = [a for a in sys.argv[1:] if not a.startswith('--')]
opt = {}
for i, a in enumerate(sys.argv):
    if a in ('--hell', '--min', '--mode', '--json'):
        opt[a[2:]] = sys.argv[i + 1]
        args.remove(sys.argv[i + 1])
path = Path(opt.get('hell', PT.HELL_PARAMETERS))
MIN = float(opt.get('min', 0.5))
MODE = opt.get('mode', 'hell')
spec = PT.load_hell(path)
table = PT.hell_table(path)
L = [NP.lightness(c) for c in range(512)]


def rgb(c):
    r, g, b = PT.channels(c)
    return f'{r}{g}{b}'


def inversions(table):
    """{family: [(darker input, lighter input)]} with the lighter input shown
    darker by at least MIN L*."""
    fams = defaultdict(list)
    for c in range(1, 512):
        fams[PT.hell_family(c, spec)[0]].append(c)
    out = {}
    for fam, cols in fams.items():
        cols.sort(key=lambda c: L[c])
        out[fam] = [(a, b) for i, a in enumerate(cols) for b in cols[i + 1:]
                    if L[b] > L[a] and L[table[a]] - L[table[b]] >= MIN]
    return out, fams


def dominance(table):
    """The fade's order: b has every channel at least a's and is shown darker."""
    out = [(a, b) for a in range(1, 512) for b in range(1, 512)
           if a != b and all(x <= y for x, y in zip(PT.channels(a), PT.channels(b)))
           and L[table[a]] - L[table[b]] >= MIN]
    return {'fade': out}, {'fade': list(range(1, 512))}


SMS = '--sms' in sys.argv
if SMS:
    table = PT.sms_table()
    MODE = opt.get('mode', 'sms')
    spec = {'mapped_entries': 512}
    inv, fams = dominance(table)
else:
    inv, fams = inversions(table)
print(f'{"sms.json" if SMS else path.name}: inversions of at least {MIN} L* (lighter input shown darker), per family')
for fam in sorted(fams):
    pairs = inv.get(fam, [])
    print(f'  {fam:6s} {len(fams[fam]):3d} colours, {len(pairs):5d} inverted pairs')
greys = [] if SMS else sorted((c for c in range(1, 512) if PT.hell_family(c, spec)[0] in ('grey', 'ash')),
                             key=lambda c: L[c])
print('greys and ash, darkest input first: input (RGB, L*) > shown (RGB, L*)')
last = -1
for c in greys:
    fam, pos = PT.hell_family(c, spec)
    flag = '   << darker than a darker grey' if L[table[c]] < last - MIN else ''
    last = max(last, L[table[c]])
    print(f'  ${c:03X} {rgb(c)} L*{L[c]:5.1f} {fam:4s} at {pos:.3f} > ${table[c]:03X} {rgb(table[c])} L*{L[table[c]]:5.1f}{flag}')
if '--pairs' in sys.argv:
    for fam in sorted(inv):
        for a, b in inv[fam]:
            print(f'  {fam:6s} ${a:03X} {rgb(a)} L*{L[a]:5.1f} > {rgb(table[a])} L*{L[table[a]]:5.1f}   '
                  f'${b:03X} {rgb(b)} L*{L[b]:5.1f} > {rgb(table[b])} L*{L[table[b]]:5.1f}')

if args:
    import numpy as np
    from PIL import Image
    pairs = {(a, b): fam for fam, ps in inv.items() for a, b in ps}
    found = defaultdict(list)
    for cap in args:
        for idx in sorted(Path(cap).glob(f'*-{MODE}-index.png')):
            base = str(idx)[:-len('-index.png')]
            ram = Path(base + '.ram').read_bytes()
            pal = np.array([(ram[2 * i] | ram[2 * i + 1] << 8) & 0x1ff for i in range(512)])
            q = np.round(np.array(Image.open(idx).convert('RGB')).astype(int) * 7 / 255).astype(int)
            e = ((q[..., 1] << 6) | (q[..., 0] << 3) | q[..., 2])[50:242]
            bg = e < spec['mapped_entries']
            col = pal[e]
            row = e >> 4
            size = e.size
            for r in np.unique(row[bg]):
                m = bg & (row == r)
                present = {int(c): int(n) for c, n in zip(*np.unique(col[m], return_counts=True))}
                for (a, b), fam in pairs.items():
                    if a in present and b in present:
                        ma, mb = m & (col == a), m & (col == b)
                        touch = int((ma[:, :-1] & mb[:, 1:]).sum() + (mb[:, :-1] & ma[:, 1:]).sum()
                                    + (ma[:-1] & mb[1:]).sum() + (mb[:-1] & ma[1:]).sum())
                        found[(a, b)].append((Path(base).name, int(r), present[a] * 100 / size,
                                              present[b] * 100 / size, touch))
    print(f'\non screen ({len(args)} capture folders, mode {MODE}): inverted pairs in one background palette row')
    summary = []
    for (a, b), hits in sorted(found.items(), key=lambda kv: -sum(h[4] for h in kv[1])):
        touching = [h for h in hits if h[4]]
        best = max(hits, key=lambda h: h[4])
        summary.append({'a': a, 'b': b, 'family': pairs[(a, b)], 'captures': len(hits), 'touching': len(touching),
                        'best': best})
        print(f'  {pairs[(a, b)]:6s} ${a:03X} {rgb(a)} > {rgb(table[a])} L*{L[table[a]]:4.1f}  with  '
              f'${b:03X} {rgb(b)} > {rgb(table[b])} L*{L[table[b]]:4.1f}: {len(hits)} captures, touching in '
              f'{len(touching)}; most in {best[0]} row {best[1]} ({best[2]:.1f}% and {best[3]:.1f}% of the playfield, '
              f'{best[4]} touching pixel pairs)')
    if opt.get('json'):
        Path(opt['json']).write_text(json.dumps(summary))
