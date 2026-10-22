"""Re-initialize a stage mid-area (Level Select path) and compare with the fresh entry."""
import sys
from core import *
from capture import Sweeper
from vdc import Background
import analyze
def bg_rows(s):
    ram = s.read(0, 0x2000)
    regs = {r[0]: int(r[1], 16) for r in s.call('get_huc6270_registers')['registers']}
    bg = Background(s.read(0, 0x10000, area=4), s.read(0, 1024, area=8), regs[9])
    return analyze.sample_rows(bg, int.from_bytes(ram[0xe4b:0xe4d], 'little')), ram
rom = Path(sys.argv[1]); label = sys.argv[2]
for stage in [int(x) for x in sys.argv[3:]]:
    with Session(Path(f'death-{label}')) as s:
        boot_to_gameplay(s, rom, lambda m: None)
        s.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'}); s.step(120)
        s.call('set_breakpoint', {'address': '23f3', 'memory_area': 'rom', 'execute': True}); run_to_hook(s)
        jump_to_stage(s, stage)
        s.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'}); s.step(90)
        s.call('set_breakpoint', {'address': '2457', 'memory_area': 'rom', 'execute': True}); s.call('debug_continue')
        sw = Sweeper(s, Path('.'), label); sw.wait_bp(polls=40000)
        fresh, r0 = bg_rows(s)
        cam0 = int.from_bytes(r0[0x20f:0x211], 'little'); pages = r0[0x237]; max_cam = pages * 256 - 256
        d = 1 if cam0 <= max_cam // 2 else -1
        for _ in range(60): sw.forced_scroll(d * 4); sw.next_update()
        mid = int.from_bytes(s.read(0x20f, 2), 'little')
        s.call('remove_breakpoint', {'address': '2457', 'memory_area': 'rom'})
        s.call('set_breakpoint', {'address': '23f3', 'memory_area': 'rom', 'execute': True}); run_to_hook(s)
        jump_to_stage(s, stage)                         # restart from live renderer state
        s.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'}); s.step(90)
        s.call('set_breakpoint', {'address': '2457', 'memory_area': 'rom', 'execute': True}); s.call('debug_continue'); sw.wait_bp(polls=40000)
        after, r1 = bg_rows(s)
        diff = sum(1 for cy in range(analyze.ROWS) for x in range(256) if fresh[cy][0][x] != after[cy][0][x])
        wdiff = sum(1 for cy in range(analyze.ROWS) for x in range(256) if fresh[cy][2][x] != after[cy][2][x])
        print(label, STAGE_NAMES[stage], 'entry', cam0, 'mid', mid, 'restart cam', int.from_bytes(r1[0x20f:0x211], 'little'),
              'BG pixel columns differing', diff, 'tile-map columns differing', wdiff, flush=True)
