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
                for step in module['prepare'].split('+'):
                    self.assertIn(step, PREPARE)


class PaletteTableTests(unittest.TestCase):
    def test_gb_dmg_table_follows_the_editable_parameters(self):
        from palette_tables import gb_dmg_table
        table = gb_dmg_table()
        self.assertEqual(len(table), 512)
        self.assertEqual(set(table), {0x040, 0x090, 0x0d0, 0x120})
        # GGGRRRBBB: black, white, pure blue / red / green at full, and the
        # darkest shade itself (Y = 0.587 < 0.6).
        for colour, shade in ((0x000, 0x040), (0x1ff, 0x120), (0x007, 0x090), (0x038, 0x0d0),
                              (0x1c0, 0x120), (0x040, 0x040), (0x092, 0x0d0), (0x124, 0x120)):
            self.assertEqual(table[colour], shade, hex(colour))

    def test_thresholds_are_exact_and_editable(self):
        import tempfile
        from palette_tables import gb_dmg_table, generate, pages
        with tempfile.TemporaryDirectory() as temp:
            spec = Path(temp) / 'gb.json'
            # A colour exactly on a threshold takes the lighter shade: G = 1
            # gives Y = 0.587 exactly.
            spec.write_text(json.dumps({'luma': ['0.299', '0.587', '0.114'],
                                        'thresholds': ['0.587', '1.8', '3.2'],
                                        'shades': ['000', '001', '002', '1FF']}))
            table = gb_dmg_table(spec)
            self.assertEqual(table[0x040], 0x001)
            self.assertEqual(table[0x000], 0x000)
            generate(temp, spec)
            include = (Path(temp) / 'gb-table.inc').read_text()
            spec.write_text(json.dumps({'luma': ['0.299', '0.587', '0.114'],
                                        'thresholds': ['3.2', '1.8', '0.6'],
                                        'shades': ['040', '090', '0D0', '120']}))
            with self.assertRaisesRegex(ValueError, 'increase'):
                gb_dmg_table(spec)
        values = [int(b[1:], 16) for line in include.splitlines() if line.startswith(' .db ')
                  for b in line[5:].split(',')]
        self.assertEqual(bytes(values), b''.join(pages(table)))
        self.assertEqual(values[0x40], 0x01)                      # gb_lo0[$40]
        self.assertEqual(values[3 * 256 + 0xff], 0x01)            # gb_hi1[$FF]: colour $1FF

    # hell.json before the dark-lift pass (candidate D): these ramps, no leaf family.
    HELL_D = {'green_ramp': [[0.0, 0, 0, 0], [0.3, 1, 1, 0], [0.6, 3, 2, 0], [1.0, 5, 3, 0]],
              'grey_ramp': [[0, 0, 0, 0], [0.14, 1, 0, 0], [0.29, 1, 0, 0], [0.43, 3, 2, 0], [0.57, 5, 2, 1],
                            [0.71, 4, 1, 0], [0.8, 4, 1, 0]],
              'steel_ramp': [[0, 0, 0, 0], [0.14, 1, 0, 0], [0.22, 2, 1, 0], [0.3, 2, 1, 0], [0.34, 3, 2, 0],
                             [0.44, 3, 2, 0], [0.48, 4, 2, 0], [0.52, 4, 2, 0], [0.54, 4, 3, 0], [0.62, 4, 3, 0],
                             [0.81, 7, 6, 2], [1.0, 7, 7, 3]]}

    def test_hell_table_is_the_owners_choice(self):
        from palette_tables import hell_table, load_hell
        table = hell_table()
        self.assertEqual(len(table), 512)
        self.assertTrue(all(0 <= c <= 0x1ff for c in table))
        # The 512 colours of the retuned candidate D (the mock-up 'Lava',
        # candidate C, with the 'steel' family: cool greys and dull teals take
        # 2-2's column golds; the owner's choice for 1-1 "more like 2-2") with
        # the dark lift "Hb" (floor plus leaf family; the dark-lift study's
        # gen/hell-Hb-floor-leaf.json) as little-endian words.
        self.assertEqual(hashlib.sha256(b''.join(c.to_bytes(2, 'little') for c in table)).hexdigest(),
                         '7be5da494c0f33287da585b598f64571cab956623eb1143cd361bbd8663c272b')
        # GGGRRRBBB: black stays black; white is pale ash; blues become lava,
        # greys gold-brown, reds stay red; 1-1's wall and sidewalk greys take
        # 2-2's golds ($0DB -> 320, $0DC -> 420 as R G B); $094 stays crimson
        # in the table (2-2's far ridge; 1-1 overrides it in the upload);
        # pure green is the leaf ramp's 641.
        for colour, hell in ((0x000, 0x000), (0x1ff, 0x1ba), (0x007, 0x078), (0x038, 0x030),
                             (0x1c0, 0x131), (0x092, 0x008), (0x124, 0x0a9), (0x0b6, 0x0b0),
                             (0x03f, 0x0b0), (0x1f8, 0x0e8), (0x0db, 0x098), (0x0dc, 0x0a0),
                             (0x094, 0x031)):
            self.assertEqual(table[colour], hell, hex(colour))
        self.assertEqual(load_hell()['mapped_entries'], 240)    # background palettes 0-14

    def test_hell_dark_lift_changes_21_colours_and_none_goes_black(self):
        # The dark lift: no colour but black becomes black (candidate D sent
        # the darkest green $040 there), the darkest grey is a brown, and the
        # saturated pure greens ('leaf': 4-1's trunks and canopy, 5-1's and
        # 6-2's greens) have a ramp of their own. Exactly 21 colours differ
        # from candidate D; the 1-1 override and the 240 mapped entries stay.
        import tempfile
        from palette_tables import HELL_PARAMETERS, channels, hell_overrides, hell_table, load_hell
        table = hell_table()
        self.assertEqual([c for c in range(1, 512) if table[c] == 0], [])
        self.assertEqual(table[0], 0)
        spec = json.loads(HELL_PARAMETERS.read_text())
        self.assertEqual(spec['leaf_windows'], [[100, 140, 0.9]])
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'hell.json'
            before = {k: v for k, v in dict(spec, **self.HELL_D).items() if not k.startswith('leaf_')}
            path.write_text(json.dumps(before))
            d = hell_table(path)
            self.assertEqual(hashlib.sha256(b''.join(c.to_bytes(2, 'little') for c in d)).hexdigest(),
                             '1435b5a189bdbbeb6964c1a8df4981883fe309b7a819506397d080766944d641')
            self.assertEqual([c for c in range(1, 512) if d[c] == 0], [0x040])
            self.assertEqual(hell_overrides(path), hell_overrides())
            self.assertEqual(load_hell(path)['mapped_entries'], load_hell()['mapped_entries'])
            rgb = lambda word: '%d%d%d' % channels(word)
            self.assertEqual({f'{c:03X}': f'{rgb(d[c])}>{rgb(table[c])}' for c in range(512) if d[c] != table[c]},
                             {'040': '000>110', '041': '100>210', '049': '100>310', '080': '110>310',
                              '0C0': '110>320', '0C1': '110>320', '100': '210>420', '101': '220>420',
                              '108': '220>420', '140': '320>430', '141': '320>430', '148': '320>430',
                              '180': '320>530', '181': '320>530', '182': '320>530', '188': '420>530',
                              '1C0': '420>641', '1C1': '420>641', '1C2': '430>641', '1C8': '430>641',
                              '1D0': '430>641'})
            # The leaf family is optional and needs its windows and mix; a
            # window over every hue takes every coloured colour steel leaves.
            plain = {k: v for k, v in spec.items() if not k.startswith('leaf_')}
            path.write_text(json.dumps(plain))
            no_leaf = hell_table(path)
            self.assertNotEqual(no_leaf[0x1c0], table[0x1c0])        # pure green: leaf only with the keys
            self.assertEqual(no_leaf[0x049], table[0x049])           # a grey: never leaf
            leaf = dict(spec, leaf_ramp=[[0.0, 0, 0, 1], [1.0, 0, 0, 7]], leaf_windows=[[0, 360, 0.0]],
                        leaf_mix=[1.0, 0.0])
            path.write_text(json.dumps(leaf))
            wide = hell_table(path)
            self.assertEqual(wide[0x038], 0x007)                     # pure red: the leaf ramp's top
            self.assertEqual(wide[0x1ff], table[0x1ff])              # white is ash: unchanged
            self.assertEqual(wide[0x0dc], table[0x0dc])              # steel comes first
            for key in ('leaf_windows', 'leaf_mix'):
                broken = dict(leaf)
                del broken[key]
                path.write_text(json.dumps(broken))
                with self.assertRaises(ValueError):
                    hell_table(path)

    def test_sms_table_is_the_owners_mockup(self):
        import tempfile
        from palette_tables import SMS_PARAMETERS, load_sms, sms_colours, sms_table
        table = sms_table()
        self.assertEqual(len(table), 512)
        # The 512 colours of candidate A (build/sms-mockup/table-A.json,
        # `by_colour`, the owner's choice) with the dark lift "Sa" (the
        # dark-lift study's gen/sms-Sa-rescue.json) as little-endian words.
        self.assertEqual(hashlib.sha256(b''.join(c.to_bytes(2, 'little') for c in table)).hexdigest(),
                         '9323ab4aef90dac5ea3b2d82fb1505a8d8780190bf89acbeca15e109f1acb314')
        # Channel by channel, independently of the parameters: PC Engine
        # 0,1 -> 0; 2,3 -> 2; 4,5 -> 5; 6,7 -> 7 (GGGRRRBBB), except the four
        # rescued dark colours (green 1; luma at least 0.5 of 7), whose
        # channels at 1 take 2 instead of vanishing into black.
        rescued = {0x040: 0x080, 0x041: 0x082, 0x048: 0x090, 0x049: 0x092}
        q = [0, 0, 2, 2, 5, 5, 7, 7]
        for colour in range(512):
            g, r, b = colour >> 6, (colour >> 3) & 7, colour & 7
            self.assertEqual(table[colour], rescued.get(colour, q[g] << 6 | q[r] << 3 | q[b]), hex(colour))
        # Only black and the three darkest blue/red/purple colours are black.
        self.assertEqual([c for c in range(512) if table[c] == 0], [0x000, 0x001, 0x008, 0x009])
        # Every output is one of the 64 SMS colours, all 64 occur, and an SMS
        # colour maps to itself.
        sms64 = {g << 6 | r << 3 | b for g in (0, 2, 5, 7) for r in (0, 2, 5, 7) for b in (0, 2, 5, 7)}
        self.assertEqual(sms_colours(), sms64)
        self.assertEqual(set(table), sms64)
        self.assertTrue(all(table[c] == c for c in sms64))
        self.assertEqual(load_sms()[1], [0, 2, 5, 7])
        # Without dark_rescue the table is candidate A exactly.
        spec = json.loads(SMS_PARAMETERS.read_text())
        self.assertEqual(spec['dark_rescue'], {'min_luma': '0.5'})
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'sms.json'
            path.write_text(json.dumps({k: v for k, v in spec.items() if k != 'dark_rescue'}))
            plain = sms_table(path)
            self.assertEqual(hashlib.sha256(b''.join(c.to_bytes(2, 'little') for c in plain)).hexdigest(),
                             'bb0779db843cfb9ee7094e11f7cf95dad5fdc8038092048ee281a0080ae8d927')
            self.assertEqual({c: table[c] for c in range(512) if table[c] != plain[c]}, rescued)

    def test_sms_dark_keys_stay_within_the_64_colours(self):
        import tempfile
        from palette_tables import SMS_PARAMETERS, sms_colours, sms_table
        spec = json.loads(SMS_PARAMETERS.read_text())
        base = {k: v for k, v in spec.items() if k != 'dark_rescue'}
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'sms.json'
            # The luma threshold is exact: $040 has luma 0.587 precisely.
            for luma, word in (('0.587', 0x080), ('0.5871', 0x000)):
                path.write_text(json.dumps(dict(base, dark_rescue={'min_luma': luma})))
                self.assertEqual(sms_table(path)[0x040], word, luma)
            # true: every colour that would vanish is rescued; only black is black.
            path.write_text(json.dumps(dict(base, dark_rescue=True)))
            table = sms_table(path)
            self.assertEqual([c for c in range(512) if table[c] == 0], [0])
            self.assertEqual((table[0x001], table[0x008], table[0x009]), (0x002, 0x010, 0x012))
            self.assertTrue(set(table) <= sms_colours(path))
            # dark_map: single colours, applied last, SMS colours only.
            path.write_text(json.dumps(dict(spec, dark_map={'$001': '$002', '$040': '$090'})))
            table = sms_table(path)
            self.assertEqual((table[0x001], table[0x040], table[0x041]), (0x002, 0x090, 0x082))
            self.assertTrue(set(table) <= sms_colours(path))
            path.write_text(json.dumps(dict(spec, dark_map={'$001': '$001'})))
            with self.assertRaisesRegex(ValueError, 'not an SMS colour'):
                sms_table(path)

    def test_sms_parameters_are_editable(self):
        import tempfile
        from palette_tables import generate, pages, sms_table
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'sms.json'
            path.write_text(json.dumps({'sms_levels': [0, 1, 254, 255], 'pce_levels': [0, 1, 6, 7]}))
            table = sms_table(path)
            self.assertEqual(table[0x1ff], 0x1ff)
            self.assertEqual(table[0x049], 0x049)                   # 1 (36.4) -> level 1, shown as 1
            self.assertEqual(table[0x124], 0x1b6)                   # 4 (145.7) -> level 254, shown as 6
            generate(temp, sms_path=path)
            include = (Path(temp) / 'sms-table.inc').read_text()
            values = [int(b[1:], 16) for line in include.splitlines() if line.startswith(' .db ')
                      for b in line[5:].split(',')]
            self.assertEqual(bytes(values), b''.join(pages(table)))
            self.assertEqual(include.splitlines()[1], 'sms_lo0:')
            for broken in ({'sms_levels': [0, 85, 170], 'pce_levels': [0, 2, 5]},
                           {'sms_levels': [0, 170, 85, 255], 'pce_levels': [0, 2, 5, 7]},
                           {'sms_levels': [0, 85, 170, 255], 'pce_levels': [0, 2, 5, 8]}):
                path.write_text(json.dumps(broken))
                with self.assertRaises(ValueError):
                    sms_table(path)

    def test_sms_mirror_copies_the_marked_code(self):
        from palette_tables import mirror
        source = (ROOT / 'src/palette/main.asm').read_text()
        text, labels = mirror(source)
        # Every label of the bank $46 code and the family-11 dispatch, renamed
        # and guarded; nothing outside the marked lines.
        for label in ('palette_entry', 'vblank_gb', 'now_gb', 'mapped_upload', 'upload_chunk',
                      'fold_queue', 'vblank_sms', 'now_sms', 'now_hell_cinema_exit'):
            self.assertIn(label, labels)
            self.assertIn(f'\nsms_{label}:\n', text)
            self.assertIn(f' .if (sms_{label} <> {label})\n .fail\n .endif', text)
        self.assertNotIn('hell_gameplay', labels)
        self.assertIn(' jmp hell_gameplay\n', text)                # labels defined elsewhere keep their names
        self.assertIn(' jmp sms_mapped_upload\n', text)
        self.assertNotIn(';', text.split('\n', 1)[1])               # comments dropped
        self.assertEqual(text.count(' .org '), 2)
        for broken in (source.replace(';@mirror end', '', 1),
                       source.replace(';@mirror begin', '', 1),
                       source.replace(';@mirror begin\n .org PALETTE_FAR', ';@mirror begin\n .bank 3\n .org PALETTE_FAR'),
                       source.replace('now_sms:\n', 'now_sms:\nvblank_sms:\n')):
            with self.assertRaises(ValueError):
                mirror(broken)

    def test_hell_stage_override_is_1_1_only(self):
        # 1-1 shows $094 (its sidewalk fleck and skyline shadow faces) as 210,
        # 2-2's dark column gold, where the table keeps crimson 601 for 2-2's
        # far ridge; every other stage sees the table; the upload gets the
        # override as four equates in hell-table.inc.
        import tempfile
        from palette_tables import (HELL_PARAMETERS, generate, hell_override_equates, hell_overrides,
                                    hell_stage_table, hell_table)
        table = hell_table()
        self.assertEqual(hell_overrides(), [(0, 0x094, 0x050)])
        one_one = hell_stage_table(0)
        self.assertEqual(one_one[0x094], 0x050)                   # R2 G1 B0
        self.assertEqual(table[0x094], 0x031)                     # R6 G0 B1, as 2-2 shows it
        self.assertEqual([c for c in range(512) if one_one[c] != table[c]], [0x094])
        for stage in range(1, 22):
            self.assertEqual(hell_stage_table(stage), table)
        self.assertEqual(hell_override_equates().split('\n'),
                         ['HELL_OVERRIDE_STAGE = $00', 'HELL_OVERRIDE_KEY = $94',
                          'HELL_OVERRIDE_LO = $50', 'HELL_OVERRIDE_HI = $00'])
        spec = json.loads(HELL_PARAMETERS.read_text())
        with tempfile.TemporaryDirectory() as temp:
            generate(temp)
            self.assertIn('HELL_OVERRIDE_KEY = $94', (Path(temp) / 'hell-table.inc').read_text())
            path = Path(temp) / 'hell.json'
            plain = {k: v for k, v in spec.items() if k != 'stage_overrides'}
            path.write_text(json.dumps(plain))
            self.assertEqual(hell_overrides(path), [])
            self.assertEqual(hell_stage_table(0, path), table)
            self.assertIn('HELL_OVERRIDE_STAGE = $ff', hell_override_equates(path))   # never visible
            for bad in ({'1-1': {'$194': [2, 1, 0]}},                 # high half: not compared
                        {'1-1': {'$000': [2, 1, 0]}},
                        {'1-1': {'$094': [2, 1, 8]}},
                        {'1-1': {'$094': [2, 1, 0], '$095': [2, 1, 0]}},   # one compare
                        {'1-1': {'$094': [2, 1, 0]}, '2-2': {'$094': [2, 1, 0]}},
                        {'7-1': {'$094': [2, 1, 0]}}):
                path.write_text(json.dumps(dict(plain, stage_overrides=bad)))
                with self.assertRaises(ValueError, msg=str(bad)):
                    hell_overrides(path)

    def test_hell_parameters_are_editable(self):
        import tempfile
        from palette_tables import HELL_PARAMETERS, generate, hell_table, pages
        spec = json.loads(HELL_PARAMETERS.read_text())
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'hell.json'
            spec['ash_ramp'] = [[0.0, 0, 0, 1], [1.0, 0, 0, 7]]      # white ash becomes blue
            path.write_text(json.dumps(spec))
            table = hell_table(path)
            self.assertEqual(table[0x1ff], 0x007)
            generate(temp, hell_path=path)
            include = (Path(temp) / 'hell-table.inc').read_text()
            self.assertIn('\nHELL_MAPPED = 240\n', include)
            values = [int(b[1:], 16) for line in include.splitlines() if line.startswith(' .db ')
                      for b in line[5:].split(',')]
            self.assertEqual(bytes(values), b''.join(pages(table)))
            for broken in ({'mapped_entries': 250}, {'mapped_entries': 272},
                           {'lava_ramp': [[0.5, 0, 0, 0], [0.2, 7, 0, 0]]}, {'grey_ramp': [[0.0, 8, 0, 0], [1.0, 0, 0, 0]]}):
                path.write_text(json.dumps(dict(spec, **broken)))
                with self.assertRaises(ValueError):
                    hell_table(path)

    def test_hell_steel_family_is_optional(self):
        # The retuned HELL table uses the optional "steel" family (steel_ramp,
        # steel_windows, steel_mix); without those keys no colour takes it,
        # and steel_ramp needs the other two.
        import tempfile
        from palette_tables import HELL_PARAMETERS, hell_table
        spec = json.loads(HELL_PARAMETERS.read_text())
        self.assertIn('steel_ramp', spec)
        shipped = hell_table()
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'hell.json'
            plain = {k: v for k, v in spec.items() if not k.startswith('steel_')}
            path.write_text(json.dumps(plain))
            table = hell_table(path)
            self.assertNotEqual(table, shipped)
            self.assertEqual(table[0x0db], shipped[0x0db])           # grey (R3 G3 B3): never steel
            self.assertNotEqual(table[0x0dc], shipped[0x0dc])        # a cool grey-blue: steel only with the keys
            # One window over every hue (degrees), saturation, chroma and value:
            # every coloured (non-grey) colour goes to the steel ramp by value.
            steel = dict(spec, steel_ramp=[[0.0, 0, 0, 1], [1.0, 3, 3, 7]], steel_windows=[[0, 360, 1.0, 1.0, 1.0]],
                         steel_mix=[1.0, 0.0])
            path.write_text(json.dumps(steel))
            table = hell_table(path)
            self.assertEqual(table[0x007], 0x0df)                    # pure blue: the ramp's top (G3 R3 B7)
            self.assertEqual(table[0x1ff], shipped[0x1ff])           # white is grey: unchanged
            for key in ('steel_windows', 'steel_mix'):
                broken = dict(steel)
                del broken[key]
                path.write_text(json.dumps(broken))
                with self.assertRaises(ValueError):
                    hell_table(path)


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


