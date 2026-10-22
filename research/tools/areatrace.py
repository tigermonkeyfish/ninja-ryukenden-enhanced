"""Frame-by-frame trace of every native forward area change ($8490) in each
parallax stage: area, Ryu, camera, timer and sprite table for 200 frames after
the change. Compare two builds with areatrace.py --compare A.json B.json.

usage: areatrace.py ROM LABEL [STAGE ...]
"""
import hashlib, json, sys
from pathlib import Path
import core
import local

if sys.argv[1] == '--compare':
    a, b = (json.loads(Path(p).read_text()) for p in sys.argv[2:4])
    for key in a:
        for i, (ta, tb) in enumerate(zip(a[key], b[key])):
            diff = [f for f, (x, y) in enumerate(zip(ta, tb)) if x != y]
            fields = sorted({k for f in diff for k in ta[f] if ta[f][k] != tb[f][k]})
            print(f'{key} change {i}: ' + (f'{len(diff)} frames differ from frame {diff[0]} ({", ".join(fields)})' if diff else 'identical'))
    sys.exit()

STAGES = [int(v) for v in sys.argv[3:]] or [0, 3, 5, 6, 8, 9, 13, 14, 15, 16, 18]
rom, label = Path(sys.argv[1]).resolve(), sys.argv[2]
SP = local.WORK / f'areatrace-{label}'
SP.mkdir(exist_ok=True)


def wait(s):
    for _ in range(40000):
        if s.status()['paused']:
            return


def row(s):
    r = s.read(0, 0x1000)
    return {'area': r[0xe60], 'stage': r[0xe5f], 'x': int.from_bytes(r[0xe9e:0xea0], 'little'), 'y': r[0xea0],
            'cam': int.from_bytes(r[0x20f:0x211], 'little'), 'timer': r[0xeda:0xede].hex(),
            'sat': hashlib.sha1(s.read(0, 512, area=6)).hexdigest()[:10]}


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
        traces = []
        for change in range(8):
            s.call('set_breakpoint', {'address': '2457', 'memory_area': 'rom', 'execute': True})
            s.call('debug_continue'); wait(s)
            s.call('remove_breakpoint', {'address': '2457', 'memory_area': 'rom'})
            if change == 0:
                s.step(30)
                s.call('set_breakpoint', {'address': '2457', 'memory_area': 'rom', 'execute': True})
                s.call('debug_continue'); wait(s)
                s.call('remove_breakpoint', {'address': '2457', 'memory_area': 'rom'})
            before = row(s)
            s.reg('PC', 0x8490)
            rows = []
            for f in range(200):
                s.step(1)
                rows.append(row(s))
            if rows[-1]['stage'] != stage:
                break
            traces.append(rows)
            if rows[-1]['area'] == before['area']:
                break
            s.step(30)
        out[core.STAGE_NAMES[stage]] = traces
        print(label, core.STAGE_NAMES[stage], len(traces), 'area changes', flush=True)
(SP / 'result.json').write_text(json.dumps(out))
