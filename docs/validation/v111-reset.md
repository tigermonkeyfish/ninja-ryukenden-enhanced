# v111-reset: APOCALYPSE, palette order, reset row, status line (1.11-dev)

Emulator evidence only (Geargrafx `78fc3d7`, headless; one session at a
time). Nothing here was seen on a console. 2026-11-12.

## What changed

Branch `v111-reset`, from `v111-final` (`d1a6da6`), for four owner requests:

1. The palette mode HELL is shown as **APOCALYPSE**: the PALETTE value
   (field widened from 8 to 10 columns) and the guides. The source keeps
   the name HELL (`hell.json`, `PALETTE_HELL`, `HELL_*`, scripts and older
   records; [architecture](../ARCHITECTURE.md#palette-modes)). Value `$18`
   and the colours are unchanged.
2. **PALETTE order** (Left/Right, wrapping): ORIGINAL, APOCALYPSE, NES-A,
   NES-B, SMS, GB DMG (before: ORIGINAL, NES-A, NES-B, GB DMG, HELL, SMS).
   Only the order of the `@` line in `src/options/menu.txt` changed; the
   values (`$00`, `$18`, `$08`, `$28`, `$38` with `$2100` bit 7, `$10`) are
   the same, so settings saved by earlier builds load unchanged.
3. A **RESET OPTIONS** row after LANGUAGE (field `PRESS I`, blinking when
   selected; Up from STAGE and Down to it wrap through it). I or II there
   writes `DEFAULT_DRAFT` (`$40`: each `@` line's first value, which is
   the power-on default: `$2100` = 0 after the RAM clear, `$3227` = 1 from
   `src/bram` `boot_load`'s `DEFAULT_LANGUAGE`; a unit test ties the two)
   into the draft `$2101` and redraws, so the palette preview follows as
   for a PALETTE change. STAGE is kept. Left/Right do nothing there. Run
   and Select are as before: Run applies the draft, saves and restarts the
   STAGE row's stage; Select discards the draft, reset included. Design as
   briefed; the row took the window's spare blank row (no new window row).
4. The save status is a **plain line at the window's top**, 24 columns,
   with a blank row under it, away from the controls line, which is now the
   window's last row: `NO BACKUP MEMORY`, `SETTINGS SAVED`, `BACKUP MEMORY
   FOUND`, `BACKUP MEMORY FULL`, `BACKUP MEMORY ERROR 1`-`5` (before: `SAVE:
   NONE`, `OK`, ... in the last row). `OK` is one status for a load at
   power-on and a save by Run (`src/bram`), so one text serves both;
   telling them apart would need a new status value in `src/bram`, which
   this branch leaves byte for byte as it is (it is waiting for its
   hardware test). The device is not named (see below).

Window (26 x 10, BAT rows 7-16, as before):

```
 BACKUP MEMORY FOUND

 STAGE: 1-1
 SMOOTH PARALLAX: ON
 NO DAMAGE: OFF
 NES FIREWHEEL: OFF
 PALETTE: APOCALYPSE
 LANGUAGE: ENGLISH
 RESET OPTIONS: PRESS I
 RUN: OK  SELECT: CANCEL
```

**Space.** The menu's claim `$4400-$4AFF` had 43 bytes left; the reset
row, the wider PALETTE texts and the 24-column status texts did not fit.
The three menu glyphs (48 bytes of data) moved to `$584F-$587E`, after the
renderer gate inside the module's own claim `$5840-$58FF`, and the status
texts (216 bytes, generated into `menu-status.inc`) to bank `$46`
`$4100-$41D7`, a new claim `$4100-$41FF` for `options` in
`src/modules.json`. That range was unowned and `$FF` (bank `$46` lies in
the expansion past the original 512 KiB, so no native code can read it;
`project.py` refuses overlapping claims and bytes outside a module's
claims). The menu now uses `$4400-$4A8C` (1,677 bytes). The window covers
the same cells, so the backup (rows 0-8 in the sprite-table buffer, row 9
in tiles `$7AB-$7AC`) and the HUD rows are as before.

**Device name.** Not done. The game sees the backup RAM through the same
bank `$F7` and the same unlock (`$1807`) and lock (`$1803`) whether a Duo,
a CD-ROM unit, a Ten no Koe 2 or a flash cartridge's emulation provides it,
and an EverDrive Pro with EXP Device `CDROM` or `TNK2` imitates those
devices. Every probe that could tell them apart reads other `$18xx`
registers (the CD interface, or the Super CD-ROM RAM's signature at
`$18C1-$18C3`, which names the Super System Card's RAM, not the backup
memory's device); none is documented here as free of side effects on all
of them, none was tested on hardware, and the owner's rule allows no new
`$18xx` access without that. So the texts say "backup memory".

## Build

SHA-256 `558fc5d2a7cda7c2d69ec2d736a7e5d66bb56a6d6808488bec3bb7534bcbc672`
(1,048,576 bytes), the same bytes from the headered and the headerless
original; `scripts/bps.py apply` of each build's patch to its original
gives the same ROM. 54 unit tests and `scripts/audit_public.py` pass.

**Against `v111-final`** (`f3114ade…a0a0`; `W=build/v111-reset`,
`base.pce`): 1,702 bytes differ, every one inside the `options` module's
claims; every other module's ranges (`palette`, `nes-palette`, `bram`, the
stage modules, ...) and everything outside the claims are identical, so
no palette data byte changed. Changed ranges (bank `$46`, MPR2 view):
`$4100-$41D7` (status texts), `$4432`, `$445A-$48C0`, `$48D5-$48F8`,
`$4909-$492C`, `$493D-$495E`, `$4971-$4AD4` (menu code and tables, moved
by the inserted code), `$584F-$587E` (the glyphs). The menu entry's
first 23 bytes (the refusals) are unchanged.

## Checks (all on this build)

`E` the pinned emulator, `R=build/toolchain/run-check.sh`, environment
`GB_WORK=$W NES_WORK=$W NG_DEBUGGER_FAST=1`.

- `check_menu.py --only options --only reset` (`$W/menu-options`): **64 of
  64 pass**, no timer-phase frames.
  - `options`, 38 cases (36 before; the press counts now come from the
    PALETTE order in `menu.txt`): each option row changed and accepted;
    each palette mode by Right from ORIGINAL with its exact colours
    (`mode_exact`), Left's wrap (ORIGINAL to GB DMG), Right's wrap (six
    presses back to ORIGINAL), NES-A by Left; 13 paths through the modes
    (each mode and back; the whole Left order and the whole Right order;
    SMS and GB DMG next to each other; NES modes between mapped ones), each
    ending with the VCE of a stage start that never left Original; 12
    cancels after changing everything, compared with the run without the
    menu for 900 frames.
  - `reset`, 26 cases: reset and Run from parallax OFF, No Damage ON, NES
    Firewheel ON, each of NES-A, NES-B, GB DMG, APOCALYPSE, SMS, Japanese,
    Chinese, everything changed with SMS and Chinese (`$BF`/2), everything
    with APOCALYPSE and Japanese (`$1F`/0), and nothing changed: the window
    shows every default after I, the preview is Original's (VCE = RAM
    palette, `$2100` palette bits clear) while the window is open, and Run
    gives `$2100` = `$00`, `$3227` = 1, the same stage (1-1), health 16 and
    the VCE of a stage start that never left Original. Also: reset with
    II; Up from STAGE to the reset row; a STAGE changed before the reset
    (2-1 starts) and after it (Down from the reset row wraps to STAGE; 1-2
    starts); an option changed after the reset is kept (GB DMG, `$10`);
    Left/Right on the reset row change nothing (SMS stays, `$B8`); the
    window texts, `APOCALYPSE` and `PRESS I` blinking, the window check;
    six Selects after a reset (from everything with SMS/Chinese and with
    APOCALYPSE/Japanese, from GB DMG with II, from NES-B, after a reset
    and a STAGE change, from the defaults): `exact_cycle`, nothing
    changed, compared with the run without the menu for 900 frames.
  - The same 64 also passed on the build before the status-line change
    (`7bcd5019…`, `$W/menu-options-orderbuild`).
- `check_boot.py` (`$W/boot-absent`, backup RAM absent): frames 1-899
  identical to the original, 136 distinct screens, first 1-1 update at
  frame 163, defaults; the log equals `v111-final`'s. **Pass.**
- `check_bram.py --only cycle` (`$W/cycle`): **17 of 17 steps and the
  System Card file check pass**. The cycle now has a reset step: booted
  with `$17` and Chinese (status OK), the reset row and Run save `$00` and
  English (status OK), and the next power-on boots `$00`/English with
  status OK. Every step also checks the window's status line against the
  boot's status (`BACKUP MEMORY FOUND` at the first, `SETTINGS SAVED`
  after). Every palette mode and language was booted.
- `check_bram.py --only matrix` for one image per status
  (`$W/matrix-status`): **9 of 9 pass** (`absent`, `blank-ff`, `garbage`,
  `empty-8800`, `full`, `pointer-low`, `ours-short`, `ours-bad-checksum`,
  `others-before`): every status the pinned emulator can give, at boot and
  after Run (NONE, OK, READY, FULL, ERROR 1, 2, 3, 5), with its text in the
  window's top line both times, boot frames equal to the baseline's, and
  the backup RAM as the model says. With the `readonly` model on the
  lock-modelling emulator (`build/v111/locktest/...`, `$W/matrix-readonly`):
  **2 of 2 pass**, `empty-8800` gives ERROR 4 after Run, shown as
  `BACKUP MEMORY ERROR 4`.
- Screenshots of the open window (`$W/menu-options/reset-menu-*.png`,
  private): the status line, `PALETTE: APOCALYPSE` and `RESET OPTIONS:
  PRESS I` fit the window; the HUD and the band are as before.

## Not covered

Real hardware (nothing of this build seen on a console; the checklist,
[bram-save-hardware-checklist.md](bram-save-hardware-checklist.md), has
reset-row steps 1.8a-1.8b); the `runs`, `sweep` and `select` parts of
`check_menu.py` (the window's position, backup and open conditions are
unchanged, the code around them moved); the lock part and the other
matrix images on this build; the stored runs (no code they run changed:
the palette, stage and bram modules are identical); the guide's menu
screenshots (they still show the 1.10 window).

## Rerunning

```sh
python3 -m unittest discover -s tests; python3 scripts/audit_public.py
python3 scripts/project.py build --rom ORIGINAL --output $W/final.pce --assembler pceas --bps-output patch.bps
python3 scripts/bps.py apply ORIGINAL patch.bps check.pce
$R scripts/check_menu.py --emulator $E --original $W/original.pce --candidate $W/final.pce --output $W/menu-options --only options --only reset
$R scripts/check_boot.py --emulator $E --original $W/original.pce --candidate $W/final.pce --output $W/boot-absent
$R scripts/check_bram.py --emulator $E --candidate $W/final.pce --baseline $W/fix2.pce --output $W/cycle --only cycle
$R scripts/check_bram.py --emulator $E --candidate $W/final.pce --baseline $W/fix2.pce --output $W/matrix-status --only matrix \
  --cases absent,blank-ff,garbage,empty-8800,full,pointer-low,ours-short,ours-bad-checksum,others-before
$R scripts/check_bram.py --emulator $L --bram-model readonly --candidate $W/final.pce --baseline $W/fix2.pce \
  --output $W/matrix-readonly --only matrix --cases empty-8800,others-before
```

## Delivered

In `/workspace/roms/` (new names; nothing there was changed):

| File | SHA-256 |
| --- | --- |
| `Ninja Ryukenden - Enhanced v1.11-dev (apocalypse, reset).pce` | `558fc5d2a7cda7c2d69ec2d736a7e5d66bb56a6d6808488bec3bb7534bcbc672` |
| `ninja-ryukenden-enhanced-v1.11-dev-apocalypse-reset.bps` (for the headered original) | `25326503f82dd12ed48110b5983381ccf0087e4ed91dfc204fbab22197e07c1c` |
| `ninja-ryukenden-enhanced-v1.11-dev-apocalypse-reset-headerless.bps` | `30ad8c2d757fd9dba2c863f538ae1cf04276492f36f72d53b563777775d85170` |
| `settings-save-hardware-checklist-apocalypse-reset-build.md` | the checklist as committed |
