#!/usr/bin/env python3
"""PC Engine backup RAM (BRAM) images for the saved-settings checks.

Three independent things live here (Python stdlib only, no ROM needed):

- builders for 2,048-byte images (`image`, `entry`, `settings_entry`) and
  the named test images of the settings-save matrix (`matrix`);
- `Directory`, a reader and writer that follows the System Card conventions
  as HuC's bm_ library implements them (huc_bram.asm: bm_open walks entries
  by length to the 00 00 terminator, bm_free and bm_create use the header's
  pointers, bm_delete closes the gap, bm_read checks the checksum). It is
  what "another game" or a backup manager would do with an image, and it
  shares no code with the model below;
- `expected_load` and `expected_save`, a model of what the game's own code
  (src/bram/main.asm) must do with an image, written from the design rules
  and not from the assembly. scripts/check_bram.py compares the game with
  it.

Run `bram_image.py list IMAGE` to read an image like a backup manager,
`bram_image.py make NAME OUT` to write a matrix image, `bram_image.py names`
to list them. Images are test data: never commit them.
"""
import argparse
from pathlib import Path
import sys

SIZE = 0x800
BASE = 0x8000               # the addresses in the header are for a bank at $8000
FIRST = 0x8010
TOP = 0x8800
TAG = b'HUBM'
NAME = b'NR ENHANCE'
ENTRY_SIZE = 0x18
VERSION = 1
# The save status the game keeps in $2105 (src/bram/main.asm ST_ values) and
# shows in the menu (src/options/menu.txt, the ? line).
STATUS = ('NONE', 'OK', 'READY', 'FULL', 'ERROR 1', 'ERROR 2', 'ERROR 3', 'ERROR 4', 'ERROR 5')
NONE, OK, READY, FULL, UNFORMATTED, CORRUPT, WRONG_SIZE, UNVERIFIED, BAD_DATA = range(9)
PALETTES = {0x00: 'ORIGINAL', 0x08: 'NES-A', 0x28: 'NES-B', 0x10: 'GB DMG', 0x18: 'HELL', 0xb8: 'SMS'}
DEFAULTS = (0x00, 1)        # $2100, $3227 after a reset without saved settings


def checksum(body):
    """The checksum of an entry whose bytes after the checksum are `body`."""
    return -sum(body) & 0xffff


def entry(name, data, ident=b'\0\0', sum_error=0, length=None):
    """One directory entry: length, checksum, id, 10-character name, data."""
    name = name.ljust(10)
    assert len(name) == 10 and len(ident) == 2
    body = ident + name + bytes(data)
    total = 4 + len(body) if length is None else length
    return total.to_bytes(2, 'little') + ((checksum(body) + sum_error) & 0xffff).to_bytes(2, 'little') + body


def settings_entry(options=0, language=1, version=VERSION, rest=bytes(5), **kwargs):
    """The game's own entry: version, $2100, $3227, five zero bytes."""
    return entry(NAME, bytes([version, options, language]) + rest, **kwargs)


def image(entries=(), end=TOP, fill=0x00, next_free=None, terminator=b'\0\0', tag=TAG):
    """A formatted image holding `entries` back to back."""
    body = b''.join(entries)
    free = FIRST + len(body) if next_free is None else next_free
    data = bytearray([fill]) * SIZE
    data[:16] = tag + end.to_bytes(2, 'little') + free.to_bytes(2, 'little') + bytes(8)
    data[16:16 + len(body) + len(terminator)] = body + terminator
    assert len(data) == SIZE, 'The entries do not fit 2 KiB'
    return bytes(data)


def other(index, size):
    """Another game's save: `size` bytes in all, recognisable contents."""
    names = (b'DRACULA X', b'YS BOOK 12', b'NEUTOPIA 2', b'SAPPHIRE', b'GATE THUND', b'SPRIGGAN')
    data = bytes((index * 37 + k * 11 + 5) & 0xff for k in range(size - 16))
    return entry(names[index % len(names)] if index < len(names) else b'GAME %04d' % index, data)