class NesPaletteTests(unittest.TestCase):
    """src/nes-palette: role data -> packed tables (scripts/nes_palette.py)."""

    @staticmethod
    def labelled_bytes(text):
        """{label: [byte or expression, ...]} from the generated .db lines."""
        out, label = {}, None
        for line in text.splitlines():
            line = line.split(';')[0].rstrip()
            if line.endswith(':'):
                label = line[:-1]
                out[label] = []
            elif line.startswith(' .db '):
                out[label] += [int(v[1:], 16) if v.startswith('$') else (int(v) if v.isdigit() else v)
                               for v in line[5:].split(',')]
            elif line.startswith(' .dw '):
                for v in line[5:].split(','):
                    w = int(v[1:], 16)
                    out[label] += [w & 0xff, w >> 8]
        return out

    def test_stored_results_are_what_the_roles_give(self):
        import nes_palette as NP
        self.assertEqual(NP.check(NP.load()), [])

    def test_packed_tables_decode_back_to_the_role_data(self):
        import nes_palette as NP
        data = NP.load()
        inc = NP.includes(data)
        t, s = self.labelled_bytes(inc['nes-tables.inc']), self.labelled_bytes(inc['nes-sets.inc'])
        s37 = self.labelled_bytes(inc['nes-sprites-37.inc'])
        s45 = self.labelled_bytes(inc['nes-sprites-45.inc'])
        files = {d['set']: d for d in data['stages'] if not d.get('variant_of')}
        self.assertEqual(len(files), 18)
        for n in range(NP.SETS):
            if n in files:
                want = [int(e['out'], 16) for e in files[n]['entries']]
                self.assertEqual(NP.unpack(bytes(s[f'nes_set_{n}']), len(want)), want)
                self.assertEqual(t['nes_set_hi'][n], f'HIGH(nes_set_{n}+$2000)+$80')   # bank $45
            else:
                # Title and cinema sets (0, 19-21): no NES copy, the original is used.
                self.assertIn(n, (0, 19, 20, 21))
                self.assertEqual((t['nes_set_lo'][n], t['nes_set_hi'][n]), (0, 0))
        variant = next(d for d in data['stages'] if d.get('variant_of'))
        self.assertEqual((variant['stage'], variant['set'], variant['level_select']), ('3-2', 6, [6]))
        self.assertEqual(t['nes_variant_set'], [6 if st == 6 else 0xff for st in range(22)])
        self.assertEqual(NP.unpack(bytes(t['nes_variant_6']), 192), [int(e['out'], 16) for e in variant['entries']])
        ryu = data['shared']['sprites'][0]
        self.assertEqual(ryu['palette'], 96)
        # Sprite palettes: a table by palette number from NES_SPRITE_FIRST;
        # each copy in bank $37's tail (read in place) or bank $45 (+$80).
        first = int(next(l for l in inc['nes-tables.inc'].splitlines() if l.startswith('NES_SPRITE_FIRST')).split('=')[1])
        records = {sp['palette']: sp for sp, _, _ in NP.sprite_records(data)}
        for k, (lo, hi) in enumerate(zip(t['nes_sprite_lo'], t['nes_sprite_hi'])):
            n = first + k
            if n not in records:
                self.assertEqual((lo, hi), (0, 0))
                continue
            label = f'nes_sprite_{n}'
            raw = s37.get(label) or s45.get(label)
            self.assertEqual(NP.unpack(bytes(raw), 16), [int(e['out'], 16) for e in records[n]['entries']])
            self.assertEqual(hi, f'HIGH({label})' if label in s37 else f'HIGH({label}+$2000)+$80')
        self.assertIn('nes_sprite_96', s37)
        hud = t['nes_hud_colours']
        self.assertEqual([hud[2 * k] | hud[2 * k + 1] << 8 for k in range(7)],
                         [int(e['out'], 16) for e in data['shared']['hud']['entries']])
        # The NES copies fit the module's ranges (bank $37 $7C30-$7FDF; bank
        # $45 $5200-$5FFF for sets and the other sprite palettes).
        self.assertLessEqual(sum(len(v) for v in s37.values()), 0x7fe0 - 0x7c30)
        self.assertLessEqual(sum(len(v) for v in s.values()) + sum(len(v) for v in s45.values()), 0x6000 - 0x5200)

    def test_every_nes_mode_colour_is_an_nes_colour(self):
        import nes_palette as NP
        self.assertEqual(len(NP.NES_COLOURS), 47)
        data = NP.load()
        lay = NP.layout(data)
        self.assertEqual(NP.nes_problems(lay), [])
        for cols in list(lay['sets'].values()) + [c for _, c in lay['variants'].values()] + \
                [c for _, c in lay['sprites']] + [lay['hud']] + [c for v in lay['animations'].values() for _, c in v]:
            self.assertTrue(set(cols) <= NP.NES_COLOURS)
        # A colour outside the set fails the check and the build's table check.
        d = data['stages'][0]
        d['entries'][5]['override'] = None
        lay['sets'][d['set']][5] = 0x123
        self.assertTrue(NP.nes_problems(lay))
        rec = {'pce': '123', 'role': 'unused', 'nes': '00', 'out': '123', 'entry': 1}
        self.assertTrue(any('not an NES colour' in p for p in NP._check_results('x', [rec], {})))

    def test_nes_b_is_a_relit_variant_of_the_same_roles(self):
        import nes_palette as NP
        data = NP.load()
        a, b = NP.layout(data), NP.layout(NP.relit(data))
        # NES colours only, the same sets and variant; sprites and HUD shared.
        self.assertEqual(NP.nes_problems(b), [])
        self.assertEqual((set(b['sets']), set(b['variants'])), (set(a['sets']), set(a['variants'])))
        self.assertEqual((b['sprites'], b['hud']), (a['sprites'], a['hud']))
        self.assertEqual({s: len(c) for s, c in b['sets'].items()}, {s: len(c) for s, c in a['sets'].items()})
        self.assertTrue(all(b['sets'][s] != a['sets'][s] for s in a['sets']))
        # Re-lit: lighter on average in every set, never a near-black that NES-A lifted to colour.
        for s in a['sets']:
            mean = lambda cols: sum(NP.lightness(c) for c in cols) / len(cols)
            self.assertGreaterEqual(mean(b['sets'][s]), mean(a['sets'][s]), s)
        # The variant keys are optional and known to the checker; lift: false keeps NES-A.
        self.assertIn('lift', NP.ROLE_KEYS)
        self.assertIn('lift_black', NP.ROLE_KEYS)
        flat = NP.load()
        for d in flat['stages']:
            for r in d['roles'].values():
                r['lift'] = False
        off = NP.layout(NP.relit(flat))
        self.assertEqual(off['sets'], a['sets'])
        # The NES-B tables: every set and the 3-2 variant from NES_B_BANK's
        # window (no bank-$45 mark), packed as the loader reads them.
        inc = NP.includes_b(data, NP.relit(data), None)
        t, s = self.labelled_bytes(inc['nes-b-tables.inc']), self.labelled_bytes(inc['nes-b-sets.inc'])
        for n in range(NP.SETS):
            if n in b['sets']:
                self.assertEqual(t['nes_b_set_hi'][n], f'HIGH(nes_b_set_{n}+$2000)')
                self.assertEqual(NP.unpack(bytes(s[f'nes_b_set_{n}']), len(b['sets'][n])), b['sets'][n])
            else:
                self.assertEqual((t['nes_b_set_lo'][n], t['nes_b_set_hi'][n]), (0, 0))
        self.assertEqual(NP.unpack(bytes(s['nes_b_variant_6']), 192), b['variants'][6][1])
        self.assertEqual(t['nes_b_variant_hi'][6], 'HIGH(nes_b_variant_6+$2000)')
        # They fit bank $3B $4200-$4FFF.
        self.assertLessEqual(sum(len(v) for v in s.values()), 0x5000 - 0x4200)

    def test_4_1_back_trunks_resolve_above_the_darkest_green(self):
        # Dark lift "Na": in 4-1 (set 8) the bark entries of rows 0 and 3
        # (the Enhanced parallax trunks) take the `backwood` role, so they
        # resolve to lighter NES colours than the fill's 08 ($040) in NES-A
        # and NES-B; no other record of the set changes role.
        import nes_palette as NP
        data = NP.load()
        stage = next(d for d in data['stages'] if d['set'] == 8 and not d.get('variant_of'))
        self.assertEqual(stage['stage'], '4-1')
        role = stage['roles']['backwood']
        self.assertEqual((role['ramp'], role['strict'], role['exclude']), (['09', '18'], True, ['08']))
        back = [e for e in stage['entries'] if e['role'] == 'backwood']
        self.assertEqual([(e['row'], e['entry']) for e in back],
                         [(row, entry) for row in (0, 3) for entry in (6, 8, 9, 10, 11)])
        self.assertEqual([(e['pce'], e['nes'], e['out']) for e in back],
                         2 * [('041', '09', '080'), ('04A', '00', '092'), ('048', '09', '080'),
                              ('051', '17', '0A0'), ('049', '18', '090')])
        a, b = NP.layout(data), NP.layout(NP.relit(data))
        fill = NP.lightness(0x040)
        for lay, want in ((a, [0x080, 0x092, 0x080, 0x0a0, 0x090]), (b, [0x080, 0x092, 0x090, 0x0a0, 0x090])):
            for row in (0, 3):
                got = [lay['sets'][8][row * 16 + entry] for entry in (6, 8, 9, 10, 11)]
                self.assertEqual(got, want)
                self.assertTrue(all(c in NP.NES_COLOURS and NP.lightness(c) > fill for c in got))

    def test_detail_keeps_distinct_colours_distinct_in_lightness_order(self):
        import nes_palette as NP
        # Eight greys on a grey role: eight NES colours, in the same order.
        greys = [0x000, 0x049, 0x092, 0x0db, 0x124, 0x16d, 0x1b6, 0x1ff]
        r = NP.resolve_role({'ramp': ['00', '10', '30']}, greys)
        out = [NP.nes9(r[c]) for c in greys]
        self.assertEqual(len(set(out)), 8)
        ls = [NP.lightness(c) for c in out]
        self.assertEqual(ls, sorted(ls))
        # The role's hue anchors: shades of blue on a red role stay red-ish
        # (never a far hue column such as blue or green).
        blues = [0x001, 0x002, 0x003, 0x004, 0x005, 0x006, 0x007]
        red = NP.resolve_role({'ramp': ['16', '26']}, blues)
        self.assertTrue(all((n & 0x0F) in (0x05, 0x06, 0x07, 0x00, 0x0F) or NP.chroma(NP.nes9(n)) < NP.NEAR_GREY
                            for n in red.values()), red)
        # Merges only once the allowed colours run out, and the report names them.
        many = list(range(0x000, 0x008)) + [0x008 * k for k in range(1, 8)]
        r = NP.resolve_role({'ramp': ['0F'], 'mode': 'match', 'strict': True, 'detail': True}, many)
        self.assertEqual(len(set(r.values())), len(set(NP.nes9(n) for n in r.values())))
        # 'detail: false' keeps the old nearest-in-the-hue-columns choice.
        flat = NP.resolve_role({'ramp': ['00', '10', '30'], 'strict': True, 'detail': False}, greys)
        self.assertTrue(set(flat.values()) <= {0x00, 0x10, 0x30, 0x0F})
        rows = NP.detail_report(NP.load())
        self.assertTrue(all(n >= 1 for _, _, _, n in rows))

    def test_packing_puts_bit_eight_first(self):
        import nes_palette as NP
        cols = [0x1ff, 0, 0x100, 0x0ff, 0x123, 0x1a5, 0x005, 0x180]
        raw = NP.pack(cols)
        self.assertEqual(raw[0], 0b10101101)
        self.assertEqual(NP.unpack(raw, 8), cols)
        with self.assertRaises(NP.NesPaletteError):
            NP.pack(cols[:7])

    def test_roles_resolve_by_lightness_with_nes_hues(self):
        import nes_palette as NP
        self.assertEqual(NP.nes9(0x30), 0x1ff)           # NES white
        self.assertEqual(NP.nes9(0x0f), 0x000)           # NES black
        fixed = NP.resolve_role({'ramp': ['25'], 'mode': 'fixed'}, {0x0b8, 0x038})
        self.assertEqual(set(fixed.values()), {0x25})
        grey = NP.resolve_role({'ramp': ['00', '10', '30'], 'strict': True}, {0x000, 0x092, 0x1ff, 0x0c4})
        self.assertEqual((grey[0x000], grey[0x1ff]), (0x0f, 0x30))
        self.assertEqual(grey[0x092], 0x00)
        self.assertTrue(all(NP.chroma(NP.nes9(n)) < NP.NEAR_GREY for n in grey.values()))
        # Black only for near-black, near-neutral colours.
        red = NP.resolve_role({'ramp': ['16', '26']}, {0x008, 0x038})
        self.assertNotEqual(red[0x038], 0x0f)
        # An edited role changes the result, and the check names the stale entry.
        data = NP.load()
        d = data['stages'][0]
        d['roles'][d['entries'][0]['role']]['ramp'] = ['16']
        d['roles'][d['entries'][0]['role']].pop('strict', None)
        self.assertTrue(any('run nes_palette.py resolve' in p for p in NP.check(data)))

    def test_data_holds_only_colours_and_role_names(self):
        import nes_palette as NP
        for p in sorted((ROOT / 'src/nes-palette').rglob('*.json')):
            text = p.read_text()
            for word in ('"captures"', '"prefix"', '"seen"', '.idx', '/workspace', '/home'):
                self.assertNotIn(word, text, p.name)


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

    def test_menu_text_is_editable_source(self):
        import tempfile
        from menu_text import BOX_ROWS, BOX_WIDTH, CODES, band, generate, layout
        source = (ROOT / 'src/options/menu.txt').read_text()
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            (work / 'menu.txt').write_text(source)
            menu = generate(work, '1.11-dev')
            include = (work / 'menu-text.inc').read_text()
        self.assertIn('BOX_WIDTH = 26\nBOX_ROWS = 10\nFIELDS = 6\n', include)
        self.assertEqual(len(menu['window']), BOX_WIDTH * BOX_ROWS)
        self.assertEqual([w for _, _, w in menu['fields']], [5, 3, 3, 3, 10, 8])
        # The dev version fits only without GITHUB.COM/; a release version with it.
        self.assertEqual(menu['band_text'], 'V1.11-DEV TIGERMONKEYFISH')
        self.assertEqual(band('V{version} {credit}', '1.11')[1], 'V1.11 GITHUB.COM/TIGERMONKEYFISH')
        with self.assertRaises(ValueError): band('V{version} {credit}', '1.11-development-build')
        self.assertEqual(len(menu['band']), 32)
        palette = menu['choices'][3]
        # PALETTE offers every mode, in the encoding of src/palette/main.asm:
        # Left/Right order: Original, APOCALYPSE (HELL in the source), NES-A
        # and NES-B (src/nes-palette), SMS, GB DMG; the values are $2100's
        # (and the saved settings') as before the order changed.
        self.assertIn('\n@ $38 $00=ORIGINAL $18=APOCALYPSE $08=NES-A $28=NES-B $38=SMS $10=GB_DMG\n', source)
        self.assertEqual((palette[0], [v for v, _ in palette[1]]), (0x38, [0x00, 0x18, 0x08, 0x28, 0x38, 0x10]))
        for k, text in enumerate(['ORIGINAL', 'APOCALYPSE', 'NES-A', 'NES-B', 'SMS', 'GB DMG']):
            text = text.ljust(10)
            self.assertEqual(palette[1][k][1], bytes(CODES[c] for c in text))
        # The language owns draft bits 6-7 (bits 0-5 are $2100's on Run).
        self.assertEqual(menu['choices'][4][0], 0xc0)
        self.assertEqual([v for v, _ in menu['choices'][4][1]], [0x40, 0x00, 0x80])
        # The reset row: its field after LANGUAGE, in the row that was blank
        # before RUN: OK; the defaults (each option's first value) are the
        # power-on settings without saved ones (src/bram, bram_image).
        import re
        from bram_image import DEFAULTS
        self.assertEqual(menu['reset'], (7, 16, 7))
        self.assertEqual(menu['reset_text'], bytes(CODES[c] for c in 'PRESS I'))
        bram = (ROOT / 'src/bram/main.asm').read_text()
        self.assertEqual(int(re.search(r'^DEFAULT_LANGUAGE = (\d+)', bram, re.M)[1]), DEFAULTS[1])
        self.assertEqual(menu['default'], DEFAULTS[0] | DEFAULTS[1] << 6)
        self.assertIn('FIELDS = 6\nRESET_TEXT_AT = 102\nDEFAULT_DRAFT = $40\n', include)
        self.assertIn('field_row:\n .db 1,2,3,4,5,6,7\n', include)
        for broken in (source.replace('| STAGE: #####             |', '| STAGE: ####              |'),  # STAGE width
                       source.replace('| NO DAMAGE: ###           |', '| NO DAMAGE: ###            |'),  # 27 columns
                       source.replace('LANGUAGE', 'LANGUAGE!'),
                       source.replace('$10=GB_DMG', '$10=GB_DMG_PALETTE'),                         # wider than its field
                       source.replace('@ $04 $00=OFF $04=ON', '@ $04 $00=OFF $02=ON'),              # value outside its bits
                       source.replace('@ $04 $00=OFF $04=ON', '@ $02 $00=OFF $02=ON'),              # bits owned twice
                       source.replace('@ $04 $00=OFF $04=ON\n', ''),                                # a field without values
                       source.replace('|                          |\n', '', 1),                     # nine rows
                       source.replace('| SAVE: ????????           |', '| SAVE:                    |'),  # no status field
                       source.replace('| SAVE: ????????           |', '| SAVE: ????? ??          |'),  # two
                       source.replace('| SAVE: ????????           |', '| SAVE: ??????            |'),  # ERROR 1 does not fit
                       source.replace(' ERROR_5\n', '\n'),                                          # a status without a text
                       source.replace('? NONE OK', '? NONE O!K'),                                   # not in the HUD font
                       source.replace('| RESET OPTIONS: !!!!!!!   |', '| RESET OPTIONS:           |'),  # no reset field
                       source.replace('\n! PRESS_I\n', '\n! PRESS_II\n'),                          # wider than its field
                       source.replace('\n! PRESS_I\n', '\n')):                                       # no reset text
            with self.assertRaises(ValueError):
                layout(broken, '1.11')
        # The save status: one field in the window's last row, a text for
        # each status of src/bram, in its order.
        from bram_image import STATUS
        self.assertEqual(menu['status'], (9, 7, 8))
        self.assertEqual(menu['status_texts'], [bytes(CODES[c] for c in text.ljust(8)) for text in STATUS])
        self.assertIn(f'STATUS_ROW = 9\nSTATUS_COL = 7\nSTATUS_WIDTH = 8\nSTATUS_COUNT = {len(STATUS)}\n', include)


