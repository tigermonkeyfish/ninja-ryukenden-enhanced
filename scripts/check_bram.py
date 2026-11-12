#!/usr/bin/env python3
"""Check the saved settings (src/bram) in headless Geargrafx.

Every case is a cold boot of the candidate with backup RAM absent or holding
an image from scripts/bram_image.py, controller input from there on, and the
debugger only to read memory and to stop at backup RAM writes. What the game
does is compared with bram_image's model of the design (`expected_load`,
`expected_save`) and with its System Card style reader (`Directory`). Parts
(`--only`):

matrix  For each image of `bram_image.matrix()` (or `--cases`): mash Run
        from power-on to the first 1-1 update; the frame it comes at must be
        the baseline build's (`--baseline`, booted without backup RAM and
        given the same settings by a debugger write after its first frame:
        a mapped palette mode moves a stage start by itself);
        $2100, $3227 and the status $2105 as the model says; backup RAM
        untouched. Then the menu: the SAVE field shows that status; Select
        (cancel) writes nothing; Run (settings as loaded) leaves the image
        and the status the model's `expected_save` gives, every other
        game's file where and as it was, no write at all when the image is
        to stay as it is (but the three writes of the writable test on a
        blank header: TEST_WRITES); the menu then shows the new status, and
        a second Run writes nothing.
cycle   From an image with other games' saves: change one setting in the
        menu, Run, power off (a new session with the image left behind),
        and the next boot starts with that setting; for every palette mode,
        each option and each language in turn, and once the reset row (I)
        from several changed settings, after which the defaults boot. The
        window's status line must show the boot's status. The last image
        must list, read and delete like a System Card file.
cut     Saves cut short: a Run that creates the entry, one that rewrites
        it, one that formats a blank memory first and one that finishes a
        stale pointer are stopped after every byte written. Each image so
        far must read like the old or the new directory to the System Card
        style reader with every other file intact, boot the game with the
        old or the new settings (`defaults` names the images where the entry
        is mid-rewrite and the game falls back to the defaults), and a Run
        from there must end in the complete new state.
timing  Master clocks of the reset loader ($FFE6 to the native init $FCBE)
        and of the save (its entry to its return, interrupts off) for the
        named images, against the baseline's 8-byte English initialization.
lock    (with `--bram-model lock` or `key`) Negative controls: copies of
        the candidate with the unlock writes removed, cut down to the single
        $80 write, ending in $00, or with the lock read removed must behave
        as that model says (no backup RAM seen and nothing written, or the
        bank left open), which proves that the model bites and that the
        "locked again" probe can fail.

`--bram-model` runs every part on the test-only emulator of
research/tools/bram-save/locktest_patch.py (give its binary as
`--emulator`), which models the backup RAM lock for a HuCard:
  lock      locked at reset, unlocked by bit 7 of a write to $1807, locked
            by a read of $1803 (the MiSTer core's rule);
  key       only the three writes $48, $75, $80 unlock;
  readonly  as lock, but writes never land: a Run that has to write ends
            with ERROR 4 (NONE on a blank memory) and the image as it was;
  openbus   no backup RAM: the bank reads the address's high byte: NONE
            before and after Run, no write attempted, whatever the image.
With lock, key and readonly a stub run by the debugger after every boot and
every Run (`bank_locked`) reads and writes bank $F7 the way the game would:
the reads must give $FF and the writes must not land (locked again). Each
invocation first proves that the emulator really applies the model
(`model_applies`).

Writes report.json to the output folder; captures stay private there.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

import bram_image as bi
from check_menu import BOX_ROWS, BOX_WIDTH, DECODE, FIRST_UPDATE, MENU, box_column, press, window_words
from comparison_video import Game

BOOT_HOOK = '1fe6'           # $FFE6: the reset trampoline (the baseline's English initialization)
NATIVE_INIT = '1cbe'         # $FCBE: where it goes on
SAVE_ENTRY = 0x46 * 0x2000 + 0xb03      # bank $46 $4B03: the menu's save
LINE = 1365                  # master clocks a raster line
# Images on which a Run changes nothing in the end but writes: the writable
# test (two patterns and the old value at $8000) passes on a blank header,
# then the rest of the memory turns out not to be blank.
TEST_WRITES = {'blank-00-one-byte': 3, 'blank-00-last-byte': 3}
# Up to this many entries the reset loader ends within the time the native
# boot leaves before its second vblank interrupt (the timing part and
# research/tools/bram-save/bootslack.py); with more, the boot runs one
# interrupt behind the baseline's and its frames are not compared. Measured
# (research/tools/bram-save/manyfiles.py, 18-byte files): the boot is the
# baseline's up to 56 entries when none is ours, and up to 46 when one is
# ours and loads (reading and checking it costs about 10,600 clocks more).
MANY_ENTRIES = 48
MANY_WITH_OURS = 42
ROWS = {'parallax': 1, 'no damage': 2, 'firewheel': 3, 'palette': 4, 'language': 5,
        'reset': len(MENU['fields'])}         # the reset row (I: every option to its default)
MODEL = None                 # --bram-model: the test-only emulator's NG_BRAM_MODEL
LOCKING = ('lock', 'key', 'readonly')
BANK46 = (0x46 * 0x2000, 0x47 * 0x2000)
UNLOCK = bytes.fromhex('a9488d0718a9758d0718a9808d0718')    # lda #$48/$75/$80, sta $1807
LOCK = bytes.fromhex('ad0318d4')                            # lda $1803, csh
STUB = 0x1f00                # work RAM offset of the probe's code: CPU $3F00


def bank_locked(game, work):
    """Is backup RAM locked right now? A stub in work RAM maps bank $F7 and
    reads and writes its first and last byte as the game's code would. True:
    all four reads gave $FF and the memory is as it was. False: the reads
    gave the memory's bytes and the writes landed. Anything else raises. The
    machine is put back (a save state from before the stub; the lock itself
    is not in a state, and the stub does not touch $1807/$1803)."""
    image = game.backup_ram()
    values = [0xa5 if image[k] == 0x5a else 0x5a for k in (0, -1)]
    code = bytes.fromhex('78 4310 48 a9f7 5310'                         # sei, tma #4, pha, lda #$f7, tam #4
                         f'ad0080 8df03f a9{values[0]:02x} 8d0080 ad0080 8df13f'
                         f'adff87 8df23f a9{values[1]:02x} 8dff87 adff87 8df33f'
                         '68 5310')                                    # pla, tam #4
    stop = f'{0x2000 + STUB + len(code):04X}'
    state = work / 'probe.state'
    game.call('save_state_file', {'file_path': str(state)})
    game.write(STUB, code + b'\x80\xfe')                               # ... and stay there
    game.reg('PC', 0x2000 + STUB)
    game.call('set_breakpoint', {'address': stop, 'execute': True})
    try:
        pc = continue_to(game)
    finally:
        game.call('remove_breakpoint', {'address': stop})
    reads = tuple(game.read(STUB + 0xf0, 4))
    after = game.backup_ram()
    game.call('load_state_file', {'file_path': str(state)})
    game.held = set()
    game.press(set())
    if pc != stop or game.backup_ram() != image:
        raise RuntimeError(f'the lock probe did not run as planned: pc {pc}')
    if reads == (0xff,) * 4 and after == image:
        return True
    if (reads == (image[0], values[0], image[-1], values[1])
            and after == bytes([values[0]]) + image[1:-1] + bytes([values[1]])):
        return False
    raise RuntimeError(f'the lock probe: reads {reads}, image changed: {after != image}')


def probe(game, work):
    """After a boot or a Run, at the stage's first update: note whether the
    bank is locked (the models that have a lock, a machine with backup RAM)."""
    if MODEL in LOCKING and game.backup_ram() is not None:
        game.locks = getattr(game, 'locks', []) + [bank_locked(game, work)]


def continue_to(game, polls=400000):
    game.call('debug_continue')
    for _ in range(polls):
        status = game.call('debug_get_status')
        if status.get('paused'):
            return status['pc']
    raise TimeoutError('the emulator did not stop')


def normalize(game, work):
    """After a breakpoint stop: save and reload, so the next frame step has a
    defined length (docs/pc-engine/EMULATOR.md)."""
    state = work / 'normal.state'
    game.call('save_state_file', {'file_path': str(state)})
    game.call('load_state_file', {'file_path': str(state)})
    game.held = set()
    game.press(set())


def clock(game, work):
    state = work / 'clock.state'
    game.call('save_state_file', {'file_path': str(state)})
    return int.from_bytes(state.read_bytes()[1:9], 'little')


def boot(game, rom, bram, work, poke=None):
    """Power on and mash Run to the first 1-1 update, counted like
    check_boot.py. The game is left 40 frames into 1-1. `poke`: ($2100,
    $3227) written by the debugger after the first frame (the baseline)."""
    game.power_on(rom, bram)
    game.call('set_breakpoint', {'address': FIRST_UPDATE, 'memory_area': 'rom', 'execute': True})
    for frame in range(3000):
        gameplay = game.read(0x240, 1)[0] == 0 and frame > 60
        game.press({'run'} if frame % 20 < 2 and not gameplay else set())
        game.step(1)
        if poke and frame == 0:
            game.write(0x100, bytes([poke[0]]))
            game.write(0x1227, bytes([poke[1]]))
        if game.call('debug_get_status').get('pc') == '8457':
            break
    else:
        raise RuntimeError('1-1 did not start')
    game.call('remove_breakpoint', {'address': FIRST_UPDATE, 'memory_area': 'rom'})
    ram = game.read(0, 0x2000)
    found = {'first_update_frame': frame + 1, 'options': ram[0x100], 'language': ram[0x1227],
             'status': ram[0x105], 'stage': ram[0xe5f], 'palette_state': ram[0x104]}
    probe(game, work)
    normalize(game, work)
    game.step(40)
    return found


def open_menu(game):
    """Press Select; the window's status row as text, or None if no window."""
    press(game, 'select', after=8)
    ram = game.read(0, 0x2000)
    row, column, width = MENU['status']
    words = window_words(game, box_column(ram))[row]
    if any(w[1] != 0xf7 for w in words):
        return None
    return ''.join(DECODE.get(w[0], '?') for w in words).strip()


