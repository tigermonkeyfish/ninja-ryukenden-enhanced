#!/usr/bin/env python3
"""Open the in-game menu (the popup window) throughout play and check it.

Headless Geargrafx, controller input (plus save states to return to the
stored runs and a few debugger writes named below). Parts (`--only`):

runs    In each stored comparison run (research/comparison-runs/), every
        `--every` frames and 30 frames after every area change: press Select
        and, when the menu opens, run `exact_cycle`: the window's text, the
        clear HUD (a VRAM write watch on rows 28-30 while it is open), the
        band (row 31), sprites off, the blinking value, every setting
        changed except the palette (or, with --preview, the palette too),
        then Select. At the moment the menu returns, VRAM must equal the
        moment it was entered except the sprite-table buffer being built
        (the backup) and RAM except ALLOWED; then the game runs UPDATES more
        frames and is compared with the same state run without the menu:
        at every frame's end VRAM (the backup buffer included: the game
        rewrote it), the sprite table and the palette, and at the next
        update boundary RAM except ALLOWED. Pictures that differ in a frame
        whose video state agrees are reported as raster timing: the music
        driver played on during the menu, so the interrupts take different
        time and identical writes land at other raster positions. With
        --same-music the run without the menu gets the music driver's state
        as the menu left it, and every picture must match. The stack's
        low-water mark is measured from a $A5 fill below the stack pointer.
        Parallax OFF variants of the runs are selected with --parallax-off.
sweep   Select pressed at every frame (`--sweep-step`) of the unsafe
        windows: a time-out death and respawn in 1-1 (timer set to 2 by a
        debugger write), the 5-4 idle death and continue, and frames -5..+45
        around every area change in the runs named by --sweep-runs. Each
        frame is refused (the menu does not open) or passes exact_cycle.
select  From a cold boot: exact_cycle in each of the 22 Level Select entries,
        then Run on the next entry: the stage, full health, options, HUD and
        band restored at its first update.
options Each option row changed and accepted with Run, from 1-1: $2100 and
        $3227 afterwards; GB DMG shows the GB table's colours for the whole
        RAM palette, HELL the HELL table's for entries 0-239 and the RAM
        colours for the rest; paths through the palette values (GB DMG then
        ORIGINAL, HELL then ORIGINAL, HELL, GB DMG, ORIGINAL and the
        reverse), each accepted with Run, show each mapped mode's table
        exactly and end with the same VCE as a stage start that never left
        Original. Cancel after changing everything (from Original with GB
        DMG or HELL previewed, from GB DMG previewing HELL, from HELL
        previewing ORIGINAL) leaves the options and $3227 unchanged and is
        compared with the run without the menu for LONG frames.
select  also checks, after a cold boot, that the LANGUAGE row reads
        ENGLISH with $3227 = 1.

Writes a JSON report to the output folder; captures stay private there.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile

from comparison_video import Game, make_seed, start_point, start_stage
from guide_screenshots import to_gameplay, to_title
from menu_text import BOX_ROWS, BOX_WIDTH, CODES, layout
from palette_tables import gb_dmg_table, hell_table, load_hell

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / 'research/comparison-runs'
DECODE = {code: char for char, code in CODES.items()}
HOOK_AFTER_DRAW = '1f73'     # $FF73: Select hook, after the pending-draw call
HOOK_RETURN = '23f6'         # bank 1 $83F6: main loop, after the Select hook
FIRST_UPDATE = '2457'        # bank 1 $8457: gameplay loop (a stage's first update)
MENU_ENTRY = 0x46 * 0x2000 + 0x400                 # bank $46 $4400
MENU_PREFIX = bytes.fromhex('adab2ec90af00dadad2ef008ad4d2e0d4e2ef003a9ff60')   # the refusals
MENU_OPEN = f'{MENU_ENTRY + len(MENU_PREFIX):x}'   # after it: the menu opens
MENU_OPEN_PC = f'{0x4400 + len(MENU_PREFIX):04X}'
CPU = {HOOK_AFTER_DRAW: 'FF73', HOOK_RETURN: '83F6', FIRST_UPDATE: '8457', MENU_OPEN: MENU_OPEN_PC}
SPACE_WORD = bytes.fromhex('9ff7')
SOURCE = (ROOT / 'src/options/main.asm').read_text()
BOX_TOP = int(re.search(r'^BOX_TOP = (\d+)', SOURCE, re.M)[1])
BOX_LEFT = int(re.search(r'^BOX_LEFT = (\d+)', SOURCE, re.M)[1])
VERSION = (ROOT / 'VERSION').read_text().strip()
MENU = layout((ROOT / 'src/options/menu.txt').read_text(), VERSION)
HUD_WORDS = (28 * 64, 31 * 64 - 1)                 # BAT rows 28-30
UPDATES = 20
SAME_MUSIC = False          # --same-music: see exact_cycle
LONG = 900                  # frames compared after a cancelled palette preview


def allowed(offset, stack_pointer):
    """RAM bytes (offsets from $2000) that may differ after a cancelled menu.

    Found by write watches while the menu waits: the vertical-blank interrupt
    sets $12 and $2E45 and reads the pad into $2E55-$2E5E; the music driver
    (banks $38-$3A) owns zero page $80-$8F and $3800-$3BFF; the menu uses the
    stack below the hook's stack pointer and keeps its draft in $2101."""
    return (offset in (0x012, 0x101, 0xe45) or 0xe55 <= offset <= 0xe5e
            or 0x080 <= offset <= 0x08f or 0x1800 <= offset <= 0x1bff
            or 0x104 <= offset <= stack_pointer - 0x2000)


