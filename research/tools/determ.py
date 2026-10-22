"""Update-aligned game-state trace: from each stage's first gameplay update,
run 90 idle updates, then force-scroll 2 px per update across the area and
back (as the captures do); record per update the sprite table, Ryu's object
bytes, timer/lives/score and a hash of RAM outside Enhanced's own bytes.
usage: determ.py ROM LABEL"""
import sys, json, hashlib, struct
from pathlib import Path
import core
from capture import Sweeper
import local
FRAME = 358995   # master clocks per frame: 1365 x 263 lines (HuC6260)
STAGES = [0, 3, 5, 6, 8, 9, 13, 14, 15, 16, 18]
rom, label = Path(sys.argv[1]), sys.argv[2]
SP = local.WORK / f'determ-{label}'
SP.mkdir(exist_ok=True)
# Bytes Enhanced owns or changes by design: zero page scratch, the stack page,
# the option/anchor bytes and the old renderer workspace it reuses.
SKIP = set(range(0x0000, 0x0100)) | set(range(0x0100, 0x0200)) | set(range(0x0257, 0x025B))


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
        core.jump_to_stage(s, stage)
        s.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'})
        s.call('set_breakpoint', {'address': '2457', 'memory_area': 'rom', 'execute': True})
        sw = Sweeper(s, SP, 'determ')
        s.call('debug_continue'); sw.wait_bp(polls=80000)
        rows, t0 = [], clock(s)
        def record(i):
            ram = s.read(0, 0x2000)
            sat = s.read(0, 512, area=6)
            game = bytes(b for k, b in enumerate(ram) if k not in SKIP)
            rows.append({'u': i, 'frame': round((clock(s) - t0) / FRAME, 2), 'sat': hashlib.sha1(sat).hexdigest()[:12],
                         'ryu': ram[0xe9e:0xeb8].hex(), 'timer': ram[0xeda:0xede].hex(), 'lives': ram[0xeaf],
                         'ram': hashlib.sha1(game).hexdigest()[:12], 'cam': int.from_bytes(ram[0x20f:0x211], 'little')})
        for i in range(90):
            sw.next_update()
        record(90)
        ram = s.read(0, 0x2000); pages = ram[0x237]; max_cam = max(0, pages * 256 - 256)
        cam = int.from_bytes(ram[0x20f:0x211], 'little')
        first = 1 if cam <= max_cam // 2 else -1
        i = 90
        for direction in (first, -first):
            for _ in range(150 if max_cam else 0):
                cam = int.from_bytes(s.read(0x20f, 2), 'little')
                target = max_cam if direction > 0 else 0
                if cam == target: break
                sw.forced_scroll(direction * min(2, abs(target - cam)))
                sw.next_update(); i += 1
                record(i)
        for _ in range(30):
            sw.next_update(); i += 1
            record(i)
        out[core.STAGE_NAMES[stage]] = rows
        print(label, core.STAGE_NAMES[stage], len(rows), 'updates recorded', flush=True)
        s.call('remove_breakpoint', {'address': '2457', 'memory_area': 'rom'})
(SP / 'result.json').write_text(json.dumps(out))
