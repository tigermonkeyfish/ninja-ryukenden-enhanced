"""ROM-free checks for reusable patch and tile tooling."""
import hashlib
import json
import struct
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import bps
from pce_tiles import decode_tile, encode_tile, horizontal_phases
from project import ROM_SIZE, load_manifest, original_image


class PatchTests(unittest.TestCase):
    def test_header_removal_changed_data_and_target_copy(self):
        body = bytes(range(256)) * 4
        source = b'H' * 512 + body
        target = body[:301] + b'changed' + body[308:] + b'\xff' * 300
        patch = bps.create(source, target, metadata=b'Synthetic test')
        self.assertEqual(bps.apply(source, patch), target)
        with self.assertRaisesRegex(ValueError, 'Source CRC'):
            bps.apply(b'J' + source[1:], patch)
        with self.assertRaisesRegex(ValueError, 'Patch CRC'):
            bps.apply(source, patch[:-1] + bytes([patch[-1] ^ 1]))

    def test_headerless_source(self):
        source = bytes(range(100))
        target = source[:50] + b'\x81' + source[51:] * 2
        self.assertEqual(bps.apply(source, bps.create(source, target, header=0)), target)


class AssetTransformTests(unittest.TestCase):
    def test_unknown_names_are_rejected(self):
        from asset_transforms import prepare
        with self.assertRaisesRegex(ValueError, 'Unknown module prepare'):
            prepare('missing', Path('.'), b'')

    def test_every_backdrop_module_regenerates_from_the_original(self):
        from asset_transforms import PREPARE
        for module in json.loads((ROOT / 'src/modules.json').read_text()):
            if 'prepare' in module:
                self.assertIn(module['prepare'], PREPARE)


def pack_half(words):
    """Inverse of the native $F13F packing for one 16-byte half tile: per
    group of 4 words a control byte, MSB first, low then high lane, 1 = literal."""
    out, lanes = bytearray(), [0, 0]
    for g in range(0, len(words), 4):
        ctrl, data = 0, bytearray()
        for i, w in enumerate(words[g:g + 4]):
            for lane, v in enumerate((w & 255, w >> 8)):
                bit = 7 - (i * 2 + lane)
                if v != lanes[lane]:
                    ctrl |= 1 << bit
                    data.append(v)
                    lanes[lane] = v
        out += bytes([ctrl]) + data
    return out