class Directory:
    """An image read and written the way HuC's bm_ routines do it."""

    def __init__(self, data):
        self.data = bytearray(data)

    def word(self, address):
        return int.from_bytes(self.data[address - BASE:address - BASE + 2], 'little')

    def put(self, address, value):
        self.data[address - BASE:address - BASE + 2] = value.to_bytes(2, 'little')

    def formatted(self):                          # bm_enable
        return bytes(self.data[:4]) == TAG

    def files(self):
        """[(address, length, 12-byte name, checksum good)] up to the
        terminator; raises on what bm_open calls a corrupt directory."""
        if not self.formatted():
            raise ValueError('not formatted')
        found, at = [], FIRST
        while True:
            if at + 2 > BASE + SIZE:
                raise ValueError(f'the directory runs off the memory at ${at:04X}')
            length = self.word(at)
            if length == 0:
                return found
            if at + length > self.word(0x8004) or length < 16:      # bm_open .x3
                raise ValueError(f'bad entry length ${length:04X} at ${at:04X}')
            if at + length > BASE + SIZE:
                raise ValueError(f'entry at ${at:04X} runs off the memory')
            raw = self.data[at - BASE:at - BASE + length]
            good = (sum(raw[4:]) + int.from_bytes(raw[2:4], 'little')) & 0xffff == 0
            found.append((at, length, bytes(raw[4:16]), good))
            at += length

    def terminator(self):
        files = self.files()
        return files[-1][0] + files[-1][1] if files else FIRST

    def free(self):                               # bm_free
        return max(0, self.word(0x8004) - self.word(0x8006) - 0x12)

    def read(self, name):                         # bm_read
        """The data of the first file of that 12-byte name; checks its sum."""
        for at, length, found, good in self.files():
            if found == name:
                if not good:
                    raise ValueError('bad file checksum')
                return bytes(self.data[at - BASE + 16:at - BASE + length])
        raise KeyError(name)

    def create(self, name, data):                 # bm_create, then bm_write
        if self.word(0x8006) + 0x12 + len(data) > self.word(0x8004):
            raise ValueError('not enough room')
        at = self.word(0x8006)
        raw = entry(name[2:], data, ident=name[:2])
        self.data[at - BASE:at - BASE + len(raw)] = raw
        self.put(0x8006, at + len(raw))
        self.put(at + len(raw), 0)

    def delete(self, name):                       # bm_delete
        for at, length, found, _ in self.files():
            if found == name:
                end = self.word(0x8006)
                tail = self.data[at + length - BASE:end + 2 - BASE]
                self.data[at - BASE:at - BASE + len(tail)] = tail
                self.put(0x8006, end - length)
                return
        raise KeyError(name)


def _settings(raw):
    """(options, language) of an ENTRY_SIZE entry, or None if the game must
    not use it: checksum, version, a palette mode the menu offers, bit 7
    exactly with SMS, bit 6 clear, a language the game has."""
    if (sum(raw[4:]) + int.from_bytes(raw[2:4], 'little')) & 0xffff:
        return None
    version, options, language = raw[16:19]
    mode = options & 0x38
    if (version != VERSION or options & 0x40 or mode in (0x20, 0x30)
            or bool(options & 0x80) != (mode == 0x38) or language > 2):
        return None
    return options, language


def _scan(data):
    """The design's validation: (status, terminator, limit, our entry) with
    status NONE, CORRUPT or OK. Addresses are $8000-based."""
    def word(address):
        return int.from_bytes(data[address - BASE:address - BASE + 2], 'little')
    if data[:4] != TAG:
        return NONE, None, None, None
    end = min(word(0x8004), TOP)
    if end < FIRST + 2:
        return CORRUPT, None, None, None
    limit, at, ours = end - 2, FIRST, None
    while True:
        length = word(at)
        if length == 0:
            break
        if length < 16 or at + length > limit:
            return CORRUPT, None, None, None
        if ours is None and data[at - BASE + 4:at - BASE + 16] == b'\0\0' + NAME:
            ours = at
        at += length
    pointer = word(0x8006)
    if pointer != at:
        # A create cut off after the entry appeared and before the pointer
        # moved (high byte first): our entry is the last one and the pointer
        # still names it, with the old or the new high byte.
        stale = (ours is not None and ours + ENTRY_SIZE == at and pointer & 0xff == ours & 0xff
                 and pointer >> 8 in (ours >> 8, at >> 8))
        if not stale:
            return CORRUPT, None, None, None
    return OK, at, limit, ours


