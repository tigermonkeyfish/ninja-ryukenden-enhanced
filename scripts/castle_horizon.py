"""Castle (5-3/5-4) and 6-1 backdrop maps and horizon uploads, from the
original ROM (native_gfx).

The castle and 6-1 mountain renderers share one scrolling horizon (map rows
14-22): the same tile slots and per-phase upload lists. The castle sky (rows
0-13) scrolls with it; the 6-1 sky is stationary.

* Loop: native_gfx.LOOPS[7], the original's columns 0-32 (33 tiles), which is
  what every round start shows. A seam search found no bridge of original
  columns that joins the horizon's clouds better than the plain wrap.
* Horizon pairs: images are generated from the decoded original tiles. A
  pair whose eight phase images an atlas slot holds byte for byte (a
  horizon pair of the sky atlas, or a phase-invariant fixed slot) uses that
  VRAM slot; every other pair goes to a borrowed VRAM tile. The upload lists
  name exactly the slots the map uses. Their images are stored phase by
  phase in tile order (STORE), so each phase uploads a few long runs: the
  per-run cost decides whether an area's first frame (a full redraw with
  both upload groups) finishes in time.
* Stars in horizon rows 14-15 belong to the sky. The castle map points those
  cells at the sky's animated star slots; the scrolling 6-1 horizon leaves
  them out because its sky is stationary.
* Sky atlas: the sky and star images (banks $7D-$7F and the $5D00 extra
  tiles) and the 32-column base map are regenerated from the original
  (atlas()), in the layout the first castle builder gave them. The static castle
  tables (sky upload lists, fixed uploads, star tables) must match it.
  Nothing is read from an earlier release.
"""
import re
from pathlib import Path

import native_gfx as N

REPO = Path(__file__).resolve().parents[1]
PROFILE = 7
ROWS = range(14, 23)
SKY_ROWS = range(N.CASTLE_SKY_ROWS)
# Native castle backdrop tiles that are loaded but unreferenced in Enhanced
# 5-3, 5-4 and 6-1 (VRAM audit, docs/ARCHITECTURE.md): map bytes $38-$3D,
# then $40-$57 ($23E/$23F and $258/$259 belong to 6-1 and 5-3 foregrounds).
# $238-$23C come first: the native 6-1 picture, shown until 6-1's first
# gameplay update draws, uses $23D, $243, $245-$247, $24C-$24F and $252.
BORROWED = [range(0x238, 0x23e), range(0x240, 0x258)]
# Horizon upload images (bank, MPR3 address, size), filled in order: banks
# $35-$36 (unused $FF in the original) and the unused tails of banks $4A/$4B.
STORE = [(0x35, 0x6000, 0x2000), (0x36, 0x6000, 0x2000),
         (0x4a, 0x7240, 0x8000 - 0x7240), (0x4b, 0x7240, 0x8000 - 0x7240)]
STAR_TILES = {0x198, 0x199, 0x1a4, 0x1a5}
# 6-1's stationary sky shows native columns 0-33 from a fixed window.
STATIONARY_COLUMNS = 34
# The original animates the stars by copying frame tile pairs ($100+n,
# $101+n) over tiles $198/$199 (group 2) and $162/$163 (group 3) in the
# order of the $FF-terminated frame lists at bank 2 $AD68 and $AD6D. The
# renderer follows the game's own frame counters ($3176/$3177).
STAR_ANIMATION = {0x162: (3, 0), 0x163: (3, 1), 0x198: (2, 0), 0x199: (2, 1)}
STAR_FRAMES = {2: 0x4000 + 0xad68 - 0xa000, 3: 0x4000 + 0xad6d - 0xa000}
# Atlas image k: bank $7D + k // 256 at $6000 + (k % 256) * 32 for the first
# three banks, then the module bank's $5D00 page (extra-tiles.bin).
ATLAS_BANKS = 3
EXTRA_TILES = 20


