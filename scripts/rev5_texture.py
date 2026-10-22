"""Upload-code generation (and extraction) for REV5-format renderers (2-2, 4-2).

These renderers upload phase tiles with immediate-store routines (`seek` then
`st1/st2` pairs) packed into code banks, select a routine per row and phase
from a row table, and place tiles through 64-word map rows. Generation
follows the original REV5 builder (no longer in the repository), so an
unmodified texture reproduces its output exactly; native_backdrops.py feeds
it textures decoded from the original ROM. Extraction simulates upload code
to recover a texture (useful for comparing older builds).
"""
import re

STATIC_CALL = r'initialize:\n lda #(\d+)\n tam #3\n jsr \$([0-9a-f]+)'
ROW_TABLE = r'^row(\d+):\n \.db .*\n \.db .*\n \.db .*$'

PROFILES = {
    # 15 code banks ($57-$65; $66 belongs to 6-1), then bank $7B and the unused
    # tails of 3-1's banks $48/$49 (see src/modules.json).
    'stage22': {'prefix': 'p3', 'bank': 0x56, 'rows': 16, 'bins': 15,
                'loops': [32] * 6 + [25] * 10, 'spill': lambda index: None,
                # Tiles $80-$FF and $6C0-$72F (cleared again at cinema entry), then
                # native 2-2 backdrop tiles that no foreground cell or sprite uses
                # (docs/ARCHITECTURE.md); the next stage reloads that VRAM.
                'slots': [*range(0x80, 0x100), *range(0x6c0, 0x730), *range(0x140, 0x14c),
                          *range(0x150, 0x15c), *range(0x160, 0x16c), *range(0x180, 0x18c),
                          *range(0x190, 0x19c), *range(0x1a0, 0x1ac), *range(0x1c0, 0x1cc),
                          *range(0x1d0, 0x1dc)],
                'extras': [(0x7b, 0x6000, 0x2000), (0x48, 0x7240, 0x8000 - 0x7240),
                           (0x49, 0x7240, 0x8000 - 0x7240)]},
    # 11 code banks ($68-$72), then the renderer bank's unused tail.
    'stage42': {'prefix': 'p5', 'bank': 0x67, 'rows': 22, 'bins': 11,
                'loops': [32] * 22, 'spill': lambda index: None,
                'extras': [(0x67, 0x761b, 0x8000 - 0x761b)]},
}


def data_bank(profile, index):
    spill = PROFILES[profile]['spill'](index)
    return spill if spill is not None else PROFILES[profile]['bank'] + 1 + index


def bank_index(profile, bank):
    for index in range(PROFILES[profile]['bins']):
        if data_bank(profile, index) == bank:
            return index
    raise ValueError(f'Bank {bank:02x} is not a {profile} code bank')


def row_table(inc_text):
    tables = {}
    for m in re.finditer(r'^row(\d+):\n \.db (.*)\n \.db (.*)\n \.db (.*)$', inc_text, re.M):
        banks, lo, hi = ([int(v) for v in m.group(i).split(',')] for i in (2, 3, 4))
        tables[int(m.group(1))] = [(banks[p], lo[p] | hi[p] << 8) for p in range(8)]
    return tables


def run_code(code, address, vram):
    """Execute one immediate-store routine: seek blocks, st1/st2 pairs, rts."""
    i = address - 0x6000
    cursor = None
    while True:
        op = code[i]
        if op == 0x60:
            return
        if code[i:i + 4] == bytes([0x64, 0x11, 0x03, 0x00]):
            assert code[i + 4] == 0x13 and code[i + 6] == 0x23
            cursor = code[i + 5] | code[i + 7] << 8
            assert code[i + 8:i + 14] == bytes([0xa9, 2, 0x85, 0x11, 0x03, 2])
            i += 14
        elif op == 0x13 and code[i + 2] == 0x23:
            vram[cursor] = code[i + 1] | code[i + 3] << 8
            cursor += 1
            i += 4
        else:
            raise ValueError(f'Unexpected opcode {op:02x} in upload routine at {address:04x}')