def cancel(game):
    press(game, 'select', after=40)


def accept(game, work, watch):
    """Press Run in the open menu and go on to the restarted stage's first
    update. With `watch`: the backup RAM after each write to it, in order
    (under a lock model a write that is attempted but does not land stops
    here too, with the memory as it was)."""
    game.press({'run'})
    game.step(2)
    game.call('set_breakpoint', {'address': FIRST_UPDATE, 'memory_area': 'rom', 'execute': True})
    if watch:
        game.call('set_breakpoint_range', {'start_address': '000', 'end_address': '7ff',
                                           'memory_area': 'backup_ram', 'write': True})
    game.press(set())
    images = []
    try:
        for _ in range(4000):
            if continue_to(game) == '8457':
                break
            images.append(game.backup_ram())
        else:
            raise RuntimeError('the stage did not restart')
    finally:
        game.call('remove_breakpoint', {'address': FIRST_UPDATE, 'memory_area': 'rom'})
        if watch:
            game.call('remove_breakpoint', {'address': '000', 'end_address': '7ff', 'memory_area': 'backup_ram'})
    probe(game, work)
    normalize(game, work)
    game.step(40)
    return images


def others(data):
    """Other games' files in an image the System Card style reader accepts:
    {address: bytes}; None if it does not."""
    try:
        return {at: bytes(data[at - bi.BASE:at - bi.BASE + length])
                for at, length, name, _ in bi.Directory(data).files() if name != b'\0\0' + bi.NAME}
    except ValueError:
        return None


