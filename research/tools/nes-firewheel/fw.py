"""Fire Wheel probe helpers (headless Geargrafx, project harness)."""
import json
import os
import sys
import tempfile
from pathlib import Path

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / 'scripts'))
from comparison_video import Game, make_seed, start_point, start_stage, StepError  # noqa: E402

EMU = os.environ['NG_EMULATOR']
OUT = Path(os.environ.get('NFW_WORK', 'build/nes-firewheel')).resolve()
ORIGINAL = os.environ['NFW_ORIGINAL']
SEED = OUT / 'seed.state'
RUNS = WT / 'research/comparison-runs'


def seed():
    if not SEED.exists():
        make_seed(EMU, ORIGINAL, SEED)
    return SEED


def session(name):
    (OUT / 'logs').mkdir(parents=True, exist_ok=True)
    d = tempfile.mkdtemp(prefix=name + '-', dir=OUT / 'logs')
    return Game(EMU, d)


def begin(game, rom, stage, flags=None):
    """Fresh session: load the seed, set options, enter `stage`, stop at update 0."""
    start_point(game, rom, seed(), enhanced=flags is not None)
    if flags:
        game.write(0x100, bytes([flags, flags]))
    start_stage(game, stage)


def call_native(game, routine, a=None):
    """At the gameplay loop ($8457, bank 1), run a synthetic JSR to `routine`
    and return to $8457. Leaves the game paused at $8457, normalized."""
    game.call('set_breakpoint', {'address': '2457', 'memory_area': 'rom', 'execute': True})
    for _ in range(4):
        if game.step(1) is None:
            break
    else:
        raise RuntimeError('$8457 not reached')
    cpu = game.call('get_huc6280_status')
    assert cpu['PC'] == '8457', cpu
    saved = {k: int(cpu[k], 16) for k in ('X', 'Y', 'P', 'S')}
    sp = saved['S']
    game.write(0x100 + sp - 1, bytes([0x56, 0x84]))
    game.reg('S', sp - 2)
    if a is not None:
        game.reg('A', a)
    game.reg('PC', routine)
    game.run_to('8457')
    cpu2 = game.call('get_huc6280_status')
    for k in ('X', 'Y', 'P'):
        game.reg(k, saved[k])
    game.call('remove_breakpoint', {'address': '2457', 'memory_area': 'rom'})
    st = Path(game.logdir) / 'norm.state'
    game.call('save_state_file', {'file_path': str(st)})
    game.call('load_state_file', {'file_path': str(st)})
    return cpu, cpu2


def sample(game):
    r = game.read(0, 0x2000)
    return {
        'health': r[0xead], 'hurt': r[0xeae], 'lives': r[0xeaf],
        'x': r[0xe9e] | r[0xe9f] << 8, 'y': r[0xea0], 'z36': r[0x36], 'z37': r[0x37],
        'kb': r[0xea5:0xeac].hex(), 'n_eff': r[0x110c], 'eff': r[0x110e:0x1113].hex(),
        'wheel': r[0x117a], 'cam': r[0x20f] | r[0x210] << 8, 'area': r[0xe60], 'stage': r[0xe5f],
        'timer': r[0xedb:0xede].hex(), 'score': r[0xed0:0xed6][::-1].hex(), 'master': r[0x240],
        'enemy_x': r[0xf1c:0xf30].hex(), 'enemy_t': r[0xfbc:0xfd0].hex(),
        'cnt': [r[0x1127 + i] | r[0x1136 + i] << 8 for i in range(5)], 'fc': r[0], 'tick': r[0xeda],
    }


def frames_of(run):
    out = []
    for count, buttons in run['segments']:
        out.extend([set(buttons)] * count)
    return out


def call_here(game, routine, a=None):
    """Paused at $8457 (after call_native): synthetic JSR to `routine`, back to $8457."""
    cpu = game.call('get_huc6280_status')
    assert cpu['PC'] == '8457', cpu
    saved = {k: int(cpu[k], 16) for k in ('X', 'Y', 'P', 'S')}
    sp = saved['S']
    game.write(0x100 + sp - 1, bytes([0x56, 0x84]))
    game.reg('S', sp - 2)
    if a is not None:
        game.reg('A', a)
    game.reg('PC', routine)
    game.call('set_breakpoint', {'address': '2457', 'memory_area': 'rom', 'execute': True})
    game.run_to('8457')
    game.call('remove_breakpoint', {'address': '2457', 'memory_area': 'rom'})
    for k in ('X', 'Y', 'P'):
        game.reg(k, saved[k])
