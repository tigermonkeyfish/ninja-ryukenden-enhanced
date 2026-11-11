"""Colour tables for the palette modes (src/palette), generated at build time.

A PC Engine colour is a 9-bit word GGGRRRBBB (3 bits a channel). A mode is a
table of 512 words, one per colour, which the vblank upload uses in place of
the colour itself. The GB DMG mode is defined by a few editable numbers in
`src/palette/gb-dmg.json` (luminance weights, three thresholds, four shades);
nothing is stored as an opaque table. Exact decimal arithmetic decides each
threshold, so a colour that lands exactly on one goes to the lighter shade.

The HELL mode ('Lava') is defined by `src/palette/hell.json`: colours sorted
into families by hue, saturation and value and re-coloured from ramps. It is
the owner's chosen mock-up (candidate C), ported operation for operation in
double-precision floating point, so the table is the mock-up's exactly; it
applies to background palettes 0-14 only (the first `mapped_entries` VCE
entries).

`generate(work)` writes `gb-table.inc` and `hell-table.inc`: each four
256-byte pages, the low and high bytes of the mapped colour for colours
$000-$0FF and $100-$1FF (indexed by the colour's low byte), in the order the
upload expects (gb_lo0, gb_hi0, gb_lo1, gb_hi1; hell_lo0 ... hell_hi1), and
`HELL_MAPPED`, the number of VCE entries the HELL mode recolours.
"""
import colorsys
from fractions import Fraction
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARAMETERS = ROOT / 'src/palette/gb-dmg.json'
HELL_PARAMETERS = ROOT / 'src/palette/hell.json'


def channels(colour):
    """(R, G, B), 0-7 each, of a 9-bit PC Engine colour word."""
    return (colour >> 3) & 7, (colour >> 6) & 7, colour & 7


def load(path=PARAMETERS):
    spec = json.loads(Path(path).read_text())
    luma = [Fraction(str(w)) for w in spec['luma']]
    thresholds = [Fraction(str(t)) for t in spec['thresholds']]
    shades = [int(str(s).lstrip('$'), 16) for s in spec['shades']]
    if len(luma) != 3 or len(thresholds) != 3 or len(shades) != 4:
        raise ValueError('gb-dmg.json needs 3 luma weights, 3 thresholds and 4 shades')
    if thresholds != sorted(thresholds):
        raise ValueError('gb-dmg.json thresholds must increase')
    if any(not 0 <= s <= 0x1ff for s in shades):
        raise ValueError('gb-dmg.json shades must be 9-bit PC Engine colours ($000-$1FF)')
    return luma, thresholds, shades


def shade(colour, luma, thresholds):
    r, g, b = channels(colour)
    y = luma[0] * r + luma[1] * g + luma[2] * b
    return sum(1 for t in thresholds if y >= t)


def gb_dmg_table(path=PARAMETERS):
    """The 512 mapped colour words of the GB DMG mode."""
    luma, thresholds, shades = load(path)
    return [shades[shade(c, luma, thresholds)] for c in range(512)]


def pages(table):
    """gb_lo0, gb_hi0, gb_lo1, gb_hi1: 256 bytes each."""
    return [bytes((table[half * 256 + i] >> (8 * byte)) & 0xff for i in range(256))
            for half in (0, 1) for byte in (0, 1)]


def load_hell(path=HELL_PARAMETERS):
    spec = json.loads(Path(path).read_text())
    for name in ('lava_ramp', 'green_ramp', 'grey_ramp', 'ash_ramp'):
        ramp = [tuple(point) for point in spec[name]]
        if len(ramp) < 2 or any(len(p) != 4 for p in ramp) or [p[0] for p in ramp] != sorted(p[0] for p in ramp):
            raise ValueError(f'hell.json {name}: at least two [position, R, G, B] points, positions increasing')
        if any(not 0 <= v <= 7 for p in ramp for v in p[1:]):
            raise ValueError(f'hell.json {name}: channels are 0-7')
        spec[name] = ramp
    if not 0 < spec['mapped_entries'] <= 256 or spec['mapped_entries'] % 16:
        raise ValueError('hell.json mapped_entries: whole background palettes, at most 256 entries')
    return spec