# Palette upload scratch, rewritten before it is read (every user of the RAM
# block-transfer instruction writes all of $2205-$220B before calling it:
# $E108 with its callers, $E7F5, $F3B5): the RAM TIA's operands
# ($2205-$220C, written before every call), $2284-$2285 and queue entries past the count. A cancelled
# palette preview leaves them as the restoring upload wrote them.
PREVIEW_SCRATCH = set(range(0x205, 0x20d)) | {0x284, 0x285} | set(range(0x261, 0x281))


def module_state_only(i, a, b):
    """$2100 differing only in bits 5-6: the palette module's left-over and
    busy-history state, which a cancelled palette preview leaves as the
    restoring upload set it (the menu never writes bits 5-7; in Original
    mode the module neither reads nor writes bits 5-6)."""
    return i == 0x100 and not (a ^ b) & ~0x60


def snapshot(game):
    return {'ram': game.read(0, 0x2000), 'vram': game.read(0, 0x10000, area=4),
            'sat': game.read(0, 512, area=6), 'vce': game.read(0, 1024, area=8)}


def vdc(game):
    regs = game.call('get_huc6270_registers')['registers']
    return {r[0]: int(r[1], 16) for r in regs if isinstance(r[0], int)}


def box_column(ram):
    return ((((ram[0xe4c] & 1) << 8 | ram[0xe4b]) >> 3) + BOX_LEFT) & 63


def window_words(game, c0):
    """The window's cells as BAT words, row by row."""
    bat = game.read(0, 0x1000 * 2, area=4)
    return [[bat[2 * ((BOX_TOP + j) * 64 + ((c0 + i) & 63)):][:2] for i in range(BOX_WIDTH)]
            for j in range(BOX_ROWS)]


def window_problems(game, c0):
    """Differences between the BAT window and menu.txt (value fields: any font cell)."""
    fields = {(r, c + k) for r, c, w in MENU['fields'] for k in range(w)}
    problems = []
    for j, row in enumerate(window_words(game, c0)):
        for i, word in enumerate(row):
            expected = MENU['window'][j * BOX_WIDTH + i]
            if word[1] != 0xf7 or ((j, i) not in fields and word[0] != expected):
                problems.append(f'window cell {j},{i} = {word.hex()}')
    return problems[:8]


def field_text(game, c0, field):
    row, col, width = MENU['fields'][field]
    words = window_words(game, c0)[row][col:col + width]
    return ''.join(DECODE.get(w[0], '?') if w[1] == 0xf7 else '#' for w in words)


def run_until(game, offsets, polls=20000):
    """Continue to the first of the ROM execute breakpoints `offsets` (or any
    watch already set); the CPU address it stopped at, None if none came.

    Continue-and-poll, not frame steps: a frame step started at a breakpoint
    whose breakpoint is still set reports a completed frame although it
    stopped at the breakpoint again, so step results cannot count hits."""
    for offset in offsets:
        game.call('set_breakpoint', {'address': offset, 'memory_area': 'rom', 'execute': True})
    try:
        game.call('debug_continue')
        for _ in range(polls):
            status = game.call('debug_get_status')
            if status.get('paused'):
                return status['pc']
        game.call('debug_pause')
        return None
    finally:
        for offset in offsets:
            game.call('remove_breakpoint', {'address': offset, 'memory_area': 'rom'})


def stop_at(game, offset, frames=None):
    """Run to the ROM breakpoint `offset`; True if it was reached."""
    return run_until(game, [offset]) == CPU[offset]


