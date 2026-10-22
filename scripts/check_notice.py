#!/usr/bin/env python3
"""Check the development splash and native boot handoff in headless Geargrafx.

Requires ffmpeg for screenshot decoding. Uses cold boots and controller input;
no save states or ROM/RAM edits. Captures remain private in the output folder.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from audit_cutscenes import unpack, TITLE_SHA256
import emulator_session as emulator


def inspect(rom, output, label, held=False, check_pixels=False):
    with emulator.Emulator() as session:
        def call(name, arguments=None):
            return unpack(session.call(name, arguments))

        def step(frames):
            call('debug_step_frame', {'frames': frames, 'mode': 'sync'})

        def button(action):
            call('controller_button', {'player': 1, 'button': 'run', 'action': action})

        def screenshot(name):
            data = base64.b64decode(session.call('get_screenshot')['content'][0]['data'])
            path = output / f'{label}-{name}.png'
            path.write_bytes(data)
            return subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(path),
                                            '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'])

        def stop_at(address):
            call('set_breakpoint', {'address': address, 'execute': True})
            try:
                step(120)
            except RuntimeError as exc:
                if 'Synchronous frame step interrupted' not in str(exc):
                    raise
            assert call('debug_get_status')['pc'] == address
            call('remove_breakpoint', {'address': address})

        call('load_media', {'file_path': str(rom.resolve())})
        call('debug_pause')
        call('debug_reset')
        if held:
            # Stop before the wrapper, so Run is down before the notice starts.
            stop_at('FEBE')
            button('press')
        else:
            step(120)
            splash = screenshot('splash')
            step(300)
            assert screenshot('waiting') == splash
            if check_pixels:
                data = rom.read_bytes()
                bat = struct.unpack('<2048H', data[0x8c800:0x8d800])
                palettes = [bytes([255, 255, 255]), bytes([255, 218, 0])]
                assert len(splash) == 256 * 242 * 3
                for y in range(239):
                    for x in range(256):
                        word = bat[(y // 8) * 64 + x // 8]
                        tile = 0x8c400 + ((word & 4095) - 256) * 32
                        bit = (data[tile + (y % 8) * 2] >> (7 - x % 8)) & 1
                        expected = palettes[word >> 12] if bit else bytes(3)
                        offset = ((y + 3) * 256 + x) * 3
                        assert splash[offset:offset + 3] == expected, (x, y)
            button('press')
            if label == 'baseline':
                step(2)
                button('release')
        # Reaching native scene setup while Run remains held proves immediate exit.
        stop_at('83DC')
        button('release')
        stop_at('80C3')
        step(64)
        hudson = screenshot('hudson')
        # Let the native title sequence run; use its independently known image.
        for _ in range(100):
            step(60)
            screenshot('title')
            if hashlib.sha256((output / f'{label}-title.png').read_bytes()).hexdigest() == TITLE_SHA256:
                break
        else:
            raise AssertionError('Native English title not reached')
        call('controller_macro', {'commands': [{'tap': 'run'}, {'wait': 120},
                                             {'tap': 'run'}, {'wait': 180},
                                             {'tap': 'run'}, {'wait': 120}]})
        ram = bytes.fromhex(call('read_memory', {'area': 0, 'offset': '0000', 'size': 8192})['data'])
        assert ram[0xe5f] == 0 and ram[0xead] == 16
        assert ram[0x100] == 0 and ram[0x1227] == 1
        screenshot('gameplay')
        return hudson


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['emulator', 'baseline', 'candidate', 'output']:
        parser.add_argument('--' + name, type=Path, required=True,
                            help='baseline: an earlier Enhanced build with the splash' if name == 'baseline' else None)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    emulator.BINARY = args.emulator.resolve()
    emulator.ROOT = args.output.resolve()
    baseline = inspect(args.baseline, args.output, 'baseline')
    candidate = inspect(args.candidate, args.output, 'candidate', check_pixels=True)
    held = inspect(args.candidate, args.output, 'held', held=True)
    assert baseline == candidate == held, 'Original Hudson screen changed'
    report = {
        'rom_sha256': hashlib.sha256(args.candidate.read_bytes()).hexdigest(),
        'emulator_sha256': hashlib.sha256(args.emulator.read_bytes()).hexdigest(),
        'splash_pixels_match_rom': True,
        'splash_stationary_300_frames': True,
        'press_and_held_run_exit_without_release': True,
        'hudson_matches_baseline': True,
        'native_english_title_and_gameplay_reached': True,
        'defaults_enhanced_normal_damage_english': True,
        'physical_hardware_tested': False,
    }
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
