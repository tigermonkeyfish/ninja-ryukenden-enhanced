"""Build the in-game menu's text and value tables from an editable layout.

`src/options/menu.txt` holds three parts, each line marked by its first
character:

- `|...|` lines: the popup window as it appears, BOX_ROWS lines of
  BOX_WIDTH columns between the bars. Runs of '#' mark the value fields, in
  row order: STAGE (5 wide), then one field per option row.
- `=` line: the band under the HUD (BAT row 31) while the menu is open,
  centred in 32 columns. `{version}` is VERSION; `{credit}` is
  GITHUB.COM/TIGERMONKEYFISH when the line fits, else TIGERMONKEYFISH. A
  line that does not fit even then fails the build.
- `@` lines: the values of the option fields after STAGE, in field order:
  the draft-byte bits the field owns, then `value=TEXT` choices in
  Left/Right order (`_` is a space in TEXT). Adding a choice is adding one
  `value=TEXT` item to its line.

`#` starts a comment line.
"""

# The native HUD font (menu text encoding in docs/ARCHITECTURE.md), plus the
# menu's own glyphs in the font's blank tiles: '.' $AA, ':' $AD and '/' $B9.
CODES = {' ': 0x9f, '-': 0x9a, '.': 0xaa, ':': 0xad, '/': 0xb9}
CODES.update({chr(ord('A') + i): 0x80 + i for i in range(26)})
CODES.update({str(i): 0xa0 + i for i in range(10)})

BOX_WIDTH, BOX_ROWS = 26, 10
BAND_WIDTH = 32
STAGE_WIDTH = 5
CREDITS = ('GITHUB.COM/TIGERMONKEYFISH', 'TIGERMONKEYFISH')
# Draft bits the option rows may own: bits 0-5 are copied to $2100 on Run,
# bits 6-7 hold the language ($3227) (src/options/main.asm).
DRAFT_BITS = 0xff


def encode(text, what):
    unknown = set(text) - set(CODES)
    if unknown:
        raise ValueError(f'{what} has characters outside the HUD font: {sorted(unknown)}')
    return bytes(CODES[c] for c in text)


def box(lines):
    """(window bytes, [(row, column, width)] value fields) for the `|` lines."""
    if len(lines) != BOX_ROWS:
        raise ValueError(f'The menu window needs {BOX_ROWS} lines, found {len(lines)}')
    data, fields = bytearray(), []
    for row, line in enumerate(lines):
        if len(line) != BOX_WIDTH + 2 or not line.endswith('|'):
            raise ValueError(f'Window line {row + 1} must be {BOX_WIDTH} columns between bars: {line!r}')
        line = line[1:-1]
        column = 0
        while column < BOX_WIDTH:
            if line[column] == '#':
                end = column
                while end < BOX_WIDTH and line[end] == '#':
                    end += 1
                fields.append((row, column, end - column))
                column = end
            else:
                column += 1
        data += encode(line.replace('#', ' '), f'Window line {row + 1}')
    if not fields or fields[0][2] != STAGE_WIDTH:
        raise ValueError(f'The first value field is STAGE, {STAGE_WIDTH} wide')
    return bytes(data), fields


def band(template, version):
    for credit in CREDITS:
        text = template.replace('{version}', version.upper()).replace('{credit}', credit)
        if len(text) <= BAND_WIDTH:
            return encode(text.center(BAND_WIDTH), 'The band line'), text
    raise ValueError(f'The band line does not fit {BAND_WIDTH} columns: {text!r}')


def choices(lines, widths):
    """Tables for the option fields: [(mask, [(value, text)])] per field."""
    if len(lines) != len(widths):
        raise ValueError(f'{len(widths)} option fields need as many @ lines, found {len(lines)}')
    rows, owned = [], 0
    for line, width in zip(lines, widths):
        mask, *items = line[1:].split()
        mask = int(mask.lstrip('$'), 16)
        if mask & ~DRAFT_BITS or mask & owned or not mask:
            raise ValueError(f'Bad or overlapping draft bits in {line!r}')
        owned |= mask
        entries = []
        for item in items:
            value, text = item.split('=', 1)
            value = int(value.lstrip('$'), 16)
            text = text.replace('_', ' ')
            if value & ~mask or value in [v for v, _ in entries]:
                raise ValueError(f'Value {value:#04x} outside {mask:#04x} or repeated in {line!r}')
            if len(text) > width:
                raise ValueError(f'{text!r} is wider than its field ({width}) in {line!r}')
            entries.append((value, encode(text.ljust(width), line)))
        if len(entries) < 2:
            raise ValueError(f'An option needs at least two values: {line!r}')
        rows.append((mask, entries))
    return rows


def layout(text, version):
    """Everything the menu module needs, from menu.txt's text."""
    lines = [line for line in text.splitlines() if line and not line.startswith('#')]
    window, fields = box([line for line in lines if line.startswith('|')])
    bands = [line[1:].strip() for line in lines if line.startswith('=')]
    if len(bands) != 1:
        raise ValueError('The layout needs exactly one = (band) line')
    band_bytes, band_text = band(bands[0], version)
    rows = choices([line for line in lines if line.startswith('@')], [w for _, _, w in fields[1:]])
    if any(not line.startswith(('|', '=', '@')) for line in lines):
        raise ValueError('Every line must start with |, =, @ or #')
    return {'window': window, 'fields': fields, 'band': band_bytes, 'band_text': band_text,
            'choices': rows}


def db(values):
    return ' .db ' + ','.join(str(v) for v in values) + '\n'


def generate(directory, version):
    menu = layout((directory / 'menu.txt').read_text(), version)
    fields, rows = menu['fields'], menu['choices']
    first, end, values, text_at, text = [], [], [], [], bytearray()
    for _, entries in rows:
        first.append(len(values))
        for value, label in entries:
            values.append(value)
            text_at.append(len(text))
            text += label
        end.append(len(values))
    if len(text) > 256 or len(values) > 255:
        raise ValueError('Option value texts exceed 256 bytes')
    out = f'BOX_WIDTH = {BOX_WIDTH}\nBOX_ROWS = {BOX_ROWS}\nFIELDS = {len(fields)}\n'
    out += 'box_text:\n'
    for row in range(BOX_ROWS):
        out += db(menu['window'][row * BOX_WIDTH:(row + 1) * BOX_WIDTH])
    out += f'band_text:\n ; "{menu["band_text"]}"\n' + db(menu['band'])
    out += 'field_row:\n' + db(r for r, _, _ in fields)
    out += 'field_col:\n' + db(c for _, c, _ in fields)
    out += 'field_width:\n' + db(w for _, _, w in fields)
    out += 'choice_mask:\n' + db(mask for mask, _ in rows)
    out += 'choice_first:\n' + db(first)
    out += 'choice_end:\n' + db(end)
    out += 'choice_value:\n' + db(values)
    out += 'choice_text_at:\n' + db(text_at)
    out += 'choice_text:\n' + db(text)
    (directory / 'menu-text.inc').write_text(out)
    return menu
