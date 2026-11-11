# Saved settings in backup RAM: status and evidence (1.11-dev, branch `bram-save`)

**Status: work in progress, stopped on request on 2026-11-11.** Load and
save work in the emulator and the image matrix passes; an early build is
delivered for the maintainer's hardware test. The evidence sweep, the lock
test and most documentation are not done: see [Not done](#not-done-next-steps-in-order).
Everything here is emulator evidence (Geargrafx `78fc3d7` with the headless
patch); nothing has been seen on hardware.

Branch `bram-save`, from `hell-1-1` at `fb1de01`. Baseline for every
comparison: the `hell-1-1` build, SHA-256 `fa158540…f4c9`
(`build/bram-save/base-hell-1-1.pce`).

Build checked here (source as of commit `ae39fe6`; later commits change
only scripts and documents): SHA-256
`598c8fb61661b55af5482bf86a9bde7f48cf0192d76c68c781a92cfd5ef22134`
(`build/bram-save/dev3.pce`). Delivered as the early build in
`/workspace/roms/`: `Ninja Ryukenden - Enhanced v1.11-dev (settings save,
early).pce`, with `ninja-ryukenden-enhanced-v1.11-dev-settings-save-early.bps`
(headered original, SHA-256 `ec4050b2…362b`) and
`…-settings-save-early-headerless.bps` (`318caf73…3718`); both patches were
applied again with `scripts/bps.py` and give that ROM.

## Branch `v111` (merge with `dark-lift`): results so far, 2026-11-11

Interim notes, kept current while the work runs; the sections below still
describe `bram-save` as it was stopped.

- `v111` = `bram-save` (`d01c060`) + `dark-lift` (`2ad5815`), merged without
  conflicts. Build SHA-256
  `7fc60a092afc359697ee95310ac398280b4be851853e32961c1c228ff768a0ae`, the
  same from the headered and the headerless original
  (`build/v111/v111.pce`); 52 unit tests and `audit_public.py` pass.
- Early build delivered in `/workspace/roms/`: `Ninja Ryukenden - Enhanced
  v1.11-dev (all palettes, dark lift, settings save, early).pce` with
  `...-all-palettes-dark-lift-settings-save-early.bps` (`f5efd8e7...9018`)
  and `...-early-headerless.bps` (`61a1d365...4082`), both applied again
  with `scripts/bps.py`.
- `check_boot.py`, backup RAM absent: frames 1-899 identical to the
  original, first update at frame 163 (`build/v111/boot-absent`).
- `check_bram.py --only cycle` on the pinned emulator: 16 of 16 steps pass
  (`build/v111/cycle`).
- **Lock test.** The test-only emulator built on `bram-save`
  (`build/bram-save/locktest`) was linked from object files compiled
  against the unpatched `memory.h` (its build log shows the LTO type
  mismatches), and the CD unit's reset re-opened the bank behind the model.
  It was rebuilt from clean objects in `build/v111/locktest` with
  `locktest_patch.py` extended (the model now also governs
  `Memory::UpdateBackupRam`); SHA-256 `2c12a540...c134`.
  `check_bram.py --bram-model MODEL` drives it, runs a stub after every boot
  and Run that reads and writes bank `$F7` (must read `$FF`, must not land)
  and refuses an emulator that does not apply the model (the pinned one is
  refused). Negative controls (`--only lock`), 12 cases each under `lock`
  and `key`, all as predicted: no unlock writes, or `$48 $75 $00`: no backup
  RAM seen, nothing lands; only `$80` written: works under `lock`, dead
  under `key`; lock read removed: works, and the probe reports the bank
  open after the boot and after each Run
  (`build/v111/lock-neg-lock`, `lock-neg-key`).
  Full matrix under `lock` (`--only matrix --bram-model lock --shard K/3`,
  `build/v111/matrix-lock`): 210 of 210 pass, the bank locked after the
  boot and after both Runs in all 209 images (the 210th is no backup RAM).
  The same under `key` (`build/v111/matrix-key`): 210 of 210, locked
  after every boot and Run. Power cycles (`--only cycle`) under `lock` and
  under `key`: 16 of 16 each, locked after every boot and Run
  (`build/v111/cycle-lock`, `cycle-key`). `openbus`, 72 images (every
  structural case and six settings cases; `build/v111/subset.txt`): 72 of
  72 show `NONE` before and after Run, no write attempted, first update at
  frame 163. `readonly`, the same 72: 70 as expected (`ERROR 4` wherever a
  write was needed, 0 bytes changed anywhere); the other two
  (`blank-00-one-byte`, `blank-00-last-byte`) showed `NONE` where the
  check's own expectation said `ERROR 1`: the check was wrong (on a memory
  that ignores writes the writable test fails first, which is the design);
  corrected, rerun pending.
