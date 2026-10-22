"""Frames per update for the first updates after a stage jump (no input).
usage: entry.py ROM LABEL STAGE [N]"""
import sys, struct
from pathlib import Path
import core
import local
FRAME = 358995   # master clocks per frame: 1365 x 263 lines (HuC6260)
rom, label, stage = Path(sys.argv[1]), sys.argv[2], int(sys.argv[3])
n = int(sys.argv[4]) if len(sys.argv) > 4 else 40
SP = local.WORK / f'entry-{label}'
SP.mkdir(exist_ok=True)


def clock(s):
    p = SP / 'clk.state'
    s.call('save_state_file', {'file_path': str(p)})
    return struct.unpack_from('<Q', p.read_bytes(), 1)[0]


with core.Session(str(SP)) as s:
    core.boot_to_gameplay(s, rom, log=lambda m: None)
    s.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'})
    s.step(120)
    s.call('set_breakpoint', {'address': '23f3', 'memory_area': 'rom', 'execute': True})
    core.run_to_hook(s)
    s.write(0x325e, bytes([0xea] * 3), area=3)
    core.jump_to_stage(s, stage)
    s.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'})
    s.call('set_breakpoint', {'address': '2457', 'memory_area': 'rom', 'execute': True})
    out, last = [], None
    for i in range(n):
        s.call('debug_continue')
        for _ in range(40000):
            if s.status()['paused']:
                break
        now = clock(s)
        if last is not None:
            out.append(round((now - last) / FRAME, 2))
        last = now
        s.call('debug_step_into')
    print(label, out)
