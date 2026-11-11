# Saved settings: hardware test checklist

For the maintainer's consoles. Everything in
[bram-save.md](bram-save.md) is emulator evidence; nothing below has been
seen on hardware yet. The emulator used cannot check the unlock sequence the
real backup RAM needs (a test-only model of it passes), so **test 1 is the
one that matters most**.

Build: `Ninja Ryukenden - Enhanced v1.11-dev (settings save).pce` (the menu's
band shows `V1.11-DEV`). The menu (Select during play) now ends with a
status line:

```
 RUN: OK  SELECT: CANCEL
 SAVE: READY
```

| Text | Meaning |
| --- | --- |
| `SAVE: NONE` | No formatted backup RAM was found (none in the machine, or locked, or blank). After Run: there is nothing to write to. Nothing was written. |
| `SAVE: READY` | Formatted backup RAM found at power-on, no settings in it yet, room for them. |
| `SAVE: OK` | At power-on: the settings were loaded. After Run: they were saved and read back. |
| `SAVE: FULL` | The backup RAM has no room for the 26 bytes. Nothing was written. |
| `SAVE: ERROR 1` | (After Run only) the memory is not formatted and not blank. Nothing was written. |
| `SAVE: ERROR 2` | The save directory is damaged (bad pointers or sizes). Nothing was written. |
| `SAVE: ERROR 3` | A file named `NR ENHANCE` of another size is there. Nothing was written. |
| `SAVE: ERROR 4` | The save was written but did not read back. |
| `SAVE: ERROR 5` | (At power-on) the `NR ENHANCE` file is there but its contents do not check out; the defaults are used and the next Run rewrites it. |

The status is set at power-on and by each Run; it is not refreshed while the
menu is open. Settings are saved by **Run** only (Select cancels and writes
nothing). A language chosen on the title screen is saved by the next Run.

For every step, please note: the console, the cartridge and its settings,
the status text **before** Run (first time the menu is opened after
power-on) and **after** Run (open the menu again in the restarted stage),
and what the game showed after the next power-on.

## 1. Duo-RX with the Turbo EverDrive Pro (the Duo's own backup RAM)

Expected: the cartridge's own CD and Ten no Koe functions are off in a Duo
(its manual: the built-in CD-ROM core does not work on a console with
built-in CD-ROM), so the game talks to the Duo's backup RAM.

1. Before anything else, note what the System Card's backup manager lists
   (hold Select and press Run on the System Card screen; or the EverDrive's
   own file menu for `.brm`), so existing saves can be compared afterwards.
2. Start the game, reach 1-1, press Select.
   - Expected: `SAVE: READY` (a formatted Duo that never ran this build).
   - `SAVE: NONE` here means the unlock did not work or the memory is not
     formatted: stop and report (also try once after formatting the backup
     RAM in the System Card, if it offers to).
3. Change PALETTE to GB DMG, NO DAMAGE to ON, LANGUAGE to JAPANESE; press
   Run. In the restarted stage press Select: expected `SAVE: OK`. Select to
   close.
4. Power off (the switch, not reset), wait a few seconds, power on, start
   the game.
   - Expected: the title's language line shows Japanese; 1-1 opens in the
     four green shades; enemies do not hurt Ryu; the menu shows the three
     values and `SAVE: OK`.
5. Reset (Run + Select, or the EverDrive's reset): the same settings come
   back.
6. Change one setting only (PALETTE to ORIGINAL), Run, power-cycle: that
   setting is back to ORIGINAL, the other two kept.
7. Open the menu, change something, press **Select**. Power-cycle: the
   change was not kept.
8. In the System Card's backup manager: a file `NR ENHANCE` is listed (26
   bytes with its header and terminator; managers that show blocks or bytes
   may round), and every save from step 1 is still there. If the manager
   can copy or delete files: delete `NR ENHANCE`, start the game: `SAVE:
   READY` and the defaults.
9. Start one of the CD games whose save was in the list in step 1 and load
   it: it loads.
10. Full memory, if a spare situation allows (not worth filling the Duo on
    purpose): with the backup RAM so full that the manager shows fewer than
    26 bytes free and no `NR ENHANCE` file, the menu shows `SAVE: FULL`
    before and after Run, and the manager's list is unchanged.

## 2. EverDrive Pro on a console without CD (PC Engine, CoreGrafx, TurboGrafx-16), if available

The cartridge's menu: Options, Default EXP Device: `OFF`, `CDROM` or `TNK2`
(its manual says to choose TNK2 or CDROM for games that save to CD backup
memory, and that each game gets its own copy under `edturbo/gamedata`).

1. `TNK2`: start the game, Select.
   - If the cartridge's fresh memory is formatted: `SAVE: READY`.
   - If it is blank: `SAVE: NONE` now, and `SAVE: OK` after the first Run
     (the game formats a blank, writable memory itself).
   - Then steps 3 to 7 of part 1. Note whether a `.brm` file appeared in the
     game's folder under `edturbo/gamedata`, and when (the manual does not
     say when the cartridge writes it: try returning to the cartridge menu
     before power-off, and powering off straight from the game).
2. `CDROM`: the same.
3. `OFF`: `SAVE: NONE` before and after Run; the game plays as before and
   starts with the defaults every time.
4. In the Rom Info screen, note what "EXT Type" shows for this ROM.

## 3. A console with nothing attached (any flash cartridge without save memory, or EXP Device OFF)

- `SAVE: NONE` before and after Run, no hang at power-on or at Run, the
  defaults at every power-on.
- If it shows `SAVE: ERROR 1` after Run instead: please report it with the
  console model. It would mean that this console's unmapped memory reads
  neither a constant nor $FF/$00, which the game takes for unformatted
  memory (still nothing is written).

## 4. MiSTer (the maintainer has none; for a tester)

Read from the core's and Main's source, not tested: a HuCard gets backup RAM,
pre-formatted when the game has no save file yet, so `SAVE: READY` at the
first boot and `SAVE: OK` after Run. The core writes the save file only on
the OSD's "Save Backup RAM", or with "Autosave" ON when the OSD is opened
after a change: without one of the two the settings are lost at power-off.

## What to send back

- For each part tried: console, cartridge and firmware, EXP Device setting,
  the status texts, and whether the settings came back.
- A photo or the exact text of the backup manager's list before and after.
- Anything that hung, flickered or sounded different at power-on or when
  pressing Run (the save holds interrupts off for about 2 ms; the first save
  on a blank memory for about half a frame).