def atlas(rom):
    """The castle sky atlas, regenerated from the original.

    Pairs of the 32-column picture (all 23 rows, wrapping at 32), each in the
    palette of its higher-numbered cell, are deduplicated in picture order.
    Their phase images fill one image pool (phase by phase, deduplicated);
    a pair whose eight phases are one image is uploaded once. Each star pair
    type then adds one image per (phase, animation frame).
    """
    backdrop = N.Backdrop(rom, PROFILE)
    v = N.tile_words(rom, PROFILE)
    frames = {g: list(rom[a:rom.index(0xff, a)]) for g, a in STAR_FRAMES.items()}
    variants = sorted({t for seq in frames.values() for t in seq})

    def pixels(word, pal):
        return N.reindex(backdrop, (word >> 12, N.tile_pixels(v, word & 0xfff)), pal)

    def animated(word):
        return (word & 0xfff) in STAR_ANIMATION

    pairs, keys, map_rows, row_first = [], {}, [], []
    for line in backdrop.rows:
        row_first.append(len(pairs))
        row = []
        for x in range(32):
            a, b = line[x], line[(x + 1) % 32]
            pal = max(a >> 12, b >> 12)
            star = animated(a) or animated(b)
            key = (pixels(a, pal), pixels(b, pal), (a, b) if star else None, pal)
            if key not in keys:
                keys[key] = len(pairs)
                pairs.append((a, b, pal, key, star))
            row.append(keys[key])
        map_rows.append(row)
    pool, lookup = [], {}

    def intern(image):
        if image not in lookup:
            lookup[image] = len(pool)
            pool.append(image)
        return lookup[image]

    descriptors = [[None if star else intern(N.phase_images(key[0], key[1])[phase])
                    for a, b, pal, key, star in pairs] for phase in range(8)]
    fixed = {i: descriptors[0][i] for i in range(len(pairs))
             if descriptors[0][i] is not None and len({descriptors[p][i] for p in range(8)}) == 1}
    variant_maps = {}
    for group, dest in ((2, 0x198), (3, 0x162)):
        shown = (N.tile_pixels(v, dest), N.tile_pixels(v, dest + 1))
        initial = next(t for t in variants if (N.tile_pixels(v, 0x100 + t), N.tile_pixels(v, 0x101 + t)) == shown)
        variant_maps[group] = [variants.index(initial)] + [variants.index(t) for t in frames[group]]
    types, tables, stars = {}, [], []
    for i, (a, b, pal, key, star) in enumerate(pairs):
        if not star:
            continue
        side = 0 if animated(a) else 1
        group, half = STAR_ANIMATION[[a, b][side] & 0xfff]
        kind = (side, half, [b, a][side])
        if kind not in types:
            types[kind] = len(tables)
            table = []
            for phase in range(8):
                for t in variants:
                    words = [a, b]
                    words[side] = 0x1100 + t + half
                    table.append(intern(N.phase_images(pixels(words[0], 1), pixels(words[1], 1))[phase]))
            tables.append(table)
        stars.append((i, group, types[kind]))
    if len(pool) > 256 * ATLAS_BANKS + EXTRA_TILES:
        raise N.NativeError(f'castle atlas: {len(pool)} images exceed the atlas banks')
    lists = {}
    for phase in range(8):
        runs = []
        for i in range(row_first[ROWS[0]]):
            tile = descriptors[phase][i]
            if tile is None or i in fixed:
                continue
            last = runs[-1] if runs else None
            if last and last[0] + last[2] == i and last[1] + last[2] == tile and last[1] // 256 == tile // 256 and last[2] < 8:
                last[2] += 1
            else:
                runs.append([i, tile, 1])
        lists[phase] = [(0x7d + t // 256, (0x800 + d * 16) & 255, (0x800 + d * 16) >> 8,
                         (0x6000 + t % 256 * 32) & 255, (0x6000 + t % 256 * 32) >> 8, c) for d, t, c in runs]
    # Horizon pairs (from row 14) keep their atlas images, so a horizon pair
    # can reuse their slots.
    slots = {i: [descriptors[p][i] for p in range(8)] for i in range(row_first[ROWS[0]], len(pairs))
             if descriptors[0][i] is not None}
    if any(t >= 256 * ATLAS_BANKS for tiles in slots.values() for t in tiles):
        raise N.NativeError('castle atlas: a horizon image lies outside the atlas banks')
    raw = b''.join(pool)
    return {'pool': raw, 'pairs': len(pairs), 'slots': slots,
            'map': b''.join(bytes((0x80 + row[x % 32]) & 255 for x in range(64)) for row in map_rows),
            'high': [pal << 4 for a, b, pal, key, star in pairs],
            'fixed': [(0x7d + t // 256, d, 0x6000 + t % 256 * 32) for d, t in fixed.items()],
            'lists': lists, 'tables': tables, 'star_dest': [i for i, g, t in stars],
            'star_group': [g for i, g, t in stars], 'variant2': variant_maps[2], 'variant3': variant_maps[3]}


def check_tables(inc, out):
    """The static sky/star tables of a castle-generated.inc must be the
    regenerated atlas's (they index its images)."""
    lists, fixed, high = parse(inc)

    def db(name):
        m = re.search(rf'^{name}:\n \.(?:db|dw) (.*)$', inc, re.M)
        return [int(x) for x in m.group(1).split(',')] if m else None
    checks = [('fixed uploads', fixed, out['fixed']), ('tile_high', high[:out['pairs']], out['high']),
              *((f'sky upload list {p}', lists[p, 0], [tuple(r) for r in out['lists'][p]]) for p in range(8)),
              *((f'star_type{i}', db(f'star_type{i}'), t) for i, t in enumerate(out['tables'])),
              *((name, db(name), out[name]) for name in ('star_dest', 'star_group', 'variant2', 'variant3'))]
    for name, got, want in checks:
        if got != want:
            raise N.NativeError(f'castle-generated.inc: {name} does not match the regenerated castle atlas')


def write_atlas(work, rom, banks):
    """Regenerated atlas images: extra-tiles.bin, and data0-2.bin (banks $7D-$7F)
    for the module that emits those banks."""
    out = atlas(rom)
    check_tables((work / 'castle-generated.inc').read_text(), out)
    pool = out['pool']
    (work / 'extra-tiles.bin').write_bytes(pool[ATLAS_BANKS * 0x2000:])
    if banks:
        for i in range(ATLAS_BANKS):
            (work / f'data{i}.bin').write_bytes(pool[i * 0x2000:(i + 1) * 0x2000])
    return out


def parse(inc):
    lists = {}
    for m in re.finditer(r'^upload_(\d)_(\d):\n((?: \.db .*\n)+)', inc, re.M):
        lines = m.group(3).strip().split('\n')
        runs = [tuple(int(v) for v in line.split('.db')[1].split(',')) for line in lines[1:]]
        if len(runs) != int(lines[0].split('.db')[1]):
            raise ValueError('Malformed upload list')
        lists[int(m.group(1)), int(m.group(2))] = runs
    fixed = [(int(b, 16), int(s), int(src, 16)) for b, s, src in re.findall(
        r'lda #\$([0-9a-f]+)\n tam #3\n lda #(\d+)\n jsr seek_tile\n tia \$([0-9a-f]+),\$0002,32', inc)]
    high = [int(v) for v in re.search(r'^tile_high:\n \.db (.*)$', inc, re.M).group(1).split(',')]
    return lists, fixed, high


def slot_images(sky):
    """slot (0-127) -> 8 phase images (32 bytes each) of the atlas slots a
    horizon pair can reuse: the fixed (phase-invariant) slots and the atlas's
    horizon slots. Sky slots that change with the phase are left out: the
    6-1 sky stays at one phase while its horizon scrolls."""
    pool = sky['pool']

    def image(t):
        return pool[t * 32:t * 32 + 32]
    images = {slot: [image((bank - 0x7d) * 256 + (src - 0x6000) // 32)] * 8 for bank, slot, src in sky['fixed']}
    images.update({slot: [image(t) for t in tiles] for slot, tiles in sky['slots'].items()})
    return images


def horizon_word(word):
    """The shared horizon leaves out the sky's stars (rows 14-15)."""
    return N.PLAIN_SKY if (word & 0xfff) in STAR_TILES else word


def build(inc, rom, sky):
    _, fixed, high = parse(inc)
    images = slot_images(sky)
    backdrop = N.Backdrop(rom, PROFILE)
    loop = N.LOOPS[PROFILE]
    length = len(loop)

    def cell(r, c):
        return backdrop.cell(horizon_word(backdrop.rows[r][c]))

    # Pairs and their eight phase images, in the palette of the pair's
    # higher-numbered cell (the castle's rule); colours never change.
    pair_of, pairs = {}, {}
    for r in ROWS:
        for u in range(length):
            a, b = cell(r, loop[u]), cell(r, loop[(u + 1) % length])
            pal = max(a[0], b[0])
            key = (pal, N.phase_images(N.reindex(backdrop, a, pal), N.reindex(backdrop, b, pal)))
            pairs.setdefault(key, len(pairs))
            pair_of[r, u] = key

    existing = {}
    for s in sorted(images):
        if None not in images[s]:
            existing.setdefault((high[s] >> 4, tuple(images[s])), s)
    assign = {key: 0x80 + existing[key] for key in pairs if key in existing}
    new = sorted((k for k in pairs if k not in assign), key=lambda k: pairs[k])
    tiles = [t for block in BORROWED for t in block]
    if len(new) > len(tiles) or any(k[0] != 0 for k in new):
        raise ValueError(f'{len(new)} new castle horizon pairs do not fit the borrowed palette-0 tiles')
    for key, t in zip(new, tiles):
        assign[key] = t
    # Upload lists: exactly the slots the horizon map uses (slots uploaded once
    # by upload_fixed need no list entry), merged into contiguous runs.
    fixed_slots = {slot for _, slot, _ in fixed}
    used = sorted({(assign[key], key) for key in pairs if assign[key] - 0x80 not in fixed_slots},
                  key=lambda tk: tk[0])
    store = [bytearray() for _ in STORE]
    region = 0
    new_lists = {}
    for phase in range(8):
        runs = []
        for tile, key in used:
            while len(store[region]) + 32 > STORE[region][2]:
                region += 1
                if region == len(STORE):
                    raise ValueError('Castle horizon tile images exceed their ROM space')
            bank, address, _ = STORE[region]
            src = address + len(store[region])
            store[region] += key[1][phase]
            last = runs[-1] if runs else None
            if (last and last[0] == bank and ((last[2] << 8) | last[1]) // 16 + last[5] == tile
                    and ((last[4] << 8) | last[3]) + 32 * last[5] == src):
                last[5] += 1
            else:
                runs.append([bank, tile * 16 & 255, tile * 16 >> 8, src & 255, src >> 8, 1])
        if 1 + 6 * len(runs) > 256:
            raise ValueError('Castle horizon upload list exceeds 256 bytes')
        new_lists[phase] = runs
    horizon = {r: bytes(assign[pair_of[r, u % length]] & 0xff for u in range(64)) for r in ROWS}
    return {'horizon': horizon, 'lists': new_lists, 'high': list(high),
            'pools': {r: bytes(data) for r, data in zip(STORE, store) if data}, 'pairs': len(pairs), 'new': len(new),
            'borrowed': sorted(t for t in assign.values() if t >= 0x100), 'backdrop': backdrop}


def sky_slots(mapdata, words):
    """(left word, right word) -> map byte of the existing castle sky slots
    (the atlas's 32-column castle sky; the stars' images are animated)."""
    slot = {}
    for r in SKY_ROWS:
        for c in range(32):
            pair = (words[r][c], words[r][(c + 1) % 32])
            if slot.setdefault(pair, mapdata[r * 64 + c]) != mapdata[r * 64 + c]:
                raise ValueError('Castle sky word pair has two slots')
    return slot


def sky_rows(mapdata, words, entry):
    """Sky rows 0-13 of a map whose entry e shows native word entry(row, e)."""
    slot = sky_slots(mapdata, words)
    out = bytearray(mapdata)
    for r in SKY_ROWS:
        for u in range(64):
            pair = (entry(r, u), entry(r, u + 1))
            if pair not in slot:
                raise ValueError(f'No castle sky slot for {pair[0]:04x},{pair[1]:04x}')
            out[r * 64 + u] = slot[pair]
    return bytes(out)


def castle_stars(horizon, mapdata, words):
    """Castle map rows 14-15: the native stars through the sky's star slots.

    Every star pair of rows 14-15 (plain sky beside 11A4/11A5 or the animated
    1198/1199) also occurs in the castle sky rows, so its slot already holds
    the right (animated) images and needs no upload of its own.
    """
    loop = N.LOOPS[PROFILE]
    slot = sky_slots(mapdata, words)
    out = dict(horizon)
    for r in (14, 15):
        row = bytearray(out[r])
        for u in range(64):
            pair = (words[r][loop[u % len(loop)]], words[r][loop[(u + 1) % len(loop)]])
            if any((w & 0xfff) in STAR_TILES for w in pair):
                if pair not in slot:
                    raise ValueError(f'No castle sky slot for star pair {pair[0]:04x},{pair[1]:04x}')
                row[u] = slot[pair]
        out[r] = bytes(row)
    return out


def castle_map(mapdata, out):
    """Castle 5-3/5-4: sky and horizon on the loop, stars from the sky slots."""
    words = out['backdrop'].rows
    loop = N.LOOPS[PROFILE]
    sky = sky_rows(mapdata, words, lambda r, u: words[r][loop[u % len(loop)]])
    horizon = castle_stars(out['horizon'], mapdata, words)
    return sky[:14 * 64] + b''.join(horizon[r] for r in ROWS)


def stationary_sky(mapdata, words):
    """6-1 sky: native columns 0-33 from entry 0, then plain sky (no wrap)."""
    def entry(r, u):
        return words[r][u] if u < STATIONARY_COLUMNS else N.PLAIN_SKY
    return sky_rows(mapdata, words, entry)


def write(work, mapfile, rom, castle):
    """Regenerate a module's map, horizon upload lists and (castle) image pool."""
    inc_path = work / 'castle-generated.inc'
    inc = inc_path.read_text()
    sky = write_atlas(work, rom, castle)
    mapdata = sky['map']
    out = build(inc, rom, sky)
    if castle:
        (work / mapfile).write_bytes(castle_map(mapdata, out))
    else:
        # The castle module emits the image pool; 6-1 must assign identically.
        shared = build((REPO / 'src/castle/castle-generated.inc').read_text(), rom, sky)
        if shared['lists'] != out['lists'] or shared['horizon'] != out['horizon']:
            raise ValueError('6-1 and castle horizon assignments differ')
        (work / mapfile).write_bytes(mapdata[:14 * 64] + b''.join(out['horizon'][r] for r in ROWS))
    for phase, runs in out['lists'].items():
        body = f' .db {len(runs)}\n' + ''.join(f' .db {",".join(map(str, run))}\n' for run in runs)
        inc, count = re.subn(rf'^upload_{phase}_1:\n(?: \.db .*\n)+', f'upload_{phase}_1:\n' + body, inc, flags=re.M)
        if count != 1:
            raise ValueError('Upload list not found in castle-generated.inc')
    inc, count = re.subn(r'^tile_high:\n \.db .*$', 'tile_high:\n .db ' + ','.join(map(str, out['high'])), inc, flags=re.M)
    if count != 1:
        raise ValueError('tile_high not found in castle-generated.inc')
    if castle:
        for i, ((bank, address, _), data) in enumerate(out['pools'].items()):
            (work / f'horizon-pool{i}.bin').write_bytes(data)
            inc += f' .bank ${bank:02x}\n .org ${address:04x}\n .incbin "horizon-pool{i}.bin"\n'
    inc_path.write_text(inc)
    return out


def write_sky(work, mapfile, rom):
    """6-1 stationary sky map (and the atlas's extra tiles)."""
    data = write_atlas(work, rom, False)['map']
    words = N.Backdrop(rom, PROFILE).rows
    (work / mapfile).write_bytes(stationary_sky(data, words)[:14 * 64] + data[14 * 64:])
