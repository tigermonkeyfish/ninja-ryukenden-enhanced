#!/usr/bin/env python3
"""Check that Enhanced boots exactly like the original, in headless Geargrafx.

Enhanced has no boot screen of its own (1.10-dev). Compares a candidate with
the original game, using cold boots and controller input only. The original
gets native English (`$3227 = 1`, Enhanced's reset default) by a debugger
write after its first frame, so the two title screens can match too:

- idle: every frame from power-on through the title screen is identical
  (except frame 0, whose screenshot differs between sessions of one ROM);
- mashing Run from power-on reaches the first 1-1 update on the same frame;
- the candidate starts on English, Enhanced and No Damage off.

Captures remain private in the output folder.
"""
import argparse
import hashlib
import json
from pathlib import Path

from comparison_video import Game

IDLE_FRAMES = 900           # frames 1-899; the title appears at frame 606


def boot(emulator, rom, output, mash, english=False):
    """Frame hashes (idle) or the first gameplay-update frame (mash)."""
    with Game(emulator, output) as game:
        game.call('load_media', {'file_path': str(Path(rom).resolve())})
        game.call('debug_pause')
        if mash:
            game.call('set_breakpoint', {'address': '2457', 'memory_area': 'rom', 'execute': True})
        hashes = []
        for frame in range(30000):          # frame 0: the first step from power-on
            if mash:
                # Run for 2 frames in every 20, released once gameplay starts.
                gameplay = game.read(0x240, 1)[0] == 0 and frame > 60
                game.press({'run'} if frame % 20 < 2 and not gameplay else set())
            elif frame == IDLE_FRAMES:
                return hashes
            game.step(1)
            if english and frame == 0:
                game.write(0x1227, b'\x01')
            if not mash and frame:
                hashes.append(hashlib.sha256(game.screenshot()).hexdigest())
            elif game.call('debug_get_status').get('pc') == '8457':
                break
        ram = game.read(0, 0x2000)
        # Counted like research/tools/starttiming.py: the step that reaches the
        # gameplay loop's first update is that update's frame.
        return {'first_update_frame': frame + 1, 'stage': ram[0xe5f], 'health': ram[0xead],
                'options': ram[0x100], 'language': ram[0x1227]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['emulator', 'original', 'candidate', 'output']:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    original = boot(args.emulator, args.original, args.output / 'original-idle', False, english=True)
    candidate = boot(args.emulator, args.candidate, args.output / 'candidate-idle', False)
    first_difference = next((i + 1 for i, (a, b) in enumerate(zip(original, candidate)) if a != b), None)
    assert len(original) == len(candidate) == IDLE_FRAMES - 1
    assert first_difference is None, f'Boot differs from the original at frame {first_difference}'
    assert len(set(original)) > 2, 'Idle boot showed no screens'
    original_mash = boot(args.emulator, args.original, args.output / 'original-mash', True, english=True)
    candidate_mash = boot(args.emulator, args.candidate, args.output / 'candidate-mash', True)
    assert original_mash['first_update_frame'] == candidate_mash['first_update_frame'], (original_mash, candidate_mash)
    assert candidate_mash['stage'] == 0 and candidate_mash['health'] == 16, candidate_mash
    assert candidate_mash['options'] == 0 and candidate_mash['language'] == 1, candidate_mash
    report = {
        'rom_sha256': hashlib.sha256(args.candidate.read_bytes()).hexdigest(),
        'emulator_sha256': hashlib.sha256(args.emulator.read_bytes()).hexdigest(),
        'idle_frames_identical_to_original': f'1-{IDLE_FRAMES - 1}',
        'distinct_idle_screens': len(set(original)),
        'mash_run_first_update_frame': candidate_mash['first_update_frame'],
        'defaults_enhanced_normal_damage_english': True,
        'physical_hardware_tested': False,
    }
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
