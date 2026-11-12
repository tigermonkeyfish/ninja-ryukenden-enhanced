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
        (the backup) and RAM except ALLOWED; then the game is compared with
        the same state run without the menu, both from the next vblank
        interrupt ($FCD7; the menu returns just after its last vblank,
        before the frame boundary, the run without it at the hook's raster
        position), for UPDATES frames at every frame's end VRAM (the backup buffer
        included: the game rewrote it), the sprite table, the palette and
        the PSG registers (not the emulator's waveform position; from the
        second frame: the sound held in the menu comes back with the
        driver's second tick, so frame 0 is reported apart), and at the
        next update boundary RAM except ALLOWED. Since 1.11-dev the menu
        holds the sound driver while it is open (src/options), so the
        interrupts after it take the time they take without it. Pictures
        that differ in a frame whose video state agrees are reported as
        raster timing (identical writes at other raster positions; with the
        sound held none are expected). With --same-music the run without
        the menu gets the music driver's state as the menu left it, and
        every picture must match. A frame whose video state differs only by
        the timer interrupt's phase (see compare_frames) is accepted but
        listed ('timer_phase_frames', the sweep's 'opened, timer phase only',
        the report's 'timer_phase_only'); --strict fails it. Sound-driver RAM that differs at the
        return is listed ('sound_ram_differs': zero page $8B, the driver's
        per-tick scratch, is cleared by the ticks in the menu). The stack's
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
        RAM palette, HELL the HELL table's for entries 0-239 (with 1-1's
        override of $094) and the RAM colours for the rest, SMS the SMS table's for the whole RAM palette;
        NES-A and NES-B: the restarted 1-1 holds that variant's NES colours
        (src/nes-palette) in the RAM palette, uploaded unmapped (the VCE
        equals the RAM palette). Paths through the palette values (each
        mode then ORIGINAL; every mode in Left order and in Right order; GB
        DMG and SMS straight after each other; NES modes between mapped
        ones), each accepted with Run, show each mapped mode's table and
        each NES mode's colours exactly (after an NES mode, the original
        colours back in the RAM palette) and end with the same VCE as a
        stage start that never left Original. Cancel after changing
        everything (from Original with NES-A, NES-B, GB DMG, HELL or SMS
        highlighted, from GB DMG, HELL, SMS, NES-A and NES-B previewing
        other values) leaves the options and $3227 unchanged and is
        compared with the run without the menu for LONG frames.
select  also checks, after a cold boot, that the LANGUAGE row reads
        ENGLISH with $3227 = 1.
reset   The reset row (RESET OPTIONS, after LANGUAGE), from 1-1: from
        settings accepted with Run (each option changed, several at once,
        SMS and APOCALYPSE (HELL in the source), Japanese and Chinese), the
        reset row with I (or II) shows every default in the window, previews
        Original's colours, and Run gives $2100 = 0 (bit 7 clear), $3227 = 1
        (the cold-boot defaults), the same stage ($2E5F) and the VCE of a
        stage start that never left Original; a STAGE changed before or
        after the reset is the stage that starts; an option changed after
        the reset is kept; Up from STAGE wraps to the reset row and Down from
        it to STAGE; Left/Right there do nothing; its field blinks. Select
        after a reset is exact_cycle's cancel (nothing changes; compared
        with the run without the menu for LONG frames), the language kept.
        Pictures of the open window (APOCALYPSE, the reset row) are kept in
        the output folder.

Writes a JSON report to the output folder; captures stay private there.
"""
import argparse
import re
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile

from comparison_video import Game, make_seed, start_point, start_stage
from guide_screenshots import to_gameplay, to_title
from menu_text import BOX_ROWS, BOX_WIDTH, CODES, layout
from palette_tables import gb_dmg_table, hell_stage_table, load_hell, sms_table

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / 'research/comparison-runs'
DECODE = {code: char for char, code in CODES.items()}
HOOK_AFTER_DRAW = '1f73'     # $FF73: Select hook, after the pending-draw call
HOOK_RETURN = '23f6'         # bank 1 $83F6: main loop, after the Select hook
FIRST_UPDATE = '2457'        # bank 1 $8457: gameplay loop (a stage's first update)
VBLANK_ENTRY = '1cd7'        # $FCD7: the VDC interrupt's entry (vblank: the sound driver's tick at $FD16)
MENU_ENTRY = 0x46 * 0x2000 + 0x400                 # bank $46 $4400
MENU_PREFIX = bytes.fromhex('adab2ec90af00dadad2ef008ad4d2e0d4e2ef003a9ff60')   # the refusals
MENU_OPEN = f'{MENU_ENTRY + len(MENU_PREFIX):x}'   # after it: the menu opens
MENU_OPEN_PC = f'{0x4400 + len(MENU_PREFIX):04X}'
CPU = {HOOK_AFTER_DRAW: 'FF73', HOOK_RETURN: '83F6', FIRST_UPDATE: '8457', MENU_OPEN: MENU_OPEN_PC,
       VBLANK_ENTRY: 'FCD7'}
SPACE_WORD = bytes.fromhex('9ff7')
SOURCE = (ROOT / 'src/options/main.asm').read_text()
BOX_TOP = int(re.search(r'^BOX_TOP = (\d+)', SOURCE, re.M)[1])
BOX_LEFT = int(re.search(r'^BOX_LEFT = (\d+)', SOURCE, re.M)[1])
VERSION = (ROOT / 'VERSION').read_text().strip()
MENU = layout((ROOT / 'src/options/menu.txt').read_text(), VERSION)
HUD_WORDS = (28 * 64, 31 * 64 - 1)                 # BAT rows 28-30
UPDATES = 20
SAME_MUSIC = False          # --same-music: see exact_cycle
STRICT = False              # --strict: timer-phase frames (compare_frames) fail too
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


STATE_IN_2104 = True        # main(): False for builds before the SMS palette
STATUS_IN_2105 = True       # main(): False for builds before the saved settings (src/bram)


def stack_fill():
    """The first byte of the watched stack margin ($2104; $2105 once $2104
    holds the palette module's state; $2106 once $2105 holds the save
    status), offset from $2000."""
    return 0x106 if STATUS_IN_2105 else 0x105 if STATE_IN_2104 else 0x104


def module_state_only(i, a, b):
    """Before the SMS palette (1.11-dev), $2100 differing only in bits 5-6:
    the palette module's left-over and busy-history state, which a cancelled
    palette preview leaves as the restoring upload set it (the menu never
    writes bits 5-7; in Original mode the module neither reads nor writes
    bits 5-6). Since then that state is in $2104 (with the stack's bytes in
    `allowed`) and $2100 is options only: no difference is the module's."""
    return not STATE_IN_2104 and i == 0x100 and not (a ^ b) & ~0x60


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


