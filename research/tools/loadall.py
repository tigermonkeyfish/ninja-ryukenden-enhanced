"""Frames from the stage-select hook to the first gameplay update, per stage
(each from the same saved select-screen state). usage: loadall.py ROM LABEL"""
import sys, struct, json
from pathlib import Path
import core
import local
FRAME = 358995   # master clocks per frame: 1365 x 263 lines (HuC6260)
STAGES = [int(v) for v in sys.argv[3:]] or [0, 3, 5, 6, 8, 9, 13, 14, 15, 16, 18]
rom, label = Path(sys.argv[1]), sys.argv[2]
SP = local.WORK / f'loadall-{label}'
SP.mkdir(exist_ok=True)


def clock(s):
    p = SP / 'clk.state'
    s.call('save_state_file', {'file_path': str(p)})
    return struct.unpack_from('<Q', p.read_bytes(), 1)[0]


out = {}
with core.Session(str(SP)) as s:
    core.boot_to_gameplay(s, rom, log=lambda m: None)
    s.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'})
    s.step(120)
    s.call('set_breakpoint', {'address': '23f3', 'memory_area': 'rom', 'execute': True})
    core.run_to_hook(s)
    hook = (SP / 'hook.state').resolve()
    s.call('save_state_file', {'file_path': str(hook)})
    for stage in STAGES:
        s.call('load_state_file', {'file_path': str(hook)})
        s.write(0x325e, bytes([0xea] * 3), area=3)
        s.call('set_breakpoint', {'address': '23f3', 'memory_area': 'rom', 'execute': True})
        t0 = clock(s)
        core.jump_to_stage(s, stage)
        s.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'})
        s.call('set_breakpoint', {'address': '2457', 'memory_area': 'rom', 'execute': True})
        s.call('debug_continue')
        for _ in range(40000):
            if s.status()['paused']:
                break
        t2 = clock(s)
        s.call('remove_breakpoint', {'address': '2457', 'memory_area': 'rom'})
        out[core.STAGE_NAMES[stage]] = round((t2 - t0) / FRAME, 2)
        print(label, core.STAGE_NAMES[stage], out[core.STAGE_NAMES[stage]], flush=True)
(SP / 'result.json').write_text(json.dumps(out))
