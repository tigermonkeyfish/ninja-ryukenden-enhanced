"""Colour tables for the palette modes (src/palette), generated at build time.

A PC Engine colour is a 9-bit word GGGRRRBBB (3 bits a channel). A mode is a
table of 512 words, one per colour, which the vblank upload uses in place of
the colour itself. The GB DMG mode is defined by a few editable numbers in
`src/palette/gb-dmg.json` (luminance weights, three thresholds, four shades);
nothing is stored as an opaque table. Exact decimal arithmetic decides each
threshold, so a colour that lands exactly on one goes to the lighter shade.

The HELL mode ('Lava') is defined by `src/palette/hell.json`: colours sorted
into families by hue, saturation and value and re-coloured from ramps: the
owner's chosen mock-up (candidate C) retuned as candidate D (1.11-dev, the
owner's choice: 1-1 "more like 2-2"), ported operation for operation in
double-precision floating point, so the table is the tuning study's exactly;
it applies to background palettes 0-14 only (the first `mapped_entries` VCE
entries). An optional "steel" family (`steel_ramp`, `steel_windows`: per
window hue from-to in degrees, maximum saturation, chroma s*v and value;
`steel_mix`: value and luma weights) takes the coloured colours inside its
windows before the hue families (candidate D's cool greys and dull teals);
without those keys no colour takes it, and with candidate C's parameters the
table is the first HELL build's exactly.

The SMS mode is defined by `src/palette/sms.json`: each channel to the
nearest of the Sega Master System's four levels, in linear terms, shown as
PC Engine channel values (the owner's chosen mock-up, candidate A); every
output is one of 64 colours. It applies to every VCE entry, as GB DMG.

`generate(work)` writes `gb-table.inc`, `hell-table.inc` and
`sms-table.inc`: each four 256-byte pages, the low and high bytes of the
mapped colour for colours $000-$0FF and $100-$1FF (indexed by the colour's
low byte), in the order the upload expects (gb_lo0, gb_hi0, gb_lo1, gb_hi1;
hell_lo0 ... hell_hi1; sms_lo0 ... sms_hi1), and `HELL_MAPPED`, the number
of VCE entries the HELL mode recolours. With the palette module's
`main.asm` (with its ;@mirror lines) in `work` it also writes
`sms-mirror.inc` (`mirror`).
"""
import colorsys
from fractions import Fraction
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PARAMETERS = ROOT / 'src/palette/gb-dmg.json'
HELL_PARAMETERS = ROOT / 'src/palette/hell.json'
SMS_PARAMETERS = ROOT / 'src/palette/sms.json'


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
    names = ['lava_ramp', 'green_ramp', 'grey_ramp', 'ash_ramp']
    if 'steel_ramp' in spec:
        names.append('steel_ramp')
        for key in ('steel_windows', 'steel_mix'):
            if key not in spec:
                raise ValueError(f'hell.json {key}: needed with steel_ramp')
    for name in names:
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
    if 'steel_ramp' in spec and any(lo <= h <= hi and s <= s_max and s * v <= c_max and v <= v_max
                                    for lo, hi, s_max, c_max, v_max in spec['steel_windows']):
        m = spec['steel_mix']
        return _ramp(spec['steel_ramp'], v * m[0] + y * m[1])
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
    """The 512 mapped colour words of the HELL mode (every stage but the
    override stage; hell_stage_table)."""
    spec = load_hell(path)
    return [hell_colour(c, spec) for c in range(512)]


# Level Select numbering, the visible stage $2E5F (as comparison_video.py).
STAGES = ['1-1', '1-2', '2-1', '2-2', '2-3', '3-1', '3-2', '3-3', '4-1', '4-2', '4-3',
          '4-4', '5-1', '5-2', '5-3', '5-4', '6-1', '6-2', '6-3', '6-4A', '6-4B', '6-4C']
