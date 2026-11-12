# Validation and limits

## 1.10 release validation

Release 1.10 is defined by `release/current.json`. A source build from either
original ROM format (`scripts/project.py build --verify-release`) and direct
application of either release patch reproduce its target SHA-256
(`3d5c05df…bbf6`).

**Emulator evidence** (headless Geargrafx; method and results in
[the background-fidelity review](validation/background-fidelity.md)). 1.10
changes the boot (the splash is removed) and the in-game menu; the stage,
background and cinema code is 1.09's.

| Check | Result |
| --- | --- |
| Boot | `scripts/check_boot.py`: every idle frame from power-on through the title (frames 1-899) is identical to the original's (given English); power-on to the first 1-1 update with Run pressed takes 163 frames, as in the original and 1.09; defaults English, Enhanced, No Damage off |
| Menu | `scripts/check_menu.py`: opened 121 times across the 11 stored stage runs (every 300 frames and after each area change), every setting changed and cancelled with Select: VRAM, sprite table and palette identical on return, RAM changed only in the interrupt's, music driver's and menu's own bytes. In all 22 Level Select entries the same, and Run starts the next entry with the right stage, full health, the options and the status bar restored |
| Gameplay | Stored button input for all 11 enhanced stages plays frame for frame identically on the original and on 1.10 (35,084 frames: sprites, Ryu, timer, lives, health, camera, area), with no re-recording needed |
| Cinemas | On 1.10, after a full play of each enhanced stage, the next cinema is identical frame for frame (the same frame counts as on 1.09). The whole-game cinema audit ([CUTSCENE-AUDIT.md](CUTSCENE-AUDIT.md)) reached all 15 cinemas on 1.08-dev |
| Backgrounds | Every Enhanced backdrop is generated from the original ROM's own art; every round of the 11 parallax entries opens exactly like the original (1.09 evidence; the code is unchanged) |
| Timing | Stage loads, respawns and area changes take the original's frame counts; force-scrolling every area at 2 px per update, no update takes longer than the original's (1.09 evidence; the code is unchanged) |

**Hardware reports** (from the maintainer; separate from the emulator
evidence above):

| Hardware | Build | Report |
| --- | --- | --- |
| NEC PC Engine Duo-RX with Krikzz Turbo EverDrive PRO | 1.10, made with each of the two release patches | The same session with each patch: 1-1 and 1-2 played, a warp to 2-2, No Damage turned on, a warp to the final boss, the boss beaten and the ending cinema started (completion of the ending not stated) |
| NEC PC Engine Duo-RX with Krikzz Turbo EverDrive PRO | 1.10 release bytes (`3d5c05df…bbf6`) | The in-game menu looks good; other areas not reported |
| NEC PC Engine Duo-RX with Krikzz Turbo EverDrive PRO | 1.09 release bytes (`f84a31a8…b912`) | Looks good; stages and settings not specified |
| NEC PC Engine Duo-RX with Krikzz Turbo EverDrive PRO | An earlier development build with the same cinema cleanup | Cinemas good; normal settings through 6-1, No Damage from 6-2 onward (completion of the ending not stated) |
| TurboGrafx-16 with Krikzz Turbo EverDrive and an EDFX RGB adapter | An earlier development build | Some play testing; build, stages and settings not specified |

CI does not emulate the game or establish hardware correctness. The checks
above need private ROMs and the headless emulator described in
[docs/pc-engine/EMULATOR.md](pc-engine/EMULATOR.md).

## Test a change

Choose checks that exercise the changed behavior, and record the exact ROM
hash, emulator/tool version and results. A renderer change should include:

- Opening view before movement, movement both ways, stops and map wrap.
- Foreground tile words/pixels, sprite data and palettes, not only background.
- Ordinary death, respawn then jumping, Continue, stage selection and native
  stage exits. Reproduce the user's exact sequence.
- Worst visible sky/background area and crowded encounters with real inputs.
- Emulated frame/scanline timing and IRQ-sensitive transfer lengths.
- Original mode compared with the original game at equivalent update points.
- A reserved-RAM guard and confirmation of restored registers/bank mappings.
- The comparison runs (`scripts/comparison_video.py make` and `cinema`): the
  stored input must still play identically on the original and the change.

Keep test modifications separate from the output ROM. For example, invulnerability,
camera forcing, temporary hooks, scripted health restoration or save-state
CRC edits must be declared in a report and absent from the released bytes.
Prefer real input replays for the final behavioral check.

