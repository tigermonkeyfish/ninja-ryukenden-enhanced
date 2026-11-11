"""Random backup RAM images against the game's loader and save (evidence for
docs/validation/bram-save.md, "Random images").

The matrix of scripts/bram_image.py is hand-picked. This probe makes COUNT
seeded random images that crowd the places where a mistake would hurt
another game's saves: directories ending in the last bytes of the 2 KiB,
end pointers below, at and above $8800, lengths and pointers off by a
little, stale pointers, blank memories with stray bytes and formats cut
short. For each image, without playing the game:

- power on with the image and run the reset code to the native init
  ($FCBE): status, $2100 and $3227 must be bram_image.expected_load's, the
  memory untouched;
- write random valid settings to $2100/$3227, fill the borrowed zero page
  with a pattern and call the save ($4B03, bank $46 in MPR2, from a stub in
  work RAM): status and memory must be bram_image.expected_save's; MPR4, the
  zero page, X, Y and the stack pointer as before the call;
- independent of that model: when the System Card style reader accepts the
  image, every other game's file is where and as it was afterwards; when
  the status is not OK, not one byte differs; when it is OK, the reader
  finds our file once with these settings and a good checksum, the header's
  pointer names the terminator, and a load of that memory gives them back;
- the save again: the same status, no byte changed.

With NG_BRAM_MODEL=lock or key the same runs on the test-only emulator
(research/tools/bram-save/locktest_patch.py).

usage: fuzz.py ROM COUNT [SEED]
"""
import json
import os
import random
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts'))
import bram_image as bi  # noqa: E402
from check_bram import continue_to, others  # noqa: E402
from comparison_video import Game  # noqa: E402

rom = sys.argv[1]
COUNT = int(sys.argv[2])
SEED = int(sys.argv[3]) if len(sys.argv) > 3 else 1
EMU = os.environ['NG_EMULATOR']
OURS = b'\0\0' + bi.NAME
STUB = 0x1f00                                        # work RAM offset: CPU $3F00
CODE = bytes.fromhex('4304 48 a946 5304 20034b 68 5304')    # tma #2, pha, lda #$46, tam #2, jsr $4b03, pla, tam #2
STOP = f'{0x2000 + STUB + len(CODE):04X}'
ZP = range(0x22, 0x2d)


def settings(rng):
    mode = rng.choice(list(bi.PALETTES))
    return mode | rng.randrange(8), rng.randrange(3)


def directory(rng):
    """A sound directory; returns (entries, room left)."""
    entries, used = [], 0
    target = rng.choice([rng.randrange(0, 0x7f0), rng.randrange(0x700, 0x7f0), 0x7ee - rng.randrange(0, 0x40)])
    place = rng.randrange(0, 6) if rng.random() < 0.6 else None        # where ours goes, if at all
    index = 0
    while True:
        if place == len(entries):
            raw = bi.settings_entry(*settings(rng))
            if rng.random() < 0.15:
                raw = bi.settings_entry(rng.randrange(256), rng.randrange(256), version=rng.randrange(3),
                                        sum_error=rng.randrange(2))
            if rng.random() < 0.05:
                raw = bi.entry(bi.NAME, bytes(rng.randrange(0, 20)))
        else:
            raw = bi.other(index, rng.choice([16, 17, 18, 24, 26, 0x40, rng.randrange(16, 0x180)]))
            index += 1
        if used + len(raw) > target:
            break
        entries.append(raw)
        used += len(raw)
    if rng.random() < 0.3:                           # end exactly where the last terminator may be
        gap = 0x7ee - used - rng.randrange(0, 4)
        if gap >= 16:
            entries.append(bi.other(index, gap))
    return entries


