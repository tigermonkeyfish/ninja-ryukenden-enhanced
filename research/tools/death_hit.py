"""2-2: death by enemy contact (health 1, Ryu idle at the area entry), then compare the respawned background."""
import sys, json
from core import *
from capture import Sweeper
from death_test import bg_rows
import analyze
rom = Path(sys.argv[1]); label = sys.argv[2]
out = Path(f'death-{label}'); out.mkdir(exist_ok=True)
with Session(out) as s:
    boot_to_gameplay(s, rom, lambda m: None)
    s.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'}); s.step(120)
    s.call('set_breakpoint', {'address': '23f3', 'memory_area': 'rom', 'execute': True}); run_to_hook(s)
    jump_to_stage(s, 3)
    s.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'}); s.step(90)
    s.call('set_breakpoint', {'address': '2457', 'memory_area': 'rom', 'execute': True}); s.call('debug_continue')
    sw = Sweeper(s, out, label); sw.wait_bp(polls=40000)
    fresh, cam0, ram0 = bg_rows(s)
    lives0 = ram0[0xeaf]
    s.call('remove_breakpoint', {'address': '2457', 'memory_area': 'rom'})
    s.button('left', 'press')                      # walk toward the enemies
    died_at = None
    for f in range(4000):
        if died_at is None: s.write(0xead, b'\x01')
        s.step(1)
        r = s.read(0, 0x2000)
        if died_at is None and r[0xeaf] < lives0:
            died_at = f; s.button('left', 'release')
        if died_at is not None and f > died_at + 240 and r[0x240] == 0:
            break
    s.call('set_breakpoint', {'address': '2457', 'memory_area': 'rom', 'execute': True}); s.call('debug_continue'); sw.wait_bp(polls=40000)
    after, cam1, ram1 = bg_rows(s)
    diff = sum(1 for cy in range(analyze.ROWS) for x in range(256) if fresh[cy][0][x] != after[cy][0][x])
    wdiff = sum(1 for cy in range(analyze.ROWS) for x in range(256) if fresh[cy][2][x] != after[cy][2][x])
    (out / 'hit-after.png').write_bytes(s.screenshot_png())
    print(label, {'entry_camera': cam0, 'died_frame': died_at, 'lives': [lives0, ram1[0xeaf]], 'respawn_camera': cam1,
                  'render_camera': [int.from_bytes(ram0[0xe4b:0xe4d], 'little'), int.from_bytes(ram1[0xe4b:0xe4d], 'little')],
                  'bg_columns_differing': diff, 'bat_columns_differing': wdiff})
