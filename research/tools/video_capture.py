"""Screenshot every update of a forced sweep through one area (same interventions as capture.py)."""
import argparse, json
from core import *
from capture import Sweeper
ap = argparse.ArgumentParser()
ap.add_argument('rom', type=Path); ap.add_argument('out', type=Path)
ap.add_argument('--stage', type=int, default=3); ap.add_argument('--area', type=int, default=2)
ap.add_argument('--step', type=int, default=2); ap.add_argument('--max', type=int, default=2000)
ap.add_argument('--direction', type=int, default=0)
a = ap.parse_args(); a.out.mkdir(parents=True, exist_ok=True)
log = []
with Session(a.out) as s:
    boot_to_gameplay(s, a.rom, lambda m: None)
    s.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'}); s.step(120)
    s.call('set_breakpoint', {'address': '23f3', 'memory_area': 'rom', 'execute': True}); run_to_hook(s)
    s.write(0x325e, bytes([0xea] * 3), area=3)
    jump_to_stage(s, a.stage)
    s.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'}); s.step(90)
    s.call('set_breakpoint', {'address': '2457', 'memory_area': 'rom', 'execute': True}); s.call('debug_continue')
    sw = Sweeper(s, a.out, 'video'); sw.wait_bp(polls=40000)
    for _ in range(a.area): sw.next_area()
    ram = s.read(0, 0x2000); pages = ram[0x237]; max_cam = max(0, pages * 256 - 256)
    cam = int.from_bytes(ram[0x20f:0x211], 'little')
    d = a.direction or (1 if cam <= max_cam // 2 else -1)
    for i in range(a.max):
        (a.out / f'{i:05}.png').write_bytes(s.screenshot_png())
        cam = int.from_bytes(s.read(0x20f, 2), 'little'); log.append(cam)
        target = max_cam if d > 0 else 0
        if cam == target: break
        sw.forced_scroll(d * min(a.step, abs(target - cam))); sw.next_update()
(a.out / 'cameras.json').write_text(json.dumps(log))
print(a.rom.name, len(log), 'frames', log[0], '->', log[-1])
