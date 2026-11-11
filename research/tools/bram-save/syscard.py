"""The real System Card's backup RAM routines against the game's file
(evidence for docs/validation/bram-save.md, "The System Card as the judge").

scripts/bram_image.py's `Directory` is a port of HuC's bm_ library. This
probe asks the code that owns the format instead: the Super System Card
3.0 ROM is loaded as a card, and after its reset has run its BM_ entries
are called from a stub in work RAM ($E048 BM_FORMAT, $E04B BM_FREE, $E04E
BM_READ, $E051 BM_WRITE, $E054 BM_DELETE, $E057 BM_FILES; parameters in the
zero page: _ax $F8, _bx $FA, _cx $FC, _dx $FE; a file name is 12 bytes: a
2-byte id and 10 characters) on backup RAM images the game produced, and
the game is then run on what the System Card left:

1. the game's loader and save (as in fuzz.py: the reset code to $FCBE, then
   the save at $4B03) on a start image, with settings to save;
2. the System Card lists the files (BM_FILES), reads every one (BM_READ
   checks the checksum), reports the free space (BM_FREE): the game's file
   must be there with its 8 data bytes, every other file as it was, and
   the free space 26 bytes less than before a create;
3. the System Card writes a file of its own (BM_WRITE), and the game's
   loader must still load the settings; the game saves other settings, and
   the System Card must read both files back;
4. the System Card deletes the game's file (BM_DELETE): the game sees READY
   and its next save puts the file back, readable by the System Card;
5. BM_FORMAT on a blank memory gives byte for byte the header the game's
   own format writes;
6. reported, not judged: what BM_WRITE does to the two states a cut save
   can leave (the header's pointer still naming the game's entry).

The System Card ROM is the user's own file: it is never copied into the
repository.

usage: syscard.py SYSTEM-CARD.pce GAME.pce
"""
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts'))
import bram_image as bi  # noqa: E402
from check_bram import continue_to  # noqa: E402
from comparison_video import Game  # noqa: E402

bios, rom = sys.argv[1:3]
EMU = os.environ['NG_EMULATOR']
OURS = b'\0\0' + bi.NAME
STUB, NAME, BUFFER, RESULT = 0x1f00, 0x1e00, 0x1000, 0x1ef0     # work RAM offsets ($2000 + ...); the buffer has $800
ENTRY = {'format': 0xe048, 'free': 0xe04b, 'read': 0xe04e, 'write': 0xe051, 'delete': 0xe054, 'files': 0xe057}
SAVE = bytes.fromhex('4304 48 a946 5304 20034b 68 5304')        # the game's save from a stub (fuzz.py)
problems = []


def expect(what, found, wanted):
    if found != wanted:
        problems.append(f'{what}: {found!r}, expected {wanted!r}')
    return found == wanted


def run_stub(game, code):
    stop = f'{0x2000 + STUB + len(code):04X}'
    game.write(STUB, code + b'\x80\xfe')
    game.reg('PC', 0x2000 + STUB)
    game.call('set_breakpoint', {'address': stop, 'execute': True})
    try:
        pc = continue_to(game)
    finally:
        game.call('remove_breakpoint', {'address': stop})
    assert pc == stop, pc


class SystemCard:
    """The System Card ROM running with a backup RAM image."""

    def __init__(self, game, image):
        self.game = game
        game.power_on(bios, image)
        game.step(90)                       # its reset code: MPRs, the stack, its RAM

    def call(self, entry, ax=0, bx=0, cx=0, dx=0):
        """-> (A, _ax, _bx, _cx, _dx) after the routine."""
        game = self.game
        game.write(0xf8, b''.join(v.to_bytes(2, 'little') for v in (ax, bx, cx, dx)))
        address = ENTRY[entry]
        # sei, jsr entry, sei, sta result, then the stop
        run_stub(game, bytes([0x78, 0x20, address & 0xff, address >> 8, 0x78, 0x8d,
                              (0x2000 + RESULT) & 0xff, (0x2000 + RESULT) >> 8]))
        words = game.read(0xf8, 8)
        return (game.read(RESULT, 1)[0],) + tuple(int.from_bytes(words[k:k + 2], 'little') for k in (0, 2, 4, 6))

    def files(self):
        """[(12-byte name, data length)] as BM_FILES lists them."""
        found = []
        for index in range(1, 130):
            a, *_ = self.call('files', ax=index, bx=0x2000 + BUFFER)
            if a != 0:
                expect('BM_FILES at the end of the list', a, 1)
                return found
            raw = self.game.read(BUFFER, 14)
            found.append((bytes(raw[:12]), raw[12] | raw[13] << 8))
        raise RuntimeError('BM_FILES never ended')

    def read(self, name, length):
        """(A, data): A = 0 good, 1 no such file, 2 bad checksum, $FF unformatted."""
        self.game.write(NAME, name)
        self.game.write(BUFFER, b'\xee' * length)
        a, *_ = self.call('read', ax=0x2000 + NAME, bx=0x2000 + BUFFER, cx=length, dx=0)
        return a, bytes(self.game.read(BUFFER, length))

    def write(self, name, data):
        self.game.write(NAME, name)
        self.game.write(BUFFER, data)
        return self.call('write', ax=0x2000 + NAME, bx=0x2000 + BUFFER, cx=len(data), dx=0)[0]

    def delete(self, name):
        self.game.write(NAME, name)
        return self.call('delete', ax=0x2000 + NAME)[0]

    def free(self):
        a, _, _, cx, _ = self.call('free')
        return a, cx

    def format(self):
        self.game.write(NAME, b'!BM FORMAT!')
        return self.call('format', ax=0x2000 + NAME)[0]

    def image(self):
        return self.game.backup_ram()