- Full matrix on the pinned emulator with the current script
  (`--only matrix --shard K/3`, `build/v111/matrix`): 210 of 210 pass; the
  48-entry directory boots at the baseline's frame (asserted); the three
  longer ones (111, 112 and 126 entries) are reported apart.
- Random images (`research/tools/bram-save/fuzz.py`, pinned emulator, seed
  2): the first 560 images, 0 problems, before the generator itself tripped
  on a short end pointer (fixed); a longer run is pending.
- Independent check of the sequence: the Super System Card 3.0 ROM itself
  (the Duo's own code) maps bank `$F7` in MPR4, executes `csl`, `sei`,
  writes the single byte `$80` to `$1807`, and afterwards reads `$1803`
  before `csh` (file offsets `$1C72-$1C7E`, `$1CA8-$1CAB`); HuC's
  `huc_bram.asm` sends `$48 $75 $80`. The game's three writes end in `$80`
  and so satisfy both.

## What is built

- **What is saved:** `$2100` (all eight bits) and `$3227`, in a System Card
  style file `NR ENHANCE` (id `00 00`), total length `$18`: 8 data bytes,
  byte 0 the format version (1), byte 1 `$2100`, byte 2 `$3227`, bytes 3-7
  zero. `$2104` is not saved.
- **Reset** (`src/bram`): the trampoline at `$FFE6-$FFF5` (the English
  initialization's place, grown from 8 to 16 bytes into the free bytes below
  the vectors) maps bank `$46`, calls the loader (`$4B00`), restores MPR2
  and jumps to the native `$FCBE`. The loader sets the defaults, unlocks the
  backup RAM (`$48`, `$75`, `$80` to `$1807`), maps bank `$F7` in MPR4 at low
  speed with interrupts off, validates the whole directory and applies our
  entry if it has length `$18`, a good checksum, version 1 and values in
  range; it locks again (read of `$1803`) and restores MPR4, zero page
  `$22-$2C`, X, Y and the flags. It never writes to the backup RAM.
- **Save** (the menu's Run, after `$2100` and `$3227` are set, before the
  stage restarts; `$4B03`): an existing entry of length `$18` is rewritten
  in place only when its contents differ (data first, checksum last); with
  no entry, a new one is written at the terminator when it and a new
  terminator fit below min(end, `$8800`): everything after the length, the
  new terminator, the length byte (from then on the directory holds it),
  then the header's pointer, high byte first. What was written is read back.
  Nothing is ever deleted, moved or resized.
- **Validation before any use:** "HUBM"; end at least `$8000`, trusted only
  up to `$8800`; every entry length 16 or more; the walk reaches a `00 00`
  terminator inside the memory the header gives; the header's first-free
  pointer names that terminator. One exception is accepted: our own entry
  is the last one and the pointer still names it (low byte; high byte old or
  new): a create cut off before the pointer moved; the next save moves it.
- **Unformatted memory** (no "HUBM"), at Run only: formatted when every
  byte from `$8012` up is `$00` (or every one `$FF`), bytes `$8001-$8011`
  are blank or already what a format puts there (a format cut short), and
  byte `$8000` takes two patterns and its old value back. Bytes
  `$8001-$8012` all alike but not blank is taken for no memory at all
  (`NONE`). Anything else is `ERROR 1` and is not touched.
- **Status** in `$2105` (new RAM contract; the watched stack margin is now
  `$2106-$213F`), shown in the popup's last row (`SAVE: ...`, texts in
  `src/options/menu.txt`): `NONE`, `OK`, `READY`, `FULL`, `ERROR 1`
  (unformatted, not blank), `ERROR 2` (directory damaged), `ERROR 3` (an
  entry of our name with another length), `ERROR 4` (did not read back),
  `ERROR 5` (our entry's contents do not check out: defaults, rewritten by
  the next Run). The meaning of each for the player is in the
  [hardware checklist](bram-save-hardware-checklist.md).