def expected_load(data):
    """(status, $2100, $3227) after a reset with backup RAM `data` (None:
    no backup RAM)."""
    if data is None:
        return (NONE,) + DEFAULTS
    status, at, limit, ours = _scan(data)
    if status != OK:
        return (status,) + DEFAULTS
    if ours is None:
        return (READY if at + ENTRY_SIZE <= limit else FULL,) + DEFAULTS
    if int.from_bytes(data[ours - BASE:ours - BASE + 2], 'little') != ENTRY_SIZE:
        return (WRONG_SIZE,) + DEFAULTS
    settings = _settings(data[ours - BASE:ours - BASE + ENTRY_SIZE])
    return (OK,) + settings if settings else (BAD_DATA,) + DEFAULTS


def expected_save(data, options, language, writable=True):
    """(status, image afterwards) for the menu's Run with these settings.
    `writable` False: the memory ignores writes."""
    if data is None:
        return NONE, None
    data = bytearray(data)
    status, at, limit, ours = _scan(data)
    if status == NONE:
        # Blank: every byte from $8012 up $00, or every one $FF, and bytes
        # 1-17 blank or already a fresh header's (a format cut short).
        header = TAG + TOP.to_bytes(2, 'little') + FIRST.to_bytes(2, 'little') + bytes(10)
        blank = data[18]
        # Bytes 1-18 alike but not blank: an unmapped bank, not memory.
        if blank not in (0x00, 0xff) and all(b == blank for b in data[1:19]):
            return NONE, bytes(data)
        if blank not in (0x00, 0xff) or any(data[k] not in (blank, header[k]) for k in range(1, 18)):
            return UNFORMATTED, bytes(data)
        if not writable:
            return NONE, bytes(data)
        if any(b != blank for b in data[18:]):
            return UNFORMATTED, bytes(data)
        data[:18] = header
        status, at, limit, ours = _scan(data)
    if status != OK:
        return status, bytes(data)
    if not writable:
        raise NotImplementedError('a formatted memory that ignores writes: see check_bram')
    if ours is None:
        if at + ENTRY_SIZE > limit:
            return FULL, bytes(data)
        raw = settings_entry(options, language)
        data[at - BASE:at - BASE + ENTRY_SIZE + 2] = raw + b'\0\0'
        at += ENTRY_SIZE
    else:
        if int.from_bytes(data[ours - BASE:ours - BASE + 2], 'little') != ENTRY_SIZE:
            return WRONG_SIZE, bytes(data)
        body = data[ours - BASE + 4:ours - BASE + 16] + bytes([VERSION, options, language]) + bytes(5)
        data[ours - BASE + 2:ours - BASE + ENTRY_SIZE] = checksum(body).to_bytes(2, 'little') + body
    data[6:8] = at.to_bytes(2, 'little')
    return OK, bytes(data)


def filled(room):
    """Other games' saves filling the memory so that `room` bytes stay
    between the terminator's place and the end ($8800): an entry of ours
    needs ENTRY_SIZE + 2."""
    space = SIZE - 16 - room
    entries, index = [], 0
    while space:
        size = 0x90 if space >= 0x90 + 16 or space == 0x90 else space
        entries.append(other(index, size))
        space -= size
        index += 1
    return entries