def formatted(rng):
    entries = directory(rng)
    body = b''.join(entries)
    end = rng.choice([bi.TOP] * 6 + [0xa000, 0x9000, 0x8801, 0x87ff, 0x8010 + len(body) + rng.randrange(0, 6),
                                     rng.randrange(0x8000, 0x8900), rng.randrange(0x10000)])
    fill = rng.choice([0x00, 0x00, 0xff, None])
    data = bytearray(bi.image(entries, end=end, fill=0 if fill is None else fill))
    if fill is None:                                 # old data after the terminator
        tail = bi.FIRST - bi.BASE + len(body) + 2
        data[tail:] = bytes(rng.randrange(256) for _ in range(bi.SIZE - tail))
    kind = rng.random()
    if kind < 0.45:
        return bytes(data)
    if kind < 0.6:                                   # the pointer: stale, or a little off
        try:
            ours = [at for at, _, name, _ in bi.Directory(bytes(data)).files() if name == OURS]
        except ValueError:                           # the end pointer already cuts the directory
            ours = []
        pointer = int.from_bytes(data[6:8], 'little')
        choice = rng.randrange(5)
        if ours and choice < 2:
            pointer = ours[0] if choice else (pointer & 0xff00) | (ours[0] & 0xff)
        elif choice == 2:
            pointer += rng.choice([-1, 1, 2, -2, 0x18, -0x18])
        elif choice == 3:
            pointer ^= 0x100
        else:
            pointer = rng.randrange(0x10000)
        data[6:8] = (pointer & 0xffff).to_bytes(2, 'little')
        return bytes(data)
    if kind < 0.85:                                  # one to three bytes of the header or the directory
        for _ in range(rng.randrange(1, 4)):
            at = rng.choice([rng.randrange(0, 18), rng.randrange(0, 18 + len(body) + 2), rng.randrange(bi.SIZE)])
            data[at] = rng.choice([data[at] ^ (1 << rng.randrange(8)), rng.randrange(256), 0x00, 0xff])
        return bytes(data)
    # A length that does not fit.
    at = 16
    walk = []
    while at < 16 + len(body):
        walk.append(at)
        at += int.from_bytes(data[at:at + 2], 'little')
    if walk:
        at = rng.choice(walk)
        data[at:at + 2] = rng.choice([0x7ff, 0x800, 0xffff, 15, 1, 0x100, bi.SIZE - at, bi.SIZE - at - 2,
                                      bi.SIZE - at - 1, rng.randrange(0x10000)]).to_bytes(2, 'little')
    return bytes(data)


def unformatted(rng):
    blank = rng.choice([0x00, 0xff, 0x00, 0xff, 0xaa, 0x80, rng.randrange(256)])
    data = bytearray([blank]) * bi.SIZE
    header = bi.image()[:18]
    kind = rng.random()
    if kind < 0.3:                                   # a format cut short (written from byte 17 down to 0)
        cut = rng.randrange(0, 18)
        data[cut:18] = header[cut:18]
        if cut == 0:
            data[0] = rng.choice([0x55, 0xaa, blank])
    elif kind < 0.5:                                 # blank but for a few bytes
        for _ in range(rng.randrange(1, 3)):
            at = rng.choice([rng.randrange(0, 24), rng.randrange(bi.SIZE), bi.SIZE - 1 - rng.randrange(4), 18, 17, 256,
                             255, 0x700 + rng.randrange(18)])
            data[at] = rng.choice([data[at] ^ (1 << rng.randrange(8)), rng.randrange(256)])
    elif kind < 0.6:                                 # the test byte left behind
        data[0] = rng.choice([0x55, 0xaa])
    elif kind < 0.75:
        data = bytearray(rng.randrange(256) for _ in range(bi.SIZE))
    elif kind < 0.9:                                 # a directory under a damaged tag
        data = bytearray(formatted(rng))
        data[rng.randrange(4)] ^= 1 << rng.randrange(8)
    return bytes(data)


def images():
    rng = random.Random(SEED)
    for k in range(COUNT):
        yield k, (formatted(rng) if rng.random() < 0.7 else unformatted(rng)), settings(rng)


def run_save(game):
    """Call the save from the stub; returns the CPU registers afterwards."""
    game.write(STUB, CODE + b'\x80\xfe')
    game.reg('PC', 0x2000 + STUB)
    game.call('set_breakpoint', {'address': STOP, 'execute': True})
    try:
        pc = continue_to(game)
    finally:
        game.call('remove_breakpoint', {'address': STOP})
    assert pc == STOP, pc
    return game.call('get_huc6280_status')


