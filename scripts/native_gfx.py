"""The original game's backdrops, decoded from the original ROM alone.

Tiles. Ninja Ryukenden stores its graphics packed. The loader (bank 0
`$EE6F`) looks up a request (4 bytes at `$E860 + 4*n`: asset, type, first
tile, count), the asset (tables `$EAD3/$EB50/$EBCD/$EC4A/$ECC7/$ED44/$EDC1`:
kind and mode, base tile, tiles, span, bank and address) and unpacks it into
VRAM. Mode 0 (`$F13F`): every 16-byte half tile starts both byte lanes (low,
high) at 0; each control byte covers 8 output bytes, one bit each, alternating
low/high: 1 reads a literal, 0 repeats that lane's last byte. The other modes
pack fewer bitplanes (`$F05F`, `$F07C`, `$F09C`).

Maps. Each backdrop (profile) is a map of 34 tile words per row at ROM
`0x7A000 + address - 0xA000`, indexed by the table at `0x221F` (height,
cutoff, address). Its stage's initialization loads the tiles to VRAM `$1000`
and `$2000` (bank 1 per-stage blocks, e.g. `$87E8` for 2-2).

Palettes. The table at bank `$37:$6000` (ROM `0x6E000`) holds (address,
colour count) per palette set; `$F211` unpacks a set into the RAM palette:
per 8 colours one byte of bit-8 values (MSB first), then the 8 low bytes.

Everything below is pinned by SHA-256 of what it decodes to, and was checked
word for word against the original's VRAM and VCE in the emulator
(docs/validation). No capture or frozen patch data is read.
"""
import hashlib
import struct

PROFILE_TABLE = 0x221F
MAP_BASE = 0x7A000 - 0xA000
PALETTE_TABLE = 0x6E000

# profile: name, tile-set requests (request, VRAM word address), palette set,
# sha256 of (decoded tile words, map bytes, packed palette bytes).
PROFILES = {
    0: ('1-1', [(0x10, 0x1000), (0x62, 0x2000)], 1, (
        '7a12bf47a8dd2dbb7419b13ad07a9fdb9a4c9fa02ffa9626c395a490a515e9f2',
        '942998212faa3dbc4f36fed2f48ed897fa224b7a9944ea7fb48169bcefd1b171',
        'f1dbd2f67aa355c3167cc7a0cb065e3fc84984a2f907c18160b7c61fdf9f2507')),
    1: ('5-2', [(0x51, 0x1000), (0x63, 0x2000)], 13, (
        '61811fc0472efa8488799fae0f89adb54dcfdf623fdee44181d83e85b72eeae4',
        'ec84eb259a4549dd4dc91ee1a8bd2cc6f26b7169e1273f526482eecd6cd88e1f',
        '852921b20a6178038adc89c671ecb768ca5acaa1fb87505b7c9b7f01e5ba6f39')),
    2: ('3-1', [(0x23, 0x1000), (0x24, 0x2000)], 6, (
        '1d35ba03d9c1c988c1031fb926ae5ebda6604dace6a753a8309b3a5fcebe1699',
        'ef2875e4c6f33e627d8df13efba01c44be849fdc0d4fee3687cf9cc33a34c788',
        '1c347415c23d4e497956ede68f623c2b0e3494a58daaefead398f4e0567b8d81')),
    3: ('2-2', [(0x64, 0x1000), (0x65, 0x2000)], 4, (
        'beb7d9670d828efcaff60d90c34c2e5c4ab96a3c1f70063b67e0fcc341b5222f',
        '03274996783eb49fa263ef1e36bbcfb48b20c5348a11b3a0079cc2a9ffa89e4d',
        'd37e3d27c92cc7a7c344aa01fc1b0f1fd459ceac0a9475b4e6f67cd706fc4e41')),
    4: ('3-2', [(0x23, 0x1000), (0x24, 0x2000)], 6, (
        '1d35ba03d9c1c988c1031fb926ae5ebda6604dace6a753a8309b3a5fcebe1699',
        '96bd9d8bf7ab8552a7b06627d3fc0367f4e789491bcb05b2dfd0745946ead94c',
        '1c347415c23d4e497956ede68f623c2b0e3494a58daaefead398f4e0567b8d81')),
    5: ('4-2', [(0x35, 0x1000), (0x66, 0x2000)], 9, (
        'e7352a04e592d838be7e8a28741ad5c2256074d0d84d6b3d673538a9d2548377',
        '3daefd2d5f99dc27783f6c9ac61229c938c47fb1be498c88960698fe2bbf7fda',
        '26b160cf0bcd91c077785c65edaa045396a3e5e46b9573bc27487679910c7ab5')),
    6: ('4-1', [(0x68, 0x1000), (0x69, 0x2000)], 8, (
        '808770e00d2defd2be9cb9ce2a47d688f3457dd5da1b815a46bafbcb6175d415',
        '1c62b30792a0f2ec4cbafc9d6ee1161cca67604934df56781e472df4cb4ef9e7',
        'e18a1b4a9f6c6b8d160e32c0c16f05a014dd6155b9a02628ab04c2197e59b497')),
    # The castle backdrop of 5-3, 5-4 and 6-1.
    7: ('castle', [(0x52, 0x1000), (0x6A, 0x2000)], 14, (
        'c1527dfe79f6e8c54dda70f883e755d7e34b4e164fdf02ded9dde73ccfd3e8de',
        'c5bbcb3b0b1d90dfd044289d9ff4ffbe7345c27ba4064f1f829b95a08f3bb14d',
        '53ebce291e824ff0d3123a0b3349e5cee20c18227a0d6ac105052a9c8d2f853b')),
    8: ('6-3', [(0x57, 0x1000), (0x6C, 0x2000)], 16, (
        '54d7711cf06c10ad844597700cf339ec0548a8abf90f9ffbe01168d5d1f1397b',
        'cb396c2a1e20fa103890ef2128bca3241c8632eb3f874b1a63e6a4b200d6fc84',
        'd80fe2a3cf6a316a737a93c3e896f85dbef5711902b803dae6ae4525d452f6bf')),
}

