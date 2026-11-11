# NES palette mode (1.11-dev): validation record

## Draft 2 (branch `nes-palette-2`, 2026-11-11)

Emulator evidence only (as below); no real hardware, audio not compared.
The colours are still a **draft** the maintainer has not reviewed.

| Build | SHA-256 | Source |
| --- | --- | --- |
| Before (draft 1) | `3dbae324d800d12555e87d2647bb39065507c051009e8b790eb47b0141a09dff` | branch `nes-palette` `9ec799f` |
| Code check build | `a15d425955601d5ac5b70d3fbddbbe7b9369048d00618e600f2fd6aaeeb79aa8` | draft 2's code with earlier data (differs from the candidate only in NES data bytes: bank `$37` sprite copies, bank `$45` sets, one bank 3 list byte) |
| Candidate (draft 2) | `052419169bfc43adf62d69ff649f8db583cbec023412c1351b9fa37fba923aa2` | branch `nes-palette-2` (the same bytes from the headered and the headerless original) |

What changed (owner, 2026-11-11: every boss NES, every room fully NES; NES
master-palette colours only, with the TG16's detail):

- **NES colours only.** Every colour NES mode loads is one of the 47 9-bit
  colours of the 2C02G palette (the set of `palettes.py nes_set('2c02g')`);
  `unused` / `keep` entries (transparent colour 0, unseen entries, the 1-1
  HUD row) take the nearest NES colour too, with no exception left.
  `nes_palette.py` fails the build otherwise (unit test
  `test_every_nes_mode_colour_is_an_nes_colour`).
- **Detail.** Per palette row the distinct colours of a role go to distinct
  NES colours in lightness order (the role's hue first, then neighbouring
  hue columns, greys and near-greys; never a far hue). Two colours share one
  only where keeping them apart would shift a colour by more than about
  30 L* (a merge costs `MERGE` = 900, the price of a 30 L* shift). Over the
  18 stage sets: 597 of 2,566 distinct row colours still merge (draft 1:
  1,333), mean lightness shift 6.8 L* (draft 1: 7.0), 90th percentile 16.3,
  largest 33.2. Without the cap only 19 merge, but 2-1's teal walls turn
  near-white and 2-2's sky pink (largest shift 70.6 L*); not used. The build
  prints the rows that merge; `nes_palette.py detail` lists them. Merged
  colours per file: 1-1 64, 1-2 10, 2-1 76, 2-2 26, 2-3 29, 3-1 9, 3-2 38,
  3-3 10, 4-1 38, 4-2 37, 4-3 31, 4-4 10, 5-1 70, 5-2 4, castle 38, 6-2 48,
  6-3 40, 6-4A/B 14, 6-4C 5, animation lists 18, enemies 1, items 3; Ryu,
  his effects and every boss 0.
- **Ryu** re-mapped: suit 02 / 11 / 22, skin 35, darks 07 / 17, outline 0F
  (draft 1 merged two suit blues into 22 and both darks into 17).
- **Sprite palettes.** All 54 palettes loaded in gameplay (found from the
  loaders: `$F1C0` calls in bank 1, the per-area lists at `$9916`, the
  row-14 table `$8714`; and traced at all 22 entries and the 11 runs):
  96-98 Ryu, 113-121 / 109 / 150-151 items and effects, 122-148 enemies
  (shared by stages; by hue class with NES ramps), and the bosses by part
  from their NES fights (below). The hook finds a copy by palette number
  (52 in bank `$37`'s free tail, read in place; 2 in bank `$45`).
- **Animated colours.** All 15 animation sets of bank 3 (`$CF32`, 55 lists)
  have NES lists; in NES gameplay `$CE98` gives the NES copy of the table
  (same records, delays and list lengths). Each set resolves as one row, so a
  colour travelling from entry to entry keeps its NES colour.
- **The once-uncaptured areas** of 2-1 (5 areas), 4-3 (5), 5-1 (2) and 6-2
  (6) were reached with `areawarp.py` (the area exit moved onto Ryu) and
  checked; 6-2's later green pillars (row 2) had been given the brown pillar
  role and now take the NES 6-2 green. 2-2's pillars (greys and beige
  browns), 3-3's floor (stone) and 4-4's room (red, no olive) were adjusted
  after looking at the stage starts.

Bosses (NES colours captured in each NES fight with the `cynes` core:
stage `$6D` / room `$6E`, palette RAM constant through each fight, no hit
flash; PC Engine rows found by index pictures of the fights):

| PC Engine | Rows (palette) | NES fight | Match |
| --- | --- | --- | --- |
| 1-2 Barbarian | 3 (102) | `$6D` 1 room 1: body 23, skin 36, metal 10 30 | good: violet body, peach skin |
| 2-3 Bomberhead | 4 (103) | 4 / 9: skin 37, hair 17, accents 1A 35 | fair: tan and brown, the PC Engine green trousers kept as the NES accent green |
| 3-3 Basaquer | 5 (104) | 7 / 12: red 16, pale 36, blades 23 34 | good |
| 4-4 Kelbeross | 6 (105) | 11 / 21: fur 37 17, eyes 16 24 30 | good (pale tan dogs as on the NES) |
| 5-4 Bloody Malth | 3, 4 (106, 101 lightning) | 15 / 34: red 16, pale 36, coat 08, bolt 16 26 30 | weak: bronze armour as olive/brown 08 18 17, blue cape red; the NES boss reads darker |
| 6-4A Jaquio | 4 (107), 3 (75 the statue orb), 5 (100 fireballs) | 19 / 45: tan 37, dark red 06, accents 13; orb 16 26 30 | fair: gold body, violet cape; orb red as on the NES |
| 6-4B demon statue | 3 (108), 5 (100) | 19 / 45: the demon head is background art 05 14 24 34, orb 16 26 30 | by role: violet/magenta statue, red details |
| 6-4C final demon | 3-5 (110-112) | not reached on the NES (after the orb the NES run went on to 6-1) | by role only: magenta body, red flesh, red/white rings |

Evidence (from `research/tools/nes-palette/`, `NES_WORK=build/nes-palette-2`):

- a. Original and GB DMG (`identity.py`, the code check build against draft
  1, all 11 runs, every frame): picture, SAT, VCE and VRAM identical in
  every frame except the CPU's S at the end of one frame (Original: 2-2
  3956; GB DMG: 1-1 2845, 2-2 3956); RAM differs only in frames of the
  next stage's load at a run's end (zero-page scratch `$2021-$2024`, the
  live stack `$21EB-$21FC`, the music driver's `$2083`, one byte `$3A34` (6-1, GB DMG), and in 2-2
  3956 RAM palette bytes `$22A3` or `$22DA-$22DD` mid-unpack): the bank 3 call adds
  about 25 cycles to each stage load, so the frame boundary catches the
  load at another instruction (the same kind as draft 1's 2-2 frames).
  Game state never differs. `check_boot.py` (code check build): passed
  (idle frames 1-899 identical to the original, first 1-1 update on frame
  163 mashing Run, defaults English, Enhanced, damage on).
  `check_menu.py --only options` (candidate): passed (PALETTE NES gives the
  NES colours of 1-1, the VCE equal to the RAM palette; GB DMG the GB table;
  Original-NES-GB-Original; cancel from Original, GB DMG and NES; stack
  low-water `$21D3`).
- b. On screen (`onscreen.py`: every 30 frames an index picture of the
  frame, each VCE entry seen checked; the replay is restored after each
  sample): the 8 boss fights (900 frames each from the Level Select entry,
  No Damage), every area of all 22 entries (`warp:`, 180 frames holding
  right per area, 70 areas) and the 11 stored runs plus 900 frames; 2,381
  samples. Boss fights (240 samples) and stored runs (1,481): every entry on
  screen an NES colour in gameplay, except 53 entry-samples in the 5-4 run's
  end fade. Area sweep (660 samples): 1,506 entry-samples in fade frames,
  each a channel-wise step at or below the NES colour the backup holds
  (see "Fades" below), and 4 others, all in rows the stage's set does not
  load (see "Leftover rows": 5-2 row 6 entry 2, and row 10 entry 4 in 4-3,
  5-2 and 6-3, holding 1-1's original colours from the start state).
  Nothing else on screen is outside the NES set.
- c. Gameplay (`nesruns.py`, the 11 runs plus 900 frames, Original against
  NES mode, every frame, 44,324 frames per mode): passed. Ryu, timer,
  camera, area, stage, lives, health, master state and the sprite table
  identical in every frame (no frame added or dropped); the 2,924 cinema
  frames after 4-1, 5-3, 5-4 and 6-3 identical in picture, VCE and RAM
  palette (original colours); 7.34 million full-value and 0.22 million
  fade-step checks of the managed entries (the stage set, the 3-2 variant,
  HUD, Ryu, the Enhanced rows; animated entries left out), 0 problems; 12
  in frames ending with the palette lock held (a load unpacking, nothing
  uploaded) counted apart.
- Stage loads (`stagecheck.py`, all 22 Level Select entries, Original and
  NES, 150 frames): every load takes the same frames in both modes (78-83);
  gameplay fields and sprite table identical in every frame; 3,968 managed
  entries hold their NES values, 0 mismatches. Stack (`stackguard.py`, NES
  mode, the 11 runs): lowest `$21C4` (draft 1: `$21C2`); the watched margin
  `$2104-$213F` untouched.
- Free space: the original's code never reads bank 3 `$D400-$D9FF` or bank
  `$37` `$7C30-$7FDF`: `freestages.py` on draft 1 (read/execute watch, all 22
  Level Select entries, 600 frames each holding right with the area exit
  moved every 150 frames, 13,200 frames): 0 stops; earlier audits cover a
  cold boot and the 11 runs for the same ranges (draft 1, below, and
  [nes-firewheel.md](nes-firewheel.md) for bank 3 `$D3FD-$DFFF`).
- Space: [architecture](../ARCHITECTURE.md#nes-palette-mode) (bank `$45`
  301 + 309 bytes free, bank `$37` 8, bank 3 claim 514).

Review sheets (private, `build/nes-palette-2/sheets/`): `boss-*.png` (PC
Engine | NES mode | real NES, frames 200 and 400 of each fight),
`bosses-contact.png`, `area-ls02.png`, `area-ls10.png`, `area-ls12.png`,
`area-ls17.png` (PC Engine | draft 1 | draft 2, each area's start and
after 120 frames), `ryu-before-after.png`.

Rerun (from `research/tools/nes-palette/`, environment as in draft 1's
Rerun, `NES_WORK=build/nes-palette-2`):

```sh
python3 identity.py BEFORE.pce CANDIDATE.pce 0 OUT          # a (and 0x10)
python3 onscreen.py CANDIDATE.pce 0x0a 30 OUT ls:1:900 ... warp:0:180 ... warp:21:180   # b
python3 onscreen.py CANDIDATE.pce 0x08 30 OUT run:1-1:900 ... run:6-3:900               # b
python3 nesruns.py CANDIDATE.pce OUT 900 ANIMATED.json      # c (ANIMATED: the entries of animations.json per stage)
python3 stagecheck.py CANDIDATE.pce 150 OUT
python3 stackguard.py CANDIDATE.pce 8
python3 freestages.py BEFORE.pce 600 150 7400 79ff 6fc30 6ffdf
python3 areawarp.py ROM FLAGS OUTDIR TAG 2,10,12,17 60 120 right [index]   # area pictures
```

and `python3 scripts/nes_palette.py detail` for the merged colours per row.

Not covered or open:

- **Fades are not NES colours.** The game fades by lowering each colour's
  channels (from the backup `$2686`), so fade frames (stage loads, area
  changes, deaths, stage ends) show dimmed NES colours that are not in the
  NES set: in the area sweep 1,506 entry-samples, every one a channel-wise
  step at or below an NES colour (the backup's). Making them NES needs the
  upload to map fade colours to the nearest NES colour (the GB DMG mapped
  path, which `hell-palette` rewrites): left for after that merge.
- **Leftover rows.** Sets shorter than 15 rows leave the rows above them as
  an earlier load left them, and a few tiles use them (5-2's last area row
  6 entry 2, 529 pixels; row 10 entry 4 in 4-3, 5-2 and 6-3, 13 pixels).
  In NES-mode play these hold the previous stage's NES colours; after a
  Level Select entry or a mode switch they hold original colours (seen in
  the area sweep, which starts from a 1-1 state saved in Original mode).
- The NES final form; enemies per stage (the hue-class pass gives every
  enemy NES colours, not the NES stage's enemy palettes); Continue and Game
  Over screens; real hardware.

## Draft 1

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

### Facts the design rests on

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

### a. Original and GB DMG against the popup-menu build

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

### b. NES mode: stage loads and stored runs

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

### c. Switching through the popup

`check_menu.py --only options`: PALETTE NES and Run gives `$2100` = `$08`,
the NES colours of 1-1 in the RAM palette, the VCE equal to the RAM palette
(native upload, bit 7 clear); GB DMG (two steps right, or one left) the GB
table; Original → NES → GB DMG → Original with Run each time: the NES
colours, then the GB table over the original colours (none of the NES ones
left), then exactly the VCE of three plain Runs; cancel after changing every
row from Original, from GB DMG and from NES (the PALETTE row stepped through
NES): options and language kept, 900 frames compared with the run without
the menu, exact. Stack low-water `$21D3` (as before).

### d. Fades, area changes, cinemas

In every stored run (above) no managed entry shows an original colour in NES
mode: full values are the NES values, fade steps stay at or below them, the
HUD stays NES through every area change. Cinemas after 4-1, 5-3, 5-4 and 6-3
(2,924 frames): picture, VCE and RAM palette identical in both modes (the
original colours); the stages loaded after a cinema or stage end (1-2, 2-3,
3-2, 3-3, 4-3, 5-3, 6-2) are NES again.

### e. Space and stack

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

### f. Screenshots

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

### GB DMG from NES colours

Only the open menu ever maps NES colours to GB DMG (opened in NES mode, GB
DMG highlighted); Run reloads the original colours first (c). Over the 18
stage sets, 69% of the entries keep their GB shade; the NES sets have fewer
lightness levels, so in 2-1, 4-3 and 6-4 A one of the four shades goes
unused: that preview is flatter than GB DMG from Original.

### Rerun

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

### Not covered

Real hardware; audio; enemy and boss sprite palettes and the animated
colours (still PC Engine colours in NES mode); a live NES preview in the
open menu; Continue and Game Over screens; the title and cinemas in NES mode
beyond the four cinemas above (original by design: `$2240` != 0).