def expected_run(image, options, language, dead):
    """(status, image afterwards) of a Run under the model in use. `dead`:
    the game cannot reach the memory at all (a negative control)."""
    if image is None:
        return bi.NONE, None
    if dead or MODEL == 'openbus':
        return bi.NONE, image
    saved, after = bi.expected_save(image, options, language)
    if MODEL == 'readonly':
        if bi.expected_load(image)[0] == bi.NONE:        # unformatted: the writable test comes first and fails
            return bi.expected_save(image, options, language, writable=False)
        if after != image:
            return bi.UNVERIFIED, image                  # written, read back: not there
    return saved, after


def check_case(emulator, rom, name, image, output, reference, dead=False, locked=True):
    """`dead`, `locked`: what a negative control must show instead (the
    memory never reached; the bank left open)."""
    work = Path(tempfile.mkdtemp(prefix='bram-', dir=output))
    problems = []
    unreachable = dead or MODEL == 'openbus'
    attempts = MODEL == 'readonly' or dead               # writes that do not land still stop the debugger

    def expect(what, found, wanted):
        if found != wanted:
            problems.append(f'{what}: {found!r}, expected {wanted!r}')

    try:
        with Game(emulator, work) as game:
            started = boot(game, rom, image, work)
            status, options, language = (bi.NONE,) + bi.DEFAULTS if unreachable else bi.expected_load(image)
            expect('status at reset', bi.STATUS[started['status']], bi.STATUS[status])
            expect('$2100', started['options'], options)
            expect('$3227', started['language'], language)
            files = None if image is None else others(image)
            # Every entry counts, ours too; exactly MANY_ENTRIES is still compared.
            entries = 0 if files is None else len(bi.Directory(image).files())
            ours = files is not None and entries > len(files)
            slow = entries > (MANY_WITH_OURS if ours else MANY_ENTRIES) and not unreachable
            if not slow:
                expect('first update frame', started['first_update_frame'], reference(options, language))
            expect('backup RAM after the boot', game.backup_ram(), image)
            probed = MODEL in LOCKING and image is not None
            if probed:
                expect('bank $F7 locked after the boot', game.locks[-1], locked)
            expect('menu after the boot', open_menu(game), bi.STATUS_TEXT[status])
            cancel(game)
            expect('backup RAM after a cancel', game.backup_ram(), image)
            expect('status after a cancel', game.read(0x105, 1)[0], status)
            # Run with the settings as they are.
            expect('menu before Run', open_menu(game), bi.STATUS_TEXT[status])
            writes = accept(game, work, image is not None)
            ram = game.read(0, 0x2000)
            saved, after = expected_run(image, ram[0x100], ram[0x1227], dead)
            expect('settings after Run', (ram[0x100], ram[0x1227]), (options, language))
            expect('status after Run', bi.STATUS[ram[0x105]], bi.STATUS[saved])
            expect('backup RAM after Run', game.backup_ram(), after)
            if probed:
                expect('bank $F7 locked after Run', game.locks[-1], locked)
            if attempts:
                expect('writes that landed', [k for k, w in enumerate(writes) if w != image], [])
            elif after == image:
                expect('writes on an image that stays as it is', len(writes),
                       0 if MODEL == 'openbus' else TEST_WRITES.get(name, 0))
            if image is not None and others(image) is not None:
                expect("other games' files after Run", others(game.backup_ram()), others(image))
            expect('menu after Run', open_menu(game), bi.STATUS_TEXT[saved])
            again = accept(game, work, image is not None)
            expect('status after a second Run', bi.STATUS[game.read(0x105, 1)[0]], bi.STATUS[saved])
            expect('backup RAM after a second Run', game.backup_ram(), after)
            if probed:
                expect('bank $F7 locked after a second Run', game.locks[-1], locked)
                expect('lock probes run', len(game.locks), 3)
            if saved == bi.OK:
                expect('writes in a second Run', len(again), 0)
            result = {'case': name, 'reset': bi.STATUS[status], 'options': f'${options:02X}', 'language': language,
                      'run': bi.STATUS[saved], 'writes': len(writes),
                      'locked_after_boot_run_run': getattr(game, 'locks', None),
                      'bytes_changed': 0 if image is None else sum(a != b for a, b in zip(image, after)),
                      'first_update_frame': started['first_update_frame'], 'problems': problems}
            if slow:
                result['boot_not_compared'] = (f'{entries} entries, more than {MANY_ENTRIES} '
                                               f'({MANY_WITH_OURS} with ours): first update at frame '
                                               f"{started['first_update_frame']}, the baseline's at "
                                               f'{reference(options, language)} (the boot runs one vblank '
                                               'interrupt behind, which moves the mashed Run presses)')
    except Exception as error:                     # a hang or a crash is a result too
        result = {'case': name, 'problems': problems + [f'{type(error).__name__}: {error}']}
    shutil.rmtree(work, ignore_errors=True)
    result['ok'] = not result['problems']
    return result