class NativeGfxTests(unittest.TestCase):
    def test_unpack_inverts_native_packing_and_restarts_lanes(self):
        import native_gfx as N
        words = [0x1234, 0x1234, 0x0034, 0xff00, 0, 0, 0x8001, 0x8001] * 2
        stream = pack_half(words[:8]) + pack_half(words[8:])
        out = []
        N._Stream(stream, 0).unpack(out, 2, 2)
        self.assertEqual(out, words)

    def test_palette_sets_unpack_bit_eight_first(self):
        import native_gfx as N
        rom = bytearray(0x70000)
        struct.pack_into('<HH', rom, N.PALETTE_TABLE + 4, 0x6100, 8)
        rom[N.PALETTE_TABLE + 0x100:N.PALETTE_TABLE + 0x109] = bytes([0b10000001, 1, 2, 3, 4, 5, 6, 7, 8])
        colours, raw = N.palette_set(bytes(rom), 1)
        self.assertEqual(colours, [0x101, 2, 3, 4, 5, 6, 7, 0x108])
        self.assertEqual(len(raw), 9)

    def test_backdrop_requires_the_recorded_original(self):
        import native_gfx as N
        with self.assertRaisesRegex(N.NativeError, 'does not decode'):
            N.Backdrop(bytes(0x80000), 3)

    def test_loops_keep_the_round_start_columns_and_fit_the_map(self):
        import native_gfx as N
        for profile, loop in N.LOOPS.items():
            keep = N.ROUND_START_COLUMNS[profile]
            self.assertEqual(loop[:keep + 1], list(range(keep + 1)))
            self.assertTrue(33 <= len(loop) + (keep == 31) <= 64 and all(0 <= c < 34 for c in loop))

    def test_phase_images_and_palettes(self):
        import native_gfx as N
        left = tuple(tuple(range(8)) for _ in range(8))
        right = tuple(tuple(range(8, 16)) for _ in range(8))
        for p, image in enumerate(N.phase_images(left, right)):
            self.assertEqual(decode_tile(image), [list(range(p, p + 8))] * 8)
        self.assertEqual(N.merged_palette([0x40, 0x10, 0x40], 'x'), [0, 0x10, 0x40] + [0] * 13)
        with self.assertRaisesRegex(N.NativeError, 'do not fit'):
            N.merged_palette(range(16), 'x')

    def fake(self):
        import native_gfx as N
        class Fake:
            name = 'fake'
            colours = list(range(0x100, 0x120))
            def cell(self, w):
                return (w >> 12, tuple(tuple([w & 15] * 8) for _ in range(8)))
            def colour(self, pal, v):
                return None if v == 0 else self.colours[pal * 16 + v]
        f = Fake()
        f.rows = [[0x0001, 0x0002, 0x0003, 0x0001, 0x0002]]
        f.height = 1
        return N, f

    def test_seams_list_joins_the_original_never_draws(self):
        N, f = self.fake()
        f.rows = [[0x0001, 0x0002, 0x0003] + [0x0003] * 31]
        self.assertEqual(N.seams(f, [[0x0001, 0x0002, 0x0003]]), [(0, 2)])
        self.assertEqual(N.seams(f, [[0x0001, 0x0002]]), [(0, 1)])

    def test_reindex_maps_colours_and_keeps_transparency(self):
        N, f = self.fake()
        cell = (1, ((0, 2),))
        self.assertEqual(N.reindex(f, cell, 1), ((0, 2),))
        palette = [0] + [0x112] + [0] * 14
        self.assertEqual(N.reindex(f, cell, 3, palette), ((0, 1),))
        with self.assertRaisesRegex(N.NativeError, 'not in palette'):
            N.reindex(f, (0, ((5,),)), 3, palette)


class NativeBackdropTests(unittest.TestCase):
    def test_round_offsets_match_measured_first_frames(self):
        from native_backdrops import opening
        # Values measured against the original's first frames for 1.02-dev loops.
        self.assertEqual(opening(45, [512, 0, 512, 0, 256, 0, 0, 0]), [14, 0, 14, 0, 30, 0, 0, 0])
        self.assertEqual(opening(45, [2048]), [8])
        self.assertEqual(opening(30, [0, 0, 1792, 0])[2] % 5, 29 % 5)

    def test_map_rows_repeat_the_loop(self):
        from native_backdrops import map_bytes, loop_include
        self.assertEqual(map_bytes([[0, 1, 2]], lambda i: 0x80 + i), bytes(0x80 + e % 3 for e in range(64)))
        self.assertIn('MAP_WRAP = 14', loop_include(50))

    def test_seek_code_targets_the_vram_word(self):
        from native_backdrops import seek_code
        self.assertEqual(seek_code(0x0812), bytes([0x64, 0x11, 0x03, 0, 0x13, 0x12, 0x23, 0x08,
                                                    0xa9, 2, 0x85, 0x11, 0x03, 2]))


