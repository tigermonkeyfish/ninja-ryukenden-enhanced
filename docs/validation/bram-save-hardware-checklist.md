# Saved settings: hardware test checklist

For the maintainer's consoles. Everything in [bram-save.md](bram-save.md) is
emulator evidence; nothing below has been seen on hardware yet.

What the emulators did and did not show: the game's unlock and lock of the
backup RAM pass on a test emulator that models the lock two ways (the
MiSTer core's rule, and a stricter one that wants the three-byte key), and
the same build fails there as it should when the unlock is removed. The
Super System Card 3.0's own code uses the same registers in the same order.
What only a console can show: that the Duo's backup RAM answers a HuCard in
the cartridge slot with the EverDrive in it. **Part 1 is the test that
matters.**

Build: `Ninja Ryukenden - Enhanced v1.11-dev (all palettes, dark lift,
settings save).pce`. In the game, press **Select** during play. The band
under the status bar must show `V1.11-DEV`, and the window ends with a
status line:

```
 STAGE: 1-1
 SMOOTH PARALLAX: ON
 NO DAMAGE: OFF
 NES FIREWHEEL: OFF
 PALETTE: ORIGINAL
 LANGUAGE: ENGLISH

 RUN: OK  SELECT: CANCEL
 SAVE: READY
```

| Text | Meaning |
| --- | --- |
| `SAVE: NONE` | No formatted backup RAM was found (none in the machine, or locked, or blank). After Run: there was nothing to write to. Nothing was written. |
| `SAVE: READY` | Formatted backup RAM found at power-on, no settings in it yet, room for them. |
| `SAVE: OK` | Before Run: the settings were loaded at power-on. After Run: they were saved and read back. |
| `SAVE: FULL` | The backup RAM has no room for the 26 bytes. Nothing was written. |
| `SAVE: ERROR 1` | (After Run only) the memory is not formatted and not blank. Nothing was written. |
| `SAVE: ERROR 2` | The list of saves is damaged (pointers or sizes that do not add up). Nothing was written. |
| `SAVE: ERROR 3` | A file named `NR ENHANCE` of another size is there. Nothing was written. |
| `SAVE: ERROR 4` | The save was written but did not read back. |
| `SAVE: ERROR 5` | (At power-on) the `NR ENHANCE` file is there but its contents do not check out; the defaults are used and the next Run rewrites it. |

The status line is drawn when the window opens: it shows what the power-on
found, or what the last **Run** came to. To see the result of a Run, open
the menu again in the restarted stage. Settings are saved by **Run** only;
Select cancels and writes nothing. A language chosen on the title screen is
saved by the next Run.

The game writes to the backup RAM only when you press Run in the menu, and
then only its own 26-byte file (or, on a completely blank memory, the
18-byte format header first). It never deletes, moves or changes another
file. If anything in a step below does not match, stop there and note what
the screen showed; do not go on to the later steps of that part.

## 1. Duo-RX with the Turbo EverDrive Pro (the Duo's own backup RAM)

Expected: the cartridge's own CD and Ten no Koe functions are off in a Duo
(its manual: the built-in CD-ROM core does not work on a console with
built-in CD-ROM), so the game talks to the Duo's backup RAM.

| Step | Do | You should see | If not |
| --- | --- | --- | --- |
| 1.1 | Without the cartridge, open the System Card's backup utility (from its start screen: Select; on some versions Select + Run). Photograph or write down the list and the free space. | The list of the saves the Duo holds. If it offers to format, the memory is unformatted: note that, and format it only if you accept losing what it shows. | Nothing to compare later: note it and go on. |
| 1.2 | Power off, insert the cartridge, start the game from its menu, press Run on the title, and in 1-1 press **Select**. | The window as above, `PALETTE: ORIGINAL`, `LANGUAGE: ENGLISH`, last line **`SAVE: READY`**. | `SAVE: NONE`: the game did not reach a formatted memory (the unlock did not work through the cartridge, or the memory is unformatted). `SAVE: OK`: an `NR ENHANCE` file was already there. `SAVE: FULL` or `ERROR 2`: see the table; nothing will be written. Stop and report the text. |
| 1.3 | In the window: Down twice to NO DAMAGE, Right (`ON`); Down twice to PALETTE, Right three times (`NES-A`, `NES-B`, `GB DMG`: at `GB DMG` the playfield turns to four green shades at once); Down once to LANGUAGE, Right (`JAPANESE`). Press **Run**. | The window closes and 1-1 restarts from its beginning in the four green shades. | The stage does not restart, or the picture hangs: report it. |
| 1.4 | In the restarted stage press **Select**. | `NO DAMAGE: ON`, `PALETTE: GB DMG`, `LANGUAGE: JAPANESE`, last line **`SAVE: OK`**. Press Select to close. | `SAVE: NONE` or `ERROR 4`: the write did not arrive. Report the text. |
| 1.5 | Power off with the switch (not reset), wait five seconds, power on, start the game. | The title's line under the logo is in Japanese. After Run, 1-1 opens in the four green shades; walk into the first enemy: Ryu is not hurt or knocked back. Select: the three values as in 1.4 and **`SAVE: OK`**. | Defaults (English, original colours) and `SAVE: READY` or `NONE`: the save did not survive power-off. `SAVE: ERROR 5`: the file is there but damaged. Report which. |
| 1.6 | Reset without switching off (the EverDrive's reset to its menu; Run + Select held together if the game takes it) and start the game again. | The same as 1.5. | Report what differs. |
| 1.7 | Select; Down four times to PALETTE, Right three times (`HELL`, `SMS`, `ORIGINAL`); **Run**. Power-cycle and start the game. | 1-1 in the original colours; the title still in Japanese; enemies still do not hurt Ryu. Select: `PALETTE: ORIGINAL`, `NO DAMAGE: ON`, `LANGUAGE: JAPANESE`, `SAVE: OK`. | Any of the other two settings lost: report it. |
| 1.8 | Select; Down twice to NO DAMAGE, Right (`OFF`); press **Select** (cancel). Power-cycle, start the game, Select. | `NO DAMAGE: ON` still (a cancelled change is not saved), `SAVE: OK`. | `NO DAMAGE: OFF`: a cancel wrote something. Report it. |
| 1.9 | Without the cartridge, open the System Card's backup utility again. | Every save from 1.1 is still listed, unchanged, plus one new file **`NR ENHANCE`**; the free space is 26 bytes less than in 1.1 (utilities that count in blocks may round). | A save missing or changed: stop using this build and report exactly what differs. |
| 1.10 | Start a CD game whose save was in the list and load that save. | It loads as before. | Report the game and what it said. |
| 1.11 | In the backup utility delete `NR ENHANCE`. Start the game, Select. | `PALETTE: ORIGINAL`, `NO DAMAGE: OFF`, `LANGUAGE: ENGLISH`, **`SAVE: READY`**. | `SAVE: ERROR 2`: the utility left the list in a state the game does not accept. Report it with the utility's list. |
| 1.12 | Only if the situation arises by itself (do not fill the Duo on purpose): the utility shows fewer than 26 bytes free and no `NR ENHANCE`. Start the game, Select, Run, Select. | **`SAVE: FULL`** before and after Run; the utility's list unchanged. | Report it. |

## 2. EverDrive Pro on a console without CD (PC Engine, CoreGrafx, TurboGrafx-16), if available

The cartridge's menu: Options, Default EXP Device: `OFF`, `CDROM` or `TNK2`
(its manual says to choose TNK2 or CDROM for games that save to CD backup
memory, and that each game gets its own copy under `edturbo/gamedata`).

| Step | Do | You should see | If not |
| --- | --- | --- | --- |
| 2.1 | EXP Device `TNK2`. Start the game, Select in 1-1. | **`SAVE: READY`** if the cartridge hands the game a formatted memory; **`SAVE: NONE`** if it hands it a blank one (the manual does not say which). | `ERROR 2`: report it. |
| 2.2 | Change PALETTE to `GB DMG`, press **Run**; in the restarted stage press Select. | Green shades, and **`SAVE: OK`** in both cases of 2.1 (a blank, writable memory is formatted by this first Run). | `SAVE: NONE` after Run: the memory is not writable or not there. `ERROR 1`: it is neither formatted nor blank. Report the text. |
| 2.3 | Return to the cartridge's menu (or power off straight from the game: try both, on different days), then start the game again. | 1-1 in green shades, `SAVE: OK`. Note whether a `.brm` file appeared under `edturbo/gamedata` and when. | Defaults and `SAVE: READY` or `NONE`: the cartridge did not keep the memory; note which way you left the game. |
| 2.4 | EXP Device `CDROM`: repeat 2.1 to 2.3. | The same. | Report what differs. |
| 2.5 | EXP Device `OFF`. Start the game, Select; Run; Select. | **`SAVE: NONE`** before and after Run; the game plays as before; defaults at every start. | `SAVE: ERROR 1` after Run: see part 3. |
| 2.6 | In the cartridge's Rom Info screen. | Note what "EXT Type" shows for this ROM. | |

## 3. A console with nothing attached (any flash cartridge without save memory, or EXP Device OFF)

| Step | Do | You should see | If not |
| --- | --- | --- | --- |
| 3.1 | Start the game, Select in 1-1. | **`SAVE: NONE`**; no delay at power-on. | A hang at power-on: report it at once. |
| 3.2 | Change a setting, **Run**, Select. | The setting applied, the stage restarted, **`SAVE: NONE`**. | `SAVE: ERROR 1`: this console's unmapped memory reads neither a constant nor `$FF`/`$00`, which the game takes for unformatted memory (still nothing is written). Report it with the console model. |
| 3.3 | Power-cycle, start the game, Select. | The defaults, `SAVE: NONE`. | |

## 4. MiSTer (the maintainer has none; for a tester)

Read from the core's and Main's source, not tested: a HuCard gets backup
RAM, pre-formatted when the game has no save file yet. The core writes the
save file only on the OSD's "Save Backup RAM", or with "Autosave" ON when
the OSD is opened after a change.

| Step | Do | You should see | If not |
| --- | --- | --- | --- |
| 4.1 | Start the game, Select in 1-1. | **`SAVE: READY`**. | `SAVE: NONE`: the core's lock did not open. Report the core's date. |
| 4.2 | Change PALETTE to `GB DMG`, **Run**, Select. | Green shades, **`SAVE: OK`**. | Report the text. |
| 4.3 | Open the OSD and choose "Save Backup RAM" (or have Autosave ON and open the OSD once). Power-cycle or reload the core, start the game. | 1-1 in green shades, `SAVE: OK`. | Defaults: the file was not written; note the Autosave setting. |

## What to send back

- For each part tried: console, cartridge and firmware, EXP Device setting,
  the step number where anything differed and the exact `SAVE:` text.
- A photo or the exact text of the backup utility's list before (1.1) and
  after (1.9).
- Anything that hung, flickered or sounded different at power-on or when
  pressing Run (the save holds interrupts off for about 2 ms; the first
  save on a blank memory for about half a frame).
