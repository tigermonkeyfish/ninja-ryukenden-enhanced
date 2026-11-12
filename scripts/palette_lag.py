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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    rec = sub.add_parser('record')
    rec.add_argument('run')
    rec.add_argument('variant')
    sv = sub.add_parser('survey')
    sv.add_argument('--runs', nargs='*')
    sv.add_argument('--variants', nargs='*')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.command == 'record':
        trace = record(args.run, args.variant)
        (OUT / 'traces').mkdir(exist_ok=True)
        trace_path(args.run, args.variant).write_text(json.dumps(trace))
    elif args.command == 'survey':
        runs = args.runs or [p.stem for p in RUN_FILES]
        survey(runs, args.variants or list(VARIANTS))


if __name__ == '__main__':
    main()