class Rev5GeneratorTests(unittest.TestCase):
    def test_code_overflow_spills_into_extra_regions(self):
        import rev5_texture as gen
        gen.PROFILES['synthetic'] = {'prefix': 'ps', 'bank': 0x10, 'rows': 2, 'bins': 1,
                                     'loops': [], 'spill': lambda index: None,
                                     'extras': [(0x30, 0x7000, 0x1000), (0x31, 0x6800, 0x1800)]}
        try:
            tile = lambda seed: tuple(tuple((seed * 7 + x * 3 + y * 5 + x * y) % 16 for x in range(8))
                                      for y in range(8))
            texture = [[tile(r * 64 + n) for n in range(45)] for r in range(2)]
            out = gen.generate('synthetic', texture, [0, 1])
            self.assertTrue(any(out['extras']))
            regions = {0x11: (0x6000, out['bins'][0])}
            for (bank, address, _), data in zip(gen.PROFILES['synthetic']['extras'], out['extras']):
                regions[bank] = (address, data)
            for phase in (0, 3):
                vram = {}
                for r in range(2):
                    bank, address = out['locations'][phase, r]
                    start, data = regions[bank]
                    image = b'\xff' * (start - 0x6000) + data + b'\x60'
                    gen.run_code(image, address, vram)
                for r, row in enumerate(texture):
                    for n in range(len(row)):
                        slot = out['map'][r * 128 + n] | out['map'][r * 128 + 64 + n] << 8 & 0xf00
                        got = gen.decode_words([vram[(slot & 0xfff) * 16 + k] for k in range(16)])
                        pair = [a + b for a, b in zip(row[n], row[(n + 1) % len(row)])]
                        self.assertEqual(got, tuple(tuple(p[phase:phase + 8]) for p in pair))
        finally:
            del gen.PROFILES['synthetic']


class CastleHorizonTests(unittest.TestCase):
    def synthetic(self):
        import castle_horizon as ch
        words = [[0x0202] * 34 for _ in range(23)]
        for (r, c), w in {(0, 3): 0x112f, (2, 7): 0x1198, (3, 7): 0x1199, (14, 5): 0x11a4,
                          (15, 5): 0x11a5, (2, 20): 0x11a4, (3, 20): 0x11a5}.items():
            words[r][c] = w
        mapdata = bytearray(23 * 64)
        slots = {}
        for r in range(14):
            for c in range(64):
                pair = (words[r][c % 32], words[r][(c % 32 + 1) % 32])
                mapdata[r * 64 + c] = slots.setdefault(pair, 0x80 + len(slots))
        return ch, words, bytes(mapdata), slots

    def test_sky_rows_reuse_existing_pair_slots(self):
        ch, words, mapdata, slots = self.synthetic()
        out = ch.sky_rows(mapdata, words, lambda r, u: words[r][u % 33])
        for r in range(14):
            for u in range(64):
                self.assertEqual(out[r * 64 + u], slots[words[r][u % 33], words[r][(u + 1) % 33]])
        self.assertEqual(out[14 * 64:], mapdata[14 * 64:])

    def test_stationary_sky_shows_columns_0_to_33_then_plain_sky(self):
        ch, words, mapdata, slots = self.synthetic()
        out = ch.stationary_sky(mapdata, words)
        self.assertEqual(out[2 * 64 + 6], slots[0x0202, 0x1198])
        self.assertEqual(out[2 * 64 + 40], slots[0x0202, 0x0202])

    def test_sky_rows_reject_missing_pairs(self):
        ch, words, mapdata, _ = self.synthetic()
        words[5][32] = 0x1163
        with self.assertRaisesRegex(ValueError, 'No castle sky slot'):
            ch.sky_rows(mapdata, words, lambda r, u: words[r][u % 33])

    def test_castle_stars_point_at_sky_slots(self):
        import native_gfx as N
        ch, words, mapdata, slots = self.synthetic()
        horizon = {r: bytes([0x55]) * 64 for r in ch.ROWS}
        out = ch.castle_stars(horizon, mapdata, words)
        length = len(N.LOOPS[ch.PROFILE])
        for r, tile in ((14, 0x11a4), (15, 0x11a5)):
            self.assertEqual(out[r][4], slots[0x0202, tile])
            self.assertEqual(out[r][5], slots[tile, 0x0202])
            self.assertEqual(out[r][4 + length], slots[0x0202, tile])
        self.assertEqual(sum(a != b for r in ch.ROWS for a, b in zip(out[r], horizon[r])), 8)

    def test_slot_images_come_from_the_regenerated_atlas(self):
        import castle_horizon as ch
        pool = b''.join(bytes([k % 251]) * 32 for k in range(600))
        sky = {'pool': pool, 'fixed': [(0x7d, 3, 0x6000 + 5 * 32)], 'slots': {40: [257 + p for p in range(8)]}}
        images = ch.slot_images(sky)
        self.assertEqual(sorted(images), [3, 40])
        self.assertEqual(images[3], [bytes([5]) * 32] * 8)
        self.assertEqual(images[40], [bytes([(257 + p) % 251]) * 32 for p in range(8)])

    def test_castle_tables_must_match_the_regenerated_atlas(self):
        import castle_horizon as ch
        import native_gfx as N
        out = {'pairs': 2, 'high': [0, 16], 'fixed': [(0x7d, 0, 0x6000)],
               'lists': {p: [(0x7d, 0x10, 0x08, 0x20 * p, 0x60, 1)] for p in range(8)},
               'tables': [[1, 2, 3]], 'star_dest': [1], 'star_group': [2], 'variant2': [0, 1], 'variant3': [1, 0]}

        def render(out):
            inc = ' lda #$7d\n tam #3\n lda #0\n jsr seek_tile\n tia $6000,$0002,32\n'
            for p in range(8):
                inc += f'upload_{p}_0:\n .db 1\n .db {",".join(map(str, out["lists"][p][0]))}\n'
            inc += 'tile_high:\n .db ' + ','.join(map(str, out['high'] + [0] * 126)) + '\n'
            inc += 'star_type0:\n .dw ' + ','.join(map(str, out['tables'][0])) + '\n'
            for name in ('star_dest', 'star_group', 'variant2', 'variant3'):
                inc += f'{name}:\n .db ' + ','.join(map(str, out[name])) + '\n'
            return inc
        ch.check_tables(render(out), out)
        changed = dict(out, tables=[[1, 2, 4]])
        with self.assertRaisesRegex(N.NativeError, 'star_type0 does not match'):
            ch.check_tables(render(changed), out)