def baseline_frames(emulator, rom, output):
    """reference(options, language): the baseline's first-update frame with
    those settings, measured once each."""
    known = {}

    def reference(options, language):
        if (options, language) not in known:
            work = Path(tempfile.mkdtemp(prefix='bram-', dir=output))
            with Game(emulator, work) as game:
                known[options, language] = boot(game, rom, None, work, poke=(options, language))['first_update_frame']
            shutil.rmtree(work, ignore_errors=True)
        return known[options, language]
    reference.known = known
    return reference


def check_matrix(emulator, rom, baseline, output, names, shard):
    cases = bi.matrix()
    names = [n for n in (names or cases)]
    names = [n for i, n in enumerate(names) if i % shard[1] == shard[0]]
    reference = baseline_frames(emulator, baseline, output)
    results = []
    for name in names:
        result = check_case(emulator, rom, name, cases[name], output, reference)
        results.append(result)
        print(name, 'ok' if result['ok'] else result['problems'],
              {k: result.get(k) for k in ('reset', 'options', 'language', 'run', 'writes', 'bytes_changed')}, flush=True)
    return {'baseline_first_update_frame': {f'${o:02X}/{l}': f for (o, l), f in sorted(reference.known.items())},
            'cases': results}


def change(game, row, presses):
    """In the open menu: go to `row`, press Left/Right."""
    for _ in range(row):
        press(game, 'down')
    for button in presses:
        press(game, button)


