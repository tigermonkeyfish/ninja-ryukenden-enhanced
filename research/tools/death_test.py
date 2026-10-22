"""Death/respawn: background after a pit death must equal the fresh area entry (decoded BG layer)."""
import sys, json
from core import *
from capture import Sweeper
from vdc import Background
import analyze
rom = Path(sys.argv[1]); label = sys.argv[2]
out = Path(f'death-{label}'); out.mkdir(exist_ok=True)
results = {}
def bg_rows(s):
    ram = s.read(0, 0x2000)
    regs = {r[0]: int(r[1], 16) for r in s.call('get_huc6270_registers')['registers']}
    bg = Background(s.read(0, 0x10000, area=4), s.read(0, 1024, area=8), regs[9])
    rc = int.from_bytes(ram[0xe4b:0xe4d], 'little')
    return analyze.sample_rows(bg, rc), int.from_bytes(ram[0x20f:0x211], 'little'), ram
for stage in [int(x) for x in sys.argv[3:]] or (3, 13, 14, 15, 18):
    with Session(out) as s:
        boot_to_gameplay(s, rom, lambda m: None)
        s.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'}); s.step(120)
        s.call('set_breakpoint', {'address': '23f3', 'memory_area': 'rom', 'execute': True}); run_to_hook(s)
        jump_to_stage(s, stage)
        s.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'}); s.step(90)
        s.call('set_breakpoint', {'address': '2457', 'memory_area': 'rom', 'execute': True}); s.call('debug_continue')
        sw = Sweeper(s, out, label); sw.wait_bp(polls=40000)
        import os
        for _ in range(int(os.environ.get('AREA', '0'))): sw.next_area()
        fresh, cam0, ram0 = bg_rows(s)
        lives0 = ram0[0xeaf]
        ram = s.read(0, 0x2000); pages = ram[0x237]; max_cam = max(0, pages * 256 - 256)
        d = 1 if cam0 <= max_cam // 2 else -1
        for _ in range(min(60, max_cam // 4)):          # move ~240 px into the area
            sw.forced_scroll(d * 4); sw.next_update()
        moved = int.from_bytes(s.read(0x20f, 2), 'little')
        s.call('remove_breakpoint', {'address': '2457', 'memory_area': 'rom'})
        died = False
        for f in range(900):
            if not died:
                s.write(0xea0, b'\xf0')                   # hold Ryu below the screen until the fall death
            s.step(1)
            r = s.read(0, 0x2000)
            if r[0xeaf] < lives0: died = True
            if died and r[0x240] == 0 and f > 200 and int.from_bytes(r[0x20f:0x211], 'little') == cam0:
                break
        for _ in range(120): s.step(1)
        s.call('set_breakpoint', {'address': '2457', 'memory_area': 'rom', 'execute': True}); s.call('debug_continue'); sw.wait_bp(polls=40000)
        after, cam1, ram1 = bg_rows(s)
        diff = sum(1 for cy in range(analyze.ROWS) for x in range(256) if fresh[cy][0][x] != after[cy][0][x])
        wdiff = sum(1 for cy in range(analyze.ROWS) for x in range(256) if fresh[cy][2][x] != after[cy][2][x])
        (out / f'{stage}-after.png').write_bytes(s.screenshot_png())
        results[stage] = {'entry_camera': cam0, 'moved_to': moved, 'died': died, 'lives': [lives0, ram1[0xeaf]],
                          'respawn_camera': cam1, 'bg_columns_differing': diff, 'bat_columns_differing': wdiff}
        print(label, STAGE_NAMES[stage], results[stage], flush=True)
(out / 'results.json').write_text(json.dumps(results, indent=1))
