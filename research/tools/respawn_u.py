"""Timer death in a stage: frames from setting the timer to 002 until the
first gameplay update after the respawn reload (the long gap between updates).
usage: respawn.py ROM LABEL STAGE..."""
import sys, struct
from pathlib import Path
import core
import local
FRAME = 358995   # master clocks per frame: 1365 x 263 lines (HuC6260)
rom, label, stages = Path(sys.argv[1]), sys.argv[2], [int(v) for v in sys.argv[3:]]
SP = local.WORK / f'respawn-{label}'
SP.mkdir(exist_ok=True)


def clock(s):
    p = SP / 'clk.state'
    s.call('save_state_file', {'file_path': str(p)})
    return struct.unpack_from('<Q', p.read_bytes(), 1)[0]


def to_hook(s):
    s.call('debug_continue')
    for _ in range(80000):
        if s.status()['paused']:
            return True
    return False


with core.Session(str(SP)) as s:
    core.boot_to_gameplay(s, rom, log=lambda m: None)
    s.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'})
    s.step(120)
    s.call('set_breakpoint', {'address': '23f3', 'memory_area': 'rom', 'execute': True})
    core.run_to_hook(s)
    hook = (SP / 'hook.state').resolve()
    s.call('save_state_file', {'file_path': str(hook)})
    for stage in stages:
        s.call('load_state_file', {'file_path': str(hook)})
        s.write(0x325e, bytes([0xea] * 3), area=3)
        s.call('set_breakpoint', {'address': '23f3', 'memory_area': 'rom', 'execute': True})
        core.jump_to_stage(s, stage)
        s.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'})
        s.call('set_breakpoint', {'address': '2457', 'memory_area': 'rom', 'execute': True})
        to_hook(s)
        t0 = clock(s)
        for _ in range(90):
            s.call('debug_step_into')
            to_hook(s)
        s.write(0xedb, bytes([2, 0, 0]))
        last, gaps = clock(s), []
        for i in range(1500):
            s.call('debug_step_into')
            if not to_hook(s):
                break
            now = clock(s)
            if now - last > 1.5 * FRAME:
                gaps.append((round((last - t0) / FRAME, 2), round((now - t0) / FRAME, 2)))
            last = now
            if gaps and now - t0 > gaps[-1][1] * FRAME + 30 * FRAME:
                break
        print(label, core.STAGE_NAMES[stage], 'update gaps (frames after the first update; timer set at update 90):', gaps, flush=True)