def matrix():
    """{name: image or None} for the settings-save matrix. None: no backup
    RAM in the machine."""
    ours = settings_entry(0x1a, 2)                # HELL, No Damage, Chinese
    cases = {
        'absent': None,
        'empty-8800': image(),
        'empty-a000': image(end=0xa000),
        'empty-ff-fill': image(fill=0xff),
        'others-before': image([other(0, 0x40), other(1, 0x123), ours]),
        'others-after': image([ours, other(2, 0x31), other(3, 0x200)]),
        'others-both': image([other(0, 0x40), ours, other(3, 0x77)]),
        'others-only': image([other(0, 0x40), other(1, 0x123), other(2, 0x31)]),
        'full': image(filled(2)),
        'full-one-short': image(filled(ENTRY_SIZE + 1)),
        'exact-room': image(filled(ENTRY_SIZE + 2)),
        'exact-room-a000': image(filled(ENTRY_SIZE + 2), end=0xa000),
        'full-with-ours': image(filled(ENTRY_SIZE + 2) + [ours]),
        'tiny-entries': image([other(k, 18) for k in range(112)]),
        'tiny-entries-ours-last': image([other(k, 18) for k in range(110)] + [ours]),
        # Our entry, not usable.
        'ours-bad-checksum': image([other(0, 0x40), settings_entry(0x1a, 2, sum_error=1)]),
        'ours-short': image([entry(NAME, bytes([VERSION, 0x1a, 2]) + bytes(4)), other(1, 0x30)]),
        'ours-long': image([entry(NAME, bytes([VERSION, 0x1a, 2]) + bytes(6)), other(1, 0x30)]),
        'ours-short-last': image([other(1, 0x30), entry(NAME, bytes([VERSION, 0x1a, 2]) + bytes(4))]),
        'ours-version-0': image([settings_entry(0x1a, 2, version=0)]),
        'ours-version-2': image([settings_entry(0x1a, 2, version=2)]),
        'ours-mode-20': image([settings_entry(0x20, 1)]),
        'ours-mode-30': image([settings_entry(0x30, 1)]),
        'ours-bit6': image([settings_entry(0x40, 1)]),
        'ours-bit7-without-sms': image([settings_entry(0x98, 1)]),
        'ours-sms-without-bit7': image([settings_entry(0x38, 1)]),
        'ours-language-3': image([settings_entry(0x00, 3)]),
        'ours-language-ff': image([settings_entry(0x00, 0xff)]),
        'ours-twice': image([settings_entry(0x08, 0), other(0, 0x20), settings_entry(0x10, 2)]),
        'same-name-other-id': image([entry(NAME, bytes(8), ident=b'\x01\x00'), other(0, 0x20)]),
        # A create cut off before the pointer moved (accepted), and pointers
        # that are simply wrong (not).
        'pointer-stale': image([other(0, 0x40), ours], next_free=FIRST + 0x40),
        'pointer-stale-high': image([other(0, 0xe8), ours], next_free=FIRST + 0xe8 + 0x100),
        'pointer-stale-not-last': image([ours, other(0, 0x40)], next_free=FIRST),
        'pointer-low': image([other(0, 0x40)], next_free=FIRST),
        'pointer-high': image([other(0, 0x40)], next_free=FIRST + 0x60),
        'pointer-below-first': image([other(0, 0x40)], next_free=0x8008),
        'pointer-past-end': image([other(0, 0x40)], next_free=0x9000),
        # Corrupt directories.
        'end-zero': image([other(0, 0x40)], end=0x0000),
        'end-low': image([other(0, 0x40)], end=0x8010),
        'end-ffff': image([other(0, 0x40)], end=0xffff),
        'end-small': image([other(0, 0x40), other(1, 0x40)], end=0x8060),
        'entry-overruns': image([other(0, 0x40), (0x7c0).to_bytes(2, 'little') + bytes(14)]),
        'entry-to-the-end': image([other(0, 0x40), (0x7b0).to_bytes(2, 'little') + bytes(14)]),
        'entry-huge': image([other(0, 0x40), b'\xff\xff' + bytes(14)]),
        'entry-length-15': image([other(0, 0x40), b'\x0f\x00' + bytes(13)]),
        'entry-length-1': image([b'\x01\x00']),
        'no-terminator': image([other(0, 0x40)], terminator=b'\x05\x00'),
        'terminator-early': image([other(0, 0x40), b'\0\0', other(1, 0x40)]),
        'garbage-after-tag': TAG + bytes((k * 73 + 11) & 0xff for k in range(SIZE - 4)),
        # Unformatted.
        'blank-00': bytes(SIZE),
        'blank-ff': b'\xff' * SIZE,
        'blank-00-one-byte': bytes(SIZE - 300) + b'\x01' + bytes(299),
        'blank-ff-one-byte': b'\xff' * 16 + b'\xfe' + b'\xff' * (SIZE - 17),
        'blank-aa': b'\xaa' * SIZE,
        'blank-aa-one-byte': b'\xaa' * 9 + b'\xab' + b'\xaa' * (SIZE - 10),
        'open-bus-80': b'\x80' * SIZE,
        'blank-00-last-byte': bytes(SIZE - 1) + b'\x80',
        'blank-ff-byte-18': b'\xff' * 18 + b'\x00' + b'\xff' * (SIZE - 19),
        # A format cut short: finished at the next Run.
        'format-cut-test-byte': b'\x55' + bytes(SIZE - 1),
        'format-cut-header': b'\xff' * 4 + image(fill=0xff)[4:],
        'format-cut-tag': b'\xffUBM' + image(fill=0xff)[4:],
        'garbage': bytes((k * 197 + 3) & 0xff for k in range(SIZE)),
        'tag-damaged': b'HUBN' + image([other(0, 0x40), ours])[4:],
        'tag-lowercase': image([other(0, 0x40)], tag=b'hubm'),
    }
    # Every valid combination of settings.
    for mode in PALETTES:
        for bits in range(8):
            for language in range(3):
                cases[f'ours-{mode | bits:02x}-{language}'] = image([other(0, 0x40), settings_entry(mode | bits, language)])
    return cases


