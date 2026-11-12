#!/usr/bin/env python3
"""Does the game stay playable, with the player's settings, when the saved
settings cannot be loaded or saved? (Headless Geargrafx; see
docs/validation/bram-fallback.md for how each case is simulated.)

Scenarios (each a cold boot of the candidate, a Run in the Select popup with
non-default settings, then 2,843 frames of a stored input run):

  control          a blank formatted memory: the save works (SETTINGS SAVED)
  no-memory        no backup RAM in the machine (pinned emulator)
  no-memory-bus    NG_BRAM_MODEL=openbus: nothing answers at the bank
  full-memory      a formatted memory filled with other games' files
  write-error      NG_BRAM_MODEL=readonly: writes are ignored, ERROR 4
  write-error-old  as write-error, but a settings entry saved earlier is
                   there: the old settings load, the new ones are used, and
                   the save fails

For each: the boot status and settings (reached within a frame bound); the
popup's status line; after Run the status, $2100/$3227, the same stage
restarted, the palette's VCE (the SMS table, equal to the control's); the
replay compared frame by frame with the control of the same settings (work
RAM without the status byte, VCE, sprite table, VRAM, the screen);
Ryu moved, took a hit or (No Damage) did not; the backup RAM byte for byte as
it was; after a power cycle the expected load. Then the negative controls:
the assertions run against what they must reject.

Writes report.json to the output folder.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import zlib

import bram_image as bi
import check_bram as cb
from check_menu import FIRST_UPDATE, mode_expected, press
from comparison_video import Game

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / 'research/comparison-runs/1-1.json'
STATUS_BYTE = 0x105
BOOT_FRAMES = 400             # the baseline's first update is frame 163
LOOSE = ('ram', 'stack')    # may differ on isolated frames only (stack_frames)
STACK_FRAMES = 0.05          # of the replay's frames may differ in RAM ...
MAX_RUN = 6                  # ... never more than this many in a row ...
MAX_ADDRESSES = 8            # ... and only at this many offsets in all
RESTART_FRAMES = 300          # Run to the restarted stage's first update
HEALTH, HURT, LIVES, CAMERA, STATE, STAGE = 0xead, 0xeae, 0xeaf, 0x20f, 0xeab, 0xe5f
# The player's settings: Smooth Parallax OFF, No Damage ON, NES Firewheel ON,
# palette SMS, language Japanese. $2100 = $01|$02|$04|$38|$80 (the menu sets
# bit 7 with SMS), $3227 = 0.
WANT = {'parallax': 1, 'no damage': 1, 'firewheel': 1, 'palette': 0x38, 'language': 0}
WANT_BYTES = (0xbf, 0)
BLANK = 'empty-8800'
OLD_SAVE = 'others-before'    # holds our entry: HELL, No Damage, Chinese ($1A, 2)


def inputs(frames=None):
    run = json.loads(RUN.read_text())
    seq = [buttons for count, buttons in run['segments'] for _ in range(count)]
    return seq[:frames] if frames else seq


# ---- driving the menu ----------------------------------------------------

PALETTE_ORDER = [0x00, 0x18, 0x08, 0x28, 0x38, 0x10]
LANGUAGE_ORDER = [1, 0, 2]            # ENGLISH, JAPANESE, CHINESE


def choose(game, want):
    """Open the popup and step every row to `want` ({row: value}); leave it
    open. Returns the status line shown. The draft ($2101) says where each
    row stands."""
    text = cb.open_menu(game)
    draft = game.read(0x101, 1)[0]
    now = {'parallax': draft & 1, 'no damage': draft >> 1 & 1, 'firewheel': draft >> 2 & 1,
           'palette': draft & 0x38, 'language': draft >> 6 & 3}
    row = 0
    for name in ('parallax', 'no damage', 'firewheel', 'palette', 'language'):
        row += 1
        if name not in want:
            press(game, 'down')
            continue
        press(game, 'down')
        if name in ('parallax', 'no damage', 'firewheel'):
            count = (want[name] - now[name]) % 2
        elif name == 'palette':
            order = PALETTE_ORDER
            count = (order.index(want[name]) - order.index(now[name])) % len(order)
        else:
            order = LANGUAGE_ORDER
            count = (order.index(want[name]) - order.index(now[name])) % len(order)
        for _ in range(count):
            press(game, 'right')
    return text


def run_menu(game, work):
    """Press Run in the open popup and count frames to the restarted stage's
    first update (bounded); settle like cb.accept. Returns the frame count."""
    game.press({'run'})
    game.step(2)
    game.press(set())
    game.call('set_breakpoint', {'address': FIRST_UPDATE, 'memory_area': 'rom', 'execute': True})
    try:
        for frames in range(3, RESTART_FRAMES + 3):
            game.step(1)
            if game.call('debug_get_status').get('pc') == '8457':
                break
        else:
            raise RuntimeError(f'the stage did not restart within {RESTART_FRAMES} frames')
    finally:
        game.call('remove_breakpoint', {'address': FIRST_UPDATE, 'memory_area': 'rom'})
    cb.normalize(game, work)
    game.step(40)
    return frames


# ---- tracing ---------------------------------------------------------------

def snapshot(game):
    """The per-frame fingerprint: work RAM without the status byte and the
    stack page, the stack page and the stack pointer apart, VCE, sprite table, VRAM and the screen."""
    ram = bytearray(game.read(0, 0x2000))
    sp = game.call('get_huc6280_status')['SP']
    live = max(0x106, int(sp, 16) - 0x2000 + 1)          # above the pointer; the bytes below are dead
    stack = bytes(ram[live:0x200]) + sp.encode()
    ram[STATUS_BYTE] = 0
    ram[0x106:0x200] = bytes(0xfa)          # the stack page: compared apart, see first_difference
    return ({'ram': hashlib.sha1(ram).hexdigest(), 'raw': zlib.compress(bytes(ram)),
             'stack': hashlib.sha1(stack).hexdigest(),
             'vce': hashlib.sha1(game.read(0, 1024, area=8)).hexdigest(),
             'sat': hashlib.sha1(game.read(0, 512, area=6)).hexdigest(),
             'vram': hashlib.sha1(game.read(0, 0x10000, area=4)).hexdigest(),
             'screen': hashlib.sha1(game.screenshot()).hexdigest()},
            {'health': ram[HEALTH], 'lives': ram[LIVES], 'camera': ram[CAMERA] | ram[CAMERA + 1] << 8,
             'state': ram[STATE], 'options': ram[0x100], 'language': ram[0x1227], 'stage': ram[STAGE]})


def replay(game, seq):
    """Drive `seq` (button sets) one frame at a time."""
    prints, facts = [], []
    for buttons in seq:
        game.press(set(buttons))
        game.step(1)
        p, f = snapshot(game)
        prints.append(p)
        facts.append(f)
    game.press(set())
    return prints, facts


def first_difference(a, b):
    """(frame, fields) of the first frame at which two traces differ, or None."""
    if len(a) != len(b):
        return (min(len(a), len(b)), ['length'])
    for k, (x, y) in enumerate(zip(a, b)):
        fields = [name for name in x if name not in LOOSE and name != 'raw' and x[name] != y[name]]
        if fields:
            return (k, fields)
    return None


def stack_frames(a, b):
    """Frames in which work RAM or the stack page differs; (count, longest
    run). A frame ends a few cycles either side of an update of a scratch
    byte or a pushed local when the save has shifted the phase by those
    cycles (seen: one zero-page temporary sampled one frame off, and one
    byte of the stack page); the next frame is equal again. The picture,
    the VCE, the sprites and VRAM are compared strictly."""
    flags = [x['ram'] != y['ram'] or x['stack'] != y['stack'] for x, y in zip(a, b)]
    run = longest = 0
    for flag in flags:
        run = run + 1 if flag else 0
        longest = max(longest, run)
    return sum(flags), longest


def differing_addresses(a, b):
    """The work RAM offsets (stack page excluded: it is masked) that differ in any frame."""
    found = set()
    for x, y in zip(a, b):
        if x['ram'] != y['ram']:
            u, v = zlib.decompress(x['raw']), zlib.decompress(y['raw'])
            found.update(i for i in range(0x2000) if u[i] != v[i])
    return sorted(found)


def play(emulator, rom, image, model, seq, want, workdir):
    """One scenario's session. Returns everything observed."""
    os.environ.pop('NG_BRAM_MODEL', None)
    if model:
        os.environ['NG_BRAM_MODEL'] = model
    work = Path(tempfile.mkdtemp(prefix='fallback-', dir=workdir))
    seen = {'model': model or 'none'}
    try:
        with Game(emulator, work) as game:
            seen['boot'] = boot = cb.boot(game, rom, image, work)
            seen['has_backup_ram'] = game.backup_ram() is not None
            seen['bram_after_boot'] = game.backup_ram()
            if want is None:                       # control with the game's own settings
                seen['menu_status'] = cb.open_menu(game)
            else:
                seen['menu_status'] = choose(game, want)
            seen['restart_frames'] = run_menu(game, work)
            ram = game.read(0, 0x2000)
            seen['after_run'] = {'status': bi.STATUS[ram[0x105]], 'options': ram[0x100],
                                 'language': ram[0x1227], 'stage': ram[STAGE],
                                 'stage_before': boot['stage'], 'health': ram[HEALTH],
                                 'camera': ram[CAMERA] | ram[CAMERA + 1] << 8}
            seen['vce'] = game.read(0, 1024, area=8)
            seen['vce_sms'] = mode_expected(game, 0x38)
            seen['prints'], seen['facts'] = replay(game, seq)
            seen['bram_end'] = game.backup_ram()
            seen['status_end'] = bi.STATUS[game.read(0x105, 1)[0]]
    finally:
        shutil.rmtree(work, ignore_errors=True)
        os.environ.pop('NG_BRAM_MODEL', None)
    return seen