class SavedSettingsTests(unittest.TestCase):
    """The backup RAM images and the model the emulator check compares the
    game with (scripts/bram_image.py): ROM-free."""

    def test_status_values_are_the_modules(self):
        import re
        import bram_image as bi
        source = (ROOT / 'src/bram/main.asm').read_text()
        values = {name: int(value) for name, value in re.findall(r'^ST_(\w+) = (\d+)', source, re.M)}
        self.assertEqual(values, {'NONE': bi.NONE, 'OK': bi.OK, 'READY': bi.READY, 'FULL': bi.FULL,
                                  'UNFORMATTED': bi.UNFORMATTED, 'CORRUPT': bi.CORRUPT, 'SIZE': bi.WRONG_SIZE,
                                  'VERIFY': bi.UNVERIFIED, 'DATA': bi.BAD_DATA, 'COUNT': len(bi.STATUS)})
        self.assertIn(f'ENTRY_SIZE = ${bi.ENTRY_SIZE:02x}\n', source)
        self.assertIn(' .db ' + ','.join(f'${c:02x}' for c in bi.NAME) + '\n', source)
        # Its claims: the reset call, the trampoline up to the vectors, and
        # bank $46 $4B00-$4FFF.
        module = next(m for m in json.loads((ROOT / 'src/modules.json').read_text()) if m['name'] == 'bram')
        self.assertEqual(module['ranges'], [[0x2c, 0x2f], [0x1fe6, 0x1ff6], [0x8cb00, 0x8d000]])

    def test_menu_check_expects_the_status_text(self):
        """check_menu compares the open window with menu.txt and the text
        of the status in $2105: the text must really be in what it expects
        (it once was not, and every opening failed on `NONE`)."""
        import bram_image as bi
        import check_menu as cm
        row, column, width = cm.MENU['status']
        at = row * cm.BOX_WIDTH + column
        seen = set()
        for status, text in enumerate(bi.STATUS):
            window = cm.expected_window(status)
            self.assertEqual(len(window), len(cm.MENU['window']))
            self.assertEqual(''.join(cm.DECODE[c] for c in window[at:at + width]), text.ljust(width))
            self.assertEqual(window[:at] + window[at + width:], cm.MENU['window'][:at] + cm.MENU['window'][at + width:])
            seen.add(bytes(window))
        self.assertEqual(len(seen), len(bi.STATUS))
        self.assertEqual(cm.expected_window(200), cm.expected_window(bi.NONE))

    def test_lock_controls_match_the_source(self):
        """check_bram's negative controls (the unlock and lock removed or
        changed) are byte patterns: they must be the module's instructions."""
        import re
        import check_bram as cb
        source = (ROOT / 'src/bram/main.asm').read_text()
        self.assertIsNotNone(re.search(r' lda #\$48\n sta BRAM_UNLOCK\n lda #\$75\n sta BRAM_UNLOCK\n'
                                       r' lda #\$80\n sta BRAM_UNLOCK\n', source))
        self.assertIsNotNone(re.search(r' lda BRAM_LOCK [^\n]*\n csh\n', source))
        self.assertIn('BRAM_UNLOCK = $1807\n', source)
        self.assertIn('BRAM_LOCK = $1803\n', source)
        self.assertEqual(cb.UNLOCK, bytes.fromhex('a948 8d0718 a975 8d0718 a980 8d0718'))
        self.assertEqual(cb.LOCK, bytes.fromhex('ad0318 d4'))
        rom = bytearray(b'\xff' * 0x100000)
        at = cb.BANK46[0] + 0xb29
        rom[at:at + 15] = cb.UNLOCK
        rom[at + 40:at + 44] = cb.LOCK
        nop = b'\xea' * 3
        self.assertEqual(cb.variant(rom, 'no-unlock')[at:at + 15],
                         b'\xa9\x48' + nop + b'\xa9\x75' + nop + b'\xa9\x80' + nop)
        self.assertEqual(cb.variant(rom, 'bit7-only')[at:at + 15],
                         b'\xa9\x48' + nop + b'\xa9\x75' + nop + b'\xa9\x80\x8d\x07\x18')
        self.assertEqual(cb.variant(rom, 'bit7-clear')[at:at + 15], cb.UNLOCK[:11] + b'\x00' + cb.UNLOCK[12:])
        self.assertEqual(cb.variant(rom, 'no-lock')[at + 40:at + 44], nop + b'\xd4')
        for kind in ('no-unlock', 'bit7-only', 'bit7-clear', 'no-lock'):
            changed = [k for k, (a, b) in enumerate(zip(rom, cb.variant(rom, kind))) if a != b]
            self.assertTrue(changed and at <= changed[0] and changed[-1] < at + 44, kind)
        with self.assertRaises(AssertionError):
            cb.variant(b'\xff' * 0x100000, 'no-unlock')

    def test_entry_is_a_system_card_file(self):
        import bram_image as bi
        raw = bi.settings_entry(0xb9, 2)
        self.assertEqual(raw[:2], b'\x18\x00')
        self.assertEqual(raw[4:16], b'\0\0NR ENHANCE')
        self.assertEqual(raw[16:], bytes([1, 0xb9, 2, 0, 0, 0, 0, 0]))
        self.assertEqual((sum(raw[4:]) + int.from_bytes(raw[2:4], 'little')) & 0xffff, 0)
        card = bi.Directory(bi.image([bi.other(0, 0x40), raw, bi.other(1, 0x33)]))
        self.assertEqual([(at, length, good) for at, length, _, good in card.files()],
                         [(0x8010, 0x40, True), (0x8050, 0x18, True), (0x8068, 0x33, True)])
        self.assertEqual(card.read(b'\0\0NR ENHANCE'), raw[16:])
        self.assertEqual(card.free(), 0x800 - 0x10 - 0x40 - 0x18 - 0x33 - 0x12)
        card.delete(b'\0\0NR ENHANCE')
        self.assertEqual(bytes(card.data[:0x83 + 2]), bi.image([bi.other(0, 0x40), bi.other(1, 0x33)])[:0x83 + 2])

    def test_model_of_load_and_save_over_the_matrix(self):
        import bram_image as bi
        cases = bi.matrix()
        self.assertGreaterEqual(len(cases), 200)
        ours = b'\0\0' + bi.NAME
        for name, image in cases.items():
            status, options, language = bi.expected_load(image)
            if status != bi.OK:
                self.assertEqual((options, language), bi.DEFAULTS, name)
            saved, after = bi.expected_save(image, 0x0b, 2)
            if image is None:
                self.assertEqual((status, saved, after), (bi.NONE, bi.NONE, None))
                continue
            self.assertEqual(len(image), bi.SIZE, name)
            if saved != bi.OK:
                self.assertEqual(after, image, name)             # nothing written
                continue
            # A save: the entry reads back for a System Card style reader,
            # every other file is where and as it was, a boot loads it, and
            # saving the same again changes nothing.
            card = bi.Directory(after)
            self.assertEqual(card.read(ours), bytes([1, 0x0b, 2, 0, 0, 0, 0, 0]), name)
            self.assertEqual(card.word(0x8006), card.terminator(), name)
            before = bi.Directory(image)
            if before.formatted():
                first = next(at for at, _, found, _ in card.files() if found == ours)
                self.assertEqual([f for f in before.files() if f[0] != first],
                                 [f for f in card.files() if f[0] != first], name)
                for at, length, _, _ in before.files():
                    if at != first:
                        self.assertEqual(after[at - bi.BASE:at - bi.BASE + length],
                                         image[at - bi.BASE:at - bi.BASE + length], name)
            self.assertEqual(bi.expected_load(after), (bi.OK, 0x0b, 2), name)
            self.assertEqual(bi.expected_save(after, 0x0b, 2), (bi.OK, after), name)
        # The statuses of the named cases.
        wanted = {'absent': 'NONE', 'empty-8800': 'READY', 'empty-a000': 'READY', 'full': 'FULL',
                  'full-one-short': 'FULL', 'exact-room': 'READY', 'others-before': 'OK', 'ours-bad-checksum': 'ERROR 5',
                  'ours-short': 'ERROR 3', 'ours-version-2': 'ERROR 5', 'ours-mode-20': 'ERROR 5',
                  'ours-language-3': 'ERROR 5', 'pointer-stale': 'OK', 'pointer-low': 'ERROR 2', 'end-zero': 'ERROR 2',
                  'entry-overruns': 'ERROR 2', 'no-terminator': 'ERROR 2', 'terminator-early': 'ERROR 2',
                  'blank-00': 'NONE', 'blank-ff': 'NONE', 'garbage': 'NONE'}
        for name, text in wanted.items():
            self.assertEqual(bi.STATUS[bi.expected_load(cases[name])[0]], text, name)
        for name, text in {'blank-00': 'OK', 'blank-ff': 'OK', 'garbage': 'ERROR 1', 'blank-aa': 'NONE', 'open-bus-80': 'NONE', 'blank-aa-one-byte': 'ERROR 1',
                           'blank-00-one-byte': 'ERROR 1', 'format-cut-tag': 'OK', 'full': 'FULL',
                           'exact-room': 'OK', 'ours-short': 'ERROR 3', 'pointer-low': 'ERROR 2'}.items():
            self.assertEqual(bi.STATUS[bi.expected_save(cases[name], 0, 1)[0]], text, name)
        # Memory that ignores writes is never formatted.
        self.assertEqual(bi.expected_save(cases['blank-ff'], 0, 1, writable=False), (bi.NONE, cases['blank-ff']))


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