def check(game, image, options, language):
    problems = []

    def expect(what, found, wanted):
        if found != wanted:
            problems.append(f'{what}: {found!r}, expected {wanted!r}')

    game.power_on(rom, image)
    game.call('set_breakpoint', {'address': '1cbe', 'memory_area': 'rom', 'execute': True})
    try:
        assert continue_to(game) == 'FCBE'
    finally:
        game.call('remove_breakpoint', {'address': '1cbe', 'memory_area': 'rom'})
    ram = game.read(0, 0x2000)
    expect('load', (bi.STATUS[ram[0x105]], ram[0x100], ram[0x1227]),
           (lambda s, o, l: (bi.STATUS[s], o, l))(*bi.expected_load(image)))
    expect('memory after the load', game.backup_ram(), image)
    # The save, with other settings.
    pattern = bytes(0xc0 + k for k in range(len(ZP)))
    game.write(ZP[0], pattern)
    game.write(0x100, bytes([options]))
    game.write(0x1227, bytes([language]))
    before = game.call('get_huc6280_status')
    cpu = run_save(game)
    ram = game.read(0, 0x2000)
    after = game.backup_ram()
    status = ram[0x105]
    saved, wanted = bi.expected_save(image, options, language)
    expect('save status', bi.STATUS[status], bi.STATUS[saved])
    expect('memory after the save', after == wanted, True)
    expect('zero page $22-$2C', ram[ZP[0]:ZP[-1] + 1], pattern)
    expect('settings', (ram[0x100], ram[0x1227]), (options, language))
    for name in ('X', 'Y', 'S'):
        expect(name, cpu[name], before[name])
    expect('MPR', cpu.get('MPR', cpu.get('mpr')), before.get('MPR', before.get('mpr')))
    # Not from the model:
    files = others(image)
    if files is not None:
        expect("other games' files", others(after), files)
    if status != bi.OK:
        expect('bytes changed without OK', sum(a != b for a, b in zip(image, after)), 0)
    else:
        try:
            card = bi.Directory(after)
            mine = [(at, length, good) for at, length, name, good in card.files() if name == OURS]
            expect('our file', [(length, good) for _, length, good in mine[:1]], [(bi.ENTRY_SIZE, True)])
            expect('our data', card.read(OURS), bytes([bi.VERSION, options, language]) + bytes(5))
            expect('pointer', card.word(0x8006), card.terminator())
        except (ValueError, KeyError) as error:
            problems.append(f'after an OK save the System Card style reader says: {error!r}')
        expect('a load of the saved memory (model)', bi.expected_load(after), (bi.OK, options, language))
    # Again: nothing more to do.
    run_save(game)
    expect('status after a second save', bi.STATUS[game.read(0x105, 1)[0]], bi.STATUS[saved])
    expect('memory after a second save', game.backup_ram() == after, True)
    return bi.STATUS[status], problems, after


def main():
    tally, bad, reload = {}, [], []
    with tempfile.TemporaryDirectory() as work, Game(EMU, work) as game:
        for k, image, (options, language) in images():
            status, problems, after = check(game, image, options, language)
            key = f'{bi.STATUS[bi.expected_load(image)[0]]} -> {status}'
            tally[key] = tally.get(key, 0) + 1
            if status == 'OK' and k % 5 == 0:
                reload.append((after, options, language))
            if problems:
                bad.append(k)
                dump = Path(os.environ.get('FUZZ_OUT', '.')) / f'fuzz-{SEED}-{k}.brm'
                dump.write_bytes(image)
                print(f'image {k} ({dump}): {problems}', flush=True)
            if k % 100 == 99:
                print(f'{k + 1} images, {len(bad)} with problems', flush=True)
        # A real cold load of some saved memories (not the model's word for it).
        for after, options, language in reload:
            game.power_on(rom, after)
            game.call('set_breakpoint', {'address': '1cbe', 'memory_area': 'rom', 'execute': True})
            assert continue_to(game) == 'FCBE'
            game.call('remove_breakpoint', {'address': '1cbe', 'memory_area': 'rom'})
            ram = game.read(0, 0x2000)
            if (ram[0x105], ram[0x100], ram[0x1227]) != (bi.OK, options, language) or game.backup_ram() != after:
                bad.append('reload')
                print('a saved memory did not load:', (ram[0x105], ram[0x100], ram[0x1227]), (options, language))
    print(json.dumps({'seed': SEED, 'images': COUNT, 'model': os.environ.get('NG_BRAM_MODEL'),
                      'status at reset -> after the save': dict(sorted(tally.items())),
                      'saved memories loaded again': len(reload), 'with_problems': bad}, indent=1))
    print('PASS' if not bad else 'FAIL')
    sys.exit(0 if not bad else 1)


if __name__ == '__main__':
    main()
