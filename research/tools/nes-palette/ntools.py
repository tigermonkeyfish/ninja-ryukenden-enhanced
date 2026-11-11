"""Shared helpers for the NES palette probes (research reference, not a
maintained tool). They reuse the GB palette probes' session helpers
(research/tools/gb-palette/gbtools.py): one seed state of the original, one
fresh session per replay (docs/pc-engine/EMULATOR.md). The work folder is
NES_WORK (default build/nes-palette); it holds seed.state and original.pce."""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ.setdefault('GB_WORK', os.environ.get('NES_WORK', '/workspace/build/nes-palette'))
sys.path.insert(0, str(HERE.parent / 'gb-palette'))
from gbtools import EMU, WORK, RUN_NAMES, Session, cv, h, load_run, queue, ram_palette, vce_words  # noqa: E402,F401

NES = 0x08                   # $2100 bits 3-4 = 01
GB = 0x10


def pc_of(status):
    return int(status['pc'], 16)


def wait_paused(g, polls=200000):
    for _ in range(polls):
        st = g.call('debug_get_status')
        if st.get('paused'):
            return st
    raise TimeoutError('not paused')


def enter_stage(g, stage, on_stop=None, stops=()):
    """cv.start_stage, but execute breakpoints at ROM offsets `stops` (hex
    strings) are kept armed during the stage load and each stop calls
    on_stop(g, status). Ends at the first update ($8457), saved and reloaded
    like cv.start_stage so frame 0 is defined."""
    cpu = g.call('get_huc6280_status')
    assert cpu['PC'] == '83F3', cpu
    saved = {k: int(cpu[k], 16) for k in ('X', 'Y', 'P', 'S')}
    g.write(0x241, bytes([stage]))
    g.write(0x247, bytes([cv.NEXT_SEQUENCE[stage], 0]))
    g.write(0xe65, bytes(22))
    g.write(0xead, bytes([16]))
    sp = saved['S']
    g.write(0x100 + sp - 1, bytes([0xf2, 0x83]))
    g.reg('S', sp - 2)
    g.reg('A', stage)
    g.reg('PC', 0x8244)
    for a in ('23f3',) + tuple(stops):
        g.call('set_breakpoint', {'address': a, 'memory_area': 'rom', 'execute': True})
    while True:
        g.call('debug_continue')
        st = wait_paused(g)
        if st['pc'] == '83F3':
            break
        if on_stop:
            on_stop(g, st)
    for k in ('X', 'Y', 'P'):
        g.reg(k, saved[k])
    g.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'})
    g.call('set_breakpoint', {'address': '2457', 'memory_area': 'rom', 'execute': True})
    while True:
        g.call('debug_continue')
        st = wait_paused(g)
        if st['pc'] == '8457':
            break
        if on_stop:
            on_stop(g, st)
    g.call('remove_breakpoint', {'address': '2457', 'memory_area': 'rom'})
    entered = Path(g.logdir) / 'entered.state'
    g.call('save_state_file', {'file_path': str(entered)})
    g.call('load_state_file', {'file_path': str(entered)})
    before = g.read(0xeda, 1)[0]
    g.checked_step(1)
    after = g.read(0xeda, 1)[0]
    g.call('load_state_file', {'file_path': str(entered)})
    if (before - after) & 0xff != 1:
        raise cv.StepError(f'first step covered {(before - after) & 0xff} updates')


def step_frame(g, on_stop=None):
    """One frame; breakpoint stops inside it call on_stop and the frame goes on."""
    while g.step(1) is None:
        if on_stop:
            on_stop(g, g.call('debug_get_status'))
