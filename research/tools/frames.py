"""Per-frame trace after a stage jump: PC, $2031-$2034 (frame vectors), $2E63.
usage: frames.py ROM LABEL STAGE N"""
import sys, json
from pathlib import Path
import core
import local
rom, label, stage, n = Path(sys.argv[1]), sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
SP = local.WORK / f'frames-{label}'
SP.mkdir(exist_ok=True)
with core.Session(str(SP)) as s:
    core.boot_to_gameplay(s, rom, log=lambda m: None)
    s.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'})
    s.step(120)
    s.call('set_breakpoint', {'address': '23f3', 'memory_area': 'rom', 'execute': True})
    core.run_to_hook(s)
    s.write(0x325e, bytes([0xea] * 3), area=3)
    core.jump_to_stage(s, stage)
    s.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'})
    rows = []
    for f in range(n):
        s.step(1)
        cpu = s.cpu()
        r = s.read(0x31, 4).hex() + ' ' + s.read(0xe63, 1).hex()
        rows.append(f'{f:3} {cpu["physical_PC"]} {r}')
    (SP / 'frames.txt').write_text('\n'.join(rows))
print('done', label)
