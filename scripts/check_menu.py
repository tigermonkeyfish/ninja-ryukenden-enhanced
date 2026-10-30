#!/usr/bin/env python3
"""Open the in-game menu throughout play and check that it corrupts nothing.

Headless Geargrafx, controller input only (plus save states to return to the
stored runs). Two parts:

1. In each stored comparison run (research/comparison-runs/), every `--every`
   frames and shortly after every area change: save the state, press Select,
   check the menu text, the clear item box and the blinking value, change every
   setting, press Select (cancel), and compare the machine at the moment the menu returns
   to the game with the moment it was entered. Video memory, the sprite table
   and the palette must be identical; RAM may differ only where the menu or
   the running interrupt legitimately writes (ALLOWED). Then reload the state
   and continue the run.
2. From a cold boot: open and cancel the menu in each of the 22 Level Select
   entries (the same exact check), then accept the next entry and check, at
   that stage's first update, the stage, full health, the options and the
   restored status bar (an idle Ryu can be hit soon after).

Writes a JSON report to the output folder; captures stay private there.
"""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile

from comparison_video import Game, make_seed, start_point, start_stage
from guide_screenshots import tap, to_gameplay, to_title
from menu_text import CODES, ITEM_BOX, layout

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / 'research/comparison-runs'
DECODE = {code: char for char, code in CODES.items()}
HOOK_AFTER_DRAW = '1f73'     # $FF73: Select hook, after the pending-draw call
HOOK_RETURN = '23f6'         # bank 1 $83F6: main loop, after the Select hook
FIRST_UPDATE = '2457'        # bank 1 $8457: gameplay loop (a stage's first update)
SPACE_WORD = bytes.fromhex('9ff7')
# BAT position of the STAGE value (HUD rows start at BAT row 28).
STAGE_AT = layout((ROOT / 'src/options/menu.txt').read_text().replace('{version}', '0').splitlines())[1]['STAGE_AT']


def allowed(offset, stack_pointer):
    """RAM bytes (offsets from $2000) that may differ after a cancelled menu.

    Found by write watches while the menu waits: the vertical-blank interrupt
    sets $12 and $2E45 and reads the pad into $2E55-$2E5E; the music driver
    (banks $38-$3A) owns zero page $80-$8F and $3800-$3BFF; the menu uses the
    stack below the hook's stack pointer and keeps its draft settings in
    $2101."""
    return (offset in (0x012, 0x101, 0xe45) or 0xe55 <= offset <= 0xe5e
            or 0x080 <= offset <= 0x08f or 0x1800 <= offset <= 0x1bff
            or 0x104 <= offset <= stack_pointer - 0x2000)


def snapshot(game):
    return {'ram': game.read(0, 0x2000), 'vram': game.read(0, 0x10000, area=4),
            'sat': game.read(0, 512, area=6), 'vce': game.read(0, 1024, area=8)}


def text(game, row, column, count):
    words = game.read(row * 64 + column, count * 2, area=4)
    return ''.join(DECODE.get(words[i], '?') if words[i + 1] == 0xf7 else '#'
                   for i in range(0, count * 2, 2))


def stop_at(game, offset, frames):
    """Step until the ROM breakpoint `offset` is hit; True if it was."""
    game.call('set_breakpoint', {'address': offset, 'memory_area': 'rom', 'execute': True})
    try:
        for _ in range(frames):
            if game.step(1) is None:
                return True
        return False
    finally:
        game.call('remove_breakpoint', {'address': offset, 'memory_area': 'rom'})


def press(game, button, after=3):
    game.press({button})
    game.step(2)
    game.press(set())
    game.step(after)