def check_cycle(emulator, rom, output):
    """One setting changed per power cycle."""
    steps = ([('palette', ['right'])] * 5 + [('parallax', ['right']), ('no damage', ['right']),
             ('firewheel', ['right']), ('language', ['right']), ('language', ['right']), ('reset', ['I']),
             ('palette', ['right']), ('language', ['right']), ('parallax', ['right']),
             ('no damage', ['right']), ('firewheel', ['right'])])
    image = bi.matrix()['others-only']
    first = others(image)
    results, seen = [], set()
    for step, (row, presses) in enumerate(steps + [(None, None)]):
        work = Path(tempfile.mkdtemp(prefix='bram-', dir=output))
        problems = []
        with Game(emulator, work) as game:
            started = boot(game, rom, image, work)
            wanted = bi.expected_load(image)
            if (started['status'], started['options'], started['language']) != wanted:
                problems.append(f'boot: {started}, expected {wanted}')
            seen.add((started['options'], started['language']))
            entry = {'step': step, 'boot_options': f"${started['options']:02X}", 'boot_language': started['language'],
                     'boot_status': bi.STATUS[started['status']]}
            if row is not None:
                text = open_menu(game)
                if text is None:
                    problems.append('the menu did not open')
                elif text != bi.STATUS_TEXT[started['status']]:
                    problems.append(f'status line {text!r}, expected {bi.STATUS_TEXT[started["status"]]!r}')
                change(game, ROWS[row], presses)
                accept(game, work, True)
                ram = game.read(0, 0x2000)
                saved, after = bi.expected_save(image, ram[0x100], ram[0x1227])
                if (ram[0x100], ram[0x1227]) == (started['options'], started['language']):
                    problems.append(f'{row} did not change')
                if row == 'reset' and (ram[0x100], ram[0x1227]) != bi.DEFAULTS:
                    problems.append(f'the reset row did not give the defaults: ${ram[0x100]:02X}, {ram[0x1227]}')
                if ram[0x105] != saved or game.backup_ram() != after or saved != bi.OK:
                    problems.append(f'save: status {bi.STATUS[ram[0x105]]}, expected {bi.STATUS[saved]}; '
                                    f'image as expected: {game.backup_ram() == after}')
                if others(game.backup_ram()) != first:
                    problems.append("other games' files changed")
                entry.update(changed=row, options=f'${ram[0x100]:02X}', language=ram[0x1227])
                image = game.backup_ram()
            if MODEL in LOCKING:
                entry['locked_after_boot_and_run'] = game.locks
                if not all(game.locks) or len(game.locks) != (1 if row is None else 2):
                    problems.append(f'bank $F7 not locked after the boot and the Run: {game.locks}')
        shutil.rmtree(work, ignore_errors=True)
        entry.update(problems=problems, ok=not problems)
        results.append(entry)
        print('cycle', entry, flush=True)
    # The last image as a System Card file: listed, read (checksum), deleted,
    # and another game's file created after it.
    card = bi.Directory(image)
    problems = []
    names = [name for _, _, name, _ in card.files()]
    if names.count(b'\0\0' + bi.NAME) != 1 or not all(good for *_, good in card.files()):
        problems.append('not listed once with good checksums')
    data = card.read(b'\0\0' + bi.NAME)
    if data != bytes([bi.VERSION, int(results[-1]['boot_options'][1:], 16), results[-1]['boot_language']]) + bytes(5):
        problems.append(f'read back {data.hex()}')
    free = card.free()
    card.create(b'\0\0AFTER US  ', bytes(range(40)))
    if card.read(b'\0\0AFTER US  ') != bytes(range(40)) or card.free() != free - 56:
        problems.append('a file created after ours does not read back')
    card.delete(b'\0\0' + bi.NAME)
    left = {name: card.read(name) for _, _, name, _ in card.files()}
    wanted = {bytes(raw[4:16]): raw[16:] for raw in first.values()}
    wanted[b'\0\0AFTER US  '] = bytes(range(40))
    if left != wanted or card.free() != free - 56 + bi.ENTRY_SIZE:
        problems.append('deleting our file did not leave the other files as they were')
    if bi.expected_load(bytes(card.data))[0] != bi.READY:
        problems.append('after the delete the game does not see a sound directory without its entry')
    modes = {options & 0xb8 for options, _ in seen}
    if modes != set(bi.PALETTES) or {language for _, language in seen} != {0, 1, 2}:
        problems.append(f'not every palette mode and language was booted: {sorted(seen)}')
    return {'steps': results, 'system_card_file': {'problems': problems, 'ok': not problems},
            'settings_booted': sorted(f'${o:02X}/{l}' for o, l in seen)}