# Colours one stage may override: the upload's override loops compare one key
# (src/palette/main.asm, hell_colour_ovr and now_hell_ovr); each further one
# is another compare in both loops.
HELL_OVERRIDES_MAX = 1


def hell_overrides(path=HELL_PARAMETERS):
    """hell.json "stage_overrides" ({stage: {"$colour": [R, G, B]}}, optional):
    [(stage number, colour, colour word)]. At most one stage and
    HELL_OVERRIDES_MAX colours (the upload's override loops); each colour in
    the low half ($001-$0FF, the half the loops compare)."""
    spec = json.loads(Path(path).read_text())
    stages = spec.get('stage_overrides', {})
    if len(stages) > 1:
        raise ValueError('hell.json stage_overrides: one stage at most (the upload has one override stage)')
    out = []
    for name, colours in stages.items():
        if name not in STAGES:
            raise ValueError(f'hell.json stage_overrides: unknown stage {name!r}')
        if not 0 < len(colours) <= HELL_OVERRIDES_MAX:
            raise ValueError(f'hell.json stage_overrides {name}: 1 to {HELL_OVERRIDES_MAX} colours '
                             '(each further one needs a compare in both override loops)')
        for key, rgb in colours.items():
            colour = int(key.lstrip('$'), 16)
            if not 0 < colour < 0x100:
                raise ValueError(f'hell.json stage_overrides {name} {key}: the low half, $001-$0FF')
            if len(rgb) != 3 or any(not 0 <= v <= 7 for v in rgb):
                raise ValueError(f'hell.json stage_overrides {name} {key}: [R, G, B], 0-7 each')
            out.append((STAGES.index(name), colour, _join(*rgb)))
    return out


def hell_stage_table(stage, path=HELL_PARAMETERS):
    """The 512 colour words HELL shows in visible stage `stage` (Level Select
    number): hell_table with that stage's overrides."""
    table = hell_table(path)
    for number, colour, word in hell_overrides(path):
        if number == stage:
            table[colour] = word
    return table


def hell_override_equates(path=HELL_PARAMETERS):
    """HELL_OVERRIDE_STAGE / _KEY / _LO / _HI for the upload. Without an
    override the stage is $FF (never visible) and $000 maps to $000, which
    the table does anyway."""
    found = hell_overrides(path)
    stage, key, word = found[0] if found else (0xff, 0, 0)
    return '\n'.join([f'HELL_OVERRIDE_STAGE = ${stage:02x}', f'HELL_OVERRIDE_KEY = ${key:02x}',
                      f'HELL_OVERRIDE_LO = ${word & 0xff:02x}', f'HELL_OVERRIDE_HI = ${word >> 8:02x}'])


def load_sms(path=SMS_PARAMETERS):
    spec = json.loads(Path(path).read_text())
    sms, pce = spec['sms_levels'], spec['pce_levels']
    if len(sms) != 4 or len(pce) != 4:
        raise ValueError('sms.json needs 4 sms_levels and 4 pce_levels')
    if sms != sorted(set(sms)) or not all(0 <= v <= 255 for v in sms):
        raise ValueError('sms.json sms_levels: four increasing levels, 0-255')
    if pce != sorted(set(pce)) or not all(0 <= v <= 7 for v in pce):
        raise ValueError('sms.json pce_levels: four increasing PC Engine channel values, 0-7')
    return [Fraction(v) for v in sms], pce


def sms_channel(c, sms, pce):
    """A 3-bit channel to the PC Engine value of the nearest SMS level (exact;
    halfway goes to the darker level)."""
    level = Fraction(255 * c, 7)
    return pce[min(range(4), key=lambda i: (abs(level - sms[i]), i))]


def sms_table(path=SMS_PARAMETERS):
    """The 512 mapped colour words of the SMS mode."""
    sms, pce = load_sms(path)
    q = [sms_channel(c, sms, pce) for c in range(8)]
    return [_join(*[q[v] for v in channels(c)]) for c in range(512)]