The boot check compares a build with the original game (given native
English after its first frame): every idle frame from power-on through the
title, the frame of the first 1-1 update when mashing Run, and the defaults:

```sh
python3 scripts/check_boot.py --emulator /path/to/geargrafx \
  --original "/path/to/original.pce" \
  --candidate "dist/Ninja Ryukenden - development.pce" \
  --output captures/boot-check
```

The menu check opens the in-game menu throughout the 11 stored runs and in
every Level Select entry, sweeps Select over deaths and area changes, and
accepts each option; a cancelled menu is compared with the same state run
without it (see the script's docstring and
[validation/popup-menu.md](validation/popup-menu.md); `--only` picks parts,
`--parallax-off`, `--preview`, `--same-music` and `--strict` the variants;
since `all-palettes` it compares from the next vblank after the menu and
also the PSG registers, and lists frames that differ only by the timer
interrupt's phase, which `--strict` fails:
[validation/all-palettes.md](validation/all-palettes.md)):

```sh
python3 scripts/check_menu.py --emulator /path/to/geargrafx \
  --original "/path/to/original.pce" \
  --candidate "dist/Ninja Ryukenden - development.pce" \
  --output captures/menu-check
```

The NES palette mode (1.11-dev) is checked by the reference probes in
`research/tools/nes-palette/` (stage loads, stored runs, cinemas, identity
of Original and GB DMG with the build before it); results and rerun
commands are in [validation/nes-palette.md](validation/nes-palette.md).
`check_menu.py --only options` covers its menu values (NES-A, NES-B) and
switching between all six palette modes; the all-palettes build's evidence
(identity of every mode with its single-mode build, NES-B, the menu's sound
hold) is in [validation/all-palettes.md](validation/all-palettes.md), its
probes in `research/tools/all-palettes/`.
HELL's candidate D and its 1-1 override (identity of the other five modes
with `all-palettes`, HELL's colours per stage, timing) are in
[validation/hell-1-1.md](validation/hell-1-1.md), probes in
`research/tools/hell-1-1/`.
The dark lift of SMS, HELL and the NES modes' 4-1 (identity of Original and
GB DMG with `hell-1-1`, the changed modes' colours in the stored runs, the
fades; brightness and screenshots still to do) is in
[validation/dark-lift.md](validation/dark-lift.md), probes in
`research/tools/dark-lift/`.

The saved settings (1.11-dev, `src/bram`) have their own check,
`scripts/check_bram.py`: a matrix of backup RAM images (absent, empty,
other games' files around ours, full, every valid setting, damaged
directories, blank and half-formatted memories) booted cold and saved from
the menu, compared with a model and with a System Card style reader; one
setting changed per power cycle; saves cut after every byte written; the
loader's and the save's time. The pinned emulator does not model the backup
RAM's lock for a HuCard, so the same check runs on a test-only emulator
that does (`--bram-model lock`, `key`, `readonly`, `openbus`; built by
`research/tools/bram-save/locktest_patch.py`), with negative controls
(`--only lock`). `scripts/check_boot.py --bram IMAGE` boots both games with
a backup RAM image. Results, the lock models' basis and what only a
console can show are in [validation/bram-save.md](validation/bram-save.md);
the console test list is
[validation/bram-save-hardware-checklist.md](validation/bram-save-hardware-checklist.md).

The build that holds the saved settings and the dark lift's fade-out fix
together (branch `v111-final`) is shown to be the byte union of the two
builds those records were made on, and has its own interaction checks
(a mode loaded from backup RAM played to a stage end among them) in
[validation/v111-final.md](validation/v111-final.md).
Its successor `v111-reset` (APOCALYPSE, the PALETTE order, the reset row
and the plain status line; only the menu module changed) has its record in
[validation/v111-reset.md](validation/v111-reset.md).

```sh
python3 scripts/check_bram.py --emulator /path/to/geargrafx \
  --candidate "dist/Ninja Ryukenden - development.pce" \
  --baseline /path/to/the-build-before.pce --output captures/bram-check
python3 scripts/check_bram.py --emulator /path/to/locktest/geargrafx --bram-model lock \
  --only matrix --only cycle --only lock \
  --candidate "dist/Ninja Ryukenden - development.pce" \
  --baseline /path/to/the-build-before.pce --output captures/bram-lock
```

## Outstanding

Complete hardware coverage of every damage/death/Continue path and every
room/transition is not claimed. Audio was not recorded or compared in the
emulator checks. The hardware reports have the scopes described above.