class TileTests(unittest.TestCase):
    def test_independent_bitplane_positions(self):
        tile = bytearray(32)
        tile[0] = 0x80
        tile[1] = 0x40
        tile[16] = 0x20
        tile[17] = 0x10
        rows = decode_tile(tile)
        self.assertEqual(rows[0], [1, 2, 4, 8, 0, 0, 0, 0])
        self.assertEqual(rows[1:], [[0] * 8 for _ in range(7)])
        self.assertEqual(encode_tile(rows), bytes(tile))

    def test_phase_crosses_tile_boundary_and_preserves_zero(self):
        left = encode_tile([list(range(8))] * 8)
        right = encode_tile([list(range(8, 16))] * 8)
        for phase, tile in enumerate(horizontal_phases(left, right)):
            self.assertEqual(decode_tile(tile), [list(range(phase, phase + 8))] * 8)

    def test_invalid_tiles(self):
        with self.assertRaises(ValueError): decode_tile(b'\0' * 31)
        with self.assertRaises(ValueError): encode_tile([[16] * 8] * 8)


class ReleaseTests(unittest.TestCase):
    def test_release_patch_and_nonoverlapping_runtime_ranges(self):
        manifest = load_manifest()
        version = (ROOT / 'VERSION').read_text().strip()
        if version != manifest['version']:
            # A development build, or a release candidate before its manifest.
            self.assertRegex(version, r'^\d+\.\d{2}(-dev)?$')
            self.assertGreater(tuple(map(int, version.removesuffix('-dev').split('.'))),
                               tuple(map(int, manifest['version'].split('.'))))
        # Both release patches: the headered and the headerless original.
        for spec in (manifest, manifest['headerless']):
            patch = (ROOT / spec['patch']['path']).read_bytes()
            self.assertEqual(hashlib.sha256(patch).hexdigest(), spec['patch']['sha256'])
            source_crc, target_crc, _ = struct.unpack('<III', patch[-12:])
            self.assertEqual(f'{source_crc:08X}', spec['source']['crc32'])
            self.assertEqual(f'{target_crc:08X}', manifest['target']['crc32'])
        self.assertEqual(sorted(p.name for p in (ROOT / 'patches').glob('*.bps')),
                         sorted(Path(s['patch']['path']).name for s in (manifest, manifest['headerless'])))
        occupied = set()
        for module in json.loads((ROOT / 'src/modules.json').read_text()):
            self.assertTrue((ROOT / module['source']).is_file())
            self.assertNotIn('assets', module)
            for lo, hi in module['ranges']:
                self.assertTrue(0 <= lo < hi <= ROM_SIZE)
                region = set(range(lo, hi))
                self.assertFalse(occupied & region)
                occupied.update(region)

    def test_source_builds_start_from_the_original_game(self):
        source = b'\x00' * 512 + bytes(range(256)) * 2048
        spec = {'size': len(source), 'sha256': hashlib.sha256(source).hexdigest()}
        headerless = source[512:]
        manifest = {'source': dict(spec, header_bytes=512), 'patch': {},
                    'headerless': {'source': {'size': len(headerless), 'header_bytes': 0,
                                              'sha256': hashlib.sha256(headerless).hexdigest()}, 'patch': {}}}
        for rom in (source, headerless):            # either original format gives the same image
            image = original_image(rom, manifest)
            self.assertEqual(len(image), ROM_SIZE)
            self.assertEqual(image[:len(headerless)], headerless)
            self.assertEqual(set(image[len(headerless):]), {0xff})
        with self.assertRaisesRegex(ValueError, 'Original ROM'):
            original_image(source[:-1], manifest)

    def test_notice_font_is_editable_source(self):
        import tempfile
        from notice_assets import GLYPHS, generate
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            (work / 'screen.json').write_text(json.dumps([[4, 'V{version}', 0]]))
            generate(work, '1.05-dev')
            font = (work / 'font.bin').read_bytes()
        characters = ' -.015DEV'
        self.assertEqual(len(font), 32 * len(characters))
        tile = font[characters.index('V') * 32:][:32]
        self.assertEqual(list(tile[:16:2]), GLYPHS['V'])
        self.assertEqual(set(tile[1:16:2] + tile[16:]), {0})


