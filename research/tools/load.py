"""Clock the stage load: the $82CD call (native init + Enhanced draw) and the
first gameplay update, in frames after the stage jump.
usage: load.py ROM LABEL STAGE"""
import sys, struct
from pathlib import Path
import core
import local
FRAME = 358995   # master clocks per frame: 1365 x 263 lines (HuC6260)
rom, label, stage = Path(sys.argv[1]), sys.argv[2], int(sys.argv[3])
SP = local.WORK / f'load-{label}'
SP.mkdir(exist_ok=True)


def clock(s):
    p = SP / 'clk.state'
    s.call('save_state_file', {'file_path': str(p)})
    return struct.unpack_from('<Q', p.read_bytes(), 1)[0]


def wait(s):
    for _ in range(40000):
        st = s.status()
        if st['paused']:
            return s.cpu()['physical_PC'][-4:].upper()


with core.Session(str(SP)) as s:
    core.boot_to_gameplay(s, rom, log=lambda m: None)
    s.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'})
    s.step(120)
    s.call('set_breakpoint', {'address': '23f3', 'memory_area': 'rom', 'execute': True})
    core.run_to_hook(s)
    s.write(0x325e, bytes([0xea] * 3), area=3)
    core.jump_to_stage(s, stage)
    s.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'})
    t0 = clock(s)
    for a in ('22CD', '22D0', '2457'):
        s.call('set_breakpoint', {'address': a, 'memory_area': 'rom', 'execute': True})
    events = []
    while True:
        s.call('debug_continue')
        pc = wait(s)
        events.append((pc, round((clock(s) - t0) / FRAME, 3)))
        if pc == '2457':
            break
        s.call('debug_step_into')
    print(label, events)
