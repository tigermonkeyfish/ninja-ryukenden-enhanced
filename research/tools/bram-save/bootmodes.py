"""Saved settings applied at reset, mode by mode (evidence for
docs/validation/bram-save.md).

For each palette mode (English) and for Japanese and Chinese (Original),
from a cold boot with backup RAM holding that entry after another game's:

- idle: every frame from power-on through the publisher screen, the intro
  cinema and the title, for FRAMES frames, is the frame of the BASELINE
  build booted without backup RAM and given the same settings by a debugger
  write after its first frame (the loader does not move the boot), and, in
  English, also the frame of this build's boot without backup RAM (cinemas
  and the title keep the original colours in every palette mode);
- play: mashing Run to 1-1, 120 frames in: the palette is what the mode is
  due (check_menu.mode_ok: a mapped mode's table over the RAM palette with
  the module's state bit set, an NES mode's own colours in the RAM palette),
  and the picture, the VCE, the RAM palette, $2100 and $2104 are those of
  the BASELINE build given the same settings by a debugger write after its
  first frame. With the original background ($2100 bit 0) palette row 1
  holds the original game's colours, not the Enhanced merged palette that
  mode_ok's check for NES left-overs expects, so a mapped mode is then due
  for its table over the RAM palette as it is (check_menu.mode_expected).

usage: bootmodes.py ROM BASELINE ORIGINAL [FRAMES [OPTIONS:LANGUAGE,...]]
       (the settings in hex:decimal; default: every palette mode in
       English, Original in Japanese and Chinese, and $BF in Chinese)
"""
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts'))
import bram_image as bi  # noqa: E402
from check_bram import boot  # noqa: E402
from check_menu import mode_expected, mode_ok, nes_expected, palette_words  # noqa: E402
from comparison_video import Game  # noqa: E402

rom, baseline, original = sys.argv[1:4]
FRAMES = int(sys.argv[4]) if len(sys.argv) > 4 else 900
EMU = os.environ['NG_EMULATOR']
data = Path(original).read_bytes()
nes = {v: nes_expected(data[512:] if len(data) % 8192 == 512 else data, v) for v in ('a', 'b')}


def idle(path, image, poke=None):
    with tempfile.TemporaryDirectory() as work, Game(EMU, work) as game:
        game.power_on(path, image)
        hashes = []
        for frame in range(FRAMES):
            game.step(1)
            if poke and frame == 0:
                game.write(0x100, bytes([poke[0]]))
                game.write(0x1227, bytes([poke[1]]))
            hashes.append(hashlib.sha256(game.screenshot()).hexdigest())
        assert game.backup_ram() == image
        return hashes


def due(game, ram):
    """The colours on screen are what the mode in $2100 is due."""
    mode = ram[0x100] & 0x38
    vce = game.read(0, 1024, area=8)
    if not mode:
        return vce[:512] == ram[0x286:0x486] and not ram[0x104] & 0x80
    if ram[0x100] & 1 and mode & 0x18 != 0x08:
        return (ram[0x100] & 0x80 == (0x80 if mode == 0x38 else 0) and vce == mode_expected(game, mode)
                and ram[0x104] & 0x80 == 0x80)
    return mode_ok(game, ram, mode, nes)


def play(path, image, poke):
    with tempfile.TemporaryDirectory() as work, Game(EMU, work) as game:
        started = boot(game, path, image, Path(work), poke=poke)
        game.step(80)
        ram = game.read(0, 0x2000)
        return game, {'frame': started['first_update_frame'], 'shot': hashlib.sha256(game.screenshot()).hexdigest(),
                      'vce': game.read(0, 1024, area=8).hex(), 'palette': ram[0x286:0x686].hex(),
                      'options': ram[0x100], 'state': ram[0x104], 'language': ram[0x1227], 'due': due(game, ram)}


plain = idle(rom, None)
ok = True
SETTINGS = ([(int(o, 16), int(l)) for o, l in (pair.split(':') for pair in sys.argv[5].split(','))]
            if len(sys.argv) > 5 else [(m, 1) for m in bi.PALETTES] + [(0x00, 0), (0x00, 2), (0xbf, 2)])
for options, language in SETTINGS:
    image = bi.image([bi.other(0, 0x40), bi.settings_entry(options, language)])
    saved = idle(rom, image)
    poked = idle(baseline, None, (options, language))
    differ = [i for i in range(1, FRAMES) if saved[i] != poked[i]]
    recoloured = [i for i in range(1, FRAMES) if saved[i] != plain[i]] if language == 1 else []
    _, here = play(rom, image, None)
    _, there = play(baseline, None, (options, language))
    same = {k: here[k] == there[k] for k in here}
    row = {'options': f'${options:02X}', 'language': language, 'idle_frames_compared': FRAMES - 1,
           'idle_frames_differing_from_baseline_with_the_settings': len(differ), 'first': differ[:3],
           'idle_frames_differing_from_a_boot_without_backup_ram': len(recoloured) if language == 1 else 'n/a',
           'distinct_idle_screens': len(set(saved)), 'first_update_frame': here['frame'],
           'palette_due': here['due'], 'state_2104': f"${here['state']:02X}", 'as_baseline_with_the_settings': all(same.values()),
           'differs': [k for k, v in same.items() if not v]}
    row['ok'] = (not differ and not recoloured and here['due'] and all(same.values())
                 and (here['options'], here['language']) == (options, language))
    ok &= row['ok']
    print(json.dumps(row), flush=True)
print('PASS' if ok else 'FAIL')
sys.exit(0 if ok else 1)
