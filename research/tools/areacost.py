"""Per forced area change ($8490): frames from the change to the first
gameplay update, and (Enhanced) cycles of the area-change draw
(init_background's jsr $fe46 at $FF63 .. $FF66).
usage: areacost.py ROM LABEL STAGE [STAGE ...]"""
import json, struct, sys
from pathlib import Path
import core
import local
FRAME = 358995   # master clocks per frame: 1365 x 263 lines (HuC6260)
rom, label = Path(sys.argv[1]).resolve(), sys.argv[2]
STAGES = [int(v) for v in sys.argv[3:]]
SP = local.WORK / f'areacost-{label}'
SP.mkdir(exist_ok=True)


def clock(s):
    p = SP / 'clk.state'
    s.call('save_state_file', {'file_path': str(p)})
    return struct.unpack_from('<Q', p.read_bytes(), 1)[0]


def run_to(s, polls=80000):
    s.call('debug_continue')
    for _ in range(polls):
        st = s.status()
        if st['paused']:
            return st['pc']
    return None


out = {}
with core.Session(str(SP)) as s:
    core.boot_to_gameplay(s, rom, log=lambda m: None)
    s.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'})
    s.step(120)
    s.call('set_breakpoint', {'address': '23f3', 'memory_area': 'rom', 'execute': True})
    core.run_to_hook(s)
    hook = str((SP / 'hook.state').resolve())
    s.call('save_state_file', {'file_path': hook})
    for stage in STAGES:
        s.call('load_state_file', {'file_path': hook})
        s.call('set_breakpoint', {'address': '23f3', 'memory_area': 'rom', 'execute': True})
        core.jump_to_stage(s, stage)
        s.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'})
        rows = []
        s.call('set_breakpoint', {'address': '2457', 'memory_area': 'rom', 'execute': True})
        run_to(s)
        s.call('remove_breakpoint', {'address': '2457', 'memory_area': 'rom'})
        s.step(30)
        for change in range(8):
            s.call('set_breakpoint', {'address': '2457', 'memory_area': 'rom', 'execute': True})
            run_to(s)
            area0 = s.read(0xe60, 1)[0]
            s.reg('PC', 0x8490)
            t0 = clock(s)
            s.call('set_breakpoint', {'address': '1f63', 'memory_area': 'rom', 'execute': True})
            s.call('set_breakpoint', {'address': '1f66', 'memory_area': 'rom', 'execute': True})
            draw, start = None, None
            while True:
                pc = run_to(s)
                if pc == '8457':
                    break
                if pc == 'FF63':
                    start = clock(s)
                elif pc == 'FF66' and start is not None:
                    draw = clock(s) - start
                    start = None
            t1 = clock(s)
            for a in ('1f63', '1f66'):
                s.call('remove_breakpoint', {'address': a, 'memory_area': 'rom'})
            s.call('remove_breakpoint', {'address': '2457', 'memory_area': 'rom'})
            area1 = s.read(0xe60, 1)[0]
            if s.read(0xe5f, 1)[0] != stage or area1 == area0:
                break
            rows.append({'from': area0, 'to': area1, 'frames': round((t1 - t0) / FRAME, 2),
                         'draw_cycles': draw})
            s.step(30)
        out[core.STAGE_NAMES[stage]] = rows
        print(label, core.STAGE_NAMES[stage], rows, flush=True)
(SP / 'result.json').write_text(json.dumps(out))