def game_load(game, image):
    """The game's reset loader on `image` -> (status text, $2100, $3227)."""
    game.power_on(rom, image)
    game.call('set_breakpoint', {'address': '1cbe', 'memory_area': 'rom', 'execute': True})
    try:
        assert continue_to(game) == 'FCBE'
    finally:
        game.call('remove_breakpoint', {'address': '1cbe', 'memory_area': 'rom'})
    ram = game.read(0, 0x2000)
    expect('the loader left the memory alone', game.backup_ram(), image)
    return bi.STATUS[ram[0x105]], ram[0x100], ram[0x1227]


def game_save(game, image, options, language):
    """The game's loader, then its save with these settings -> (status text, image)."""
    game_load(game, image)
    game.write(0x100, bytes([options]))
    game.write(0x1227, bytes([language]))
    run_stub(game, SAVE)
    return bi.STATUS[game.read(0x105, 1)[0]], game.backup_ram()


def listing(image):
    """What the port (bram_image.Directory) lists: [(name, data length)]."""
    return [(name, length - 16) for _, length, name, _ in bi.Directory(image).files()]


def scenario(game, label, start, settings=(0x1a, 2)):
    print(f'== {label}', flush=True)
    before = SystemCard(game, start)
    free_before = before.free() if bi.Directory(start).formatted() else None
    had = OURS in [name for name, _ in listing(start)] if bi.Directory(start).formatted() else False
    status, saved = game_save(game, start, *settings)
    if not expect(f'{label}: the game saved', status, 'OK'):
        return
    card = SystemCard(game, saved)
    files = card.files()
    expect(f'{label}: BM_FILES agrees with the port', files, listing(saved))
    expect(f'{label}: our file listed once with 8 data bytes', [f for f in files if f[0] == OURS], [(OURS, 8)])
    for name, length in files:
        a, data = card.read(name, length)
        at = next(at for at, _, n, _ in bi.Directory(saved).files() if n == name)
        expect(f'{label}: BM_READ {name[2:].decode()!r}', (a, data), (0, saved[at - bi.BASE + 16:at - bi.BASE + 16 + length]))
    expect(f'{label}: our data', card.read(OURS, 8)[1], bytes([bi.VERSION, *settings]) + bytes(5))
    a, free = card.free()
    expect(f'{label}: BM_FREE agrees with the port', (a, free), (0, bi.Directory(saved).free()))
    if free_before and not had:
        # The file's 24 bytes (its terminator only moved); BM_FREE stops at 0.
        expect(f'{label}: free space fell by the file', free_before[1] - free, min(24, free_before[1]))
    expect(f'{label}: nothing changed by listing and reading', card.image(), saved)
    # The System Card writes its own file after ours ...
    theirs, payload = b'\0\0SYSCARD   ', bytes((7 * k + 3) & 0xff for k in range(40))
    if free < len(payload):
        # A game asks BM_FREE first; BM_WRITE itself does not check before
        # it creates the entry, so it is not called without room here.
        print(f'   {free} bytes free: no System Card file written', flush=True)
        return
    expect(f'{label}: BM_WRITE', card.write(theirs, payload), 0)
    with_theirs = card.image()
    expect(f'{label}: BM_READ of the new file', card.read(theirs, 40), (0, payload))
    expect(f'{label}: the port accepts what BM_WRITE left', listing(with_theirs), listing(saved) + [(theirs, 40)])
    # ... the game still loads, and saves other settings ...
    expect(f'{label}: the game loads after BM_WRITE', game_load(game, with_theirs), ('OK',) + settings)
    status, resaved = game_save(game, with_theirs, 0xb9, 0)
    expect(f'{label}: the game saves again', status, 'OK')
    card = SystemCard(game, resaved)
    expect(f'{label}: BM_READ ours after the second save', card.read(OURS, 8), (0, bytes([bi.VERSION, 0xb9, 0]) + bytes(5)))
    expect(f'{label}: BM_READ theirs after the second save', card.read(theirs, 40), (0, payload))
    expect(f'{label}: the list after the second save', card.files(), files + [(theirs, 40)])
    # ... the System Card deletes our file, the game puts it back.
    expect(f'{label}: BM_DELETE ours', card.delete(OURS), 0)
    without = card.image()
    expect(f'{label}: the list after BM_DELETE', card.files(), [f for f in files if f[0] != OURS] + [(theirs, 40)])
    expect(f'{label}: the game after BM_DELETE', game_load(game, without), ('READY',) + bi.DEFAULTS)
    status, again = game_save(game, without, 0x10, 1)
    expect(f'{label}: the game saves after BM_DELETE', status, 'OK')
    card = SystemCard(game, again)
    expect(f'{label}: BM_READ ours after that', card.read(OURS, 8), (0, bytes([bi.VERSION, 0x10, 1]) + bytes(5)))
    for name, length in [f for f in files if f[0] != OURS]:
        at = next(at for at, _, n, _ in bi.Directory(start).files() if n == name)
        expect(f'{label}: {name[2:].decode()!r} at the end', card.read(name, length),
               (0, start[at - bi.BASE + 16:at - bi.BASE + 16 + length]))