- **Space:** bank `$46` `$4B00-$4FFF` (962 bytes used to `$4EC1`; the range
  was `$FF` and unowned in the baseline); the menu grew to 1,749 of its
  1,792 bytes (`$4400-$4AD4`); fixed bank `$FFEE-$FFF5` (were `$FF`).
  `$4100-$42FF`, `$5B00-$5FFF` and `$FECF-$FEDF` are untouched and still
  free. Outside `src/modules.json`'s ranges for `bram` and `options` the ROM
  is the baseline's, byte for byte (2,340 bytes differ, all inside them).
  `src/english` is folded into `src/bram`.

Deviations from the brief's design, for review:

1. The header pointer may be stale by one commit (above): without it a save
   cut off between two byte writes would leave a directory the game calls
   corrupt for good.
2. The writable test (three writes to `$8000`, ending with its old value)
   runs before the 2 KiB blank check, but only when bytes `$8001-$8012`
   already look blank: a machine without backup RAM must leave the save
   after a few instructions, not after reading 2 KiB with interrupts off.
   Two matrix images (`blank-00-one-byte`, `blank-00-last-byte`) therefore
   see those three writes and end unchanged.
3. A format cut short is finished (above), and uniform non-blank reads count
   as "no memory" so that a console without backup RAM shows `NONE` whatever
   its unmapped bank reads, as long as it reads the same every time.
4. More status texts than the four suggested, to tell causes apart on
   hardware.

## Harness (commit `e441da5`)

Headless Geargrafx never applies the desktop setting "Force Backup RAM"
(only the GUI start-up calls it), so every existing check always ran
**without** backup RAM: bank `$F7` reads `$FF`, and no `.sav` is read or
written. `emulator_session.Emulator.call` now verifies that after every
`load_media`. `power_on(rom, bram=image)` gives a machine with backup RAM
holding a 2,048-byte image, by patching a save state taken at reset (the
state carries the memory and whether the machine has it); a boot of the
baseline through such a state is identical to a plain boot (700 frames'
pictures and all of RAM). A machine with backup RAM writes
`<rom name>.sav` beside the emulator binary on a normal exit, so such a
session is ended with SIGKILL and any `.sav` that appeared is removed.
`check_boot.py --bram IMAGE` boots both games with an image.

The lock is not modelled by this emulator build for a HuCard (`$18xx` is
not decoded): backup RAM, when present, is always unlocked. **The unlock and
lock sequence is unverified** (see Not done).

## Verified (all on `dev3.pce`, baseline `base-hell-1-1.pce`)

`W=/workspace/build/bram-save`, `E=/workspace/build/toolchain/geargrafx/platforms/linux/geargrafx`,
`R=/workspace/build/toolchain/run-check.sh`.

- **ROM-free tests:** `python3 -m unittest tests.test_tools` (49 tests,
  including the model against the System Card style reader over all 210
  images) and `python3 scripts/audit_public.py`: pass.
- **Matrix** (`$R scripts/check_bram.py --emulator $E --candidate $W/dev3.pce --baseline $W/base-hell-1-1.pce --output $W/matrix3 --only matrix --shard K/3`,
  K = 0, 1, 2; 208 images at the time, two more added since and not yet
  run): 206 pass every check: status, `$2100` and `$3227` at the first 1-1
  update as the model says; backup RAM untouched by the boot and by a
  cancel; the menu's SAVE text; after Run the image and status the model
  gives, byte for byte, other games' files where and as they were; no write
  when nothing has to change; a second Run writes nothing. Covered: absent;
  empty with end `$8800` and `$A000`; other games' files before, after and
  around ours; full, one byte short, exactly enough room; all 144 valid
  settings combinations; our entry with a bad checksum, wrong length, wrong
  version, values out of range; pointers and lengths that are wrong in 17
  ways; blank `$00` and `$FF` (formatted and saved), blank but for one byte,
  garbage, a damaged tag (`ERROR 1`, untouched); formats cut short.
  The first 1-1 update comes at the baseline's frame (163; 164 in GB DMG,
  HELL and SMS, on the baseline too when it is given the same settings).
  The other 2 (`tiny-entries`, 112 files of 18 bytes, and the same with our
  entry last) behave correctly but boot one interrupt late: see Timing.
  They were run before `check_bram.py` learned to report such boots apart
  (`MANY_ENTRIES`), so their logs say FAIL for the boot frame only.
