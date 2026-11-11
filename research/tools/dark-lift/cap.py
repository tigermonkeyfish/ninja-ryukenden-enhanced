"""Captures for the dark-lift measurements (research reference, not a
maintained tool): the dark-colour survey's driver with the ROM and the
output folder as arguments, so a build is measured exactly as the survey
measured the hell-1-1 build. One fresh session from the seed state, native
English, $2100 = the mode.
usage: cap.py ROM OUT MODE KIND ARGS...
MODE: original, nes-a, nes-b, gb-dmg, hell, sms
KIND: run NAME f1,f2,.. [scout]   stored run; the picture after f frames
                                   (scout: the picture only)
      warp STAGE                  Level Select entry; per area the picture
                                   after 60 idle frames ('start') and after
                                   120 more holding right ('hold'), then the
                                   area exit moved onto Ryu (health refilled)
      boss STAGE f1,f2,..         Level Select entry, idle, health refilled
Each capture: NAME-MODE.png, .vce (512 words), .ram (RAM palette $2286,
backup $2686, $2100), .sat, and NAME-MODE-index.png: the same frame drawn
with the VCE set to the identity (entry i = colour i) and the palette lock
$2283 set, from a saved state that is restored afterwards.
(GB_WORK: seed.state, original.pce)"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'gb-palette'))
sys.path.insert(0, str(HERE.parents[2] / 'scripts'))
from gbtools import Session, cv, load_run  # noqa: E402

MODES = {'original': 0x00, 'nes-a': 0x08, 'nes-b': 0x28, 'gb-dmg': 0x10, 'hell': 0x18, 'sms': 0xb8}
IDENT = b''.join(bytes([i & 0xff, i >> 8]) for i in range(512)).hex(' ')
rom, out, mode, kind = sys.argv[1], Path(sys.argv[2]), sys.argv[3], sys.argv[4]
args = sys.argv[5:]
flags = MODES[mode]
out.mkdir(parents=True, exist_ok=True)


def save(g, name, index=True, full=True):
    base = out / f'{name}-{mode}'
    base.with_suffix('.png').write_bytes(g.screenshot())
    if not full:
        return
    Path(str(base) + '.vce').write_bytes(g.read(0, 1024, 8))
    Path(str(base) + '.ram').write_bytes(g.read(0x286, 1024) + g.read(0x686, 1024) + g.read(0x100, 1))
    Path(str(base) + '.sat').write_bytes(g.read(0, 512, 6))
    if index:
        st = Path(g.logdir) / 'idx.state'
        g.call('save_state_file', {'file_path': str(st)})
        g.call('write_memory', {'area': 8, 'offset': '0000', 'bytes': IDENT})
        g.write(0x283, b'\x01')
        g.checked_step(1)
        Path(str(base) + '-index.png').write_bytes(g.screenshot())
        g.call('load_state_file', {'file_path': str(st)})


def frames(g, n, buttons):
    g.press(buttons)
    for _ in range(n):
        g.write(0xead, bytes([16]))
        g.checked_step(1)


with Session(rom, flags) as g:
    g.write(0x1227, b'\x01')
    if kind == 'run':
        name, wanted = args[0], [int(x) for x in args[1].split(',')]
        full = len(args) < 3
        run = load_run(name)
        inputs = [b for c, b in run['segments'] for _ in range(c)] + [[]] * 60
        cv.start_stage(g, run['stage'])
        for f in range(max(wanted) + 1):
            if f in wanted:
                g.press(set())
                save(g, f'{name}-f{f}', full=full)
            g.press(set(inputs[f]))
            g.checked_step(1)
    elif kind == 'warp':
        stage, area = int(args[0]), 0
        cv.start_stage(g, stage)
        while True:
            frames(g, 60, set())
            save(g, f'ls{stage}-a{area}-start')
            frames(g, 120, {'right'})
            save(g, f'ls{stage}-a{area}-hold')
            r = g.read(0xe9f, 1)[0]
            box = g.read(0xeb5, 6)
            g.write(0xe87, bytes([r]))
            g.write(0xe81, bytes([(box[0] + box[3]) // 2, (box[2] + box[5]) // 2]))
            moved = False
            for _ in range(240):
                g.write(0xead, bytes([16]))
                g.checked_step(1)
                ram = g.read(0x240, 1) + g.read(0xe5f, 2)
                if ram[1] != stage or ram[0]:
                    break
                if ram[2] != area:
                    area, moved = ram[2], True
                    break
            print(mode, stage, 'area', area, 'moved' if moved else 'end', flush=True)
            if not moved or area > 12:
                break
    elif kind == 'boss':
        stage, wanted = int(args[0]), [int(x) for x in args[1].split(',')]
        cv.start_stage(g, stage)
        n = 0
        for f in wanted:
            frames(g, f - n, set())
            n = f
            save(g, f'ls{stage}-f{f}')
print('done', mode, kind, *args)