class ComparisonRunTests(unittest.TestCase):
    def test_every_parallax_stage_has_a_wellformed_run(self):
        from comparison_video import BUTTONS, STAGE_NAMES
        runs = {path.stem: json.loads(path.read_text())
                for path in (ROOT / 'research/comparison-runs').glob('*.json')}
        self.assertEqual(sorted(runs), ['1-1', '2-2', '3-1', '3-2', '4-1', '4-2',
                                        '5-2', '5-3', '5-4', '6-1', '6-3'])
        for name, run in runs.items():
            self.assertEqual(STAGE_NAMES[run['stage']], name)
            self.assertEqual(run['frames'], sum(count for count, _ in run['segments']))
            for count, buttons in run['segments']:
                self.assertGreater(count, 0)
                self.assertLessEqual(set(buttons), set(BUTTONS))


class GuideImageTests(unittest.TestCase):
    def test_options_guide_uses_exactly_the_allowed_screenshots(self):
        import re
        from audit_public import GUIDE_IMAGES
        guide = (ROOT / 'docs/OPTIONS.md').read_text()
        used = {'docs/' + path for path in re.findall(r'!\[[^\]]*\]\(([^)]+)\)', guide)}
        self.assertEqual(used, GUIDE_IMAGES)


if __name__ == '__main__':
    unittest.main()