def power_cycle(emulator, rom, image, model, workdir):
    os.environ.pop('NG_BRAM_MODEL', None)
    if model:
        os.environ['NG_BRAM_MODEL'] = model
    work = Path(tempfile.mkdtemp(prefix='fallback-', dir=workdir))
    try:
        with Game(emulator, work) as game:
            found = cb.boot(game, rom, image, work)
    finally:
        shutil.rmtree(work, ignore_errors=True)
        os.environ.pop('NG_BRAM_MODEL', None)
    return {'status': bi.STATUS[found['status']], 'options': found['options'], 'language': found['language']}


# ---- assertions ------------------------------------------------------------

def judge(seen, expect, control, reference_want=WANT_BYTES, seq_moves=True):
    """The problems found in one scenario's observations. `expect`: boot
    status, settings in force at boot, run status, bram afterwards (None: as
    before); `control`: the control's observations with the same settings."""
    problems = []

    def need(what, found, wanted):
        if found != wanted:
            problems.append(f'{what}: {found!r}, expected {wanted!r}')

    boot, run = seen['boot'], seen['after_run']
    need('has backup RAM', seen['has_backup_ram'], expect['has_backup_ram'])
    need('boot status ($2105)', bi.STATUS[boot['status']], expect['boot_status'])
    need('boot settings ($2100,$3227)', (boot['options'], boot['language']), expect['boot_settings'])
    if not boot['first_update_frame'] <= BOOT_FRAMES:
        problems.append(f"boot took {boot['first_update_frame']} frames to 1-1, bound {BOOT_FRAMES}")
    need('popup status line', seen['menu_status'], expect['menu_status'])
    need('status after Run', run['status'], expect['run_status'])
    need('$2100 after Run', run['options'], reference_want[0])
    need('$3227 after Run', run['language'], reference_want[1])
    need('same stage restarted', run['stage'], run['stage_before'])
    need('health after the restart', run['health'], 16)
    need('camera after the restart', run['camera'], 0)
    need('SMS palette in the VCE', seen['vce'] == seen['vce_sms'], True)
    need('VCE equals the control\'s', seen['vce'] == control['vce'], True)
    need('backup RAM at the end', seen['bram_end'], expect['bram_end'])
    need('status at the end of the replay', seen['status_end'], expect['run_status'])
    facts = seen['facts']
    need('$2100 in force through the replay', {f['options'] for f in facts}, {reference_want[0]})
    need('$3227 in force through the replay', {f['language'] for f in facts}, {reference_want[1]})
    need('stage through the replay', {f['stage'] for f in facts}, {run['stage_before']})
    cameras = [f['camera'] for f in facts]
    if not (max(cameras) - cameras[0] >= 700 and len({f['state'] for f in facts}) >= 4):
        problems.append(f'Ryu did not move and act: camera {cameras[0]}..{max(cameras)}, '
                        f"{len({f['state'] for f in facts})} states")
    if reference_want[0] & 2:
        need('No Damage: lowest health', min(f['health'] for f in facts), 16)
        need('No Damage: lives', {f['lives'] for f in facts}, {facts[0]['lives']})
    difference = first_difference(seen['prints'], control['prints'])
    if difference:
        problems.append(f'the replay differs from the control at frame {difference[0]} in {difference[1]}')
    count, longest = stack_frames(seen['prints'], control['prints'])
    if count > STACK_FRAMES * len(facts) or longest > MAX_RUN or len(differing_addresses(seen['prints'], control['prints'])) > MAX_ADDRESSES or seen['prints'][-1]['ram'] != control['prints'][-1]['ram']:
        problems.append(f'work RAM differs from the control in {count} of {len(facts)} frames, '
                        f'{longest} in a row, offsets {[hex(a) for a in differing_addresses(seen["prints"], control["prints"])]}')
    return problems