def expected_window(status):
    """menu.txt's window with the text of save status `status` in its field
    (an unknown status shows the first text, as the menu does)."""
    window = bytearray(MENU['window'])
    row, column, width = MENU['status']
    at = row * BOX_WIDTH + column
    window[at:at + width] = MENU['status_texts'][status if status < len(MENU['status_texts']) else 0]
    return window


def window_problems(game, c0):
    """Differences between the BAT window and menu.txt (value fields and the
    reset field: any font cell; the save status field: the text of the
    status in $2105)."""
    fields = {(r, c + k) for r, c, w in MENU['fields'] + [MENU['reset']] for k in range(w)}
    window = expected_window(game.read(0x105, 1)[0])
    problems = []
    for j, row in enumerate(window_words(game, c0)):
        for i, word in enumerate(row):
            expected = window[j * BOX_WIDTH + i]
            if word[1] != 0xf7 or ((j, i) not in fields and word[0] != expected):
                problems.append(f'window cell {j},{i} = {word.hex()}')
    return problems[:8]


def field_text(game, c0, field):
    row, col, width = MENU['fields'][field]
    words = window_words(game, c0)[row][col:col + width]
    return ''.join(DECODE.get(w[0], '?') if w[1] == 0xf7 else '#' for w in words)


def reset_field_text(game, c0):
    row, col, width = MENU['reset']
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


IRQ_EVENT = re.compile(r'@(\d+)\s.*?\[CPU\]\s+IRQ\s+(\S+)')


def interrupts(game, pos):
    """The CPU's interrupt entries logged since trace position `pos`:
    (new position, [(kind, master clock)]); kind IRQ1 (VDC) or TIQ (timer)."""
    end = game.call('get_trace_log', {'count': 1}).get('total_logged', 0)
    events = []
    while pos < end:
        chunk = game.call('get_trace_log', {'start': pos, 'count': 1000})
        lines = chunk.get('entries') or chunk.get('lines') or []
        if not lines:
            break
        for line in lines:
            m = IRQ_EVENT.search(line if isinstance(line, str) else line.get('text', ''))
            if m:
                events.append((m.group(2), int(m.group(1))))
        pos += len(lines)
    return pos, events


def frames(game, count, state_dir):
    """From a breakpoint stop: normalize (save and reload the state, so frame
    steps have a defined length), then `count` whole frames; for each, the
    completed frame's picture, the video state at its end (VRAM, sprite
    table, palette), the PSG registers and the CPU's interrupt entries in
    the frame (master clocks from the frame's VDC interrupt). A screenshot
    taken at a breakpoint can show a frame in progress, so pictures are only
    taken after whole frame steps."""
    state = Path(state_dir) / 'normal.state'
    game.call('save_state_file', {'file_path': str(state)})
    game.call('load_state_file', {'file_path': str(state)})
    game.call('set_trace_log', {'enabled': True, 'output': 'memory', 'memory_size': '1M', 'filters': ['cpu.irqs']})
    pos = game.call('get_trace_log', {'count': 1}).get('total_logged', 0)
    shots = []
    for _ in range(count):
        game.checked_step(1)
        pos, events = interrupts(game, pos)
        vdc = [t for kind, t in events if kind == 'IRQ1']
        t0 = vdc[-1] if vdc else 0
        video = hashlib.sha256()
        for area, size in ((4, 0x10000), (6, 512), (8, 1024)):
            video.update(game.read(0, size, area=area))
        shots.append((hashlib.sha256(game.screenshot()).hexdigest()[:16], video.hexdigest()[:16], psg(game),
                      tuple((kind, t - t0) for kind, t in events)))
    game.call('set_trace_log', {'enabled': False})
    return shots


def psg(game):
    """The PSG's registers (per channel enable, amplitude, frequency,
    balance, noise; the main amplitude and LFO), without the emulator's
    waveform playback position (an oscillator phase, not a register)."""
    st = game.call('get_psg_status')
    return tuple((c['enabled'], c['amplitude'], c['frequency'], c['vol_left'], c['vol_right'], c['noise'], c['dda'])
                 for c in st['channels']) + (st['main_amplitude'], st['lfo_control'], st['lfo_frequency'])