def menu_cycle(game):
    """Press Select; if the menu opens, exercise it, cancel with Select and compare.

    Returns None when the game does not accept the menu here (transitions),
    else a dict of findings; 'ok' is False on any corruption."""
    game.press({'select'})
    for _ in range(3):
        if not stop_at(game, HOOK_AFTER_DRAW, 3):
            return None
        ram = game.read(0, 0x2000)
        if ram[0xe57] & 4:
            break
    else:
        return None
    if ram[0xe63] or not ram[0x201]:
        game.press(set())
        return None
    stack_pointer = int(game.call('get_huc6280_status')['SP'], 16)
    before = snapshot(game)
    game.press(set())
    game.step(4)
    rows = [text(game, row, 0, 32) for row in (28, 29, 30, 31)]
    found = {'rows': rows, 'problems': []}
    if not rows[0].startswith('STAGE:') or 'ACCEPT' not in rows[3]:
        found['problems'].append('menu text not shown')
    if any(text(game, row, ITEM_BOX.start, len(ITEM_BOX)).strip() for row in (29, 30)):
        found['problems'].append('item box not clear')
    shown = set()
    for _ in range(36):
        game.step(1)
        shown.add(bool(text(game, 28 + STAGE_AT // 64, STAGE_AT % 64, 5).strip()))
    if shown != {True, False}:
        found['problems'].append('selected value does not blink')
    for button in ('right', 'left', 'down', 'right', 'down', 'right', 'up', 'up'):
        press(game, button)
    game.press({'select'})
    game.step(2)
    game.press(set())
    if not stop_at(game, HOOK_RETURN, 120):
        found['problems'].append('menu did not return to the game')
        found['ok'] = False
        return found
    after = snapshot(game)
    for area in ('vram', 'sat', 'vce'):
        if before[area] != after[area]:
            changed = [i for i, (a, b) in enumerate(zip(before[area], after[area])) if a != b]
            found['problems'].append(f'{area} changed at {len(changed)} bytes, first {changed[0]:#06x}')
    bad = [i for i, (a, b) in enumerate(zip(before['ram'], after['ram']))
           if a != b and not allowed(i, stack_pointer)]
    if bad:
        found['problems'].append('RAM changed at ' + ', '.join(f'${0x2000 + i:04x}' for i in bad[:16]))
    found['ok'] = not found['problems']
    return found


def check_runs(emulator, candidate, seed, every, output):
    results = {}
    for path in sorted(RUNS.glob('*.json')):
        run = json.loads(path.read_text())
        inputs = [buttons for count, buttons in run['segments'] for _ in range(count)]
        checks = []
        with Game(emulator, Path(tempfile.mkdtemp(prefix='menu-', dir=output))) as game:
            start_point(game, candidate, seed, enhanced=True)
            start_stage(game, run['stage'])
            state = Path(game.logdir) / 'resume.state'
            area, area_frame = None, None
            for frame, buttons in enumerate(inputs):
                game.press(set(buttons))
                game.step(1)
                current = game.read(0xe60, 1)[0]
                if current != area:
                    area, area_frame = current, frame
                if frame % every != every // 2 and frame != area_frame + 30:
                    continue
                game.call('save_state_file', {'file_path': str(state)})
                found = menu_cycle(game)
                game.call('load_state_file', {'file_path': str(state)})
                game.held = set()
                if found is not None:
                    checks.append(dict(found, frame=frame, area=area))
        results[run['name']] = {
            'menus_checked': len(checks), 'ok': all(c['ok'] for c in checks) and bool(checks),
            'problems': [c for c in checks if not c['ok']]}
        print(run['name'], results[run['name']]['menus_checked'], 'menus',
              'ok' if results[run['name']]['ok'] else 'FAILED', flush=True)
    return results


def check_level_select(emulator, candidate, output):
    results = []
    with Game(emulator, Path(tempfile.mkdtemp(prefix='menu-select-', dir=output))) as game:
        game.call('load_media', {'file_path': str(Path(candidate).resolve())})
        game.call('debug_pause')
        to_title(game)
        to_gameplay(game)
        for stage in range(22):
            entry = {'stage': stage, 'problems': []}
            found = menu_cycle(game)
            if found is None:
                entry['problems'].append('menu not available')
            elif not found['ok']:
                entry['problems'] += found['problems']
            if stage == 21:
                results.append(entry)
                break
            game.step(20)
            press(game, 'select', after=6)
            press(game, 'right', after=4)
            game.press({'run'})
            game.step(2)
            game.press(set())
            # Read the stage as it starts: an idle Ryu can be hit soon after.
            if not stop_at(game, FIRST_UPDATE, 600):
                entry['problems'].append('chosen stage did not start')
            ram = game.read(0, 0x2000)
            if ram[0xe5f] != stage + 1 or ram[0xead] != 16 or ram[0x100] != 0:
                entry['problems'].append(f'after accept: stage {ram[0xe5f]}, health {ram[0xead]}, options {ram[0x100]:#04x}')
            if (game.read(0x7c0, 64, area=4) != SPACE_WORD * 32 or any(game.read(0x7aa0, 128, area=4))
                    or any(game.read(0x7b90, 32, area=4))):
                entry['problems'].append('band under the HUD or borrowed tiles not restored')
            if text(game, 30, 3, 2) != 'P-':
                entry['problems'].append(f'HUD row 30 not restored: {text(game, 30, 0, 32)!r}')
            entry['ok'] = not entry['problems']
            results.append(entry)
            game.step(60)
            print('level select', stage, 'ok' if entry['ok'] else entry['problems'], flush=True)
        results[-1]['ok'] = not results[-1]['problems']
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['emulator', 'original', 'candidate', 'output']:
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--every', type=int, default=300, help='frames between menu checks in a run')
    parser.add_argument('--only', choices=('runs', 'select'), help='run one part only')
    args = parser.parse_args()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    report = {
        'rom_sha256': hashlib.sha256(args.candidate.read_bytes()).hexdigest(),
        'emulator_sha256': hashlib.sha256(args.emulator.read_bytes()).hexdigest(),
        'physical_hardware_tested': False,
    }
    if args.only != 'select':
        seed = make_seed(args.emulator, args.original, args.output / 'seed.state')
        report['runs'] = check_runs(args.emulator, args.candidate, seed, args.every, args.output)
    if args.only != 'runs':
        report['level_select'] = check_level_select(args.emulator, args.candidate, args.output)
    report['ok'] = (all(r['ok'] for r in report.get('runs', {}).values())
                    and all(e['ok'] for e in report.get('level_select', [])))
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('menu check', 'passed' if report['ok'] else 'FAILED')
    raise SystemExit(0 if report['ok'] else 1)


if __name__ == '__main__':
    main()
