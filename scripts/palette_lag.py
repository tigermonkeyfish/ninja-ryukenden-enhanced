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
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import palette_video as pv                                              # noqa: E402
from comparison_video import Game, start_point, start_stage, make_seed, STAGE_NAMES, NEXT_SEQUENCE  # noqa: E402

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


def step_recording(game, hits, tmp, frame):
    """One frame step; every stop at an armed breakpoint inside it is
    recorded (frame, PC, master clock) and stepped over, then the step goes
    on to the frame's end."""
    while True:
        if game.step(1) is not None:
            return
        pc = game.call('debug_get_status')['pc']
        hits.append((frame, pc, master_clock(game, tmp)))
        area = {'4006': MUSIC_ENTRY}.get(pc)
        if area is None:
            raise RuntimeError(f'unexpected stop at {pc}')
        game.call('remove_breakpoint', {'address': f'{area:x}', 'memory_area': 'rom'})
        game.call('debug_step_into')
        game.call('set_breakpoint', {'address': f'{area:x}', 'memory_area': 'rom', 'execute': True})


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
        previous, since, presses, pressed = None, 0, [200], False
        for frame in range(1, 20000):
            step_recording(game, hits, tmp, -frame)
            since += 1
            ram = game.read(0, 0x300)
            master = bytes(ram[0x240:0x242])
            if master != previous:
                previous, since = master, 0
            if master == b'\x01\x01' and since == 180 and not pressed:
                presses.append(frame)
                pressed = True
            if master in (b'\x00\x00', b'\x01\x00') and since % 300 == 150:
                presses.append(frame)
            for p in presses:
                if frame == p:
                    game.call('controller_button', {'player': 1, 'button': 'run', 'action': 'press'})
                elif frame == p + 2:
                    game.call('controller_button', {'player': 1, 'button': 'run', 'action': 'release'})
            if pressed and master[0] == 0 and frame > presses[-1] + 2:
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
    ee = sub.add_parser('e2e')
    ee.add_argument('--modes', nargs='*')
    ee.add_argument('--run', default='1-1')
    ee.add_argument('--rom', default=str(ROM_111))
    ee.add_argument('--out', default=str(OUT / 'e2e'))
    lt = sub.add_parser('loadtime')
    lt.add_argument('--stages', nargs='*', type=int)
    lt.add_argument('--modes', nargs='*')
    lt.add_argument('--rom', default=str(ROM_111))
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
    elif args.command == 'report':
        print(report([p.stem for p in RUN_FILES], list(VARIANTS)))
    elif args.command == 'survey':
        runs = args.runs or [p.stem for p in RUN_FILES]
        survey(runs, args.variants or list(VARIANTS))


if __name__ == '__main__':
    main()
