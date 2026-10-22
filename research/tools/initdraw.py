"""Clock init_background during a stage load: entry, after the native init,
after the Enhanced draw; frames after the select hook. usage: initdraw.py ROM LABEL STAGE"""
import sys, struct
from pathlib import Path
import core
import local
FRAME = 358995   # master clocks per frame: 1365 x 263 lines (HuC6260)
rom, label, stage = Path(sys.argv[1]), sys.argv[2], int(sys.argv[3])
SP = local.WORK / f'initdraw-{label}'
SP.mkdir(exist_ok=True)
def clock(s):
    p = SP / 'clk.state'; s.call('save_state_file', {'file_path': str(p)})
    return struct.unpack_from('<Q', p.read_bytes(), 1)[0]
with core.Session(str(SP)) as s:
    core.boot_to_gameplay(s, rom, log=lambda m: None)
    s.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'})
    s.step(120)
    s.call('set_breakpoint', {'address': '23f3', 'memory_area': 'rom', 'execute': True})
    core.run_to_hook(s)
    s.write(0x325e, bytes([0xea] * 3), area=3)
    t0 = clock(s)
    pts = {'1F40': 'init_background', '1F43': 'after native init', sys.argv[4]: 'after Enhanced draw', '2457': 'first update'}
    core.jump_to_stage(s, stage)
    s.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'})
    for a in pts:
        s.call('set_breakpoint', {'address': a, 'memory_area': 'rom', 'execute': True})
    ev = []
    for _ in range(40):
        s.call('debug_continue')
        for _ in range(80000):
            if s.status()['paused']: break
        pc = s.cpu()['physical_PC'][-4:].upper()
        ev.append((pts.get(pc, pc), round((clock(s) - t0) / FRAME, 3)))
        if pc == '2457': break
        s.call('debug_step_into')
    print(label, ev)
