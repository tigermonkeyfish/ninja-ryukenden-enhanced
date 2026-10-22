"""Per-update background shift for both ROMs over a short sweep (same interventions)."""
import sys, json
from collections import Counter
from core import *
from capture import Sweeper
from vdc import Background
import analyze, stitch
stage, sub, n_updates, step = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
R = analyze.R
name = f'{stage:02}-{STAGE_NAMES[stage]}'
res = {}
for which, rom in (('orig', ORIGINAL), ('enh', ENHANCED)):
    out = Path(f'fine-{which}'); out.mkdir(exist_ok=True)
    with Session(out) as s:
        s.call('load_media', {'file_path': str(rom)})
        s.call('debug_pause')
        st = R / which / name / f'area{sub-1}-end.state' if sub else None
        # area start: reuse capture's hook state + jump for sub 0
        s.call('load_state_file', {'file_path': str((R / which / 'hook.state').resolve())})
        s.write(0x325e, bytes([0xea] * 3), area=3)
        s.call('set_breakpoint', {'address': '23f3', 'memory_area': 'rom', 'execute': True})
        jump_to_stage(s, stage)
        s.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'})
        s.step(90)
        s.call('set_breakpoint', {'address': '2457', 'memory_area': 'rom', 'execute': True})
        s.call('debug_continue')
        sw = Sweeper(s, out, which); sw.wait_bp(polls=40000)
        for _ in range(sub):
            sw.next_area()
        frames = []
        cam0 = int.from_bytes(s.read(0x20f, 2), 'little')
        direction = 1 if cam0 < 200 else -1
        for i in range(n_updates):
            ram = s.read(0, 0x2000)
            regs = {r[0]: int(r[1], 16) for r in s.call('get_huc6270_registers')['registers']}
            bg = Background(s.read(0, 0x10000, area=4), s.read(0, 1024, area=8), regs[9])
            rc = int.from_bytes(ram[0xe4b:0xe4d], 'little')
            frames.append((int.from_bytes(ram[0x20f:0x211], 'little'), rc, analyze.sample_rows(bg, rc)))
            sw.forced_scroll(direction * step)
            sw.next_update()
    rows = {}
    for row in map(int, sys.argv[5].split(',')):
        seq = []
        for k in range(1, len(frames)):
            pc = frames[k-1][2][row][0]; c = frames[k][2][row][0]
            allf = [True] * 256
            v = stitch.shift_between(pc, allf, c, allf)
            v = Counter({a: b for a, b in v.items() if abs(a) <= 40})
            seq.append(v.most_common(1)[0][0] if v else None)
        rows[row] = seq
    res[which] = {'cams': [f[0] for f in frames], 'rcams': [f[1] for f in frames], 'shifts': rows}
    print(which, 'cams', res[which]['cams'][:40])
    for row, seq in rows.items():
        print(which, 'row', row, seq)