def main():
    cases = bi.matrix()
    with tempfile.TemporaryDirectory() as work, Game(EMU, work) as game:
        # Does the System Card run here at all? An empty formatted memory.
        card = SystemCard(game, cases['empty-8800'])
        print('System Card on an empty memory: files', card.files(), 'free', card.free(), flush=True)
        expect('BM_FREE of an empty memory', card.free(), (0, 0x800 - 0x10 - 0x12))
        for label in ('empty-8800', 'others-only', 'others-before', 'others-both', 'exact-room', 'full-with-ours',
                      'pointer-stale', 'pointer-stale-high', 'ours-bad-checksum', 'blank-ff', 'blank-00'):
            scenario(game, label, cases[label])
        # 5. The formats.
        # The game formats and creates its file in one save: with the file
        # deleted again (by the System Card) the first 18 bytes must be
        # what BM_FORMAT writes on the same blank memory (BM_FORMAT also
        # zero-fills the rest, which the game leaves as it was).
        for label in ('blank-00', 'blank-ff'):
            _, ours = game_save(game, cases[label], 0x00, 1)
            card = SystemCard(game, ours)
            expect(f'{label}: BM_DELETE of our file after the game\'s format', card.delete(OURS), 0)
            emptied = card.image()
            card = SystemCard(game, cases[label])
            a = card.format()
            theirs = card.image()
            print(f'== format of {label}: BM_FORMAT returned {a}; header {theirs[:18].hex(" ")}; '
                  f'the game\'s, emptied: {emptied[:18].hex(" ")}', flush=True)
            expect(f'{label}: BM_FORMAT', a, 0)
            expect(f'{label}: the game\'s format header is BM_FORMAT\'s', emptied[:18], theirs[:18])
            expect(f'{label}: an empty directory either way', (bi.Directory(theirs).files(), bi.Directory(emptied).files()),
                   ([], []))
        # 6. Cut-save states under the System Card (reported).
        report = {}
        for label in ('pointer-stale', 'pointer-stale-high'):
            start = cases[label]
            card = SystemCard(game, start)
            listed = card.files()
            a = card.write(b'\0\0SYSCARD   ', bytes(range(40)))
            after = card.image()
            others_kept = all(card.read(name, length - 16) == (0, start[at - bi.BASE + 16:at - bi.BASE + length])
                              for at, length, name, _ in bi.Directory(start).files() if name != OURS)
            report[label] = {'BM_FILES before': [(n[2:].decode(), size) for n, size in listed], 'BM_WRITE returned': a,
                             'BM_FILES after': [(n[2:].decode(), size) for n, size in card.files()],
                             "other games' files still read back": others_kept,
                             'the game afterwards': game_load(game, after)}
            expect(f'{label}: other files after a System Card write on the cut state', others_kept, True)
        print(json.dumps({'cut-save states under BM_WRITE': report}, indent=1))
    for problem in problems:
        print('PROBLEM', problem)
    print('PASS' if not problems else 'FAIL')
    sys.exit(0 if not problems else 1)


if __name__ == '__main__':
    main()
