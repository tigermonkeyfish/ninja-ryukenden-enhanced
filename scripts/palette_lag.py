#!/usr/bin/env python3
"""Lag-frame survey of the stored replay runs in every palette mode.

Emulator evidence only (headless Geargrafx, see docs/pc-engine/EMULATOR.md).
Each (run, variant) is one fresh session that loads one saved start state,
optionally sets the palette mode through the in-game menu exactly as
scripts/palette_video.py does, then replays the stored input one frame step
at a time. Per frame it records the game-update counter (RAM $2000, one
increment per main-loop update), the vblank-wait flag $12, and the gameplay
fields scripts/comparison_video.py compares, plus hashes of the sprite table
and the VCE palette.

A lag frame is a frame step in which the update counter did not advance.

  palette_lag.py record RUN VARIANT   one session -> OUT/traces/RUN.VARIANT.json
  palette_lag.py survey               every run x variant (resumes)
  palette_lag.py report               tables from the stored traces
  palette_lag.py pairs                two menus (mode1 into 1-1, then 3-2 in mode2), all 36 pairs
  palette_lag.py fastok               review F2: FASTOK after a vblank inside the worker's last colours
  palette_lag.py dispatch RUN START N  the vblank palette dispatch paths and their cycles
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import palette_video as pv                                              # noqa: E402
from comparison_video import Game, start_point, start_stage, make_seed, STAGE_NAMES, NEXT_SEQUENCE, StepError  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
EMULATOR = Path('/workspace/build/toolchain/geargrafx/platforms/linux/geargrafx')
ORIGINAL = Path('/workspace/DO_NOT_COMMIT_ROMS/Ninja Ryukenden (J).pce')
ROMS = Path('/workspace/roms')
ROM_111 = ROMS / 'Ninja Ryukenden - Enhanced v1.11-dev (apocalypse, reset 2).pce'
# PALETTE_LAG_ROM: test another 1.11-dev build in the six menu variants and
# 'v1.11-nomenu'; PALETTE_LAG_TRACES: where its traces go (default traces/).
import os
if os.environ.get('PALETTE_LAG_ROM'):
    ROM_111 = Path(os.environ['PALETTE_LAG_ROM'])
ROM_110 = ROMS / 'Ninja Ryukenden - Enhanced v1.10.pce'
SHA_111 = 'cec5f7b3d1fddc224ad8da921b20e6b0eec55295d59f001a714c209a33bb8059'
OUT = Path('/workspace/build/palette-lag')
TAIL = 60

# variant -> (rom, enhanced, palette mode through the menu or None = no menu)
VARIANTS = {
    'orig-rom': (ORIGINAL, False, None),
    'v1.10': (ROM_110, True, None),
    'v1.11-nomenu': (ROM_111, True, None),
    'original': (ROM_111, True, 'original'),
    'apocalypse': (ROM_111, True, 'apocalypse'),
    'nes-a': (ROM_111, True, 'nes-a'),
    'nes-b': (ROM_111, True, 'nes-b'),
    'sms': (ROM_111, True, 'sms'),
    'gb dmg': (ROM_111, True, 'gb dmg'),
}
RUN_FILES = sorted((ROOT / 'research/comparison-runs').glob('*.json'))


def seed_state():
    seed = OUT / 'seed.state'
    if not seed.exists():
        make_seed(EMULATOR, ORIGINAL, seed)
    return seed


def load_run(name):
    path = ROOT / 'research/comparison-runs' / f'{name}.json'
    return json.loads(path.read_text())


def record(runname, variant, upto=None, outdir=None, extra=None):
    run = load_run(runname)
    rom, enhanced, mode = VARIANTS[variant]
    inputs = []
    for count, buttons in run['segments']:
        inputs += [frozenset(buttons)] * count
    inputs += [frozenset()] * TAIL
    if upto:
        inputs = inputs[:upto]
    log = Path(outdir or OUT / 'work') / f'{runname}-{variant.replace(" ", "")}'
    trace, prev_vce = [], None
    with Game(EMULATOR, log) as game:
        start_point(game, rom, seed_state(), enhanced)
        if mode is None:
            start_stage(game, run['stage'])
        else:
            pv.enter_stage(game, run['stage'], mode, 0)
        for n, buttons in enumerate(inputs):
            game.press(set(buttons))
            game.checked_step(1)
            ram = game.read(0, 0x2000)
            vce = game.read(0, 1024, area=8)
            changed = 0 if prev_vce is None else sum(
                vce[i:i + 2] != prev_vce[i:i + 2] for i in range(0, 1024, 2))
            prev_vce = vce
            trace.append({
                'f': n, 'c': ram[0], 'f12': ram[0x12],
                'sat': hashlib.sha1(game.read(0, 512, area=6)).hexdigest()[:10],
                'vce': hashlib.sha1(vce).hexdigest()[:10], 'vce_changed': changed,
                'ryu': ram[0xe9e:0xeb8].hex(), 'timer': ram[0xeda:0xede].hex(),
                'stage': ram[0xe5f], 'area': ram[0xe60], 'lives': ram[0xeaf],
                'health': ram[0xead], 'cam': int.from_bytes(ram[0x20f:0x211], 'little'),
                'master': ram[0x240], 'boss': ram[0x1035], 'state': ram[0xeab],
                'opt': ram[0x100]})
            if changed or n == 0:
                trace[-1]['vce_words'] = vce.hex()     # the whole VCE when it changed
    return trace


TRACES = Path(os.environ.get('PALETTE_LAG_TRACES', OUT / 'traces'))


def trace_path(runname, variant):
    if variant in ('orig-rom', 'v1.10') and not (TRACES / f'{runname}.{variant}.json').exists():
        return OUT / 'traces' / f'{runname}.{variant}.json'      # the shared baseline
    return TRACES / f'{runname}.{variant.replace(" ", "")}.json'


def survey(runs, variants):
    TRACES.mkdir(parents=True, exist_ok=True)
    for run in runs:
        for variant in variants:
            path = trace_path(run, variant)
            if path.exists():
                continue
            for attempt in range(3):
                try:
                    trace = record(run, variant)
                    break
                except Exception as exc:        # a mis-step: fresh session
                    print('retry', run, variant, exc, flush=True)
            else:
                raise SystemExit(f'{run} {variant} failed')
            path.write_text(json.dumps(trace))
            lag = sum(1 for i, t in enumerate(trace) if i and (t['c'] - trace[i - 1]['c']) & 255 == 0)
            print(f'{run} {variant}: {len(trace)} frames, {lag} lag', flush=True)


def deltas(trace):
    """Updates completed in each frame step (frame 0: counter change from
    the first step is unknown, reported as 1)."""
    return [1] + [(trace[i]['c'] - trace[i - 1]['c']) & 255 for i in range(1, len(trace))]


GAMEPLAY = ('sat', 'ryu', 'timer', 'lives', 'health', 'cam', 'area', 'stage')


def first_diff(a, b):
    """First frame where the gameplay fields or the update count differ."""
    da, db = deltas(a), deltas(b)
    for i in range(min(len(a), len(b))):
        if any(a[i][k] != b[i][k] for k in GAMEPLAY) or da[i] != db[i]:
            return i
    return None if len(a) == len(b) else min(len(a), len(b))


VBLANK_INC = 'FD1F'     # INC $12 in the vblank interrupt handler ($FCD7)
WAIT_STZ = 'FD67'       # STZ $12 at the start of the wait-for-vblank routine ($FD67-$FD6F)
FRAME_CLOCKS = 358995   # master clocks per frame (263 lines x 1365)
VBLANK_PHASE = 350895   # master clock mod FRAME_CLOCKS at which the vblank interrupt is taken (+0-9 jitter)


def master_clock(game, tmp):
    game.call('save_state_file', {'file_path': str(tmp)})
    return int.from_bytes(Path(tmp).read_bytes()[1:9], 'little')


def margin(runname, variant, start, frames):
    """Replay with frame steps to boundary `start`, then run on with
    breakpoints at the vblank handler's INC $12 and the wait routine's
    STZ $12 and report the master clock of each stop. The input held at
    `start` must stay constant for `frames` frames (checked by the caller).
    Returns [(kind, clock, update counter, ryu x)] ."""
    run = load_run(runname)
    rom, enhanced, mode = VARIANTS[variant]
    inputs = []
    for count, buttons in run['segments']:
        inputs += [frozenset(buttons)] * count
    inputs += [frozenset()] * TAIL
    log = OUT / 'work' / f'{runname}-{variant.replace(" ", "")}-margin'
    tmp = log / 'clock.state'
    events = []
    with Game(EMULATOR, log) as game:
        start_point(game, rom, seed_state(), enhanced)
        if mode is None:
            start_stage(game, run['stage'])
        else:
            pv.enter_stage(game, run['stage'], mode, 0)
        for n in range(start):
            game.press(set(inputs[n]))
            game.checked_step(1)
        game.press(set(inputs[start]))
        base = master_clock(game, tmp)
        for addr in (VBLANK_INC, WAIT_STZ):
            game.call('set_breakpoint', {'address': addr.lower(), 'memory_area': 'cpu_addr', 'execute': True})
        vblanks = 0
        while vblanks <= frames:
            game.call('debug_continue')
            for _ in range(200000):
                status = game.call('debug_get_status')
                if status.get('paused'):
                    break
            else:
                raise TimeoutError('no breakpoint hit')
            pc = status['pc']
            ram = game.read(0, 0xf00)
            kind = {VBLANK_INC: 'vblank', WAIT_STZ: 'update-done'}.get(pc)
            if kind is None:
                raise RuntimeError(f'stopped at {pc}')
            events.append((kind, master_clock(game, tmp) - base, ram[0], int.from_bytes(ram[0xe9e:0xea0], 'little')))
            vblanks += kind == 'vblank'
    return events


def itrace(runname, variant, start, frames, out):
    """Replay frame steps 0..start-1, then record every CPU instruction and
    interrupt of the next `frames` frame steps (with their stored inputs)
    to `out` (gzip, one trace line each, prefixed by the frame index)."""
    import gzip
    run = load_run(runname)
    rom, enhanced, mode = VARIANTS[variant]
    inputs = []
    for count, buttons in run['segments']:
        inputs += [frozenset(buttons)] * count
    inputs += [frozenset()] * TAIL
    log = OUT / 'work' / f'{runname}-{variant.replace(" ", "")}-itrace'
    with Game(EMULATOR, log) as game, gzip.open(out, 'wt') as fh:
        start_point(game, rom, seed_state(), enhanced)
        if mode is None:
            start_stage(game, run['stage'])
        else:
            pv.enter_stage(game, run['stage'], mode, 0)
        for n in range(start):
            game.press(set(inputs[n]))
            game.checked_step(1)
        game.call('set_trace_log', {'enabled': True, 'output': 'memory', 'memory_size': '1M',
                                    'filters': ['cpu.instructions', 'cpu.irqs']})
        pos = game.call('get_trace_log', {'count': 1}).get('total_logged', 0)
        for n in range(start, start + frames):
            game.press(set(inputs[n]))
            game.checked_step(1)
            end = game.call('get_trace_log', {'count': 1}).get('total_logged', 0)
            while pos < end:
                chunk = game.call('get_trace_log', {'start': pos, 'count': min(1000, end - pos)})
                if chunk.get('overrun'):
                    raise RuntimeError('trace ring overrun')
                lines = chunk.get('lines') or []
                if not lines:
                    raise RuntimeError(f'trace read stalled at {pos}')
                for ln in lines:
                    fh.write(f'{n} {ln}\n')
                pos += len(lines)
            ram = game.read(0, 0x100)
            fh.write(f'{n} #frame-end counter {ram[0]} f12 {ram[0x12]}\n')
        game.call('set_trace_log', {'enabled': False})


MUSIC_ENTRY = 0x38 * 0x2000 + 0x0006    # bank $38 $4006: the sound driver's command entry (main loop)
FIRST_UPDATE_ROM = 0x2457               # bank 1 $8457: a stage's first update
MODE_BITS = {'original': 0x00, 'apocalypse': 0x18, 'nes-a': 0x08, 'nes-b': 0x28, 'sms': 0xb8, 'gb dmg': 0x10}


def load_timing(rom, stage, bits, vce_log=None):
    """Level Select entry into `stage` with $2100 bits 3-5/7 = `bits` set
    before the load (the native stage load, no menu). Returns the master
    clock (from the debugger's request) of every sound-driver command call
    ($38:$4006) up to the stage's first update, and of that first update."""
    log = OUT / 'work' / f'loadtime-{stage}-{bits:02x}'
    tmp = log / 'clock.state'
    with Game(EMULATOR, log) as game:
        start_point(game, rom, seed_state(), True)
        x = game.read(0x100, 1)[0]
        game.write(0x100, bytes([(x & 0x47) | bits]))
        configure(game, rom)
        # Let the mode settle (a mapped mode re-uploads every colour after
        # the change) before the load: 60 updates, stopping at the hook.
        game.call('set_breakpoint', {'address': '23f3', 'memory_area': 'rom', 'execute': True})
        for _ in range(60):
            game.run_to('83F3')
        game.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'})
        cpu = game.call('get_huc6280_status')
        assert cpu['PC'] == '83F3', cpu
        sp = int(cpu['S'], 16)
        game.write(0x241, bytes([stage]))
        game.write(0x247, bytes([NEXT_SEQUENCE[stage], 0]))
        game.write(0xe65, bytes(22))
        game.write(0xead, bytes([16]))
        game.write(0x100 + sp - 1, bytes([0xf2, 0x83]))
        game.reg('S', sp - 2)
        game.reg('A', stage)
        game.reg('PC', 0x8244)
        if vce_log:
            game.call('set_trace_log', {'enabled': True, 'output': 'memory', 'memory_size': '1M',
                                        'filters': ['cpu.irqs', 'vce.registers']})
            pos = game.call('get_trace_log', {'count': 1})['total_logged']
        for addr in (MUSIC_ENTRY, FIRST_UPDATE_ROM):
            game.call('set_breakpoint', {'address': f'{addr:x}', 'memory_area': 'rom', 'execute': True})
        events = []
        while True:
            pc = game.run_to(None, polls=400000)
            clock = master_clock(game, tmp)
            kind = 'first-update' if pc == '8457' else 'sound-command'
            events.append((kind, clock))
            if kind == 'first-update':
                break
            game.call('remove_breakpoint', {'address': f'{MUSIC_ENTRY:x}', 'memory_area': 'rom'})
            game.call('debug_step_into')
            game.call('set_breakpoint', {'address': f'{MUSIC_ENTRY:x}', 'memory_area': 'rom', 'execute': True})
        if vce_log:
            end = game.call('get_trace_log', {'count': 1})['total_logged']
            with open(vce_log, 'w') as fh:
                while pos < end:
                    chunk = game.call('get_trace_log', {'start': pos, 'count': min(1000, end - pos)})
                    for line in chunk['lines']:
                        fh.write(line + '\n')
                    pos += len(chunk['lines'])
    return events


def resume_step(game):
    """Finish a frame step that a breakpoint interrupted.

    Frame-step hazard (palette-lag review F4; Geargrafx 78fc3d7,
    platforms/shared/desktop/emu.cpp): a sync debug_step_frame adds its
    frames to a pending count that only a completed frame decrements; a
    breakpoint stop leaves the count at 1, so the next step(1) asks for 2:
    it reports after the first frame end and the emulator runs a second
    frame on its own, with the same input, before the next request is
    served. Only debug_pause during an active frame step clears the count.
    So the step is sent together with a debug_pause (one write): the step
    runs to the frame end (or the next breakpoint), the pause is served
    there and clears the count, and one more instruction runs (the pause
    leaves a single-instruction step). Returns the step's result like
    Game.step (None: another breakpoint stopped it)."""
    emu = game.emu
    emu.counter += 2
    step_id, pause_id = emu.counter - 1, emu.counter
    emu.proc.stdin.write(json.dumps({'jsonrpc': '2.0', 'id': step_id, 'method': 'tools/call', 'params': {
        'name': 'debug_step_frame', 'arguments': {'frames': 1, 'mode': 'sync'}}}) + '\n'
        + json.dumps({'jsonrpc': '2.0', 'id': pause_id, 'method': 'tools/call', 'params': {
            'name': 'debug_pause', 'arguments': {}}}) + '\n')
    emu.proc.stdin.flush()
    replies = {}
    while len(replies) < 2:
        message = emu.messages.get(timeout=60)
        if message is None:
            raise RuntimeError('emulator exited')
        if message.get('id') in (step_id, pause_id):
            replies[message['id']] = message
    step = replies[step_id]
    if 'error' in step:
        raise RuntimeError(step['error'])
    result = step['result']
    if result.get('isError'):
        if 'interrupted' in json.dumps(result):
            return None
        raise RuntimeError(result)
    texts = [item['text'] for item in result.get('content', []) if item['type'] == 'text']
    return json.loads(texts[0]) if texts else result


def step_with_stops(game, tmp, frame, on_stop):
    """One frame step with execution breakpoints armed. At each stop
    on_stop(pc, clock) is called (it may return True to leave the machine
    there, mid-frame), the breakpoint is stepped over and the frame goes on
    (resume_step). Every step with a stop is checked by master clock to end
    in the frame it began in (the harness's frame ends are the multiples of
    FRAME_CLOCKS, phase 0): StepError otherwise. `game.frame_end` carries the
    boundary from step to step; set it to None after anything else moves
    the machine (run_to, a state load). Returns True if on_stop kept the
    machine at a stop (the emulator's pending count is then 1: the next
    step_with_stops resumes with resume_step)."""
    if getattr(game, 'frame_end', None) is None:
        game.frame_end = (master_clock(game, tmp) // FRAME_CLOCKS + 1) * FRAME_CLOCKS
    boundary, stopped = game.frame_end, False
    # A stop left the emulator's pending frame count at 1: resume_step.
    result = resume_step(game) if getattr(game, 'leftover', False) else game.step(1)
    game.leftover = False
    while result is None:
        stopped = game.leftover = True
        pc = game.call('debug_get_status')['pc']
        clock = master_clock(game, tmp)
        if clock >= boundary + FRAME_CLOCKS // 2:
            raise StepError(f'frame {frame}: a stop at {clock}, past the frame end {boundary}')
        if on_stop(pc, clock):
            game.frame_end = None
            return True
        area = game.stop_areas[pc]
        game.call('remove_breakpoint', {'address': f'{area[1]:x}', 'memory_area': area[0]})
        game.call('debug_step_into')
        game.call('set_breakpoint', {'address': f'{area[1]:x}', 'memory_area': area[0], 'execute': True})
        if master_clock(game, tmp) >= boundary:
            break               # the frame end came in the stepped-over instruction (count still 1)
        result = resume_step(game)
        if result is not None:
            game.leftover = False
    if stopped:
        end = master_clock(game, tmp)
        if not boundary <= end < boundary + FRAME_CLOCKS // 2:
            raise StepError(f'frame {frame}: a step with a breakpoint stop ended at {end}, '
                            f'the frame end is {boundary}')
        game.frame_end = (end // FRAME_CLOCKS + 1) * FRAME_CLOCKS
    else:
        game.frame_end = boundary + FRAME_CLOCKS
    return False


def step_recording(game, hits, tmp, frame):
    """One frame step; every stop at the sound-command breakpoint
    ($38:$4006) inside it is recorded (frame, PC, master clock) and stepped
    over, then the step goes on to the frame's end (step_with_stops)."""
    game.stop_areas = {'4006': ('rom', MUSIC_ENTRY)}

    def record_hit(pc, clock):
        if pc not in game.stop_areas:
            raise RuntimeError(f'unexpected stop at {pc}')
        hits.append((frame, pc, clock))
        return False
    step_with_stops(game, tmp, frame, record_hit)


def e2e(mode, runname, rom, out):
    """Power-on with backup RAM holding settings in `mode` (the menu never
    opened), the title left with Run as comparison_video.boot does, the
    game's own start into 1-1, then `runname`'s input from 1-1's first
    update (stop at $8457, saved and reloaded). Records the per-frame trace
    (as record) and every sound-driver command call ($38:$4006) with its
    master clock, from power-on."""
    import bram_image as bi
    run = load_run(runname)
    inputs = []
    for count, buttons in run['segments']:
        inputs += [frozenset(buttons)] * count
    inputs += [frozenset()] * TAIL
    log = OUT / 'work' / f'e2e-{mode.replace(" ", "")}'
    tmp = log / 'clock.state'
    bram = bi.image([bi.settings_entry(options=MODE_BITS[mode])])
    hits, trace = [], []
    with Game(EMULATOR, log) as game:
        game.power_on(rom, bram)
        game.call('set_breakpoint', {'address': f'{MUSIC_ENTRY:x}', 'memory_area': 'rom', 'execute': True})
        previous, since, presses, pressed, title = None, 0, [200], False, False
        for frame in range(1, 20000):
            step_recording(game, hits, tmp, -frame)
            since += 1
            ram = game.read(0, 0x300)
            master = bytes(ram[0x240:0x242])
            if master != previous:
                previous, since = master, 0
            if master == b'\x01\x01':
                title = True
            if master == b'\x01\x01' and since == 180 and not pressed:
                presses.append(frame)
                pressed = True
            if master in (b'\x00\x00', b'\x01\x00') and since % 300 == 150 and not title:
                presses.append(frame)
            for p in presses:
                if frame == p:
                    game.call('controller_button', {'player': 1, 'button': 'run', 'action': 'press'})
                elif frame == p + 2:
                    game.call('controller_button', {'player': 1, 'button': 'run', 'action': 'release'})
            if title and master[0] == 0 and frame > presses[-1] + 2:
                break
        else:
            raise RuntimeError('gameplay not reached')
        status = {'opt': game.read(0x100, 1)[0], 'save_status': game.read(0x105, 1)[0], 'boot_frames': frame}
        # 1-1's first update
        game.call('set_breakpoint', {'address': f'{FIRST_UPDATE_ROM:x}', 'memory_area': 'rom', 'execute': True})
        while True:
            pc = game.run_to(None, polls=400000)
            if pc == '8457':
                break
            hits.append((0, pc, master_clock(game, tmp)))
            game.call('remove_breakpoint', {'address': f'{MUSIC_ENTRY:x}', 'memory_area': 'rom'})
            game.call('debug_step_into')
            game.call('set_breakpoint', {'address': f'{MUSIC_ENTRY:x}', 'memory_area': 'rom', 'execute': True})
        game.call('remove_breakpoint', {'address': f'{FIRST_UPDATE_ROM:x}', 'memory_area': 'rom'})
        status['first_update'] = master_clock(game, tmp)
        entered = log / 'entered.state'
        game.call('save_state_file', {'file_path': str(entered)})
        game.call('load_state_file', {'file_path': str(entered)})
        game.held = set()
        game.frame_end = None       # run_to stopped mid-frame: step_recording finds the next end
        prev_vce = None
        for n, buttons in enumerate(inputs):
            game.press(set(buttons))
            step_recording(game, hits, tmp, n)
            ram = game.read(0, 0x2000)
            vce = game.read(0, 1024, area=8)
            trace.append({'f': n, 'c': ram[0], 'sat': hashlib.sha1(game.read(0, 512, area=6)).hexdigest()[:10],
                          'vce': hashlib.sha1(vce).hexdigest()[:10], 'ryu': ram[0xe9e:0xeb8].hex(),
                          'timer': ram[0xeda:0xede].hex(), 'stage': ram[0xe5f], 'area': ram[0xe60],
                          'health': ram[0xead], 'cam': int.from_bytes(ram[0x20f:0x211], 'little'),
                          'master': ram[0x240]})
    out.write_text(json.dumps({'status': status, 'hits': hits, 'trace': trace}))
    return status, hits, trace


def event_run(runname, variant, out):
    """The clock of every interrupt entry (with the interrupted PC), pad
    read and VCE register write over a whole replay (hardware-event trace,
    no breakpoints), stored per frame step. Two variants whose streams carry
    the same clocks ran their interrupts, vblank handlers and uploads at the
    same master clocks: a main-loop or vblank difference of even a few
    cycles shows up as moved interrupt entries."""
    run = load_run(runname)
    rom, enhanced, mode = VARIANTS[variant]
    inputs = []
    for count, buttons in run['segments']:
        inputs += [frozenset(buttons)] * count
    inputs += [frozenset()] * TAIL
    log = OUT / 'work' / f'events-{runname}-{variant.replace(" ", "")}'
    frames = []
    with Game(EMULATOR, log) as game:
        start_point(game, rom, seed_state(), enhanced)
        if mode is None:
            start_stage(game, run['stage'])
        else:
            pv.enter_stage(game, run['stage'], mode, 0)
        game.call('set_trace_log', {'enabled': True, 'output': 'memory', 'memory_size': '500K',
                                    'filters': ['cpu.irqs', 'input.reads', 'vce.registers']})
        pos = game.call('get_trace_log', {'count': 1})['total_logged']
        for n, buttons in enumerate(inputs):
            game.press(set(buttons))
            game.checked_step(1)
            end = game.call('get_trace_log', {'count': 1})['total_logged']
            ev = []
            while pos < end:
                chunk = game.call('get_trace_log', {'start': pos, 'count': min(1000, end - pos)})
                for line in chunk['lines']:
                    m = re.match(r'@(\d+)\s.*?\[(\w+)\]\s+(\S+)\s*(.*)', line)
                    if m:
                        kind = m.group(2) + ' ' + m.group(3)
                        extra = m.group(4)
                        if kind.startswith('CPU'):
                            extra = extra.split()[0] + ' ' + (re.search(r'PC:\$(\w+)', extra) or ['', ''])[1]
                        elif kind.startswith('VCE'):
                            extra = ''
                        ev.append((int(m.group(1)), kind, extra))
                pos += len(chunk['lines'])
            frames.append(ev)
    Path(out).write_text(json.dumps(frames))
    return frames


SOUND_RAM = [(0x080, 0x090), (0x1800, 0x1c00)]     # the sound driver's zero page and RAM ($2080-$208F, $3800-$3BFF)
PAIR_MODES = ['original', 'apocalypse', 'nes-a', 'nes-b', 'sms', 'gb dmg']


def drain_irqs(game, pos):
    """Master clocks of the interrupt entries logged since `pos` (cpu.irqs
    trace); returns (clocks, new pos)."""
    end = game.call('get_trace_log', {'count': 1})['total_logged']
    clocks = []
    while pos < end:
        chunk = game.call('get_trace_log', {'start': pos, 'count': min(1000, end - pos)})
        lines = chunk.get('lines') or []
        if chunk.get('overrun') or not lines:
            raise RuntimeError(f'irq trace lost at {pos}')
        for line in lines:
            m = re.match(r'@(\d+)', line)
            if m:
                clocks.append(int(m.group(1)))
        pos += len(lines)
    return clocks, pos


def pair_run(mode1, mode2, runname, frames, rom, out):
    """Two menu sessions, the route of palette-lag review F1: menu 1 (opened
    in 1-1 in Original, as enter_stage does) Runs into 1-1 in `mode1`; 30
    frames later menu 2, opened in that mode, chooses `runname`'s stage and
    `mode2` with Right presses from mode1, padded to five on the reset row
    (every pair presses the same buttons, the same number of times), and
    Runs. At the stage's first update ($8457) its master clock; then the
    run's stored input for `frames` frame steps, per frame the update
    counter, Ryu, the sound driver's RAM (hash) and the interrupt entries'
    master clocks."""
    from check_menu import press, stop_at, FIRST_UPDATE, palette_presses
    run = load_run(runname)
    inputs = []
    for count, buttons in run['segments']:
        inputs += [frozenset(buttons)] * count
    inputs += [frozenset()] * max(0, frames - len(inputs))
    log = OUT / 'work' / f'pair-{mode1.replace(" ", "")}-{mode2.replace(" ", "")}'
    tmp = log / 'clock.state'
    trace = []
    with Game(EMULATOR, log) as game:
        start_point(game, rom, seed_state(), True)
        pv.enter_stage(game, 0, mode1, 0)
        opt1 = game.read(0x100, 1)[0]
        game.step(30)
        press(game, 'select', after=6)
        for _ in range(run['stage']):
            press(game, 'right')                    # STAGE row, from 1-1
        for _ in range(4):
            press(game, 'down')                     # to PALETTE
        way = palette_presses(mode1, mode2, 'right')
        for b in way:
            press(game, b)
        press(game, 'down')
        press(game, 'down')                         # the reset row: Left/Right do nothing
        for _ in range(5 - len(way)):
            press(game, 'right')
        game.press({'run'})
        game.step(2)
        game.press(set())
        if not stop_at(game, FIRST_UPDATE, 600):
            raise RuntimeError('stage did not restart')
        first = master_clock(game, tmp)
        entered = log / 'entered.state'
        game.call('save_state_file', {'file_path': str(entered)})
        game.call('load_state_file', {'file_path': str(entered)})
        game.held = set()
        status = {'first_update': first, 'opt1': opt1, 'opt2': game.read(0x100, 1)[0],
                  'stage': game.read(0xe5f, 1)[0]}
        game.call('set_trace_log', {'enabled': True, 'output': 'memory', 'memory_size': '100K',
                                    'filters': ['cpu.irqs']})
        pos = game.call('get_trace_log', {'count': 1})['total_logged']
        for n in range(frames):
            game.press(set(inputs[n]))
            game.checked_step(1)
            irqs, pos = drain_irqs(game, pos)
            ram = game.read(0, 0x2000)
            snd = hashlib.sha1(b''.join(ram[a:b] for a, b in SOUND_RAM)).hexdigest()[:12]
            trace.append({'f': n, 'c': ram[0], 'ryu': ram[0xe9e:0xeb8].hex(), 'snd': snd,
                          'stage': ram[0xe5f], 'master': ram[0x240], 'irq': irqs})
        game.call('set_trace_log', {'enabled': False})
    out.write_text(json.dumps({'status': status, 'trace': trace}))
    return status, trace


def pair_compare(ref, cur):
    """One matrix cell against ORIGINAL -> ORIGINAL."""
    rs, rt = ref
    cs, ct = cur
    d = deltas(ct)
    lag = [i for i in range(1, len(ct)) if d[i] == 0]
    snd = [t['f'] for a, t in zip(rt, ct) if a['snd'] != t['snd']]
    game = [t['f'] for a, t in zip(rt, ct) if (a['c'], a['ryu'], a['stage'], a['master']) != (t['c'], t['ryu'], t['stage'], t['master'])]
    shifted, worst = 0, 0
    for a, t in zip(rt, ct):
        if a['irq'] != t['irq']:
            shifted += 1
            worst = max([worst] + ([abs(x - y) for x, y in zip(a['irq'], t['irq'])]
                                   if len(a['irq']) == len(t['irq']) else [FRAME_CLOCKS]))
    return {'first_update': cs['first_update'] - rs['first_update'], 'opt2': cs['opt2'],
            'snd_frames': len(snd), 'snd_first': snd[0] if snd else None,
            'game_frames': len(game), 'game_first': game[0] if game else None,
            'lag': lag, 'irq_frames': shifted, 'irq_max': worst}


def dispatch_paths(lines):
    """From instruction-trace lines (itrace format): every vblank call of
    src/palette's palette_entry (bank $46 $5000, carry clear: palette_now's
    calls take the bcs) with its path and the CPU cycles from palette_entry
    to where the path leaves the dispatch: its rts (locked, empty) or the
    first instruction of the upload it jumps to (plain: the native $F3B5;
    fast: fast_upload; fallback: the mapped upload; -requeue: QUEUE_ALL was
    called on the way). Returns [(frame, path, cycles)]."""
    out, cur = [], None
    for ln in lines:
        m = re.match(r'(\d+) @(\d+)\s+(?:\+\d+\s+)?([0-9A-F]{2}):([0-9A-F]{4})\s.*?\s([A-Z]{3})\b(.*)$', ln)
        if not m:
            continue
        frame, clock, bank, pc, op, rest = int(m[1]), int(m[2]), m[3], m[4], m[5], m[6]
        if cur is not None:
            if cur['n'] == 1 and pc != '5002':
                cur = None                      # bcs taken: palette_now
            elif cur['jumped']:
                path = 'plain' if pc == 'F3B5' else ('fast' if cur['dec'] and not cur['queue'] else 'fallback')
                out.append((cur['frame'], path + ('-requeue' if cur['requeue'] else ''), (clock - cur['clock']) // 3))
                cur = None
            elif cur['depth']:
                cur['depth'] += {'JSR': 1, 'RTS': -1}.get(op, 0)
            elif op == 'RTS':
                path = 'empty' if cur['queue'] else ('locked' if not cur['live'] else 'other')
                out.append((cur['frame'], path, (clock - cur['clock']) // 3))
                cur = None
            else:
                cur['live'] |= op == 'LDA' and '$37E0' in rest
                cur['dec'] |= op == 'DEC' and '$37E1' in rest
                cur['queue'] |= op == 'LDA' and '$2260' in rest
                if op == 'JSR':
                    cur['requeue'], cur['depth'] = True, 1
                cur['jumped'] = op == 'JMP'
            if cur is not None:
                cur['n'] += 1
        if cur is None and bank == '46' and pc == '5000' and op == 'BCS':
            cur = {'frame': frame, 'clock': clock, 'live': False, 'dec': False, 'queue': False,
                   'requeue': False, 'jumped': False, 'depth': 0, 'n': 1}
    return out

def worker_rom_offset(rom):
    """ROM offset of src/palette's worker (bank $46), from the jsr in
    WAITR's mapped template (wait_mapped) in the build."""
    data = Path(rom).read_bytes()
    data = data[len(data) % 0x2000:]
    bank = data[0x46 * 0x2000:0x47 * 0x2000]
    at = bank.find(bytes.fromhex('6412' '93ff6022' 'd007' 'a512c90190fa60' '4304' '48' 'a946' '5304' '20'))
    if at < 0:
        raise RuntimeError('no WAITR template in bank $46')
    addr = bank[at + 23] | bank[at + 24] << 8
    return 0x46 * 0x2000 + (addr & 0x1fff)


def fastok_probe(rom, lengths, runname='2-2', mode='gb dmg', first=785, last=800, out=None, late=100000):
    """Palette-lag review F2's reproduction: `runname` in `mode` through the
    menu, replayed (step_recording, a breakpoint on the worker) to the first
    worker call in frames first..last whose queue holds 256 colours or more
    and that starts less than `late` master clocks before the vblank (2-2's
    area change near frame 792: 512 colours queued about 43k clocks before
    it), saved there. Per trial: that state,
    the queue cut to one entry of N colours from its first colour (only the
    length varies), run on (instruction trace) to the main loop's return
    from the wait ($E064). Returns per N: FASTOK, the queue count and
    $2104 there, and the vblank dispatch paths taken on the way."""
    run = load_run(runname)
    inputs = []
    for count, buttons in run['segments']:
        inputs += [frozenset(buttons)] * count
    log = OUT / 'work' / f'fastok-{mode.replace(" ", "")}'
    tmp = log / 'clock.state'
    worker = worker_rom_offset(rom)
    rows = []
    with Game(EMULATOR, log) as game:
        start_point(game, rom, seed_state(), True)
        pv.enter_stage(game, run['stage'], mode, 0)
        for n in range(first):
            game.press(set(inputs[n]))
            game.checked_step(1)
        game.call('set_breakpoint', {'address': f'{worker:x}', 'memory_area': 'rom', 'execute': True})
        game.stop_areas = {f'{0x4000 | (worker & 0x1fff):04X}': ('rom', worker)}
        game.frame_end, found = None, None
        for n in range(first, last):
            game.press(set(inputs[n]))

            def at_worker(pc, clock, n=n):
                nonlocal found
                if pc not in game.stop_areas:
                    raise RuntimeError(f'unexpected stop at {pc}')
                ram = game.read(0, 0x300)
                count = ram[0x260]
                colours = sum(ram[0x261 + i] | ram[0x269 + i] << 8 for i in range(count)) // 2
                before = ((clock - VBLANK_PHASE) // FRAME_CLOCKS + 1) * FRAME_CLOCKS + VBLANK_PHASE - clock
                print(f'worker call: frame {n}, {colours} colours in {count} entries, {before} clk before the vblank', flush=True)
                if colours >= 256 and before < late:
                    found = (n, clock, count, colours)
                    return True
                return False
            if step_with_stops(game, tmp, n, at_worker):
                break
        if not found:
            raise RuntimeError('no large worker call')
        game.call('remove_breakpoint', {'address': f'{worker:x}', 'memory_area': 'rom'})
        frame, clock, count, colours = found
        vblank = ((clock - VBLANK_PHASE) // FRAME_CLOCKS + 1) * FRAME_CLOCKS + VBLANK_PHASE
        base = log / 'worker.state'
        game.call('save_state_file', {'file_path': str(base)})
        ram = game.read(0, 0x300)
        queue = [(ram[0x271 + i] | ram[0x279 + i] << 8, (ram[0x261 + i] | ram[0x269 + i] << 8) // 2) for i in range(count)]
        head = {'frame': frame, 'clock_before_vblank': vblank - clock, 'queue': queue}
        game.call('set_breakpoint', {'address': '64', 'memory_area': 'rom', 'execute': True})
        for length in lengths:
            game.call('load_state_file', {'file_path': str(base)})
            game.write(0x260, bytes([1]))
            game.write(0x261, bytes([(2 * length) & 0xff]))
            game.write(0x269, bytes([(2 * length) >> 8]))
            game.call('set_trace_log', {'enabled': True, 'output': 'memory', 'memory_size': '1M',
                                        'filters': ['cpu.instructions']})
            pos = game.call('get_trace_log', {'count': 1})['total_logged']
            pc = game.run_to(None, polls=400000)
            end = game.call('get_trace_log', {'count': 1})['total_logged']
            lines = []
            while pos < end:
                chunk = game.call('get_trace_log', {'start': pos, 'count': min(1000, end - pos)})
                if chunk.get('overrun'):
                    raise RuntimeError('trace ring overrun')
                lines += [f'0 {ln}' for ln in chunk['lines']]
                pos += len(chunk['lines'])
            game.call('set_trace_log', {'enabled': False})
            ram = game.read(0, 0x2000)
            rows.append({'colours': length, 'stop': pc, 'fastok': ram[0x17e1], 'queue_count': ram[0x260],
                         'first_colour': ram[0x271] | ram[0x279] << 8, 'state_2104': ram[0x104],
                         'paths': [(path, cyc) for _, path, cyc in dispatch_paths(lines)],
                         'fastok_writes': [m[1] for m in (re.search(r'\s(STZ|STA|INC|DEC) \$37E1\s', ln) for ln in lines) if m]})
    if out:
        Path(out).write_text(json.dumps({'head': head, 'rows': rows}))
    return head, rows


def configure(game, rom):
    """Builds with palette timing (src/palette's configure at bank $46 $5B03,
    since palette-lag): run it once from a RAM stub, as the menu and the reset
    do after a change of $2100 bits 3-5, so a mode written by the debugger
    gets its WAITR and ANIMR. Builds without it: nothing. Stops where it
    started (the main-loop hook)."""
    data = Path(rom).read_bytes()
    if data[0x46 * 0x2000 + 0x1b03] != 0x4c:
        return
    cpu = game.call('get_huc6280_status')
    pc = int(cpu['PC'], 16)
    stub = bytes([0x43, 0x04, 0x48, 0xa9, 0x46, 0x53, 0x04, 0x20, 0x03, 0x5b, 0x68, 0x53, 0x04, 0x4c, pc & 0xff, pc >> 8])
    game.write(0x3f00 - 0x2000, stub)
    saved = {k: int(cpu[k], 16) for k in ('A', 'X', 'Y', 'P')}
    game.reg('PC', 0x3f00)
    game.call('set_breakpoint', {'address': f'{0x3f0d:x}', 'memory_area': 'cpu_addr', 'execute': True})
    game.run_to('3F0D', polls=40000)
    game.call('remove_breakpoint', {'address': f'{0x3f0d:x}', 'memory_area': 'cpu_addr'})
    for k, v in saved.items():
        game.reg(k, v)
    game.reg('PC', pc)


def updates(events):
    """Per completed update: (counter after it, clocks the update took from
    its waking vblank, clocks left before the next vblank; negative = the
    update ran past it, a lag frame)."""
    rows, prev_done = [], None
    vb = [e[1] for e in events if e[0] == 'vblank']
    for kind, clock, counter, _ in events:
        if kind != 'update-done':
            continue
        if prev_done is not None:
            wake = min((v for v in vb if v > prev_done), default=None)
            after = [v for v in vb if wake is not None and v > wake]
            if wake is not None and after:
                rows.append((counter, clock - wake, after[0] - clock))
        prev_done = clock
    return rows


def end_frame(trace, stage):
    """First frame of the stage-end transition (the update counter stops
    there by design): a cinema flag, another stage, or 5-4's boss dead."""
    for t in trace:
        if t['master'] != 0 or t['stage'] != stage or (stage == 15 and t['boss'] == 0 and t['f'] > 100):
            return t['f']
    return len(trace)


def stats(trace, stage):
    d = deltas(trace)
    end = end_frame(trace, stage)
    lag = [i for i in range(1, end) if d[i] == 0]
    dbl = [i for i in range(1, end) if d[i] > 1]
    return {'frames': len(trace), 'end': end, 'lag': lag, 'double': dbl}


def report(runs, variants):
    lines = []
    head = ['run', 'build / mode', 'frames', 'play frames', 'lag frames', 'double', 'first lag frames',
            'first diff vs 1.11 ORIGINAL', 'first diff vs 1.10']
    lines.append('| ' + ' | '.join(head) + ' |')
    lines.append('|' + '---|' * len(head))
    for run in runs:
        stage = load_run(run)['stage']
        tr = {v: json.loads(trace_path(run, v).read_text()) for v in variants if trace_path(run, v).exists()}
        for v in variants:
            if v not in tr:
                continue
            s = stats(tr[v], stage)
            a = first_diff(tr['original'], tr[v]) if 'original' in tr and v != 'original' else None
            b = first_diff(tr['v1.10'], tr[v]) if 'v1.10' in tr and v != 'v1.10' else None
            lines.append(f"| {run} | {v} | {s['frames']} | {s['end']} | {len(s['lag'])} | {len(s['double'])} | "
                         f"{', '.join(map(str, s['lag'][:6]))} | {'-' if a is None else a} | {'-' if b is None else b} |")
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    rec = sub.add_parser('record')
    rec.add_argument('run')
    rec.add_argument('variant')
    sv = sub.add_parser('survey')
    sv.add_argument('--runs', nargs='*')
    sv.add_argument('--variants', nargs='*')
    mg = sub.add_parser('margin')
    mg.add_argument('run')
    mg.add_argument('variant')
    mg.add_argument('start', type=int)
    mg.add_argument('frames', type=int)
    mg.add_argument('--raw', action='store_true')
    it = sub.add_parser('itrace')
    it.add_argument('run')
    it.add_argument('variant')
    it.add_argument('start', type=int)
    it.add_argument('frames', type=int)
    it.add_argument('out')
    ev = sub.add_parser('events')
    ev.add_argument('run')
    ev.add_argument('--variants', nargs='*')
    ev.add_argument('--out', default=str(OUT / 'events'))
    ee = sub.add_parser('e2e')
    ee.add_argument('--modes', nargs='*')
    ee.add_argument('--run', default='1-1')
    ee.add_argument('--rom', default=str(ROM_111))
    ee.add_argument('--out', default=str(OUT / 'e2e'))
    lt = sub.add_parser('loadtime')
    lt.add_argument('--stages', nargs='*', type=int)
    lt.add_argument('--modes', nargs='*')
    lt.add_argument('--rom', default=str(ROM_111))
    pr = sub.add_parser('pairs')
    pr.add_argument('--pairs', nargs='*', help='mode1:mode2 (default: all 36)')
    pr.add_argument('--run', default='3-2')
    pr.add_argument('--frames', type=int, default=1200)
    pr.add_argument('--rom', default=str(ROM_111))
    pr.add_argument('--out', default=str(OUT / 'pairs'))
    fo = sub.add_parser('fastok')
    fo.add_argument('--rom', default=str(ROM_111))
    fo.add_argument('--lengths', nargs='*', type=int, default=list(range(198, 213)))
    fo.add_argument('--out')
    dp = sub.add_parser('dispatch')
    dp.add_argument('run')
    dp.add_argument('start', type=int)
    dp.add_argument('frames', type=int)
    dp.add_argument('--variants', nargs='*')
    sub.add_parser('report')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.command == 'record':
        trace = record(args.run, args.variant)
        (OUT / 'traces').mkdir(exist_ok=True)
        trace_path(args.run, args.variant).write_text(json.dumps(trace))
    elif args.command == 'margin':
        events = margin(args.run, args.variant, args.start, args.frames)
        if args.raw:
            for kind, clock, c, x in events:
                print(f'{kind:12s} +{clock:8d} clk  line {clock / 1365:7.1f}  counter {c}  ryu_x {x}')
        for c, busy, left in updates(events):
            print(f'{args.run} {args.variant:10s} update->counter {c:3d}  busy {busy:7d} clk ({busy / 1365:6.1f} lines)  '
                  f'left {left:7d} clk ({left / 1365:6.1f} lines){"  OVERRUN" if left < 0 else ""}')
    elif args.command == 'itrace':
        itrace(args.run, args.variant, args.start, args.frames, args.out)
    elif args.command == 'events':
        folder = Path(args.out)
        folder.mkdir(parents=True, exist_ok=True)
        res = {}
        for v in args.variants or ['original', 'apocalypse', 'sms', 'gb dmg', 'nes-a', 'nes-b']:
            res[v] = event_run(args.run, v, folder / f'{args.run}.{v.replace(" ", "")}.json')
        ref = res.get('original')
        for v, fr in res.items():
            if v == 'original' or ref is None:
                continue
            diff, worst, where = 0, 0, None
            for n, (a, b) in enumerate(zip(ref, fr)):
                ta = [e[0] for e in a if not e[1].startswith('VCE')]
                tb = [e[0] for e in b if not e[1].startswith('VCE')]
                va = [e[0] for e in a if e[1].startswith('VCE')]
                vb = [e[0] for e in b if e[1].startswith('VCE')]
                if ta != tb or va != vb:
                    diff += 1
                    d = max([abs(x - y) for x, y in zip(ta, tb)] + [0])
                    if len(ta) != len(tb):
                        d = max(d, FRAME_CLOCKS)
                    if d > worst:
                        worst, where = d, n
            print(f"{args.run} {v:10s} frames {len(fr)}: frames whose interrupt/pad-read/VCE-write clocks differ from ORIGINAL: {diff}; "
                  f"largest interrupt/pad-read shift {worst} clk (frame {where})", flush=True)
    elif args.command == 'e2e':
        folder = Path(args.out)
        folder.mkdir(parents=True, exist_ok=True)
        ref = None
        for mode in args.modes or list(MODE_BITS):
            status, hits, trace = e2e(mode, args.run, Path(args.rom), folder / f'{args.run}.{mode.replace(" ", "")}.json')
            if ref is None:
                ref = (status, hits, trace)
            keys = ['c', 'sat', 'ryu', 'timer', 'stage', 'area', 'health', 'cam', 'master']
            diff = next((i for i, (a, b) in enumerate(zip(ref[2], trace)) if any(a[k] != b[k] for k in keys)), None)
            dh = [(h[0], h[2] - r[2]) for h, r in zip(hits, ref[1]) if h[2] != r[2] or h[0] != r[0]]
            margins = [FRAME_CLOCKS - ((h[2] - VBLANK_PHASE) % FRAME_CLOCKS) for h in hits]
            print(f"{mode:10s} $2100={status['opt']:02x} save status {status['save_status']} boot frames {status['boot_frames']} "
                  f"first update {status['first_update'] - ref[0]['first_update']:+d} clk; sound commands {len(hits)} "
                  f"(vs first mode: {len(ref[1])}), differing clocks {len(dh)} {dh[:4]}; min margin to next vblank "
                  f"{min(margins) if margins else None}; first differing frame {diff} of {len(trace)}", flush=True)
    elif args.command == 'loadtime':
        stages = args.stages if args.stages is not None else list(range(22))
        modes = args.modes or list(MODE_BITS)
        for stage in stages:
            ref = None
            for mode in modes:
                ev = load_timing(Path(args.rom), stage, MODE_BITS[mode])
                if ref is None:
                    ref = ev
                cells = []
                for i, (kind, clock) in enumerate(ev):
                    r = ref[i][1] if i < len(ref) and ref[i][0] == kind else None
                    vb, into = divmod(clock - VBLANK_PHASE, FRAME_CLOCKS)
                    cells.append(f"{kind[0]} vblank {vb} +{into}" + ('' if r is None else f" ({clock - r:+d})"))
                print(f'stage {stage:2d} {mode:10s} ' + ' '.join(cells), flush=True)
    elif args.command == 'pairs':
        folder = Path(args.out)
        folder.mkdir(parents=True, exist_ok=True)
        pairs = [tuple(x.split(':')) for x in args.pairs] if args.pairs else \
            [(a, b) for a in PAIR_MODES for b in PAIR_MODES]
        pairs = [('original', 'original')] + [x for x in pairs if x != ('original', 'original')]
        ref = None
        for mode1, mode2 in pairs:
            path = folder / f'{args.run}.{mode1.replace(" ", "")}.{mode2.replace(" ", "")}.json'
            if path.exists():
                data = json.loads(path.read_text())
                res = (data['status'], data['trace'])
            else:
                res = pair_run(mode1, mode2, args.run, args.frames, Path(args.rom), path)
            if ref is None:
                ref = res
            r = pair_compare(ref, res)
            print(f"{mode1:10s} -> {mode2:10s} $2100={r['opt2']:02x} first update {r['first_update']:+d} clk; "
                  f"sound RAM differs in {r['snd_frames']} frames (first {r['snd_first']}); "
                  f"counter/Ryu/stage differ in {r['game_frames']} (first {r['game_first']}); "
                  f"lag frames {r['lag'][:8]}; irq clocks differ in {r['irq_frames']} frames, max {r['irq_max']} clk", flush=True)
    elif args.command == 'fastok':
        head, rows = fastok_probe(Path(args.rom), args.lengths, out=args.out)
        print(f"worker call at frame {head['frame']}, {head['clock_before_vblank']} clk before the vblank, queue {head['queue']}")
        for r in rows:
            print(f"{r['colours']:4d} colours: stop {r['stop']} FASTOK {r['fastok']:02x} queue {r['queue_count']} "
                  f"first colour {r['first_colour']} $2104 {r['state_2104']:02x} FASTOK writes {r['fastok_writes']} "
                  f"vblank paths {r['paths']}", flush=True)
    elif args.command == 'dispatch':
        import collections
        import gzip
        for v in args.variants or ['original', 'gb dmg']:
            tmp = OUT / 'work' / f'dispatch-{v.replace(" ", "")}.gz'
            tmp.parent.mkdir(parents=True, exist_ok=True)
            itrace(args.run, v, args.start, args.frames, tmp)
            with gzip.open(tmp, 'rt') as fh:
                paths = dispatch_paths(fh)
            tmp.unlink()
            print(f"{args.run} {v:10s} frames {args.start}-{args.start + args.frames - 1}: "
                  f"{dict(collections.Counter((p, c) for _, p, c in paths))}", flush=True)
    elif args.command == 'report':
        print(report([p.stem for p in RUN_FILES], list(VARIANTS)))
    elif args.command == 'survey':
        runs = args.runs or [p.stem for p in RUN_FILES]
        survey(runs, args.variants or list(VARIANTS))


if __name__ == '__main__':
    main()