def sms_colours(path=SMS_PARAMETERS):
    """The 64 colour words the SMS mode can show."""
    _, pce = load_sms(path)
    return {_join(r, g, b) for r in pce for g in pce for b in pce}


MIRROR_BEGIN, MIRROR_END = ';@mirror begin', ';@mirror end'


def mirror(source, prefix='sms_'):
    """sms-mirror.inc from the palette module's source text: the lines between
    each ';@mirror begin' and ';@mirror end', with every label defined there
    renamed `prefix` + label (definitions and references), then a guard per
    label that the copy's address equals the original's. Assembled in another
    bank, the copy is byte for byte the original at the same addresses: the
    same instructions, and every operand the same address or value."""
    lines, inside, sections = source.splitlines(), False, 0
    body = []
    for line in lines:
        if line.strip() == MIRROR_BEGIN:
            if inside:
                raise ValueError('nested ;@mirror begin')
            inside, sections = True, sections + 1
        elif line.strip() == MIRROR_END:
            if not inside:
                raise ValueError(';@mirror end without begin')
            inside = False
        elif inside:
            body.append(line.split(';', 1)[0].rstrip())
    if inside or not sections:
        raise ValueError('unterminated or missing ;@mirror section')
    labels = [m.group(1) for line in body for m in [re.match(r'([A-Za-z_]\w*):', line)] if m]
    if len(set(labels)) != len(labels):
        raise ValueError('a label is defined twice in the mirrored lines')
    if any(re.match(r'\s*\.(bank|include|incbin)\b', line, re.I) for line in body):
        raise ValueError('mirrored lines must not change bank or include files')
    pattern = re.compile(r'\b(' + '|'.join(sorted(labels, key=len, reverse=True)) + r')\b')
    out = [f'; Generated by scripts/palette_tables.py from the ;@mirror lines of src/palette/main.asm.']
    out += [pattern.sub(lambda m: prefix + m.group(1), line) for line in body if line]
    for label in labels:
        out += [f' .if ({prefix}{label} <> {label})', ' .fail', ' .endif']
    return '\n'.join(out) + '\n', labels


def write_include(path, source, names, table, extra=''):
    lines = [f'; Generated by scripts/palette_tables.py from {source}.']
    if extra:
        lines.append(extra)
    for name, page in zip(names, pages(table)):
        lines.append(f'{name}:')
        for row in range(0, 256, 16):
            lines.append(' .db ' + ','.join(f'${b:02x}' for b in page[row:row + 16]))
    Path(path).write_text('\n'.join(lines) + '\n')


def generate(work, path=PARAMETERS, hell_path=HELL_PARAMETERS, sms_path=SMS_PARAMETERS):
    table = gb_dmg_table(path)
    write_include(Path(work) / 'gb-table.inc', 'src/palette/gb-dmg.json',
                  ('gb_lo0', 'gb_hi0', 'gb_lo1', 'gb_hi1'), table)
    write_include(Path(work) / 'hell-table.inc', 'src/palette/hell.json',
                  ('hell_lo0', 'hell_hi0', 'hell_lo1', 'hell_hi1'), hell_table(hell_path),
                  f'HELL_MAPPED = {load_hell(hell_path)["mapped_entries"]}\n' + hell_override_equates(hell_path))
    write_include(Path(work) / 'sms-table.inc', 'src/palette/sms.json',
                  ('sms_lo0', 'sms_hi0', 'sms_lo1', 'sms_hi1'), sms_table(sms_path))
    module = Path(work) / 'main.asm'
    if module.exists() and MIRROR_BEGIN in module.read_text():
        (Path(work) / 'sms-mirror.inc').write_text(mirror(module.read_text())[0])
    return table


if __name__ == '__main__':
    from collections import Counter
    t = gb_dmg_table()
    print({f'${k:03x}': v for k, v in sorted(Counter(t).items())})
    print(len(set(hell_table())), 'distinct HELL colours')
    print(len(set(sms_table())), 'distinct SMS colours')