# Loops of original columns only. The original never scrolls these backdrops
# (they are screen-locked), so it has no designed loop. Each loop keeps the
# native picture in order, as far as round starts show it (columns 0-31 when
# every round with backdrop opens at camera 0, 0-32 when some open later),
# then repeats native columns chosen by scripts/native_seams.py (fewest 16x8
# windows that the original never shows in that row) before wrapping to
# column 0. docs/validation records the review of each loop.
LOOPS = {
    0: list(range(32)) + [18, 19, 20],
    1: list(range(33)),
    2: list(range(32)) + [2, 3, 4, 5, 6, 7, 8, 9],
    3: list(range(34)) + list(range(9, 25)),
    4: list(range(32)),
    5: list(range(34)),
    6: list(range(32)) + [17, 18, 19, 20, 21, 22, 23, 3, 4, 26, 27, 28, 29, 30],
    7: list(range(33)),
    8: list(range(33)) + [3, 4],
}
# Last native column each loop must keep in order for exact round starts.
ROUND_START_COLUMNS = {0: 31, 1: 32, 2: 31, 3: 32, 4: 31, 5: 31, 6: 31, 7: 32, 8: 32}
# Castle sky rows (0-13) continue with plain sky (native word $0202) instead,
# so a bridge never repeats part of the moon.
CASTLE_SKY_ROWS = 14
PLAIN_SKY = 0x0202


class NativeError(ValueError):
    pass


class _Stream:
    def __init__(self, rom, pos):
        self.rom, self.pos = rom, pos

    def byte(self):
        v = self.rom[self.pos]
        self.pos += 1
        return v

    def unpack(self, out, halves, groups):
        """$F13F: per half tile both lanes restart at 0; per group a control
        byte, then 4 x (low, high): bit 1 = literal, 0 = the lane's last byte"""
        for _ in range(halves):
            lanes = [0, 0]
            for _ in range(groups):
                ctrl = self.byte()
                for _ in range(4):
                    pair = []
                    for lane in (0, 1):
                        ctrl <<= 1
                        if ctrl & 0x100:
                            lanes[lane] = self.byte()
                        ctrl &= 0xFF
                        pair.append(lanes[lane])
                    out.append(pair[0] | pair[1] << 8)

    def skip_groups(self, count):
        """$F119: skip packed groups (a control byte and its literals)"""
        for _ in range(count):
            self.pos += bin(self.byte()).count('1')

    def plane(self, out):
        """$F0F6: one plane, low bytes literal-or-repeat, high bytes zero"""
        ctrl = self.byte()
        a = 0
        for _ in range(8):
            ctrl <<= 1
            if ctrl & 0x100:
                a = self.byte()
            ctrl &= 0xFF
            out.append(a)


def _b0(rom, addr):
    return rom[addr - 0xE000]           # bank 0 is fixed at $E000