def compare_frames(found, menu_shots, reference_shots):
    """Every frame must end with the same VRAM, sprite table and palette.
    A picture may differ only in a frame whose video state agrees: the same
    writes landed at another raster position (the interrupts take different
    time after the menu: the music driver played on), which is reported."""
    video = [k for k, (a, b) in enumerate(zip(menu_shots, reference_shots)) if a[1] != b[1]]
    # The timer interrupt (an acknowledge only, $FCD3; reload $74: a period
    # 143 CPU cycles longer than a frame) runs on through the menu, so after
    # it its phase against the frame differs, which the menu cannot restore.
    # It moves the main loop by its own length; a frame end that catches
    # work spanning frames (a stage load, an area change's redraw) may then
    # see one write more or less. Such a frame is reported apart when the
    # VDC interrupts came at the same times in every frame of both runs, the
    # timer's did not, the sound driver's RAM was the same at the return
    # ($8B apart: the held sound; so its work in every interrupt was the
    # same), its picture is the same and the video state agrees again at the
    # end of the next frame. found['vdc_interrupts_agree'] and
    # found['timer_moved'] report the two conditions.
    vdc = lambda shot: tuple(t for kind, t in shot[3] if kind == 'IRQ1')
    timer = lambda shot: tuple(t for kind, t in shot[3] if kind != 'IRQ1')
    # (the CPU takes an interrupt at the end of its current instruction, so
    # the entries may lie a few cycles apart: a quarter line is allowed)
    same_vdc = all(len(vdc(a)) == len(vdc(b)) and all(abs(x - y) <= 1365 // 4 for x, y in zip(vdc(a), vdc(b)))
                   for a, b in zip(menu_shots, reference_shots))
    timer_moved = any(timer(a) != timer(b) for a, b in zip(menu_shots, reference_shots))
    found['vdc_interrupts_agree'], found['timer_moved'] = same_vdc, timer_moved
    driver_held = set(found.get('sound_ram_differs', [])) <= {'$208b'}
    found['timer_phase_frames'] = [k for k in video if same_vdc and timer_moved and driver_held and k + 1 < len(menu_shots)
                                   and menu_shots[k][0] == reference_shots[k][0] and k + 1 not in video]
    video = [k for k in video if k not in found['timer_phase_frames']]
    if STRICT and found['timer_phase_frames']:
        found['problems'].append(f'video state differs (timer phase only) at the end of frames '
                                 f'{found["timer_phase_frames"]}')
    if video or len(menu_shots) != len(reference_shots):
        found['problems'].append(f'video state differs at the end of frames {video[:20]}')
    sound = [k for k, (a, b) in enumerate(zip(menu_shots, reference_shots)) if a[2] != b[2]]
    # The sound held in the menu comes back with the driver's second tick
    # after the return (its first re-enables the volumes the held ticks
    # zeroed): frame 0 may differ; from frame 1 on every register must agree.
    found['sound_resume_frames'] = [k for k in sound if k < 1]
    if [k for k in sound if k >= 1]:
        found['problems'].append(f'PSG registers differ at the end of frames {[k for k in sound if k >= 1][:20]}')
    found['raster_timing_frames'] = [k for k, (a, b) in enumerate(zip(menu_shots, reference_shots))
                                     if a[0] != b[0] and a[1] == b[1]]
    if SAME_MUSIC and found['raster_timing_frames']:
        found['problems'].append(f'pictures differ with the same music state in frames {found["raster_timing_frames"]}')


def exact_cycle(game, state_dir, actions=None, n=UPDATES, shots=None, blink=True):
    """At the hook with Select newly pressed (select_at_hook). Returns None if
    the menu is refused here, else findings ('ok' False on any problem)."""
    sp = int(game.call('get_huc6280_status')['SP'], 16) - 0x2000   # $100 + S
    game.write(stack_fill(), b'\xa5' * (sp - stack_fill() + 1))   # stack low-water mark
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
    low = next((i for i in range(stack_fill(), sp + 1) if after['ram'][i] != 0xa5), None)
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
    # Frames are compared from the next vblank interrupt in both runs (the
    # one that ends the frame the hook was in; the sound driver's next tick):
    # the menu returns just after its last vblank, before the emulator's
    # frame boundary, the run without it at the hook's raster position, so
    # frame steps from the return would be one frame apart.
    if run_until(game, [VBLANK_ENTRY]) != CPU[VBLANK_ENTRY]:
        found['problems'].append('no vblank after the menu returned')
    menu_vblank = snapshot(game)
    menu_vblank['psg'] = psg(game)
    menu_vblank['cpu'] = game.call('get_huc6280_status')
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
    found['sound_ram_differs'] = [f'${0x2000 + i:04x}' for i, (a, b) in enumerate(zip(reference, after['ram']))
                                  if a != b and (0x080 <= i <= 0x08f or 0x1800 <= i <= 0x1bff)]
    if run_until(game, [VBLANK_ENTRY]) != CPU[VBLANK_ENTRY]:
        found['problems'].append('reference: no vblank after the hook')
    reference_vblank = snapshot(game)
    reference_vblank['psg'] = psg(game)
    reference_vblank['cpu'] = game.call('get_huc6280_status')
    # Where each run was when that vblank came (diagnostic only: the run
    # without the menu may still be in the hook's update there, the menu's
    # run already waits; the state is compared at the frame ends that follow).
    found['vblank_interrupted'] = []
    for snap in (menu_vblank, reference_vblank):
        s0 = int(snap['cpu']['SP'], 16) - 0x2000
        found['vblank_interrupted'].append(f"${snap['ram'][s0 + 2] | snap['ram'][s0 + 3] << 8:04x}")
    found['psg_held_at_first_vblank'] = menu_vblank['psg'] != reference_vblank['psg']
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
            'timer_phase': {c['frame']: c['timer_phase_frames'] for c in checks if c.get('timer_phase_frames')},
            'problems': [c for c in checks if not c['ok']]}
        print(run['name'], results[run['name']]['menus_checked'], 'menus',
              results[run['name']]['wrapping_windows'], 'wrapping, stack low', results[run['name']]['stack_low'],
              'timer phase only', results[run['name']]['timer_phase'],
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
            info['result'] = 'refused' if found is None else ('opened, FAILED' if not found['ok'] else
                                                              'opened, timer phase only' if found['timer_phase_frames']
                                                              else 'opened, exact')
            if found and not found['ok']:
                info['problems'] = found['problems']
            if found and found['timer_phase_frames']:
                info['timer_phase_frames'] = found['timer_phase_frames']
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
            if found and found.get('timer_phase_frames'):
                entry['timer_phase_frames'] = found['timer_phase_frames']
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
            if ram[0xe5f] != stage + 1 or ram[0xead] != 16 or ram[0x100] & 0x3f != 0:
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
    border unchanged), with the visible stage's override ($2E5F: 1-1's
    colour $094); SMS ($38) the SMS table, as GB DMG."""
    ram = game.read(0x286, 1024)
    colours = [ram[2 * i] | ram[2 * i + 1] << 8 for i in range(512)]
    border = game.read(0x281, 2)
    colours[0x100] = border[0] | border[1] << 8
    if mode in (0x10, 0x38):
        table = gb_dmg_table() if mode == 0x10 else sms_table()
        words = [table[c & 0x1ff] for c in colours]
    else:
        stage = game.read(0xe5f, 1)[0]              # $2E5F: HELL's per-stage override
        table, mapped = hell_stage_table(stage), load_hell()['mapped_entries']
        words = [table[c & 0x1ff] if i < mapped else c for i, c in enumerate(colours)]
    return b''.join(w.to_bytes(2, 'little') for w in words)


def to_level(game, candidate, seed):
    start_point(game, candidate, seed, enhanced=True)
    game.write(0x1227, b'\x01')                     # English, Enhanced's reset default
    start_stage(game, 0)
    game.step(30)


def nes_data(variant):
    """The NES palette data of `variant` ('a' NES-A, 'b' NES-B, the re-lit
    version of the same role data: scripts/nes_palette.py)."""
    import nes_palette as NP
    data = NP.load()
    return NP.relit(data) if variant == 'b' else data


def nes_expected(original, variant='a'):
    """1-1 in NES mode (src/nes-palette, `variant` 'a' or 'b'): {RAM palette
    index: colour} for the NES copy of set 1 (rows 0 and 2-14; row 1 is the
    Enhanced merged palette, row 15 the HUD's), the NES HUD entries
    $F1-$F7 and Ryu's sprite row 0; entries the game animates in 1-1 (r9:7,
    r9:d, r11:f) left out. Returns (NES colours, original colours) by index;
    only entries whose NES colour differs from the original are in the
    second."""
    import nes_palette as NP
    data = nes_data(variant)
    lay = NP.layout(data)
    set1 = next(d for d in data['stages'] if d['set'] == 1)
    orig = {i: int(e['pce'], 16) for i, e in enumerate(set1['entries'])}
    want = {i: c for i, c in enumerate(lay['sets'][1]) if i < 240 and not 16 <= i < 32 and (i % 16 or i == 0)}
    for i in (0x97, 0x9d, 0xbf):
        want.pop(i, None)
    want.update({0xf1 + k: c for k, c in enumerate(lay['hud'])})
    orig.update({0xf1 + k: int(e['pce'], 16) for k, e in enumerate(data['shared']['hud']['entries'])})
    want.update({256 + k: c for k, c in enumerate(dict(lay['sprites'])[96]) if k})
    orig.update({256 + e['entry']: int(e['pce'], 16) for e in data['shared']['sprites'][0]['entries']})
    if original is not None:
        m, n = NP.enhanced_palettes('stage11', original, variant=variant)['extra_palette_nes']
        want.update({16 + k: n[k] for k in range(1, 16)})
        orig.update({16 + k: m[k] for k in range(1, 16)})
    return want, {i: orig[i] for i in want if orig[i] != want[i]}


def mode_ok(game, ram, mode, nes):
    """After a Run into palette bits `mode`: a mapped mode's VCE is exactly
    its table over the RAM palette (mode_expected), with $2104 bit 7 set; an
    NES mode's RAM palette holds that variant's NES colours (nes: {'a': ...,
    'b': ...} from nes_expected) and the VCE equals the RAM palette; in a
    mapped mode the RAM palette holds the original colours wherever an NES
    variant differs from them (nothing of an earlier NES mode is left).
    $2100 bit 7 is set exactly with SMS."""
    pal = palette_words(ram)
    vce = game.read(0, 1024, area=8)
    if ram[0x100] & 0x80 != (0x80 if mode == 0x38 else 0):
        return False
    if mode & 0x18 == 0x08:
        want, _ = nes[('a', 'b')[mode >> 5 & 1]]
        return all(pal[i] == c for i, c in want.items()) and vce[:512] == ram[0x286:0x486]
    originals = {i: c for v in nes.values() for i, c in v[1].items()}
    pal_ok = all(pal[i] == originals[i] for i in originals)
    return pal_ok and vce == mode_expected(game, mode) and ram[0x104] & 0x80 == 0x80


def palette_words(ram):
    return [ram[0x286 + 2 * i] | ram[0x287 + 2 * i] << 8 for i in range(512)]


def check_options(emulator, candidate, seed, output, original=None):
    work = Path(tempfile.mkdtemp(prefix='menu-options-', dir=output))
    results = {}
    nes = {variant: nes_expected(original, variant) for variant in ('a', 'b')}
    # PALETTE values in Left/Right order: ORIGINAL, NES-A, NES-B, GB_DMG,
    # HELL, SMS.
    cases = [('parallax off', 1, ['right'], 0x01, None), ('no damage on', 2, ['right'], 0x02, None),
             ('nes firewheel on', 3, ['right'], 0x04, None), ('palette nes-a', 4, ['right'], 0x08, None),
             ('palette nes-b', 4, ['right'] * 2, 0x28, None), ('palette gb dmg', 4, ['right'] * 3, 0x10, None),
             ('palette hell', 4, ['right'] * 4, 0x18, None), ('palette sms', 4, ['right'] * 5, 0x38, None),
             ('palette wraps left to sms', 4, ['left'], 0x38, None),
             ('palette nes-a by left', 4, ['left'] * 5, 0x08, None),
             ('language japanese', 5, ['right'], 0x00, 0), ('language chinese', 5, ['left'], 0x00, 2)]
    for name, row, presses, bits, language in cases:
        with Game(emulator, work) as game:
            to_level(game, candidate, seed)
            ram = menu_to(game, row, presses)
            entry = {'options': f'{ram[0x100]:#04x}', 'language': ram[0x1227], 'stage': ram[0xe5f]}
            entry['ok'] = (ram[0x100] & 0x3f == bits and ram[0x1227] == (1 if language is None else language)
                           and ram[0xe5f] == 0)
            if row == 4:
                entry['mode_exact'] = mode_ok(game, ram, bits, nes)
                entry['ok'] = entry['ok'] and entry['mode_exact']
                if bits & 0x18 == 0x08:
                    pal = palette_words(ram)
                    entry['nes_colours_wrong'] = [i for i, c in nes[('a', 'b')[bits >> 5 & 1]][0].items()
                                                  if pal[i] != c][:10]
                (Path(output) / f'options-{name.replace(" ", "-")}.png').write_bytes(game.screenshot())
            results[name] = entry
            print('option', name, entry, flush=True)
    # The reference for ORIGINAL: the same Runs with nothing changed. Each
    # path must end with exactly its VCE; each accepted mode on the way must
    # show exactly its colours (mode_ok).
    R, L = 'right', 'left'
    paths = {'original restored exactly (nes-a, original)': [[R], [L]],
             'original restored exactly (nes-b, original)': [[R] * 2, [L] * 2],
             'original restored exactly (gb dmg, original)': [[R] * 3, [L] * 3],
             'original restored exactly (hell, original)': [[R] * 4, [L] * 4],
             'original restored exactly (sms, original)': [[L], [R]],
             'sms, hell, gb dmg, nes-b, nes-a, original': [[L]] * 6,
             'nes-a, nes-b, gb dmg, hell, sms, original': [[R]] * 6,
             'sms, gb dmg, original': [[L], [L, L], [L] * 3],
             'gb dmg, sms, original': [[R] * 3, [R, R], [R]],
             'nes-a, gb dmg, original': [[R], [R, R], [L] * 3],
             'sms, nes-b, hell, nes-a, original': [[L], [L] * 3, [R, R], [L] * 3, [L]],
             'nes-b, sms, nes-a, original': [[R, R], [L] * 3, [R, R], [L]]}
    runs = max(len(steps) for steps in paths.values())
    with Game(emulator, work) as game:
        to_level(game, candidate, seed)
        for _ in range(runs):
            menu_to(game, 0, [])
        plain = game.read(0, 1024, area=8)
    for name, steps in paths.items():
        with Game(emulator, work) as game:
            to_level(game, candidate, seed)
            on_the_way = []
            for presses in steps:
                ram = menu_to(game, 4, presses)
                mode = ram[0x100] & 0x38
                if mode:
                    on_the_way.append((f'{mode:#04x}', mode_ok(game, ram, mode, nes)))
            for _ in range(runs - len(steps)):
                menu_to(game, 0, [])
            back = game.read(0, 1024, area=8)
            ram = game.read(0, 0x2000)
        results[name] = {'ok': back == plain and ram[0x100] & 0xbf == 0 and ram[0x104] & 0x80 == 0
                         and all(ok for _, ok in on_the_way) and len(on_the_way) == len(steps) - 1,
                         'modes_exact': on_the_way}
        print(name, results[name], flush=True)
    # Cancel after changing everything: nothing changes. Long comparisons
    # (LONG frames, the stage timer included) show whether the palette
    # module's state a cancelled preview may leave has any effect. The
    # PALETTE row is stepped by `steps` from the opening mode: an NES value
    # on the way keeps the colours; opened in an NES mode, the RAM palette
    # holds NES colours, which ORIGINAL shows unmapped and the mapped modes map.
    def everything(steps):
        return [R, 'down', R, 'down', R, 'down', R, 'down'] + steps + ['down', R]
    for name, first, actions in (
            ('cancel after changing everything, palette nes-a', None, everything([R])),
            ('cancel after changing everything, palette nes-b', None, everything([R] * 2)),
            ('cancel after changing everything, palette gb dmg', None, everything([R] * 3)),
            ('cancel after changing everything, palette hell', None, everything([R] * 4)),
            ('cancel after changing everything, palette sms', None, everything([L])),
            ('cancel after changing everything, from GB DMG to HELL', [R] * 3, everything([R])),
            ('cancel after changing everything, from GB DMG to NES-B', [R] * 3, everything([L])),
            ('cancel after changing everything, from HELL to SMS', [R] * 4, everything([R])),
            ('cancel after changing everything, from SMS to ORIGINAL', [L], everything([R])),
            ('cancel after changing everything, from SMS to GB DMG', [L], everything([L, L])),
            ('cancel after changing everything, from NES-A via NES-B to HELL', [R], everything([R] * 3)),
            ('cancel after changing everything, from NES-B via NES-A to SMS', [R] * 2, everything([L] * 3))):
        with Game(emulator, work) as game:
            to_level(game, candidate, seed)
            if first:
                menu_to(game, 4, first)
            before = game.read(0, 0x2000)
            found = exact_cycle(game, work, actions=actions, n=LONG) \
                if select_at_hook(game) else {'ok': False, 'problems': ['menu not available']}
            after = game.read(0, 0x2000)
            found['options_and_language_kept'] = after[0x100] & 0xbf == before[0x100] & 0xbf and after[0x1227] == 1
            found['ok'] = found['ok'] and found['options_and_language_kept']
            results[name] = found
            print(name, found, flush=True)
    shutil.rmtree(work, ignore_errors=True)
    return results


RESET_ROW = len(MENU['fields'])     # rows: STAGE, the options, then the reset row
DEFAULT_OPTIONS, DEFAULT_LANGUAGE = 0x00, 1     # a cold boot without saved settings (src/bram)


def default_texts():
    """The option fields' texts for the defaults (each @ line's first
    value), as the window shows them."""
    return [''.join(DECODE[c] for c in entries[0][1]) for _, entries in MENU['choices']]


def option_texts(game):
    c0 = box_column(game.read(0, 0x2000))
    return [field_text(game, c0, k) for k in range(1, len(MENU['fields']))]


def open_menu(game):
    press(game, 'select', after=6)


def finish(game, accept=True):
    """Run (to the restarted stage's first update) or Select, then settle
    as menu_to does."""
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


def check_reset(emulator, candidate, seed, output):
    """The reset row (see the module's description, part `reset`)."""
    work = Path(tempfile.mkdtemp(prefix='menu-reset-', dir=output))
    results = {}
    R, L, D, U = 'right', 'left', 'down', 'up'
    defaults = default_texts()
    # The VCE of 1-1 after two Runs that never left Original: what every
    # reset-and-Run case below must end with (its first Run sets the
    # options it starts from, its second is the reset's).
    with Game(emulator, work) as game:
        to_level(game, candidate, seed)
        for _ in range(2):
            menu_to(game, 0, [])
        plain = game.read(0, 1024, area=8)
    # The settings before the reset, set with one Run: (row, presses) steps.
    everything_sms = [(1, [R]), (1, [R]), (1, [R]), (1, [L]), (1, [L])]     # parallax off, No Damage,
    everything_apocalypse = [(1, [R]), (1, [R]), (1, [R]), (1, [R] * 4), (1, [R])]  # NES Firewheel; SMS/APOCALYPSE;
    #                                                                       Chinese / Japanese
    starts = [('parallax off', [(1, [R])], 0x01, 1), ('no damage on', [(2, [R])], 0x02, 1),
              ('nes firewheel on', [(3, [R])], 0x04, 1), ('palette nes-a', [(4, [R])], 0x08, 1),
              ('palette nes-b', [(4, [R] * 2)], 0x28, 1), ('palette gb dmg', [(4, [R] * 3)], 0x10, 1),
              ('palette apocalypse', [(4, [R] * 4)], 0x18, 1), ('palette sms', [(4, [L])], 0x38, 1),
              ('language japanese', [(5, [R])], 0x00, 0), ('language chinese', [(5, [L])], 0x00, 2),
              ('everything, sms, chinese', everything_sms, 0x3f, 2),
              ('everything, apocalypse, japanese', everything_apocalypse, 0x1f, 0),
              ('nothing changed', [], 0x00, 1)]

    def set_up(game, steps):
        """Open the menu, make the steps (each `row` Downs from the row
        before, then presses), Run; the options and language it set."""
        open_menu(game)
        for down, presses in steps:
            for _ in range(down):
                press(game, D)
            for button in presses:
                press(game, button)
        ram = finish(game)
        return ram[0x100], ram[0x1227]

    def reset_case(name, steps, bits, language, way, button='I', expect_stage=0, expect_options=DEFAULT_OPTIONS,
                   expect_texts=None):
        with Game(emulator, work) as game:
            to_level(game, candidate, seed)
            entry = {'problems': []}
            if steps:
                options, lang = set_up(game, steps)
                entry['before'] = {'options': f'{options:#04x}', 'language': lang}
                if options & 0x3f != bits or lang != language:
                    entry['problems'].append('the starting settings were not set')
            else:
                menu_to(game, 0, [])
            stage = game.read(0xe5f, 1)[0]
            open_menu(game)
            for button_name in way[0]:                  # before the reset (e.g. STAGE)
                press(game, button_name)
            press(game, button)
            game.step(40)                               # the live preview's upload
            ram = game.read(0, 0x2000)
            c0 = box_column(ram)
            entry['after_reset_texts'] = option_texts(game)
            entry['reset_field'] = reset_field_text(game, c0)
            if expect_texts is None and entry['after_reset_texts'] != defaults:
                entry['problems'].append(f'window after the reset: {entry["after_reset_texts"]}')
            vce = game.read(0, 1024, area=8)
            entry['preview_original'] = ram[0x100] & 0xb8 == 0 and vce[:512] == ram[0x286:0x486]
            if not entry['preview_original']:
                entry['problems'].append('the reset did not preview Original')
            for button_name in way[1]:                  # after it
                press(game, button_name)
            if expect_texts is not None:
                entry['texts_before_run'] = option_texts(game)
                if entry['texts_before_run'] != expect_texts:
                    entry['problems'].append(f'window before Run: {entry["texts_before_run"]}')
            ram = finish(game)
            entry.update({'options': f'{ram[0x100]:#04x}', 'language': ram[0x1227], 'stage_before': stage,
                          'stage': ram[0xe5f]})
            if ram[0x100] != expect_options or ram[0x1227] != DEFAULT_LANGUAGE:
                entry['problems'].append('options or language not the defaults after Run')
            if ram[0xe5f] != expect_stage:
                entry['problems'].append(f'stage {ram[0xe5f]}, expected {expect_stage}')
            if ram[0xead] != 16:
                entry['problems'].append('health not refilled')
            if expect_options == DEFAULT_OPTIONS and expect_stage == 0:
                entry['vce_as_never_changed'] = game.read(0, 1024, area=8) == plain
                if not entry['vce_as_never_changed']:
                    entry['problems'].append('VCE differs from a stage start that never left Original')
            entry['ok'] = not entry['problems']
            return entry

    to_reset = [D] * RESET_ROW
    for name, steps, bits, language in starts:
        case = f'reset and run, from {name}'
        results[case] = reset_case(case, steps, bits, language, (to_reset, []))
        print(case, results[case], flush=True)
    for case, steps, bits, language, way, kwargs in (
            ('reset with II and run, from everything, sms, chinese', everything_sms, 0x3f, 2, (to_reset, []),
             {'button': 'II'}),
            ('up from stage wraps to the reset row, from palette apocalypse', [(4, [R] * 4)], 0x18, 1, ([U], []), {}),
            ('stage changed before the reset is kept (2-1), from everything, sms, chinese', everything_sms, 0x3f, 2,
             ([R, R] + to_reset, []), {'expect_stage': 2}),
            ('stage changed after the reset is kept (1-2, down wraps to stage), from palette apocalypse',
             [(4, [R] * 4)], 0x18, 1, (to_reset, [D, R]), {'expect_stage': 1}),
            ('an option changed after the reset is kept (gb dmg), from everything, apocalypse, japanese',
             everything_apocalypse, 0x1f, 0, (to_reset, [U, U, R, R, R]),
             {'expect_options': 0x10, 'expect_texts': defaults[:3] + ['GB DMG    '] + defaults[4:]})):
        results[case] = reset_case(case, steps, bits, language, way, **kwargs)
        print(case, results[case], flush=True)
    # Left and Right on the reset row change nothing; Run then keeps SMS.
    with Game(emulator, work) as game:
        to_level(game, candidate, seed)
        set_up(game, [(4, [L])])                        # SMS
        open_menu(game)
        for button in to_reset + [R, L, R, R, L]:
            press(game, button)
        entry = {'problems': [], 'texts': option_texts(game)}
        if entry['texts'] != defaults[:3] + ['SMS       '] + defaults[4:]:
            entry['problems'].append('Left/Right on the reset row changed the window')
        ram = finish(game)
        entry.update({'options': f'{ram[0x100]:#04x}', 'language': ram[0x1227], 'stage': ram[0xe5f]})
        if ram[0x100] != 0xb8 or ram[0x1227] != 1 or ram[0xe5f] != 0:
            entry['problems'].append('settings changed')
        entry['ok'] = not entry['problems']
        results['left and right on the reset row do nothing, from palette sms'] = entry
        print('left and right on the reset row', entry, flush=True)
    # The reset field blinks while selected, and pictures of the window.
    with Game(emulator, work) as game:
        to_level(game, candidate, seed)
        set_up(game, [(4, [R] * 4)])                    # APOCALYPSE
        open_menu(game)
        c0 = box_column(game.read(0, 0x2000))
        entry = {'problems': [], 'palette_text': field_text(game, c0, 4), 'reset_text': reset_field_text(game, c0)}
        (Path(output) / 'reset-menu-apocalypse.png').write_bytes(game.screenshot())
        for _ in range(4):
            press(game, D)
        seen, shots = set(), 0
        for _ in range(40):
            game.step(1)
            text = field_text(game, c0, 4)
            seen.add(text)
            if text.strip() and shots == 0:
                (Path(output) / 'reset-menu-apocalypse-selected.png').write_bytes(game.screenshot())
                shots += 1
        entry['palette_row_seen'] = sorted(seen)
        press(game, D, after=0)
        press(game, D, after=0)
        seen = set()
        for _ in range(40):
            game.step(1)
            text = reset_field_text(game, c0)
            if text.strip() and 'shown' not in entry:
                (Path(output) / 'reset-menu-reset-row-selected.png').write_bytes(game.screenshot())
                entry['shown'] = True
            seen.add(text)
        entry['reset_row_seen'] = sorted(seen)
        want_reset = ''.join(DECODE[c] for c in MENU['reset_text'])
        if entry['palette_text'] != 'APOCALYPSE' or entry['reset_text'] != want_reset:
            entry['problems'].append('window texts')
        if set(entry['palette_row_seen']) != {'APOCALYPSE', ' ' * 10}:
            entry['problems'].append('PALETTE APOCALYPSE does not blink')
        if set(entry['reset_row_seen']) != {want_reset, ' ' * len(want_reset)}:
            entry['problems'].append('the reset field does not blink')
        entry['problems'] += window_problems(game, c0)
        finish(game, accept=False)
        entry['ok'] = not entry['problems']
        results['window: apocalypse and the blinking reset field'] = entry
        print('window', entry, flush=True)
    # Select after a reset: nothing changes (exact_cycle's cancel, compared
    # with the run without the menu), from settings set with one Run.
    for name, steps, actions in (
            ('cancel after reset, from everything, sms, chinese', everything_sms, to_reset + ['I']),
            ('cancel after reset, from everything, apocalypse, japanese', everything_apocalypse, to_reset + ['I']),
            ('cancel after reset with II, from palette gb dmg', [(4, [R] * 3)], to_reset + ['II']),
            ('cancel after reset, from palette nes-b', [(4, [R] * 2)], to_reset + ['I']),
            ('cancel after reset and a stage change, from palette apocalypse', [(4, [R] * 4)],
             to_reset + ['I', D, R]),
            ('cancel after reset, from nothing changed', [], to_reset + ['I'])):
        with Game(emulator, work) as game:
            to_level(game, candidate, seed)
            if steps:
                set_up(game, steps)
            before = game.read(0, 0x2000)
            found = exact_cycle(game, work, actions=actions, n=LONG) \
                if select_at_hook(game) else {'ok': False, 'problems': ['menu not available']}
            after = game.read(0, 0x2000)
            found['options_and_language_kept'] = (after[0x100] == before[0x100] and after[0x1227] == before[0x1227]
                                                  and after[0xe5f] == before[0xe5f])
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
    parser.add_argument('--only', choices=('runs', 'sweep', 'select', 'options', 'reset'), action='append',
                        help='run these parts only (repeatable)')
    parser.add_argument('--parallax-off', action='store_true', help='runs: with $2100 bit 0 set')
    parser.add_argument('--preview', action='store_true', help='runs: change the palette too before cancelling')
    parser.add_argument('--same-music', action='store_true',
                        help='give the run without the menu the music driver state the menu left, and require '
                             'identical pictures in every frame')
    parser.add_argument('--strict', action='store_true',
                        help='frames whose video state differs only by the timer interrupt\'s phase fail too')
    parser.add_argument('--sweep-step', type=int, default=1)
    parser.add_argument('--sweep-runs', default='1-1,2-2,5-3,6-3')
    parser.add_argument('--shots', type=Path, help='runs: keep the first open-window picture of each check here')
    args = parser.parse_args()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    parts = set(args.only or ('runs', 'sweep', 'select', 'options', 'reset'))
    global SAME_MUSIC, STATE_IN_2104, STATUS_IN_2105, STRICT
    SAME_MUSIC = args.same_music
    STRICT = args.strict
    rom = args.candidate.read_bytes()
    if MENU_PREFIX != rom[MENU_ENTRY:MENU_ENTRY + len(MENU_PREFIX)]:
        raise SystemExit('The menu entry is not where this check expects it')
    # The palette module's state: $2104 since the SMS palette (its code in
    # bank $46 $5000-$53FF reads lda $2104), $2100 bits 5-7 before.
    STATE_IN_2104 = bytes.fromhex('ad0421') in rom[0x46 * 0x2000 + 0x1000:0x46 * 0x2000 + 0x1400]
    print('palette module state in', '$2104' if STATE_IN_2104 else '$2100 bits 5-7', flush=True)
    # The save status: $2105 once the menu calls src/bram's save (jsr $4B03).
    STATUS_IN_2105 = bytes.fromhex('20034b') in rom[MENU_ENTRY:MENU_ENTRY + 0x700]
    if not STATUS_IN_2105:
        raise SystemExit("This check reads the current menu.txt (with the save status row); "
                         "check an older build with that build's own scripts")
    report = {
        'rom_sha256': hashlib.sha256(args.candidate.read_bytes()).hexdigest(),
        'emulator_sha256': hashlib.sha256(args.emulator.read_bytes()).hexdigest(),
        'physical_hardware_tested': False, 'audio_compared': False, 'same_music': args.same_music,
    }
    seed = None
    if parts & {'runs', 'sweep', 'options', 'reset'}:
        seed = make_seed(args.emulator, args.original, args.output / 'seed.state')
    oks = []
    if 'runs' in parts:
        actions = None
        if args.preview:
            # PALETTE stepped three times: NES-A and NES-B (colours kept), then GB DMG.
            actions = ['down', 'right', 'down', 'right', 'down', 'right', 'down', 'right', 'right', 'right', 'down',
                       'right', 'down']
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
        rom = args.original.read_bytes()
        report['options'] = check_options(args.emulator, args.candidate, seed, args.output,
                                          rom[512:] if len(rom) % 8192 == 512 else rom)
        oks += [e['ok'] for e in report['options'].values()]
    if 'reset' in parts:
        report['reset'] = check_reset(args.emulator, args.candidate, seed, args.output)
        oks += [e['ok'] for e in report['reset'].values()]
    # Every frame accepted as timer phase only, listed in one place.
    timer = []
    for name, r in report.get('runs', {}).items():
        timer += [{'part': 'runs', 'run': name, 'opened_at': f, 'frames': v} for f, v in r['timer_phase'].items()]
    for window, outcome in report.get('sweep', {}).items():
        timer += [{'part': 'sweep', 'window': window, 'opened_at': o['frame'], 'frames': o['timer_phase_frames']}
                  for o in outcome if o.get('timer_phase_frames')]
    for part in ('options', 'reset'):
        for name, r in report.get(part, {}).items():
            if r.get('timer_phase_frames'):
                timer.append({'part': part, 'case': name, 'frames': r['timer_phase_frames']})
    for e in report.get('level_select', []):
        if e.get('timer_phase_frames'):
            timer.append({'part': 'select', 'stage': e.get('stage'), 'frames': e['timer_phase_frames']})
    report['timer_phase_only'] = timer
    report['strict'] = args.strict
    print('openings whose video state differed only by the timer interrupt\'s phase:', len(timer),
          '(failures with --strict)' if args.strict else '(accepted; --strict fails them)', flush=True)
    for t in timer:
        print('  timer phase only:', t, flush=True)
    report['ok'] = all(oks)
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('menu check', 'passed' if report['ok'] else 'FAILED')
    raise SystemExit(0 if report['ok'] else 1)


if __name__ == '__main__':
    main()
