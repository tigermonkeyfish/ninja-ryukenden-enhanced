"""Build the in-game menu's text rows from an editable layout and VERSION.

`src/options/menu.txt` holds the four menu rows as they appear: HUD rows
28-30 and the blank band under the HUD (row 31). Runs of '#' mark the value
fields, in order STAGE, PARALLAX and NO DAMAGE; the menu draws (and blinks)
the values there.
"""

# The native HUD font (menu text encoding in docs/ARCHITECTURE.md), plus the
# menu's own glyphs in the font's blank tiles: '.' $AA, ':' $AD and '/' $B9.
CODES = {' ': 0x9f, '-': 0x9a, '.': 0xaa, ':': 0xad, '/': 0xb9}
CODES.update({chr(ord('A') + i): 0x80 + i for i in range(26)})
CODES.update({str(i): 0xa0 + i for i in range(10)})

WIDTH, ROWS = 32, 4
FIELDS = (('STAGE_AT', 5), ('PARALLAX_AT', 3), ('DAMAGE_AT', 3))
# The held item's icon is a sprite over columns 13-14 of HUD rows 29-30
# (layout lines 2-3); nothing may be drawn there.
ITEM_BOX, ITEM_ROWS = range(13, 15), (1, 2)


def layout(lines):
    """(row bytes, {field: BAT low byte}) for four layout lines."""
    if len(lines) != ROWS:
        raise ValueError(f'Menu layout needs {ROWS} lines, found {len(lines)}')
    fields, data = [], bytearray()
    for row, line in enumerate(lines):
        if len(line) > WIDTH:
            raise ValueError(f'Menu line {row + 1} is longer than {WIDTH} columns: {line!r}')
        line = line.ljust(WIDTH)
        if row in ITEM_ROWS and any(line[c] != ' ' for c in ITEM_BOX):
            raise ValueError(f'Menu line {row + 1} reaches the item box (columns 13-14): {line!r}')
        column = 0
        while column < WIDTH:
            if line[column] == '#':
                end = column
                while end < WIDTH and line[end] == '#':
                    end += 1
                fields.append((row * 64 + column, end - column))
                column = end
            else:
                column += 1
        unknown = set(line) - set(CODES) - {'#'}
        if unknown:
            raise ValueError(f'Menu line {row + 1} has characters outside the HUD font: {sorted(unknown)}')
        data.extend(CODES[' ' if c == '#' else c] for c in line)
    if [width for _, width in fields] != [width for _, width in FIELDS]:
        raise ValueError(f'Menu layout needs value fields of widths {[w for _, w in FIELDS]} in order')
    return bytes(data), {name: at for (name, _), (at, _) in zip(FIELDS, fields)}


def generate(directory, version):
    lines = (directory / 'menu.txt').read_text().replace('{version}', version.upper()).splitlines()
    data, fields = layout(lines)
    text = ''.join(f'{name} = ${at:02x}\n' for name, at in fields.items())
    text += 'menu_rows:\n'
    for row in range(ROWS):
        text += f' ; "{lines[row]}"\n .db {",".join(str(b) for b in data[row * WIDTH:(row + 1) * WIDTH])}\n'
    (directory / 'menu-text.inc').write_text(text)
