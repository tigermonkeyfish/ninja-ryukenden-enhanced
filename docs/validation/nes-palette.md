# NES palette mode (1.11-dev): validation record

Emulator evidence only (headless Geargrafx `78fc3d7` with the headless-fast
patch, [EMULATOR.md](../pc-engine/EMULATOR.md)); no real hardware yet, audio
not compared. Design: [architecture, NES palette mode](../ARCHITECTURE.md#nes-palette-mode).
The colours are a **draft** the maintainer has not reviewed; this record
covers the machinery (the ROM shows exactly the generated data), not the
colour choices.

| Build | SHA-256 | Source |
| --- | --- | --- |
| Before (`popup-menu`) | `43db8b4c9c3f662c6edd4d22dd03d62385b0e84748ff8d898cb936a12aa6ecb5` | commit `46bbbe3` |
| NES palette | `3dbae324d800d12555e87d2647bb39065507c051009e8b790eb47b0141a09dff` | branch `nes-palette` (the same bytes from the headered and the headerless original) |

Method: one start state (a cold boot of the original saved at the 1-1
main-loop hook), one fresh session per replay, `$2100`/`$2101` written to the
mode (0 Original, `$08` NES, `$10` GB DMG) before the stage is entered as
Level Select does. Probes: [`research/tools/nes-palette/`](../../research/tools/nes-palette)
(`loads.py`, `stagecheck.py`, `nesruns.py`, `identity.py`, `framediff.py`,
`peek.py`, `stackguard.py`, `shots.py`); the GB palette probes'
`freewatch.py` for the free-space audit.

## Facts the design rests on

- Only `$F211` (sets) and `$F1C0` (sprite palettes) map bank `$37`
  (`lda #$37 / tam #3`; no other `$37` bank load in the original's code), and
  both unpack through `$F2BE` with MPR3 = bank `$37`.
- `loads.py` (breakpoints on `$F211`, `$F1C0`, `$83C3`) over all 22 Level
  Select entries and the 11 stored runs: each stage loads exactly one set at
  its load, `$2240` = 0 there; the stage → set map is
  1,2,3,4,5,6,6,7,8,9,10,11,12,13,14,14,14,15,16,17,17,18; 3-1 and 3-2 both
  load set 6 with `$2E5F` = 5 and 6. No set loads at area changes; the HUD
  routine runs at every load and area change (`$F3` path), sprite palette
  96 → row 0 at every load and once more in 6-3 (`$86A7`). The highest
  sprite palette used is 151 (`$7C1E-$7C2F`), so bank `$37` is free from
  `$7C30`.
- Ryu's palette 96 is at `$37:$7840` ($7180 + 18 x 96); the study's
  `$77C0` was a slip (its data were right).
- The generator reproduces the draft exactly: every set, the 3-2 variant,
  Ryu, the HUD words and the three Enhanced palettes equal the draft's
  `out/*.bin` and `enhanced-nes.json` byte for byte.

## a. Original and GB DMG against the popup-menu build

`identity.py` (all 11 runs, 35,084 frames each mode; screenshot, SAT, VCE
every frame, VRAM every 30 frames, RAM without the dead stack):

| Mode | Picture | SAT, VCE | VRAM samples | RAM |
| --- | --- | --- | --- | --- |
| Original | identical except 2 frames of 2-2 (789: the backdrop mid-redraw at an area change, 28,950 pixels; 1660: 72 pixels on 2 lines) | identical | identical | differs only in load and area-change frames (zero-page scratch `$21-$24`, live stack), and in 2-2 throughout in the music driver (`$38xx`, ZP `$83-$88`): its tick runs one step apart from the stage load on, so S at the frame end differs in 1,835 frames |
| GB DMG | identical except 1 frame (5-3 6494: 5 pixels on one line) | identical | one sample differs (5-2 2940, in a load) | as Original, without the 2-2 music shift |

Cause: outside NES mode each palette load costs 15 cycles more (the bank
`$37` hook's test and jump) and the HUD routine about 40 (its trampoline);
the frame boundary then catches the load at another instruction. In 2-2 the
stage load's few hundred cycles push the music driver's start past a timer
tick, which moves its interrupt work in every later frame; that is what
redraws 2-2's backdrop at 789 and 1660 a moment apart (the GB palette record
saw the same two frames for the same kind of reason). Game state (Ryu,
timer, camera, enemies, SAT) never differs.

`scripts/check_boot.py`: passed (idle frames 1-899 identical to the
original, first 1-1 update on frame 163 when mashing Run, defaults English,
Enhanced, damage on). `scripts/check_menu.py`: options passed (below);
`--only select --only runs --same-music`: passed, 140 menu cycles in the 11
runs all exact (no raster-timing frames), stack low-water `$21D3`; all 22
Level Select entries and the cold-boot LANGUAGE check passed.

## b. NES mode: stage loads and stored runs

`stagecheck.py` (all 22 Level Select entries, Original and NES, 150
frames): the load takes the same frames in both modes (78-83, per stage);
gameplay fields and SAT identical in every frame; over the last 60 frames
every managed RAM palette entry that Original mode holds at its set value
holds the NES value: 3,968 entries checked, 0 mismatches (the set, the 3-2
variant in 3-2, HUD `$F1-$F7`, Ryu's row 0, 1-1 row 1 and 2-2 rows 13-14).
Entries the game animates were listed separately and match the draft's
animated list exactly (e.g. 2-3 145-149, 6-2 162-166, 6-4C 2-6); in NES mode
they show the game's original animation values (out of scope).

`nesruns.py` (the 11 runs plus 900 frames: stage end, cinema where there is
one, the next stage's start; 44,324 frames per mode): gameplay (Ryu, timer,
camera, area, stage, lives, health, master state, SAT) identical in every
frame of all 11 runs; colours: 7.3 million full-value and 0.22 million
fade-step checks, 0 problems; 9 entries in one frame (2-2 3958) taken while
the 2-3 set was being unpacked with the palette lock held (nothing uploaded;
picture identical) are counted apart.

## c. Switching through the popup

`check_menu.py --only options`: PALETTE NES and Run gives `$2100` = `$08`,
the NES colours of 1-1 in the RAM palette, the VCE equal to the RAM palette
(native upload, bit 7 clear); GB DMG (two steps right, or one left) the GB
table; Original → NES → GB DMG → Original with Run each time: the NES
colours, then the GB table over the original colours (none of the NES ones
left), then exactly the VCE of three plain Runs; cancel after changing every
row from Original, from GB DMG and from NES (the PALETTE row stepped through
NES): options and language kept, 900 frames compared with the run without
the menu, exact. Stack low-water `$21D3` (as before).

## d. Fades, area changes, cinemas

In every stored run (above) no managed entry shows an original colour in NES
mode: full values are the NES values, fade steps stay at or below them, the
HUD stays NES through every area change. Cinemas after 4-1, 5-3, 5-4 and 6-3
(2,924 frames): picture, VCE and RAM palette identical in both modes (the
original colours); the stages loaded after a cinema or stage end (1-2, 2-3,
3-2, 3-3, 4-3, 5-3, 6-2) are NES again.

## e. Space and stack

| Region | Use | Free |
| --- | --- | --- |
| Fixed bank `$F1DC-$F1DE`, `$F234-$F236` | call operands only (`jsr $F2BE` → `jsr $7FE0`) | `$FECF-$FEDF` (17) and `$FFEE-$FFF5` (8) untouched |
| Bank `$37` `$7FE0-$7FF9` | hook, 26 bytes | `$7C30-$7FDF` (944), `$7FFA-$7FFF` (6) |
| Bank 1 `$83C3-$83D5` | HUD trampoline, 19 bytes (old `$83D6-$83E4` dead) | |
| Bank `$45` `$4000-$4236` | code 249 bytes, tables, HUD, Ryu, 3-2 variant | `$4237-$43FF` (457) |
| Bank `$45` `$5200-$5EA7` | 18 NES sets, 3,240 bytes | `$5EA8-$5FFF` (344) |
| Bank `$45` `$4400-$51FF` | `stage61-upload` (code ends `$5113`, guarded) | 236 |
| Bank `$46` | menu grows 20 bytes (to `$4A10` of `$4AFF`) | `$4100-$42FF`, `$4B00-$4FFF` untouched |
| stage11 / stage22 | NES merged palettes and the mode test: +54 / +92 bytes | |

Free-space audit (`freewatch.py`, read/execute watch on the popup build over
bank `$37` `$7C30-$7FFF` and bank `$45` `$4000-$43FF`, `$5200-$5FFF`): 0
stops over a cold boot to 600 updates of 1-1 (683 frames) and all 11 runs
(35,084 frames). Positive control: the same watch on the NES palette build
stops at `$7FE0` (MPR3 = `$37`) 52 frames after power-on (the publisher
scene's palette loads). Bank `$45` is otherwise mapped only by
`stage61-upload`, whose code ends at `$5113` (its guard now fails the build
past `$5200`).

Stack (`stackguard.py`, `$A5` fill, each run's stage load and the whole
run): NES mode's low-water mark `$21C2`, the same as Original on the popup
build; the watched margin `$2104-$213F` is untouched.

## f. Screenshots

Private, `build/nes-palette/shots/`: `nes-1-1-start.png`,
`nes-2-2-start.png`, `nes-4-1-start.png`, `nes-5-2-start.png`,
`nes-5-3-start.png` (150 frames after each entry), `nes-1-1-f600.png`,
`nes-2-2-f900.png`, `nes-4-1-f900.png`, `nes-5-2-f900.png`,
`nes-5-3-f900.png` (stored runs) and `nes-1-1-f600-menu-open-{0,1}.png` (the
popup in NES mode, PALETTE: NES blinking). Compared by eye with the draft
sheets (`build/nes-draft/sheets/`): the same colours (1-1 grey street, red
brick, blue skyline, white HUD text and pink bars; 2-2 pale sky, brown
mountains, white cloud sea, grey pillars; 4-1 dark greens; 5-2 orange rock
and salmon ledges; 5-3 olive girders on dark green). Enemies keep their PC
Engine colours, as in the draft.

## GB DMG from NES colours

Only the open menu ever maps NES colours to GB DMG (opened in NES mode, GB
DMG highlighted); Run reloads the original colours first (c). Over the 18
stage sets, 69% of the entries keep their GB shade; the NES sets have fewer
lightness levels, so in 2-1, 4-3 and 6-4 A one of the four shades goes
unused: that preview is flatter than GB DMG from Original.

## Rerun

From `research/tools/nes-palette/`, with `LD_LIBRARY_PATH` and
`NG_EMULATOR` set as in `build/toolchain/run-check.sh`, `NG_DEBUGGER_FAST=1`,
and `NES_WORK` (default `build/nes-palette`) holding `seed.state` (a
`comparison_video.make_seed` of the original) and `original.pce`:

```sh
python3 identity.py BEFORE.pce NES.pce 0    OUT       # a, Original
python3 identity.py BEFORE.pce NES.pce 0x10 OUT       # a, GB DMG
python3 stagecheck.py NES.pce 150 OUT.json "" SHOTS 0,3,8,13,14   # b
python3 nesruns.py NES.pce OUT.json 900 ANIMATED.json # b, d (ANIMATED: stagecheck's game_written per stage)
python3 stackguard.py NES.pce 8                       # e
python3 shots.py NES.pce SHOTS 1-1:600:open 2-2:900 4-1:900 5-2:900 5-3:900   # f
python3 framediff.py BEFORE.pce NES.pce FLAGS RUN FIRST LAST [SHOTS]          # diagnosis
GB_WORK=$NES_WORK python3 ../gb-palette/freewatch.py BEFORE.pce RUN 6fc30 6ffff 8a000 8a3ff 8b200 8bfff
```

and from the repository root `scripts/check_boot.py`,
`scripts/check_menu.py --only options` and `--only select --only runs
--same-music` (c), and `python3 -m unittest tests.test_tools` (the data:
stored results equal the roles', the packed tables decode back to them).

## Not covered

Real hardware; audio; enemy and boss sprite palettes and the animated
colours (still PC Engine colours in NES mode); a live NES preview in the
open menu; Continue and Game Over screens; the title and cinemas in NES mode
beyond the four cinemas above (original by design: `$2240` != 0).