def run_from(emulator, rom, image, output, changes):
    """Boot with `image`, apply `changes` in the menu, Run. -> (settings at
    boot, settings after, status, image after, images after each write)."""
    work = Path(tempfile.mkdtemp(prefix='bram-', dir=output))
    try:
        with Game(emulator, work) as game:
            started = boot(game, rom, image, work)
            if open_menu(game) is None:
                raise RuntimeError('the menu did not open')
            for row, presses in changes:
                change(game, ROWS[row], presses)
                for _ in range(ROWS[row]):
                    press(game, 'up')
            writes = accept(game, work, True)
            ram = game.read(0, 0x2000)
            return ((started['status'], started['options'], started['language']), (ram[0x100], ram[0x1227]),
                    ram[0x105], game.backup_ram(), writes)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def check_cut(emulator, rom, output, shard):
    cases = bi.matrix()
    scenarios = [
        ('create', cases['others-only'], [('palette', ['right'] * 4), ('language', ['right'] * 2)]),
        ('rewrite', cases['others-both'], [('palette', ['right']), ('language', ['right'])]),
        ('format', cases['blank-ff'], [('no damage', ['right'])]),
        ('format-zero', cases['blank-00'], [('palette', ['right'] * 3)]),
        ('stale pointer', cases['pointer-stale-high'], []),
        ('create at the page end', bi.image([bi.other(0, 0xe8)]), [('firewheel', ['right'])]),
    ]
    report = []
    for index, (label, image, changes) in enumerate(scenarios):
        if index % shard[1] != shard[0]:
            continue
        old, new, status, final, writes = run_from(emulator, rom, image, output, changes)
        entry = {'scenario': label, 'writes': len(writes), 'problems': [], 'defaults': [], 'old': 0, 'new': 0}
        if status != bi.OK or bi.expected_save(image, *new) != (bi.OK, final) or writes[-1] != final:
            entry['problems'].append(f'the uncut save: status {bi.STATUS[status]}')
        new_load = (bi.OK,) + new
        files_old, files_new = others(image), others(final)
        if files_new is None or files_old not in (None, files_new):
            entry['problems'].append("the uncut save changed another game's file")
        for k, cut in enumerate(writes[:-1]):
            where = f'after write {k + 1}'
            # A System Card style reader: the old files or the new ones, the
            # other games' untouched. (An image that is not formatted yet has
            # no files to keep: the scenario's start was blank.)
            if bi.Directory(cut).formatted():
                if others(cut) != files_new:
                    entry['problems'].append(f'{where}: the directory or another file is not as it was')
            elif files_old is not None:
                entry['problems'].append(f'{where}: no longer formatted')
            # The game from a cold boot with this image, then the same Run.
            loaded = bi.expected_load(cut)
            started, after, status, image_after, _ = run_from(emulator, rom, cut, output, [])
            if started != loaded:
                entry['problems'].append(f'{where}: boot {started}, model {loaded}')
            if started == old:
                entry['old'] += 1
            elif started == new_load:
                entry['new'] += 1
            elif started[1:] == bi.DEFAULTS:
                entry['defaults'].append(k + 1)
            else:
                entry['problems'].append(f'{where}: boots with {started}: neither old nor new')
            if status != bi.OK or bi.expected_save(cut, *after) != (bi.OK, image_after):
                entry['problems'].append(f'{where}: a Run from here: status {bi.STATUS[status]}')
            # Finishing with the settings the cut save was writing must give
            # the uncut save's image exactly.
            if bi.expected_save(cut, *new)[1] != final:
                entry['problems'].append(f'{where}: the model does not finish in the uncut image')
            if others(image_after) != files_new:
                entry['problems'].append(f'{where}: other files after the finishing Run')
        entry['ok'] = not entry['problems']
        report.append(entry)
        print('cut', entry, flush=True)
    return report


def variant(data, kind):
    """The candidate with its unlock or lock code changed (negative
    controls). The unlock is lda #$48, sta $1807, lda #$75, sta $1807,
    lda #$80, sta $1807; the lock is lda $1803."""
    data = bytearray(data)
    assert data.count(UNLOCK) == 1 and data.count(LOCK, *BANK46) == 1, 'the unlock or lock code was not found once'
    unlock, lock = (data.index(code, *BANK46) for code in (UNLOCK, LOCK))
    nop = b'\xea' * 3
    if kind == 'no-unlock':                 # nothing is written to $1807
        for at in (2, 7, 12):
            data[unlock + at:unlock + at + 3] = nop
    elif kind == 'bit7-only':               # only $80 (what the System Card itself writes)
        for at in (2, 7):
            data[unlock + at:unlock + at + 3] = nop
    elif kind == 'bit7-clear':              # $48, $75, $00
        data[unlock + 11] = 0x00
    elif kind == 'no-lock':                 # $1803 is never read
        data[lock:lock + 3] = nop
    else:
        raise ValueError(kind)
    return bytes(data)