# ---- the scenarios ---------------------------------------------------------

def scenarios():
    images = bi.matrix()
    after_blank = bi.expected_save(images[BLANK], *WANT_BYTES)[1]
    after_old = bi.expected_save(images[OLD_SAVE], *WANT_BYTES)[1]
    return {
        'control': dict(image=images[BLANK], model=None, control='control', has_backup_ram=True,
                        boot_status='READY', boot_settings=bi.DEFAULTS, menu_status='BACKUP MEMORY FOUND',
                        run_status='OK', bram_end=after_blank, cycle=('LOADED', *WANT_BYTES)),
        'no-memory': dict(image=None, model=None, control='control', has_backup_ram=False,
                          boot_status='NONE', boot_settings=bi.DEFAULTS, menu_status='NO BACKUP MEMORY',
                          run_status='NONE', bram_end=None, cycle=('NONE', *bi.DEFAULTS)),
        'no-memory-bus': dict(image=images[BLANK], model='openbus', control='control', has_backup_ram=True,
                              boot_status='NONE', boot_settings=bi.DEFAULTS, menu_status='NO BACKUP MEMORY',
                              run_status='NONE', bram_end=images[BLANK], cycle=('NONE', *bi.DEFAULTS)),
        'full-memory': dict(image=images['full'], model=None, control='control', has_backup_ram=True,
                            boot_status='FULL', boot_settings=bi.DEFAULTS, menu_status='BACKUP MEMORY FULL',
                            run_status='FULL', bram_end=images['full'], cycle=('FULL', *bi.DEFAULTS)),
        'write-error': dict(image=images[BLANK], model='readonly', control='control', has_backup_ram=True,
                            boot_status='READY', boot_settings=bi.DEFAULTS, menu_status='BACKUP MEMORY FOUND',
                            run_status='ERROR 4', bram_end=images[BLANK], cycle=('READY', *bi.DEFAULTS)),
        'control-old': dict(image=images[OLD_SAVE], model=None, control='control-old', has_backup_ram=True,
                            boot_status='LOADED', boot_settings=(0x1a, 2), menu_status='SETTINGS LOADED',
                            run_status='OK', bram_end=after_old, cycle=('LOADED', *WANT_BYTES)),
        'write-error-old': dict(image=images[OLD_SAVE], model='readonly', control='control-old',
                                has_backup_ram=True, boot_status='LOADED', boot_settings=(0x1a, 2),
                                menu_status='SETTINGS LOADED', run_status='ERROR 4', bram_end=images[OLD_SAVE],
                                cycle=('LOADED', 0x1a, 2)),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--emulator', type=Path, required=True, help='the pinned headless Geargrafx')
    parser.add_argument('--model-emulator', type=Path, required=True,
                        help='the test-only build with NG_BRAM_MODEL (research/tools/bram-save/locktest_patch.py)')
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--frames', type=int, help='replay only this many frames (a trial; the movement '
                        'and fall-back assertions need the whole run)')
    args = parser.parse_args()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    seq = inputs(args.frames)
    table = scenarios()
    report = {'rom_sha256': hashlib.sha256(args.candidate.read_bytes()).hexdigest(),
              'emulator_sha256': hashlib.sha256(args.emulator.read_bytes()).hexdigest(),
              'model_emulator_sha256': hashlib.sha256(args.model_emulator.read_bytes()).hexdigest(),
              'replay_frames': len(seq), 'physical_hardware_tested': False, 'scenarios': {}, 'negative': {}}
    seen = {}

    def observe(name, spec=None, want=WANT, frames=None, image=None):
        spec = spec or table[name]
        emulator = args.model_emulator if spec['model'] else args.emulator
        return play(emulator, args.candidate, spec['image'] if image is None else image, spec['model'],
                    frames if frames is not None else seq, want, args.output)

    ok = True
    for name, spec in table.items():
        seen[name] = observe(name)
        control = seen[spec['control']]
        problems = judge(seen[name], spec, control)
        cycle = power_cycle(args.model_emulator if spec['model'] else args.emulator, args.candidate,
                            seen[name]['bram_end'] if spec['image'] is not None else None,
                            spec['model'], args.output)
        if (cycle['status'], cycle['options'], cycle['language']) != spec['cycle']:
            problems.append(f"power cycle: {cycle}, expected {spec['cycle']}")
        facts = seen[name]['facts']
        report['scenarios'][name] = {
            'boot': {k: v for k, v in seen[name]['boot'].items()}, 'menu_status': seen[name]['menu_status'],
            'run_status': seen[name]['after_run']['status'], 'restart_frames': seen[name]['restart_frames'],
            'ram_transient_frames': stack_frames(seen[name]['prints'], seen[spec['control']]['prints'])[0],
            'ram_offsets_ever_differing': [hex(a) for a in differing_addresses(seen[name]['prints'], seen[spec['control']]['prints'])],
            'camera_range': [min(f['camera'] for f in facts), max(f['camera'] for f in facts)],
            'health_range': [min(f['health'] for f in facts), max(f['health'] for f in facts)],
            'lives': sorted({f['lives'] for f in facts}), 'power_cycle': cycle,
            'bram_bytes_changed': None if seen[name]['bram_end'] is None or spec['image'] is None
            else sum(a != b for a, b in zip(spec['image'], seen[name]['bram_end'])),
            'problems': problems, 'ok': not problems}
        ok &= not problems
        print(name, 'PASS' if not problems else problems, flush=True)
    # ---- negative controls: the assertions must be able to fail -------------
    negative = report['negative']

    def must_flag(name, problems, *needles):
        missing = [n for n in needles if not any(n in p for p in problems)]
        negative[name] = {'flagged': problems if len(problems) < 8 else problems[:8], 'missing': missing,
                          'ok': bool(problems) and not missing}
        print('negative', name, 'bites' if negative[name]['ok'] else f'DID NOT BITE {missing}', flush=True)
        return negative[name]['ok']

    control = seen['control']
    for name, spec in table.items():
        if name == 'control':
            continue
        # This scenario's expectations (boot status, run status, bram) against the control's observations.
        kept = {k: spec[k] for k in ('boot_status', 'boot_settings', 'menu_status', 'run_status')}
        needles = [n for n, k in (('boot status', 'boot_status'), ('boot settings', 'boot_settings'),
                                  ('popup status line', 'menu_status'), ('status after Run', 'run_status'))
                   if kept[k] != table['control'][k]]
        ok &= must_flag(f'{name} expectations against the control run', judge(control, spec, control), *needles)
        # The control's expectations against this scenario's observations.
        ok &= must_flag(f'control expectations against the {name} run',
                        judge(seen[name], table['control'], control), *needles)
    default = observe('control', want={})
    problems = judge(default, table['control'], control)
    ok &= must_flag('default settings instead of the player\'s', problems, '$2100 after Run', 'VCE equals',
                    'differs from the control')
    hit = [f['health'] for f in default['facts']]
    negative['default settings instead of the player\'s']['health_range_default'] = [min(hit), max(hit)]
    ok &= must_flag('No Damage assertion against a default-settings game',
                    judge(default, dict(table['control']), control, reference_want=(0x02, 0)), 'No Damage: lowest health')
    frozen = observe('control', frames=[[]] * len(seq))
    ok &= must_flag('no input (a frozen game)', judge(frozen, table['control'], control),
                    'Ryu did not move', 'differs from the control')
    english = observe('control', want=dict(WANT, language=1))
    negative['language English instead of Japanese (information)'] = {
        'first_difference': first_difference(english['prints'], control['prints'])}
    # Synthetic faults in a copy of a trace.
    altered = dict(seen['no-memory'], prints=[dict(p) for p in seen['no-memory']['prints']])
    altered['prints'][len(seq) // 2]['screen'] = '0' * 40
    ok &= must_flag('one wrong screen hash', judge(altered, table['no-memory'], control), 'differs from the control')
    altered = dict(seen['no-memory'], prints=[dict(p) for p in seen['no-memory']['prints']])
    for k in range(len(seq) // 2, len(seq) // 2 + MAX_RUN + 1):
        altered['prints'][k]['ram'] = '0' * 40
    ok &= must_flag('a long run of RAM differences', judge(altered, table['no-memory'], control), 'work RAM differs')
    altered = dict(seen['write-error'], bram_end=bytes([seen['write-error']['bram_end'][0] ^ 1]) + seen['write-error']['bram_end'][1:])
    ok &= must_flag('one BRAM byte changed', judge(altered, table['write-error'], control), 'backup RAM at the end')
    report['ok'] = bool(ok)
    json.dump(report, (args.output / 'report.json').open('w'), indent=2)
    print('PASS' if ok else 'FAIL')
    raise SystemExit(0 if ok else 1)


if __name__ == '__main__':
    main()