def _q(x):
    """A 0-1 channel to 3 bits (round half to even, as the mock-up)."""
    return max(0, min(7, int(round(x * 7))))


def _join(r, g, b):
    return g << 6 | r << 3 | b


def _ramp(ramp, y):
    for (y0, *c0), (y1, *c1) in zip(ramp, ramp[1:]):
        if y <= y1:
            t = (y - y0) / (y1 - y0) if y1 > y0 else 0
            return _join(*[_q((a + (b - a) * t) / 7) for a, b in zip(c0, c1)])
    return _join(*ramp[-1][1:])


def _hsv_out(h, s, v):
    r, g, b = colorsys.hsv_to_rgb((h % 360) / 360, max(0, min(1, s)), max(0, min(1, v)))
    return _join(_q(r), _q(g), _q(b))


def hell_colour(colour, spec):
    """The HELL mode's colour for one 9-bit colour (the mock-up's map_C)."""
    if colour == 0:
        return 0
    r, g, b = [x / 7 for x in channels(colour)]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    h *= 360
    w = spec['luma']
    y = w[0] * r + w[1] * g + w[2] * b
    if s < spec['sat_low']:
        if v >= spec['ash_v']:
            return _ramp(spec['ash_ramp'], (v - spec['ash_v']) / (1 - spec['ash_v']))
        return _ramp(spec['grey_ramp'], v)
    if spec['blue_hue'][0] <= h <= spec['blue_hue'][1]:
        return _ramp(spec['lava_ramp'], v * spec['lava_mix'][0] + y * spec['lava_mix'][1])
    if spec['green_hue'][0] <= h < spec['green_hue'][1]:
        return _ramp(spec['green_ramp'], y * spec['green_luma_scale'])
    keep = spec['warm_keep_hue']
    hue = h if h <= keep[0] or h >= keep[1] else spec['warm_other_hue']
    if spec['warm_magenta'][0] <= hue < spec['warm_magenta'][1]:
        hue = spec['warm_magenta'][1]
    return _hsv_out(hue, s * spec['warm_s'], v * spec['warm_v'])


def hell_table(path=HELL_PARAMETERS):
    """The 512 mapped colour words of the HELL mode."""
    spec = load_hell(path)
    return [hell_colour(c, spec) for c in range(512)]


def write_include(path, source, names, table, extra=''):
    lines = [f'; Generated by scripts/palette_tables.py from {source}.']
    if extra:
        lines.append(extra)
    for name, page in zip(names, pages(table)):
        lines.append(f'{name}:')
        for row in range(0, 256, 16):
            lines.append(' .db ' + ','.join(f'${b:02x}' for b in page[row:row + 16]))
    Path(path).write_text('\n'.join(lines) + '\n')


def generate(work, path=PARAMETERS, hell_path=HELL_PARAMETERS):
    table = gb_dmg_table(path)
    write_include(Path(work) / 'gb-table.inc', 'src/palette/gb-dmg.json',
                  ('gb_lo0', 'gb_hi0', 'gb_lo1', 'gb_hi1'), table)
    write_include(Path(work) / 'hell-table.inc', 'src/palette/hell.json',
                  ('hell_lo0', 'hell_hi0', 'hell_lo1', 'hell_hi1'), hell_table(hell_path),
                  f'HELL_MAPPED = {load_hell(hell_path)["mapped_entries"]}')
    return table


if __name__ == '__main__':
    from collections import Counter
    t = gb_dmg_table()
    print({f'${k:03x}': v for k, v in sorted(Counter(t).items())})
    print(len(set(hell_table())), 'distinct HELL colours')