def press(game, button, after=3):
    game.press({button})
    game.step(2)
    game.press(set())
    game.step(after)


def select_at_hook(game):
    """Press Select and stop at the hook in the update that sees it newly
    pressed; False if no update did (a transition)."""
    game.press({'select'})
    for _ in range(3):
        if not stop_at(game, HOOK_AFTER_DRAW):
            break
        if game.read(0xe57, 1)[0] & 4:
            return True
    game.press(set())
    return False


def opens(game):
    """At the hook with Select newly pressed: run on to the menu's opening
    (True) or the hook's return (False: refused)."""
    return run_until(game, [MENU_OPEN, HOOK_RETURN]) == MENU_OPEN_PC


def frames(game, count, state_dir):
    """From a breakpoint stop: normalize (save and reload the state, so frame
    steps have a defined length), then `count` whole frames; for each, the
    completed frame's picture and the video state at its end (VRAM, sprite
    table, palette). A screenshot taken at a breakpoint can show a frame in
    progress, so pictures are only taken after whole frame steps."""
    state = Path(state_dir) / 'normal.state'
    game.call('save_state_file', {'file_path': str(state)})
    game.call('load_state_file', {'file_path': str(state)})
    shots = []
    for _ in range(count):
        game.checked_step(1)
        video = hashlib.sha256()
        for area, size in ((4, 0x10000), (6, 512), (8, 1024)):
            video.update(game.read(0, size, area=area))
        shots.append((hashlib.sha256(game.screenshot()).hexdigest()[:16], video.hexdigest()[:16]))
    return shots


def compare_frames(found, menu_shots, reference_shots):
    """Every frame must end with the same VRAM, sprite table and palette.
    A picture may differ only in a frame whose video state agrees: the same
    writes landed at another raster position (the interrupts take different
    time after the menu: the music driver played on), which is reported."""
    video = [k for k, (a, b) in enumerate(zip(menu_shots, reference_shots)) if a[1] != b[1]]
    if video or len(menu_shots) != len(reference_shots):
        found['problems'].append(f'video state differs at the end of frames {video[:20]}')
    found['raster_timing_frames'] = [k for k, (a, b) in enumerate(zip(menu_shots, reference_shots))
                                     if a[0] != b[0] and a[1] == b[1]]
    if SAME_MUSIC and found['raster_timing_frames']:
        found['problems'].append(f'pictures differ with the same music state in frames {found["raster_timing_frames"]}')