def describe(data):
    lines = []
    directory = Directory(data)
    if not directory.formatted():
        blank = data[0] if all(b == data[0] for b in data) else None
        return ['not formatted' + (f' (blank: every byte ${blank:02X})' if blank is not None else '')]
    lines.append(f'end ${directory.word(0x8004):04X}, first free ${directory.word(0x8006):04X}, '
                 f'{directory.free()} bytes free for a new file')
    try:
        for at, length, name, good in directory.files():
            text = name[2:].decode('ascii', 'replace')
            lines.append(f'${at:04X} {length:5d} bytes  id {name[:2].hex()}  "{text}"  '
                         f'checksum {"good" if good else "BAD"}')
            if name == b'\0\0' + NAME and length == ENTRY_SIZE:
                settings = _settings(data[at - BASE:at - BASE + length])
                lines.append('        settings: ' + (f'$2100 = ${settings[0]:02X}, language {settings[1]}'
                                                     if settings else 'not usable'))
        if directory.terminator() != directory.word(0x8006):
            lines.append(f'the terminator is at ${directory.terminator():04X}, not at the first free byte')
    except ValueError as error:
        lines.append(f'corrupt: {error}')
    status, options, language = expected_load(data)
    lines.append(f'the game at reset: SAVE: {STATUS[status]}, $2100 = ${options:02X}, language {language}')
    return lines


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('names')
    p = sub.add_parser('list')
    p.add_argument('image', type=Path)
    p = sub.add_parser('make')
    p.add_argument('name')
    p.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.command == 'names':
        print('\n'.join(matrix()))
    elif args.command == 'list':
        data = args.image.read_bytes()
        if len(data) < SIZE:
            sys.exit(f'{args.image}: {len(data)} bytes; a backup RAM image has {SIZE}')
        print('\n'.join(describe(data[:SIZE])))
    else:
        data = matrix()[args.name]
        if data is None:
            sys.exit(f'{args.name}: a machine without backup RAM has no image')
        args.output.write_bytes(data)
        print('\n'.join(describe(data)))


if __name__ == '__main__':
    main()
