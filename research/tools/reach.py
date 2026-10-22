"""Reach 5-3 (stage 14) area N at the gameplay hook; shared by the slowdown probes."""
import sys, struct
from pathlib import Path
import core
from capture import Sweeper
import local
SP = local.WORK
FRAME = 358995   # master clocks per frame: 1365 x 263 lines (HuC6260)


def clock(s, name='clk.state'):
    p = SP / name
    s.call('save_state_file', {'file_path': str(p)})
    return struct.unpack_from('<Q', p.read_bytes(), 1)[0]


def reach(s, rom, stage=14, area=2):
    core.boot_to_gameplay(s, rom, log=lambda m: None)
    s.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'})
    s.step(120)
    s.call('set_breakpoint', {'address': '23f3', 'memory_area': 'rom', 'execute': True})
    core.run_to_hook(s)
    s.write(0x325e, bytes([0xea] * 3), area=3)
    core.jump_to_stage(s, stage)
    s.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'})
    s.step(90)
    s.call('set_breakpoint', {'address': '2457', 'memory_area': 'rom', 'execute': True})
    s.call('debug_continue')
    sw = Sweeper(s, SP, 'slow')
    sw.wait_bp(polls=40000)
    for _ in range(area):
        sw.next_area()
    return sw