def model_applies(emulator, rom, output):
    """Proof that this emulator applies MODEL: with the unlock writes
    removed (lock, key, readonly), or as it is (openbus), the game must not
    see a formatted memory that holds its settings."""
    image = bi.matrix()['others-before']
    work = Path(tempfile.mkdtemp(prefix='bram-', dir=output))
    try:
        test = work / 'model.pce'
        test.write_bytes(variant(Path(rom).read_bytes(), 'no-unlock') if MODEL in LOCKING else Path(rom).read_bytes())
        with Game(emulator, work) as game:
            started = boot(game, test, image, work)
            return ((started['status'], started['options'], started['language']) == (bi.NONE,) + bi.DEFAULTS
                    and game.backup_ram() == image and (MODEL not in LOCKING or game.locks == [True]))
    finally:
        shutil.rmtree(work, ignore_errors=True)


def check_lock(emulator, rom, baseline, output):
    """Negative controls under `lock` or `key` (see the module text)."""
    cases = bi.matrix()
    data = Path(rom).read_bytes()
    reference = baseline_frames(emulator, baseline, output)
    # kind: (the game never reaches the memory, the bank is locked afterwards)
    plan = {'no-unlock': (True, True), 'bit7-clear': (True, True),
            'bit7-only': (MODEL == 'key', True), 'no-lock': (False, False)}
    work = Path(tempfile.mkdtemp(prefix='bram-', dir=output))
    report = []
    try:
        for kind, (dead, locked) in plan.items():
            test = work / f'{kind}.pce'
            test.write_bytes(variant(data, kind))
            for name in ('others-before', 'empty-8800', 'blank-ff'):
                result = check_case(emulator, test, name, cases[name], output, reference, dead=dead, locked=locked)
                result.update(variant=kind, must_show=('no backup RAM, nothing written' if dead else 'works')
                              + (', locked afterwards' if locked else ', bank left open'))
                report.append(result)
                print('lock', kind, name, 'as predicted' if result['ok'] else result['problems'],
                      {k: result.get(k) for k in ('reset', 'run', 'writes', 'bytes_changed', 'locked_after_boot_run_run')},
                      flush=True)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return report


def loader_clocks(emulator, rom, image, output):
    work = Path(tempfile.mkdtemp(prefix='bram-', dir=output))
    try:
        with Game(emulator, work) as game:
            game.power_on(rom, image)
            for offset in (BOOT_HOOK, NATIVE_INIT):
                game.call('set_breakpoint', {'address': offset, 'memory_area': 'rom', 'execute': True})
            assert continue_to(game) == 'FFE6'
            start = clock(game, work)
            assert continue_to(game) == 'FCBE'
            return clock(game, work) - start
    finally:
        shutil.rmtree(work, ignore_errors=True)


def save_clocks(emulator, rom, image, output, changes):
    """Master clocks from the save's entry to its return in the menu."""
    data = Path(rom).read_bytes()
    call = data.index(bytes.fromhex('20034b'), 0x46 * 0x2000 + 0x400, 0x46 * 0x2000 + 0xb00)
    work = Path(tempfile.mkdtemp(prefix='bram-', dir=output))
    try:
        with Game(emulator, work) as game:
            boot(game, rom, image, work)
            if open_menu(game) is None:
                raise RuntimeError('the menu did not open')
            for row, presses in changes:
                change(game, ROWS[row], presses)
            game.press({'run'})
            game.step(2)
            for offset in (SAVE_ENTRY, call + 3):
                game.call('set_breakpoint', {'address': f'{offset:x}', 'memory_area': 'rom', 'execute': True})
            game.press(set())
            assert continue_to(game) == '4B03'
            start = clock(game, work)
            continue_to(game)
            return clock(game, work) - start, bi.STATUS[game.read(0x105, 1)[0]]
    finally:
        shutil.rmtree(work, ignore_errors=True)