def asset(rom, x):
    bank = ((_b0(rom, 0xEDC1 + x) << 3) | (_b0(rom, 0xED44 + x) >> 5)) & 0xFF
    addr = _b0(rom, 0xECC7 + x) | ((_b0(rom, 0xED44 + x) & 0x1F) | 0x60) << 8
    return {'offset': bank * 0x2000 + addr - 0x6000, 'kind': _b0(rom, 0xEAD3 + x) & 0x0F,
            'mode': (_b0(rom, 0xEAD3 + x) >> 3) & 6, 'base': _b0(rom, 0xEB50 + x),
            'count': _b0(rom, 0xEBCD + x), 'span': _b0(rom, 0xEC4A + x)}


def request(rom, n, vbase):
    """[(VRAM word address, word)] written by request n with VRAM base vbase
    (tile sets only: $EEFB with its header $EF5B)"""
    e = 0xE860 + n * 4
    x, typ, start, cnt = _b0(rom, e), _b0(rom, e + 1) >> 3, _b0(rom, e + 2), _b0(rom, e + 3)
    a = asset(rom, x)
    if typ != 0 or a['kind'] != 1:
        raise NativeError(f'request {n:#x}: only tile sets are modelled (type {typ}, kind {a["kind"]})')
    lead, skip = (a['base'] - start) & 0xFF, 0
    if a['base'] < start:
        lead, skip = 0, (start - a['base']) & 0xFF
    t27 = (0 - start - cnt) & 0xFF
    y = 0
    if a['span'] >= t27:
        trail = a['span'] - t27
    else:
        y, trail = (a['span'] - t27) & 0xFF, 0
    n_tiles = (y + a['count'] - skip) & 0xFF
    words = [0] * (lead * 16)
    src = _Stream(rom, a['offset'])
    mode = a['mode']
    if n_tiles:
        for _ in range(skip):
            src.skip_groups({0: 4, 2: 3, 4: 2, 6: 1}[mode])
        for _ in range(n_tiles):
            if mode == 0:                   # four bitplanes
                src.unpack(words, 2, 2)
            elif mode == 2:                 # planes 0-1 packed, plane 2 packed, plane 3 zero
                src.unpack(words, 1, 2)
                src.plane(words)
            elif mode == 4:                 # planes 0-1 packed, 2-3 zero
                src.unpack(words, 1, 2)
                words += [0] * 8
            else:                           # plane 0 packed
                src.plane(words)
                words += [0] * 8
    words += [0] * (trail * 16)
    dest = ((start << 4) + vbase) & 0xFFFF
    return [((dest + k) & 0xFFFF, w) for k, w in enumerate(words)]


def tile_words(rom, profile):
    """{VRAM word address: word} after the profile's two tile-set requests"""
    v = {}
    for n, vbase in PROFILES[profile][1]:
        for addr, w in request(rom, n, vbase):
            v[addr] = w
    return v


def profile_map(rom, profile):
    h, _, addr = struct.unpack_from('<BBH', rom, PROFILE_TABLE + profile * 4)
    raw = rom[MAP_BASE + addr:MAP_BASE + addr + 34 * h * 2]
    words = struct.unpack(f'<{34 * h}H', raw)
    return [list(words[r * 34:(r + 1) * 34]) for r in range(h)], raw