def decode_words(words):
    rows = []
    for y in range(8):
        p0, p1 = words[y] & 255, words[y] >> 8
        p2, p3 = words[8 + y] & 255, words[8 + y] >> 8
        rows.append(tuple((((p0 >> (7 - x)) & 1) | (((p1 >> (7 - x)) & 1) << 1) |
                           (((p2 >> (7 - x)) & 1) << 2) | (((p3 >> (7 - x)) & 1) << 3)) for x in range(8)))
    return tuple(rows)


def encode(rows):
    t = bytearray(32)
    for y, row in enumerate(rows):
        for x, pix in enumerate(row):
            for bit in range(4):
                t[bit // 2 * 16 + y * 2 + bit % 2] |= ((pix >> bit) & 1) << (7 - x)
    return bytes(t)


def extract(profile, assets, inc_text, main_text, loops=None):
    """Return (texture, rowpal): per row a list of 8x8 tiles in loop order."""
    cfg = PROFILES[profile]
    prefix, height = cfg['prefix'], cfg['rows']
    loops = loops or cfg['loops']
    bins = [assets[f'{prefix}-code{i}.bin'] for i in range(cfg['bins'])]
    bins = [b + b'\xff' * (8192 - len(b)) for b in bins]
    table = row_table(inc_text)
    m = re.search(STATIC_CALL, main_text)
    static_bank, static_addr = int(m.group(1)), int(m.group(2), 16)
    phase0 = {}
    run_code(bins[bank_index(profile, static_bank)], static_addr, phase0)
    for r in range(height):
        bank, addr = table[r][0]
        run_code(bins[bank_index(profile, bank)], addr, phase0)
    mp = assets[f'{prefix}-map.bin']
    texture, rowpal = [], []
    for r in range(height):
        row, pals = [], set()
        for n in range(loops[r]):
            word = mp[r * 128 + n] | mp[r * 128 + 64 + n] << 8
            slot = word & 0xfff
            pals.add(word >> 12)
            words = [phase0.get(slot * 16 + k) for k in range(16)]
            if None in words:
                raise ValueError(f'{profile}: tile for row {r} column {n} was never uploaded')
            row.append(decode_words(words))
        if len(pals) != 1:
            raise ValueError(f'{profile}: row {r} mixes palettes {pals}')
        texture.append(row)
        rowpal.append(pals.pop())
    return texture, rowpal


def generate(profile, texture, rowpal):
    """REV5 generation from per-row loop textures; returns maps, code banks and tables."""
    cfg = PROFILES[profile]
    pairs, lookup, map_rows, ranges = [], {}, [], []
    for y, row in enumerate(texture):
        first = len(pairs)
        out = []
        for n in range(len(row)):
            a, b = row[n], row[(n + 1) % len(row)]
            key = tuple(tuple(ra + rb) for ra, rb in zip(a, b))
            if key not in lookup:
                lookup[key] = len(pairs)
                pairs.append(key)
            out.append((rowpal[y], lookup[key]))
        ranges.append((first, len(pairs)))
        map_rows.append(out)
    available = cfg.get('slots') or [0x80 + i if i < 128 else 0x6c0 + i - 128 for i in range(320)]
    if len(pairs) > len(available):
        raise ValueError(f'{profile}: {len(pairs)} phase-tile pairs exceed the {len(available)}-slot atlas')
    slots = available[:len(pairs)]
    atlases = []
    for phase in range(8):
        data = bytearray()
        for pair in pairs:
            data += encode([r[phase:phase + 8] for r in pair])
        atlases.append(bytes(data))
    static_words = set()
    for first, end in ranges:
        run = []
        for word in range(first * 16, end * 16 + 1):
            fixed = word < end * 16 and len({atlas[word * 2:word * 2 + 2] for atlas in atlases}) == 1
            if fixed:
                run.append(word)
            else:
                if len(run) >= 4:
                    static_words.update(run)
                run = []

    def seek(address):
        return bytes([0x64, 0x11, 0x03, 0, 0x13, address & 255, 0x23, address >> 8, 0xa9, 2, 0x85, 0x11, 0x03, 2])

    static_code, last = bytearray(), -2
    for word in sorted(static_words):
        address = slots[word // 16] * 16 + word % 16
        if address != last + 1:
            static_code += seek(address)
        static_code += bytes([0x13, atlases[0][word * 2], 0x23, atlases[0][word * 2 + 1]])
        last = address
    if static_code:
        static_code += b'\x60'
    maps = bytearray()
    for row in map_rows:
        words = [(row[x % len(row)][0] << 12) | slots[row[x % len(row)][1]] for x in range(64)]
        maps += bytes(w & 255 for w in words) + bytes(w >> 8 for w in words)
    routines = []
    for phase, data in enumerate(atlases):
        for row, (first, end) in enumerate(ranges):
            code, last = bytearray(), -2
            for word in range(first * 16, end * 16):
                if word in static_words:
                    continue
                address = slots[word // 16] * 16 + word % 16
                if address != last + 1:
                    code += seek(address)
                code += bytes([0x13, data[word * 2], 0x23, data[word * 2 + 1]])
                last = address
            code += b'\x60'
            routines.append(((phase, row), bytes(code)))
    if static_code:
        routines.append(('static', bytes(static_code)))

    def pack(order):
        bins, extras, locations = [], [bytearray() for _ in cfg.get('extras', [])], {}
        for key, code in order:
            choice = next((j for j, x in enumerate(bins) if len(x) + len(code) <= 8192), len(bins))
            if choice == len(bins) and len(bins) < cfg['bins']:
                bins.append(bytearray())
            if choice < len(bins):
                locations[key] = (data_bank(profile, choice), 0x6000 + len(bins[choice]))
                bins[choice] += code
                continue
            for j, (bank, address, size) in enumerate(cfg.get('extras', [])):
                if len(extras[j]) + len(code) <= size:
                    locations[key] = (bank, address + len(extras[j]))
                    extras[j] += code
                    break
            else:
                return None
        return bins, extras, locations

    # Generation order first (reproduces the frozen assets); largest-first if needed.
    packed = pack(routines) or pack(sorted(routines, key=lambda kc: -len(kc[1])))
    if packed is None:
        raise ValueError(f'{profile}: upload code does not fit its banks and extra regions')
    bins, extras, locations = packed
    static_location = locations.pop('static', None)
    bins.extend([bytearray()] * (cfg['bins'] - len(bins)))
    return {'pairs': len(pairs), 'map': bytes(maps), 'bins': [bytes(b) for b in bins],
            'extras': [bytes(e) for e in extras], 'locations': locations,
            'static': static_location, 'loops': [len(r) for r in texture]}


def row_table_text(locations, height):
    out = []
    for r in range(height):
        locs = [locations[p, r] for p in range(8)]
        out.append(f'row{r}:\n .db ' + ','.join(str(b) for b, _ in locs) + '\n .db ' +
                   ','.join(str(a & 255) for _, a in locs) + '\n .db ' + ','.join(str(a >> 8) for _, a in locs))
    return '\n'.join(out)


def write(profile, work, out):
    """Write regenerated map, code banks, row tables and static call into a build directory."""
    cfg = PROFILES[profile]
    prefix, height = cfg['prefix'], cfg['rows']
    (work / f'{prefix}-map.bin').write_bytes(out['map'])
    for i, data in enumerate(out['bins']):
        (work / f'{prefix}-code{i}.bin').write_bytes(data)
    inc_path, main_path = work / f'{prefix}-generated.inc', work / 'main.asm'
    tables = {int(m.group(1)): m.group(0) for m in
              re.finditer(ROW_TABLE, row_table_text(out['locations'], height), re.M)}
    inc = re.sub(ROW_TABLE, lambda m: tables[int(m.group(1))], inc_path.read_text(), flags=re.M)
    for j, ((bank, address, _), data) in enumerate(zip(cfg.get('extras', []), out.get('extras', []))):
        if data:
            (work / f'{prefix}-extra{j}.bin').write_bytes(data)
            inc += f' .bank ${bank:02x}\n .org ${address:04x}\n .incbin "{prefix}-extra{j}.bin"\n'
    inc_path.write_text(inc)
    if out['static'] is None:
        raise ValueError(f'{profile}: generation produced no static upload code')
    bank, address = out['static']
    main = re.sub(STATIC_CALL, f'initialize:\n lda #{bank}\n tam #3\n jsr ${address:04x}', main_path.read_text())
    main_path.write_text(main)