def check_timing(emulator, rom, baseline, output):
    cases = bi.matrix()
    report = {'unit': 'master clocks (1,365 a line, 358,995 a frame)', 'loader': {}, 'save': {}}
    report['loader']['baseline, 8-byte English initialization'] = loader_clocks(emulator, baseline, None, output)
    for name in ('absent', 'empty-8800', 'blank-ff', 'garbage', 'others-only', 'others-before', 'full',
                 'tiny-entries', 'tiny-entries-ours-last'):
        report['loader'][name] = loader_clocks(emulator, rom, cases[name], output)
        print('loader', name, report['loader'][name], f"{report['loader'][name] / LINE:.2f} lines", flush=True)
    for name, changes in (('absent', []), ('empty-8800', []), ('others-before', []),
                          ('others-before', [('no damage', ['right'])]), ('full', []), ('tiny-entries', []),
                          ('tiny-entries-ours-last', [('no damage', ['right'])]), ('garbage', []),
                          ('blank-00-last-byte', []), ('blank-ff', []), ('corrupt: end-zero', [])):
        image = cases[name.split(': ')[-1]]
        clocks, status = save_clocks(emulator, rom, image, output, changes)
        label = name + (' (a setting changed)' if changes else '')
        report['save'][label] = {'clocks': clocks, 'lines': round(clocks / LINE, 2), 'status': status}
        print('save', label, report['save'][label], flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for name in ('emulator', 'candidate', 'baseline', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--only', choices=('matrix', 'cycle', 'cut', 'timing', 'lock'), action='append')
    parser.add_argument('--bram-model', choices=('lock', 'key', 'readonly', 'openbus'),
                        help='the test-only emulator (locktest_patch.py) with this NG_BRAM_MODEL')
    parser.add_argument('--cases', help='matrix: comma-separated image names (default: all)')
    parser.add_argument('--shard', default='0/1', help='matrix, cut: do every N-th case, K/N')
    args = parser.parse_args()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    shard = tuple(int(x) for x in args.shard.split('/'))
    parts = set(args.only or ('matrix', 'cycle', 'cut', 'timing'))
    report = {'rom_sha256': hashlib.sha256(args.candidate.read_bytes()).hexdigest(),
              'baseline_sha256': hashlib.sha256(args.baseline.read_bytes()).hexdigest(),
              'emulator_sha256': hashlib.sha256(args.emulator.read_bytes()).hexdigest(),
              'physical_hardware_tested': False,
              'backup_ram_lock': 'not modelled by this emulator build: $1807/$1803 are not decoded for a HuCard'}
    ok = True
    if args.bram_model:
        global MODEL
        MODEL = os.environ['NG_BRAM_MODEL'] = args.bram_model
        report['backup_ram_lock'] = (f'test-only emulator, NG_BRAM_MODEL={MODEL} '
                                     '(research/tools/bram-save/locktest_patch.py)')
        report['model_applies'] = model_applies(args.emulator, args.candidate, args.output)
        if not report['model_applies']:
            raise SystemExit(f'This emulator does not apply NG_BRAM_MODEL={MODEL}: is it the test-only build?')
    elif 'NG_BRAM_MODEL' in os.environ:
        raise SystemExit('NG_BRAM_MODEL is set: use --bram-model')
    if 'lock' in parts:
        if MODEL not in ('lock', 'key'):
            raise SystemExit('--only lock needs --bram-model lock or key')
        report['lock'] = check_lock(args.emulator, args.candidate, args.baseline, args.output)
        ok &= all(entry['ok'] for entry in report['lock'])
    if 'matrix' in parts:
        report['matrix'] = check_matrix(args.emulator, args.candidate, args.baseline, args.output,
                                        args.cases.split(',') if args.cases else None, shard)
        ok &= all(case['ok'] for case in report['matrix']['cases'])
    if 'cycle' in parts:
        report['cycle'] = check_cycle(args.emulator, args.candidate, args.output)
        ok &= all(step['ok'] for step in report['cycle']['steps']) and report['cycle']['system_card_file']['ok']
    if 'cut' in parts:
        report['cut'] = check_cut(args.emulator, args.candidate, args.output, shard)
        ok &= all(entry['ok'] for entry in report['cut'])
    if 'timing' in parts:
        report['timing'] = check_timing(args.emulator, args.candidate, args.baseline, args.output)
    report['ok'] = bool(ok)
    name = 'report.json' if shard == (0, 1) else f'report-{shard[0]}-of-{shard[1]}.json'
    (args.output / name).write_text(json.dumps(report, indent=2) + '\n')
    print('PASS' if ok else 'FAIL', args.output / name, flush=True)
    raise SystemExit(0 if ok else 1)


if __name__ == '__main__':
    main()
