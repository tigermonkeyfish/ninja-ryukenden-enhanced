"""Late updates in every scrolling area: force-scroll each area end to end
(both directions) and count updates that take two frames.
usage: sweep.py ROM LABEL --step PX [--only STAGE:AREA ...]"""
import argparse, json, struct, sys
from pathlib import Path
import core
from capture import Sweeper
import local
FRAME = 358995   # master clocks per frame: 1365 x 263 lines (HuC6260)
AREAS = {0: [0], 3: [0, 1, 2], 5: [0], 6: [0], 8: [0, 2], 9: [0], 13: [0, 1, 2, 3],
         14: [0, 1, 2, 3, 4, 5, 6], 16: [0], 18: [0, 2, 3]}
ap = argparse.ArgumentParser()
ap.add_argument('rom', type=Path)
ap.add_argument('label')
ap.add_argument('--step', type=int, default=2)
ap.add_argument('--only', nargs='*')
args = ap.parse_args()
SP = local.WORK / f'sweep-{args.label}-{args.step}'
SP.mkdir(exist_ok=True)


def clock(s):
    p = SP / 'clk.state'
    s.call('save_state_file', {'file_path': str(p)})
    return struct.unpack_from('<Q', p.read_bytes(), 1)[0]


todo = [(st, a) for st, areas in AREAS.items() for a in areas]
if args.only:
    todo = [tuple(map(int, x.split(':'))) for x in args.only]
out = {}
with core.Session(str(SP)) as s:
    core.boot_to_gameplay(s, args.rom, log=lambda m: None)
    s.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'})
    s.step(120)
    s.call('set_breakpoint', {'address': '23f3', 'memory_area': 'rom', 'execute': True})
    core.run_to_hook(s)
    hook = (SP / 'hook.state').resolve()
    s.call('save_state_file', {'file_path': str(hook)})
    for stage, area in todo:
        s.call('load_state_file', {'file_path': str(hook)})
        s.write(0x325e, bytes([0xea] * 3), area=3)
        s.call('set_breakpoint', {'address': '23f3', 'memory_area': 'rom', 'execute': True})
        core.jump_to_stage(s, stage)
        s.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'})
        s.step(90)
        s.call('set_breakpoint', {'address': '2457', 'memory_area': 'rom', 'execute': True})
        s.call('debug_continue')
        sw = Sweeper(s, SP, 'sweep')
        sw.wait_bp(polls=40000)
        for _ in range(area):
            sw.next_area()
        ram = s.read(0, 0x2000)
        pages = ram[0x237]; max_cam = max(0, pages * 256 - 256)
        cam = int.from_bytes(ram[0x20f:0x211], 'little')
        first = 1 if cam <= max_cam // 2 else -1
        late, updates, worst = [], 0, 0
        last = clock(s)
        for direction in (first, -first):
            stuck = 0
            while updates < 2000:
                cam = int.from_bytes(s.read(0x20f, 2), 'little')
                target = max_cam if direction > 0 else 0
                if cam == target or stuck > 4:
                    break
                sw.forced_scroll(direction * min(args.step, abs(target - cam)))
                sw.next_update()
                now = clock(s)
                d = now - last; last = now
                updates += 1
                worst = max(worst, d)
                if d > 1.5 * FRAME:
                    late.append(cam)
                cam2 = int.from_bytes(s.read(0x20f, 2), 'little')
                stuck = stuck + 1 if cam2 == cam else 0
        key = f'{core.STAGE_NAMES[stage]} area {area}'
        out[key] = {'updates': updates, 'late': len(late), 'late_cams': late[:20], 'max_frames': round(worst / FRAME, 2)}
        print(key, out[key], flush=True)
s.call = None
(SP / 'result.json').write_text(json.dumps(out, indent=1))