def exact_cycle(game, state_dir, actions=None, n=UPDATES, shots=None, blink=True):
    """At the hook with Select newly pressed (select_at_hook). Returns None if
    the menu is refused here, else findings ('ok' False on any problem)."""
    sp = int(game.call('get_huc6280_status')['SP'], 16) - 0x2000   # $100 + S
    game.write(0x104, b'\xa5' * (sp - 0x104 + 1))   # stack low-water mark
    state = Path(state_dir) / 'cycle.state'
    game.call('save_state_file', {'file_path': str(state)})
    before = snapshot(game)
    if not opens(game):
        game.press(set())
        game.step(1)
        after = game.read(0, 0x2000)
        return None if after[0x100] == before['ram'][0x100] else {'ok': False, 'problems': ['refused but options changed']}
    found = {'problems': []}
    c0 = box_column(before['ram'])
    found['column'] = c0
    found['wraps'] = c0 + BOX_WIDTH > 64
    game.call('set_breakpoint_range', {'start_address': f'{HUD_WORDS[0]:x}', 'end_address': f'{HUD_WORDS[1]:x}',
                                       'memory_area': 'vram', 'write': True})
    try:
        game.press(set())
        if game.step(4) is None:
            found['problems'].append('HUD rows 28-30 written while opening')
        found['problems'] += window_problems(game, c0)
        band = game.read(31 * 64, 64, area=4)
        if band != bytes(x for c in MENU['band'] for x in (c, 0xf7)):
            found['problems'].append('band (row 31) does not show the version line')
        if vdc(game).get(5, 0) & 0x40:
            found['problems'].append('sprites still enabled')
        if shots is not None:
            shots.append(game.screenshot())
        seen = {True, False} if not blink else set()
        for _ in range(36 if blink else 0):
            if game.step(1) is None:
                found['problems'].append('HUD rows 28-30 written while open')
                break
            seen.add(bool(field_text(game, c0, 0).strip()))
        if seen != {True, False}:
            found['problems'].append('selected value does not blink')
        if actions is None:
            actions = ['right', 'left', 'down', 'right', 'down', 'right', 'down', 'right',
                       'down', 'down', 'right', 'up', 'up']
        for button in actions:
            game.press({button})
            hit = game.step(2) is None
            game.press(set())
            hit = hit or game.step(3) is None
            if hit:
                found['problems'].append('HUD rows 28-30 written while open')
        game.press({'select'})
        game.step(2)
        game.press(set())
        pc = run_until(game, [HOOK_RETURN])
        if pc != '83F6':
            found['problems'].append(f'menu did not return to the game (stopped at {pc})')
            found['ok'] = False
            return found
    finally:
        game.call('remove_breakpoint', {'address': f'{HUD_WORDS[0]:x}', 'end_address': f'{HUD_WORDS[1]:x}',
                                        'memory_area': 'vram'})
    after = snapshot(game)
    low = next((i for i in range(0x104, sp + 1) if after['ram'][i] != 0xa5), None)
    found['stack_low'] = f'${0x2000 + low:04x}' if low is not None else None
    build = before['ram'][0xb81]
    spare = range(2 * (0x7e00 + 0x100 * build), 2 * (0x7f00 + 0x100 * build))
    changed = [i for i, (a, b) in enumerate(zip(before['vram'], after['vram'])) if a != b and i not in spare]
    if changed:
        found['problems'].append(f'VRAM changed at {len(changed)} bytes outside the backup, first word {changed[0] // 2:#06x}')
    found['backup_words_used'] = sum(before['vram'][i] != after['vram'][i] for i in spare)
    for area in ('sat', 'vce'):
        if before[area] != after[area]:
            found['problems'].append(f'{area} changed at return')
    bad = [i for i, (a, b) in enumerate(zip(before['ram'], after['ram'])) if a != b and not allowed(i, 0x2000 + sp)]
    found['scratch_differs'] = [f'${0x2000 + i:04x}' for i in bad if i in PREVIEW_SCRATCH]
    if module_state_only(0x100, before['ram'][0x100], after['ram'][0x100]) and 0x100 in bad:
        found['scratch_differs'].append(f'$2100 {before["ram"][0x100]:#04x} -> {after["ram"][0x100]:#04x}')
    bad = [i for i in bad if i not in PREVIEW_SCRATCH and not module_state_only(i, before['ram'][i], after['ram'][i])]
    if bad:
        found['problems'].append('RAM changed at ' + ', '.join(f'${0x2000 + i:04x}' for i in bad[:16]))
    pad = after['ram'][0xe55:0xe5f]
    menu_shots = frames(game, n, state_dir)
    # State is compared at an update boundary (the next hook): at a frame's
    # end the update in progress is a few cycles apart in the two runs (the
    # music driver, which ran on during the menu, takes different time in
    # the interrupts).
    stop_at(game, HOOK_AFTER_DRAW)
    menu_end = snapshot(game)
    menu_cpu = game.call('get_huc6280_status')
    # The same state without the menu: the pad bytes as the menu left them.
    game.call('load_state_file', {'file_path': str(state)})
    game.held = set()
    game.write(0xe55, pad)
    if SAME_MUSIC:
        # Control: the music driver's state as the menu left it, so the
        # interrupts take the same time in both runs.
        game.write(0x080, after['ram'][0x080:0x090])
        game.write(0x1800, after['ram'][0x1800:0x1c00])
    if not stop_at(game, HOOK_RETURN, 3):
        found['problems'].append('reference did not return from the hook')
    reference = game.read(0, 0x2000)
    bad = [i for i, (a, b) in enumerate(zip(reference, after['ram']))
           if a != b and not allowed(i, 0x2000 + sp) and i not in PREVIEW_SCRATCH and not module_state_only(i, a, b)]
    if bad:
        found['problems'].append('RAM differs from the run without the menu at ' + ', '.join(f'${0x2000 + i:04x}' for i in bad[:16]))
    reference_shots = frames(game, n, state_dir)
    stop_at(game, HOOK_AFTER_DRAW)
    reference_end = snapshot(game)
    reference_cpu = game.call('get_huc6280_status')
    compare_frames(found, menu_shots, reference_shots)
    for area in ('vram', 'sat', 'vce'):
        if menu_end[area] != reference_end[area]:
            words = [i // 2 for i in range(0, len(menu_end[area]), 2) if menu_end[area][i:i + 2] != reference_end[area][i:i + 2]]
            found['problems'].append(f'{area} differs {n} updates later at {len(words)} words, first {words[0]:#06x}')
    # The stack below the deeper of the two stack pointers at the end is
    # dead in both; the CPU registers are reported.
    end_sp = max(int(menu_cpu['SP'], 16), int(reference_cpu['SP'], 16))
    found['end_cpu'] = [{k: c[k] for k in ('PC', 'X', 'Y', 'S')} for c in (menu_cpu, reference_cpu)]
    if found['end_cpu'][0] != found['end_cpu'][1]:
        found['problems'].append(f'CPU differs {n} frames later: {found["end_cpu"]}')
    bad = [i for i, (a, b) in enumerate(zip(menu_end['ram'], reference_end['ram']))
           if a != b and not allowed(i, end_sp) and not module_state_only(i, a, b) and i not in PREVIEW_SCRATCH]
    if bad:
        found['problems'].append(f'RAM differs {n} updates later at ' + ', '.join(f'${0x2000 + i:04x}' for i in bad[:16]))
    found['ok'] = not found['problems']
    return found


def check_runs(emulator, candidate, seed, every, output, options=0, actions=None, shots_dir=None):
    results = {}
    for path in sorted(RUNS.glob('*.json')):
        run = json.loads(path.read_text())
        inputs = [buttons for count, buttons in run['segments'] for _ in range(count)]
        checks = []
        work = Path(tempfile.mkdtemp(prefix='menu-', dir=output))
        with Game(emulator, work) as game:
            start_point(game, candidate, seed, enhanced=True)
            game.write(0x100, bytes([options]))
            start_stage(game, run['stage'])
            state = work / 'resume.state'
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
                found = None
                if select_at_hook(game):
                    shots = [] if shots_dir else None
                    found = exact_cycle(game, work, actions, shots=shots)
                    if shots:
                        (Path(shots_dir) / f'{run["name"]}-{frame}.png').write_bytes(shots[0])
                game.call('load_state_file', {'file_path': str(state)})
                game.held = set()
                game.press(set())
                if found is not None:
                    checks.append(dict(found, frame=frame, area=area))
        shutil.rmtree(work, ignore_errors=True)
        results[run['name']] = {
            'menus_checked': len(checks), 'ok': all(c['ok'] for c in checks) and bool(checks),
            'wrapping_windows': sum(c.get('wraps', False) for c in checks),
            'columns': sorted({c.get('column') for c in checks if 'column' in c}),
            'stack_low': min((c['stack_low'] for c in checks if c.get('stack_low')), default=None),
            'raster_timing': {c['frame']: c['raster_timing_frames'] for c in checks if c.get('raster_timing_frames')},
            'problems': [c for c in checks if not c['ok']]}
        print(run['name'], results[run['name']]['menus_checked'], 'menus',
              results[run['name']]['wrapping_windows'], 'wrapping, stack low', results[run['name']]['stack_low'],
              'ok' if results[run['name']]['ok'] else 'FAILED', flush=True)
    return results


def sweep_frames(game, work, frames, label, step):
    """Select at each frame of a window of play driven by `frames` (a list of
    button sets); returns the per-frame outcomes."""
    state = work / 'sweep.state'
    outcome = []
    for k, buttons in enumerate(frames):
        game.press(set(buttons))
        game.step(1)
        if k % step:
            continue
        ram = game.read(0, 0x2000)
        info = {'frame': k, 'stage': ram[0xe5f], 'area': ram[0xe60], 'health': ram[0xead],
                'lives': ram[0xeaf], 'ryu': ram[0xeab], 'e63': ram[0xe63], 'pause_ok': ram[0x201],
                'lock': ram[0x283], 'cr': ram[0x0e]}
        game.call('save_state_file', {'file_path': str(state)})
        if not select_at_hook(game):
            info['result'] = 'no update saw Select'
        else:
            found = exact_cycle(game, work, actions=['down', 'right', 'down', 'right'], n=10, blink=False)
            info['result'] = 'refused' if found is None else ('opened, exact' if found['ok'] else 'opened, FAILED')
            if found and not found['ok']:
                info['problems'] = found['problems']
        game.call('load_state_file', {'file_path': str(state)})
        game.held = set()
        game.press(set())
        outcome.append(info)
    print(label, {r: sum(o['result'] == r for o in outcome) for r in {o['result'] for o in outcome}}, flush=True)
    return outcome


def check_sweep(emulator, candidate, seed, output, step, run_names):
    results = {}
    work = Path(tempfile.mkdtemp(prefix='sweep-', dir=output))
    # 1-1: the timer set to 2 (units first, $2EDB-$2EDD), Ryu idle: a time-out
    # death, the respawn and its fades.
    with Game(emulator, work) as game:
        start_point(game, candidate, seed, enhanced=True)
        start_stage(game, 0)
        game.write(0xedb, bytes([2, 0, 0]))
        game.step(60)
        results['1-1 time-out death'] = sweep_frames(game, work, [()] * 420, '1-1 time-out death', step)
    # 5-4 idle: Ryu is killed and the game continues in 5-3.
    with Game(emulator, work) as game:
        start_point(game, candidate, seed, enhanced=True)
        start_stage(game, 15)
        game.step(530)
        results['5-4 idle death'] = sweep_frames(game, work, [()] * 200, '5-4 idle death', step)
    for name in run_names:
        run = json.loads((RUNS / f'{name}.json').read_text())
        inputs = [buttons for count, buttons in run['segments'] for _ in range(count)]
        with Game(emulator, work) as game:
            start_point(game, candidate, seed, enhanced=True)
            start_stage(game, run['stage'])
            changes, area = [], game.read(0xe60, 1)[0]
            # Find the area changes first (a pass without menus), then sweep.
            entered = work / 'entered.state'
            game.call('save_state_file', {'file_path': str(entered)})
            for frame, buttons in enumerate(inputs):
                game.press(set(buttons))
                game.step(1)
                current = game.read(0xe60, 1)[0]
                if current != area:
                    changes.append(frame)
                    area = current
            game.call('load_state_file', {'file_path': str(entered)})
            game.held = set()
            game.press(set())
            outcome, frame = [], 0
            for change in changes:
                start = max(frame, change - 5)
                for buttons in inputs[frame:start]:
                    game.press(set(buttons))
                    game.step(1)
                window = inputs[start:change + 45]
                for o in sweep_frames(game, work, window, f'{name} area change at {change}', step):
                    outcome.append(dict(o, frame=start + o['frame']))
                frame = start + len(window)
            results[f'{name} area changes'] = outcome
    shutil.rmtree(work, ignore_errors=True)
    return results


def check_level_select(emulator, candidate, output):
    results = []
    work = Path(tempfile.mkdtemp(prefix='menu-select-', dir=output))
    with Game(emulator, work) as game:
        game.call('load_media', {'file_path': str(Path(candidate).resolve())})
        game.call('debug_pause')
        to_title(game)
        to_gameplay(game)
        # A cold boot: the LANGUAGE row reads ENGLISH ($3227 = 1).
        press(game, 'select', after=8)
        ram = game.read(0, 0x2000)
        language = field_text(game, box_column(ram), 5).strip()
        results.append({'cold_boot_language': language, 'language_byte': ram[0x1227],
                        'ok': language == 'ENGLISH' and ram[0x1227] == 1, 'problems': []})
        print('cold boot language row', language, ram[0x1227], flush=True)
        press(game, 'select', after=30)
        for stage in range(22):
            entry = {'stage': stage, 'problems': []}
            game.call('save_state_file', {'file_path': str(work / 'select.state')})
            found = exact_cycle(game, work) if select_at_hook(game) else None
            game.call('load_state_file', {'file_path': str(work / 'select.state')})
            game.held = set()
            game.press(set())
            if found is None:
                entry['problems'].append('menu not available')
            elif not found['ok']:
                entry['problems'] += found['problems']
            if stage == 21:
                entry['ok'] = not entry['problems']
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
            if ram[0xe5f] != stage + 1 or ram[0xead] != 16 or ram[0x100] & 0x1f != 0:
                entry['problems'].append(f'after accept: stage {ram[0xe5f]}, health {ram[0xead]}, options {ram[0x100]:#04x}')
            if (game.read(0x7c0, 64, area=4) != SPACE_WORD * 32 or any(game.read(0x7aa0, 128, area=4))
                    or any(game.read(0x7b90, 32, area=4))):
                entry['problems'].append('band under the HUD or borrowed tiles not restored')
            hud = game.read(30 * 64, 64, area=4)
            if DECODE.get(hud[6]) != 'P' or vdc(game).get(5, 0) & 0x40 == 0:
                entry['problems'].append('HUD row 30 or sprites not as in play')
            entry['ok'] = not entry['problems']
            results.append(entry)
            game.step(60)
            print('level select', stage, 'ok' if entry['ok'] else entry['problems'], flush=True)
    shutil.rmtree(work, ignore_errors=True)
    return results


def menu_to(game, row, presses, accept=True):
    """Open the menu, go down `row` rows, press Right/Left (list), then Run
    (accept) or Select."""
    press(game, 'select', after=6)
    for _ in range(row):
        press(game, 'down')
    for button in presses:
        press(game, button)
    game.press({'run' if accept else 'select'})
    game.step(2)
    game.press(set())
    if accept:
        if not stop_at(game, FIRST_UPDATE, 600):
            raise RuntimeError('stage did not restart')
    else:
        game.step(40)
    game.step(90)
    return game.read(0, 0x2000)


def mode_expected(game, mode):
    """The VCE in gameplay for palette bits `mode`: GB DMG ($10) the GB
    table applied to the RAM palette ($2286) and to the border colour
    ($2281) at entry $100; HELL ($18) the HELL table applied to entries
    below its mapped_entries only (the HUD and sprite palettes and the
    border unchanged)."""
    ram = game.read(0x286, 1024)
    colours = [ram[2 * i] | ram[2 * i + 1] << 8 for i in range(512)]
    border = game.read(0x281, 2)
    colours[0x100] = border[0] | border[1] << 8
    if mode == 0x10:
        table = gb_dmg_table()
        words = [table[c & 0x1ff] for c in colours]
    else:
        table, mapped = hell_table(), load_hell()['mapped_entries']
        words = [table[c & 0x1ff] if i < mapped else c for i, c in enumerate(colours)]
    return b''.join(w.to_bytes(2, 'little') for w in words)


def to_level(game, candidate, seed):
    start_point(game, candidate, seed, enhanced=True)
    game.write(0x1227, b'\x01')                     # English, Enhanced's reset default
    start_stage(game, 0)
    game.step(30)


def check_options(emulator, candidate, seed, output):
    work = Path(tempfile.mkdtemp(prefix='menu-options-', dir=output))
    results = {}
    # PALETTE values in Left/Right order: ORIGINAL, GB_DMG, HELL.
    cases = [('parallax off', 1, ['right'], 0x01, None), ('no damage on', 2, ['right'], 0x02, None),
             ('nes firewheel on', 3, ['right'], 0x04, None), ('palette gb dmg', 4, ['right'], 0x10, None),
             ('palette hell', 4, ['right', 'right'], 0x18, None),
             ('palette wraps left to hell', 4, ['left'], 0x18, None),
             ('language japanese', 5, ['right'], 0x00, 0), ('language chinese', 5, ['left'], 0x00, 2)]
    for name, row, presses, bits, language in cases:
        with Game(emulator, work) as game:
            to_level(game, candidate, seed)
            ram = menu_to(game, row, presses)
            entry = {'options': f'{ram[0x100]:#04x}', 'language': ram[0x1227], 'stage': ram[0xe5f]}
            entry['ok'] = (ram[0x100] & 0x1f == bits and ram[0x1227] == (1 if language is None else language)
                           and ram[0xe5f] == 0)
            if bits in (0x10, 0x18):
                vce = game.read(0, 1024, area=8)
                expected = mode_expected(game, bits)
                entry['vce_is_mode_table'] = vce == expected
                entry['ok'] = entry['ok'] and vce == expected and ram[0x100] & 0x80 == 0x80
                (Path(output) / f'options-{name.replace(" ", "-")}.png').write_bytes(game.screenshot())
            results[name] = entry
            print('option', name, entry, flush=True)
    # The reference for ORIGINAL: the same Runs with nothing changed. Each
    # path through the mapped modes must end with exactly its VCE; each
    # accepted mapped mode on the way must show exactly its table.
    paths = {'original restored exactly (gb dmg, original)': [['right'], ['left']],
             'original restored exactly (hell, original)': [['left'], ['right']],
             'hell, gb dmg, original': [['left'], ['left'], ['left']],
             'gb dmg, hell, original': [['right'], ['right'], ['right']]}
    with Game(emulator, work) as game:
        to_level(game, candidate, seed)
        for _ in range(3):
            menu_to(game, 0, [])
        plain = game.read(0, 1024, area=8)
    for name, steps in paths.items():
        with Game(emulator, work) as game:
            to_level(game, candidate, seed)
            on_the_way = []
            for presses in steps:
                ram = menu_to(game, 4, presses)
                mode = ram[0x100] & 0x18
                if mode:
                    on_the_way.append((f'{mode:#04x}', game.read(0, 1024, area=8) == mode_expected(game, mode)))
            for _ in range(3 - len(steps)):
                menu_to(game, 0, [])
            back = game.read(0, 1024, area=8)
            ram = game.read(0, 0x2000)
        results[name] = {'ok': back == plain and ram[0x100] & 0x9f == 0 and all(ok for _, ok in on_the_way),
                         'mapped_modes_exact': on_the_way}
        print(name, results[name], flush=True)
    # Cancel after changing everything: nothing changes. Long comparisons
    # (LONG frames, the stage timer included) show whether the palette
    # module's state bits a cancelled preview may leave have any effect:
    # from Original (preview GB DMG, or HELL), from GB DMG (preview HELL)
    # and from HELL (preview ORIGINAL).
    everything = ['right', 'down', 'right', 'down', 'right', 'down', 'right', 'down', 'right', 'down', 'right']
    leftwards = everything[:8] + ['left'] + everything[9:]
    for name, first, actions in (('cancel after changing everything', None, everything),
                                 ('cancel after changing everything, palette hell', None, leftwards),
                                 ('cancel after changing everything, from GB DMG', ['right'], everything),
                                 ('cancel after changing everything, from HELL', ['left'], everything)):
        with Game(emulator, work) as game:
            to_level(game, candidate, seed)
            if first:
                menu_to(game, 4, first)
            before = game.read(0, 0x2000)
            found = exact_cycle(game, work, actions=actions, n=LONG) \
                if select_at_hook(game) else {'ok': False, 'problems': ['menu not available']}
            after = game.read(0, 0x2000)
            found['options_and_language_kept'] = after[0x100] & 0x1f == before[0x100] & 0x1f and after[0x1227] == 1
            found['ok'] = found['ok'] and found['options_and_language_kept']
            results[name] = found
            print(name, found, flush=True)
    shutil.rmtree(work, ignore_errors=True)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['emulator', 'original', 'candidate', 'output']:
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--every', type=int, default=300, help='frames between menu checks in a run')
    parser.add_argument('--only', choices=('runs', 'sweep', 'select', 'options'), action='append',
                        help='run these parts only (repeatable)')
    parser.add_argument('--parallax-off', action='store_true', help='runs: with $2100 bit 0 set')
    parser.add_argument('--preview', action='store_true', help='runs: change the palette too before cancelling')
    parser.add_argument('--same-music', action='store_true',
                        help='give the run without the menu the music driver state the menu left, and require '
                             'identical pictures in every frame')
    parser.add_argument('--sweep-step', type=int, default=1)
    parser.add_argument('--sweep-runs', default='1-1,2-2,5-3,6-3')
    parser.add_argument('--shots', type=Path, help='runs: keep the first open-window picture of each check here')
    args = parser.parse_args()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    parts = set(args.only or ('runs', 'sweep', 'select', 'options'))
    global SAME_MUSIC
    SAME_MUSIC = args.same_music
    if MENU_PREFIX != args.candidate.read_bytes()[MENU_ENTRY:MENU_ENTRY + len(MENU_PREFIX)]:
        raise SystemExit('The menu entry is not where this check expects it')
    report = {
        'rom_sha256': hashlib.sha256(args.candidate.read_bytes()).hexdigest(),
        'emulator_sha256': hashlib.sha256(args.emulator.read_bytes()).hexdigest(),
        'physical_hardware_tested': False, 'audio_compared': False, 'same_music': args.same_music,
    }
    seed = None
    if parts & {'runs', 'sweep', 'options'}:
        seed = make_seed(args.emulator, args.original, args.output / 'seed.state')
    oks = []
    if 'runs' in parts:
        actions = None
        if args.preview:
            actions = ['down', 'right', 'down', 'right', 'down', 'right', 'down', 'right', 'down', 'right', 'down']
        if args.shots:
            args.shots.mkdir(parents=True, exist_ok=True)
        report['runs'] = check_runs(args.emulator, args.candidate, seed, args.every, args.output,
                                    1 if args.parallax_off else 0, actions, args.shots)
        oks += [r['ok'] for r in report['runs'].values()]
    if 'sweep' in parts:
        report['sweep'] = check_sweep(args.emulator, args.candidate, seed, args.output, args.sweep_step,
                                      [n for n in args.sweep_runs.split(',') if n])
        oks += [o['result'] != 'opened, FAILED' for window in report['sweep'].values() for o in window]
    if 'select' in parts:
        report['level_select'] = check_level_select(args.emulator, args.candidate, args.output)
        oks += [e['ok'] for e in report['level_select']]
    if 'options' in parts:
        report['options'] = check_options(args.emulator, args.candidate, seed, args.output)
        oks += [e['ok'] for e in report['options'].values()]
    report['ok'] = all(oks)
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('menu check', 'passed' if report['ok'] else 'FAILED')
    raise SystemExit(0 if report['ok'] else 1)


if __name__ == '__main__':
    main()