- **Power cycles** (`--only cycle`, `$W/cycle3`): 15 settings changes, one
  per session (every palette mode, each option, each language), each found
  again by the next cold boot with the image left behind; 16 of 16 steps
  pass. The last image lists once with good checksums for the System Card
  style reader (a port of HuC's `bm_` routines), reads back, lets another
  file be created after it, and deleting it leaves the other files as they
  were.
- **Saves cut short** (`--only cut`, `$W/cut3`; stopped after every byte
  written, each image booted and then saved again; `--shard 0/2` and
  `1/2`), all six scenarios pass: create (26 writes: 24 images boot as
  before the save, 1 with the new settings); create where the pointer's
  high byte changes (27 writes: 24 as before, 2 new: the stale pointer is
  accepted and finished); rewrite (10 writes: 1 as before, 8 with the entry
  mid-rewrite, where the game boots with the defaults and `ERROR 5` and the
  next Run repairs it: inherent in "data first, checksum last"); format of
  a `$FF` and of a `$00` memory (47 writes each: 20 images still
  unformatted and booting with `NONE`, 25 formatted and empty, `READY`, 1
  with the settings); a stale pointer finished (1 write). In every image
  the System Card style reader finds the other files where and as they
  were, and a Run from it ends in a complete, valid state.
- **check_boot** (on the build before the last speed-up, `dev2.pce`, not
  repeated on `dev3.pce`): frames 1-899 identical to the original and the
  first update at frame 163, without backup RAM and with a full one
  (14 files).
- **Timing** (`--only timing`, master clocks; 1,365 a line):

  | Reset loader (`$FFE6` to `$FCBE`) | Clocks | Lines |
  | --- | --- | --- |
  | baseline (8-byte English initialization) | 33 | 0.02 |
  | no backup RAM, blank, garbage | 2,448 | 1.8 |
  | formatted, empty | 5,448 | 4.0 |
  | 3 other files | 8,508 | 6.2 |
  | 2 other files and ours (loaded) | 17,856 | 13.1 |
  | full, 14 files | 19,152 | 14.0 |
  | 112 files of 18 bytes | 113,496 | 83.2 |

  The native reset runs about 5.8 frames with interrupts off, then takes
  the pending vblank interrupt at once; the next one comes 59,832 clocks
  (43.8 lines) later (`research/tools/bram-save/bootslack.py`). A loader
  that ends within that time leaves the interrupt history and every frame
  as the baseline's; a longer one makes the boot run one interrupt behind.
  The walk costs about 950 clocks an entry, so the boot is unchanged up to
  about 55 entries (48 is what the check asserts; **the 48-entry image has
  not been run yet**). A real 2 KiB memory holds far fewer.

  | Save (interrupts off; entry to return) | Clocks | Lines |
  | --- | --- | --- |
  | no backup RAM | 5,877 | 4.3 |
  | corrupt, garbage | about 3,000 | 2.2 |
  | entry unchanged (3 files) | 18,897 | 13.8 |
  | entry rewritten (3 files) | 35,937 | 26.3 |
  | entry created (empty memory) | 31,353 | 23.0 |
  | format and create (`$FF` memory) | 228,462 | 167.4 |
  | rewritten, 111 files | 244,701 | 179.3 |

## Not done: next steps, in order

1. Rerun the matrix with the current script (210 images, `MANY_ENTRIES`) and
   `check_boot.py` three times on the final build: without backup RAM, with
   `empty-8800` and with `full` (`scripts/bram_image.py make NAME FILE`).
2. **The lock.** `research/tools/bram-save/locktest_patch.py` makes a
   test-only Geargrafx copy (`build/bram-save/locktest/geargrafx`, already
   patched and built; the project's emulator is untouched) in which
   `NG_BRAM_MODEL` = `lock` (the MiSTer core's rule), `key` (only `$48`,
   `$75`, `$80` unlock), `readonly` or `openbus` applies to HuCards. Not yet
   used. Run the matrix on it for `lock` and `key` (`NG_EMULATOR` set to
   that binary), check that physical bank `$F7` reads `$FF` after the boot
   and after Run (locked again), a negative control with the unlock writes
   patched out, `readonly` (expect `ERROR 4`) and `openbus` (expect `NONE`
   before and after Run).
3. Evidence against the baseline with backup RAM absent: the 11 stored runs
   in all six palette modes (`research/tools/hell-1-1/record11.py` through
   `sms-palette/runmany.py`, compared with `analyse.py identity` against the
   baseline's recordings in `build/hell-1-1/rec/h1-*`, same ROM hash);
   `check_menu.py` (all parts) against `build/hell-1-1/menu/report.json`.
4. `research/tools/bram-save/bootmodes.py` (each saved palette mode and
   language applied at reset: idle boot frames and the first stage against
   the baseline given the same settings; written, not run) and
   `stackguard.py` (stack low-water of the loader and the save; written,
   not run).
5. Free-space audit on the baseline: a read/execute watch over file offsets
   `$8CB00-$8CFFF` and `$1FEE-$1FF5` during a cold boot and the 11 runs
   (`research/tools/sms-palette/freewatch.py`). So far only shown: the bytes
   were `$FF` and outside every module's range.
6. Documents not yet updated: the full guide in `docs/OPTIONS.md` (only its
   "not saved" paragraph and the menu picture are corrected), LESSONS,
   HARDWARE, the CHANGELOG; the options guide's menu screenshots show the
   old window.
7. Final delivery: `... v1.11-dev (settings save).pce` and its two patches.

## Platforms (what the player has to do)

| Platform | Expectation | Basis |
| --- | --- | --- |
| Duo, Duo-R, Duo-RX (built-in backup RAM), any cartridge | Nothing to do if the memory is formatted (it is once a CD game or the System Card formatted it). The EverDrive Pro's own CD and Ten no Koe cores are off in a Duo. | EverDrive: documented (its manual, "Limitations"). That the game then reaches the Duo's memory: assumed, not seen. |
| Console with a CD-ROM unit, Ten no Koe 2 or Backup Booster | As the Duo. | assumed (same registers; the three-byte unlock is what HuC's library sends) |
| Turbo EverDrive Pro on a console without CD | Options, Default EXP Device: `TNK2` or `CDROM` ("Set the 'Default EXP Device' option to 'TNK2' or 'CDROM'" for games that save to CD memory; `.brm` files, one copy per game under `edturbo/gamedata`). With `OFF`: `SAVE: NONE`. | documented (manual of 2024-12-12). Whether a fresh `.brm` is formatted, the factory default of the option and when the file is written: not stated; a blank memory is formatted by the game at the first Run. |
| MiSTer (TurboGrafx16 core) | Backup RAM is always there for a HuCard, locked at reset, unlocked by bit 7 of a write to `$1807`, locked by a read of `$1803`; a game without a save file gets a pre-formatted empty memory ("HUBM", end `$8800`). The file is written only by the OSD's "Save Backup RAM", or with "Autosave" ON (default OFF) when the OSD is opened after a write: the player must do one of the two before power-off. | read from source (`rtl/cd/cd.vhd`, `rtl/pce_top.vhd`, `TurboGrafx16.sv`; Main_MiSTer `user_io.cpp`), fetched 2026-11-11; not tested |
| Geargrafx desktop | "Force Backup RAM" (default on) gives a pre-formatted memory (end `$A000`) and a `.sav` in its save folder: works with nothing to do. | read from source; the headless build was tested with injected images |
| Other emulators | Works where a HuCard is given backup RAM; otherwise `SAVE: NONE`. | assumed |
| Console with nothing attached | `SAVE: NONE`, defaults at every power-on, nothing written. | emulated with bank `$F7` reading `$FF`; other unmapped-bank behaviour only in the model |

## Open questions

- Is the Duo's backup RAM reached with the EverDrive Pro in the slot, and
  does `$48 $75 $80` unlock it (hardware checklist, part 1)?
- The four deviations above.
- No Damage is saved like every other setting (the brief's default).
- A boot with more than about 55 saved files runs one vblank interrupt
  behind the original's (frames one later). Keeping the walk at low CPU
  speed costs that; reading at high speed would remove it but is not known
  to be safe on real backup RAM.
- The first save on a blank memory holds interrupts off for about half a
  frame (once per memory).