def palette_set(rom, n):
    """(colours as 9-bit VCE values, packed bytes) of palette set n"""
    addr, count = struct.unpack_from('<HH', rom, PALETTE_TABLE + 4 * n)
    pos = PALETTE_TABLE + addr - 0x6000
    raw = rom[pos:pos + count // 8 * 9]
    out = []
    for g in range(0, len(raw), 9):
        for i in range(8):
            out.append(raw[g + 1 + i] | ((raw[g] >> (7 - i)) & 1) << 8)
    return out, raw


def tile_pixels(v, tile):
    w = [v.get(tile * 16 + k, 0) for k in range(16)]
    out = []
    for y in range(8):
        a, b = w[y], w[y + 8]
        out.append(tuple(((a >> (7 - x)) & 1) | ((a >> (15 - x)) & 1) << 1 |
                         ((b >> (7 - x)) & 1) << 2 | ((b >> (15 - x)) & 1) << 3 for x in range(8)))
    return tuple(out)


def encode(pixels):
    """8x8 palette indices -> 32-byte PC Engine tile"""
    t = bytearray(32)
    for y, row in enumerate(pixels):
        for x, i in enumerate(row):
            for b in range(4):
                t[b // 2 * 16 + y * 2 + b % 2] |= ((i >> b) & 1) << (7 - x)
    return bytes(t)


def digest(rom, profile):
    v = tile_words(rom, profile)
    tiles = hashlib.sha256(b''.join(struct.pack('<HH', a, w) for a, w in sorted(v.items()))).hexdigest()
    palette = hashlib.sha256(palette_set(rom, PROFILES[profile][2])[1]).hexdigest()
    return tiles, hashlib.sha256(profile_map(rom, profile)[1]).hexdigest(), palette


class Backdrop:
    """A native backdrop: map words, per-word pixels and the palette set."""

    def __init__(self, rom, profile):
        try:
            found = digest(rom, profile)
        except (IndexError, struct.error, NativeError):
            found = None
        if found != PROFILES[profile][3]:
            raise NativeError(f'{PROFILES[profile][0]}: the ROM does not decode to the recorded backdrop')
        self.profile = profile
        self.name = PROFILES[profile][0]
        self.rows, _ = profile_map(rom, profile)
        self.height = len(self.rows)
        self.colours = palette_set(rom, PROFILES[profile][2])[0]
        v = tile_words(rom, profile)
        self.pixels = {w: tile_pixels(v, w & 0xFFF) for row in self.rows for w in row}

    def cell(self, word):
        """(palette, 8x8 indices) as the original draws this map word"""
        return (word >> 12, self.pixels[word])

    def colour(self, palette, index):
        return None if index == 0 else self.colours[palette * 16 + index]

    def loop_words(self, sequence=None, row_override=None):
        """per row, the map words of the loop in order"""
        sequence = LOOPS[self.profile] if sequence is None else sequence
        out = []
        for r, row in enumerate(self.rows):
            if row_override and r in row_override:
                out.append(row_override[r](row, sequence))
            else:
                out.append([row[c] for c in sequence])
        return out


def prefix(sequence):
    """Length of the loop's leading run of native columns 0, 1, 2, ..."""
    n = 0
    while n < len(sequence) and sequence[n] == n:
        n += 1
    return n


def castle_sky(row, sequence):
    """Castle sky rows: the loop's native picture, then plain sky."""
    n = prefix(sequence)
    return [row[c] for c in range(n)] + [PLAIN_SKY] * (len(sequence) - n)


def native_pairs(backdrop):
    """Every pair of cells the original draws side by side in its on-screen
    columns 0-31 (columns 32-33 are filler for the backdrop's 8px jitter)."""
    return {(backdrop.cell(row[x]), backdrop.cell(row[x + 1])) for row in backdrop.rows for x in range(31)}


def seams(backdrop, words):
    """Joins (row, loop position) whose two cells the original never draws side by side."""
    native = native_pairs(backdrop)
    out = []
    for r in range(backdrop.height):
        loop = words[r]
        for u in range(len(loop)):
            pair = (backdrop.cell(loop[u]), backdrop.cell(loop[(u + 1) % len(loop)]))
            if pair[0] != pair[1] and pair not in native:
                out.append((r, u))
    return out


def phase_images(left, right):
    """Eight one-pixel phases of two adjacent 8x8 index tiles (same palette)."""
    return tuple(encode([ra[p:] + rb[:p] for ra, rb in zip(left, right)]) for p in range(8))


def merged_palette(colours, name):
    """Opaque colours (9-bit) -> a 16-entry palette: entry 0 unused, then the
    colours in ascending order. Pixel 0 stays transparent everywhere."""
    colours = sorted(set(colours))
    if len(colours) > 15:
        raise NativeError(f'{name}: {len(colours)} colours do not fit one palette')
    return [0] + colours + [0] * (15 - len(colours))


def reindex(backdrop, cell, target, palette=None):
    """Pixels of `cell` expressed in palette `target` (its native colours, or the
    16 colours `palette`), colour for colour; pixel 0 stays 0."""
    pal, px = cell
    if palette is None and pal == target:
        return px
    entries = palette if palette is not None else [backdrop.colours[target * 16 + i] for i in range(16)]
    lookup = {}
    for i in range(1, 16):
        lookup.setdefault(entries[i], i)

    def index(v):
        if v == 0:
            return 0
        c = backdrop.colour(pal, v)
        if c not in lookup:
            raise NativeError(f'{backdrop.name}: colour {c:03x} of palette {pal} is not in palette {target}')
        return lookup[c]
    return tuple(tuple(index(v) for v in row) for row in px)
