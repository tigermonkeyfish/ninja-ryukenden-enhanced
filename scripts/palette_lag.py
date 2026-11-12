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
from comparison_video import Game, start_point, start_stage, make_seed, STAGE_NAMES  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
EMULATOR = Path('/workspace/build/toolchain/geargrafx/platforms/linux/geargrafx')
ORIGINAL = Path('/workspace/DO_NOT_COMMIT_ROMS/Ninja Ryukenden (J).pce')
ROMS = Path('/workspace/roms')
ROM_111 = ROMS / 'Ninja Ryukenden - Enhanced v1.11-dev (apocalypse, reset 2).pce'
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
    return trace


def trace_path(runname, variant):
    return OUT / 'traces' / f'{runname}.{variant.replace(" ", "")}.json'


def survey(runs, variants):
    (OUT / 'traces').mkdir(parents=True, exist_ok=True)
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
    elif args.command == 'report':
        print(report([p.stem for p in RUN_FILES], list(VARIANTS)))
    elif args.command == 'survey':
        runs = args.runs or [p.stem for p in RUN_FILES]
        survey(runs, args.variants or list(VARIANTS))


if __name__ == '__main__':
    main()
