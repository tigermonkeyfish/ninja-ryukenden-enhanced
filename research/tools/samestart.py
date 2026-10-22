"""Load one hook state (select screen) into a ROM, jump to a stage and time the
first gameplay update. usage: samestart.py ROM HOOKSTATE LABEL STAGE"""
import sys, struct
from pathlib import Path
import core
import local
FRAME = 358995   # master clocks per frame: 1365 x 263 lines (HuC6260)
rom, hook, label, stage = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], int(sys.argv[4])
SP = local.WORK / f'same-{label}'
SP.mkdir(exist_ok=True)


def clock(s):
    p = SP / 'clk.state'
    s.call('save_state_file', {'file_path': str(p)})
    return struct.unpack_from('<Q', p.read_bytes(), 1)[0]


with core.Session(str(SP)) as s:
    core.boot_to_gameplay(s, rom, log=lambda m: None)
    s.call('load_state_file', {'file_path': str(hook.resolve())})
    s.write(0x325e, bytes([0xea] * 3), area=3)
    s.call('set_breakpoint', {'address': '23f3', 'memory_area': 'rom', 'execute': True})
    t0 = clock(s)
    core.jump_to_stage(s, stage)
    s.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'})
    t1 = clock(s)
    s.call('set_breakpoint', {'address': '2457', 'memory_area': 'rom', 'execute': True})
    s.call('debug_continue')
    for _ in range(40000):
        if s.status()['paused']:
            break
    t2 = clock(s)
    print(label, 'jump took', round((t1 - t0) / FRAME, 2), 'first update after', round((t2 - t1) / FRAME, 2), 'total', round((t2 - t0) / FRAME, 2))
