# HELL: candidate D and the 1-1 override (1.11-dev)

Emulator evidence (headless Geargrafx `78fc3d7` with the headless-fast patch,
binary SHA-256 `2de50e51…`, [EMULATOR.md](../pc-engine/EMULATOR.md)); no real
hardware, audio not listened to. Design:
[architecture, palette modes](../ARCHITECTURE.md#palette-modes).

The owner's decision (2026-11-11): "1-1 hell should be more like 2-2. The 1-1
foreground sidewalk/walls can use the same 2-2 bridge column color."

| Build | SHA-256 | Source |
| --- | --- | --- |
| `all-palettes` (reference) | `8682d4401c92c00df5c4c1027a733e3aa6541785aeaca7c3df9a46f51665b723` | `cc2e0a4`, rebuilt here: the bytes of its record |
| Candidate D only (no override) | `ccbf092f5485b2fae71ad8524637bcdf13d0c79a52060086396959258c3e9489` | `cc4b205` |
| Candidate | `fa158540598587c3b47dad4344ad99040cf46d62dfc9ccf01184d7a6320ef4c9` | branch `hell-1-1` (the same bytes from the headered and the headerless original) |

Work folder (private): `build/hell-1-1/` with `seed.state` and
`original.pce` (the `all-palettes` record's), `ap.pce`, `d.pce`, `h1.pce`.
Every replay is a fresh session from the seed state with `$2100` written to
the mode. Probes: [`research/tools/hell-1-1/`](../../research/tools/hell-1-1)
and, unchanged, the SMS, HELL and GB palette probes named below.

## 1. Candidate D

`src/palette/hell.json` is `build/hell-tune/gen/hell-D-ship.json` (the tuning
study's candidate D: the "steel" family takes cool greys and dull teals to
2-2's column golds, a new grey ramp; lava sky, brick red and the rest as
before), plus the override below. The generated table equals the tuning
generator's `cand-D.json` table in all 512 words (SHA-256 of the words
`1435b5a1…d641`; the unit test pins it); with candidate C's parameters
(`all-palettes`' `hell.json`) the generator still gives the first HELL table
(`1388df9d…`). In the ROM only 19 table bytes change (bank `$43`
`$7C82-$7FA6`).

## 2. The 1-1 override

Colour `$094` (R2 G2 B4) is 1-1's sidewalk fleck (palette 3 entry 5, entry
53) and the shadow faces of the Enhanced skyline (palette 1 entry 2, entry
18); 1-1 also holds it at entries 1 and 181 (`census.py`, the 1-1 run and
Level Select). It is also 2-2's far mountain ridge (entries 4, 20, 181), and
other stages hold it at entries 181 and others (3-1, 3-2, 4-1, 4-3, 4-4, 5-2
to 6-4C), so the table keeps it crimson (R6 G0 B1) and 1-1 alone overrides
it.

Choice of colour (`build/hell-1-1/choose-094.png`, `choose-zoom.png`: 1-1's
sidewalk and skyline with 601, 210, 110, 410 and 320 next to 2-2's columns
and bridge). The neighbours under D: sidewalk 420 (base), 320, 430, 100;
skyline 420, 320, 210, 651. 2-2's column and bridge colours under D: 110,
320, 420, 410, 521, 762, 210. **210 (`$050`, the dark gold-brown of 2-2's
columns, `$0C9` there)** keeps `$094` darker than its 320/420 neighbours as
in the original, reads as the columns' shadow on the skyline and as a brown
fleck on the gold sidewalk; 110 (2-2's olive groove colour) puts the shadow
faces below `$08A`'s 210 (the original has them lighter); 410 keeps a red
cast; 320 merges the fleck with the sidewalk's 320. 210 is what the tuning
study proposed; it also equals `$08A`'s colour on the skyline (no new colour
on screen).

Implementation (`src/palette/main.asm`, `hell_colour_ovr`, `now_hell_ovr`):
no RAM and no stage-load hook. Where HELL's upload picks its loop (each
mapped chunk, and palette_now's mapped part) it compares `$2E5F` with the
generated `HELL_OVERRIDE_STAGE` (0, 1-1) and in that stage runs a copy of the
loop with `cpx #$94 / beq` on the low half; a hit writes `$050` as
immediates. Data: `hell.json` `"stage_overrides": {"1-1": {"$094": [2, 1,
0]}}`; `scripts/palette_tables.py` checks it (one stage, at most
`HELL_OVERRIDES_MAX` = 1 colour, low half, channels 0-7) and writes four
equates into `hell-table.inc`; `hell_stage_table(stage)` gives what a stage
shows (`check_menu.py` and the probes use it).

Cost (`upload_cost11.py`, synthetic queues at the 1-1 hook, `$2E5F` written
per case): a mapped colour takes 156 master clocks in the plain loop (this
build in 2-2, the `all-palettes` and D builds: identical) and 162 in the
override loop (+6, 3.8%); a key colour 150. The loop choice adds 27 master
clocks (9 cycles) per mapped chunk: the first write of a chunk moves from
1.316 to 1.336 lines after the interrupt in 2-2, 1.341 in 1-1. Raw chunks
are unchanged.

## 3. What changed in the ROM

Against `all-palettes` only these bytes differ:

| Region | Change |
| --- | --- |
| Bank `$43` `$7800-$7BD4` (file `$87800`) | HELL code, 842 → 981 bytes (+139): the loop choice in `hell_chunk` and `now_hell`, `hell_colour_ovr` after `hell_colour`, `now_hell_ovr` at the end; the code after them moved |
| Bank `$43` `$7C82-$7FA6` | 19 table bytes (candidate D) |
| Bank `$46` `$50F3-$50F4` (file `$8D0F3`) | the operand of `jmp now_hell` in `now_hell_far` (HELL only: SMS leaves by the `bmi` before it, the other modes never reach it) |
| Bank `$3B` `$50F3-$50F4` (file `$770F3`) | the same operand in the SMS copy of that code (never executed: SMS jumps to bank `$3B` only at `now_gb`) |

No RAM, no fixed-bank bytes, no new claim in `src/modules.json`: the new
bytes are inside the palette module's existing range `$87800-$87FFF` (stage11's
unreachable tail, [hell-palette record e](hell-palette.md#e-space-stack-and-free-rom-audit)),
`$FF` before. Free there now: `$7BD5-$7BFF` (43 bytes); the `.if/.fail`
guard keeps the code before the table. Bank `$46` `$4100-$42FF` and
`$4B00-$4FFF` untouched.

Free-ROM watch (`gb-palette/freewatch.py`, read/execute over
`$87B4A-$87BFF` on the `all-palettes` build): 0 stops over a cold boot to
600 updates of 1-1 (683 frames) and the 1-1 and 2-2 runs in Original, and
the 1-1 run in HELL (2,903 frames). Positive control: the same watch on the
candidate in HELL stops in the first 20 frames of 1-1 (39 stops, PC
`$7B4A`…, MPR3 = `$43`).

## 4. Evidence

### Original, NES-A, NES-B, GB DMG and SMS: identical

`hell-1-1/record11.py` (the SMS record's fields and format) on the
candidate, all 11 runs (35,084 frames) in each mode, compared with the
`all-palettes` record's recordings of its candidate (`build/all-palettes/rec`,
`ap-*`) by `sms-palette/analyse.py identity`: **identical** in Original
(`$00`), NES-A (`$08`), NES-B (`$28`), GB DMG (`$10`) and SMS (`$B8`): every
frame's screenshot, VCE, sprite table, game RAM (outside
`comparison_video.OWNED`) and gameplay fields (Ryu, timer, camera, area,
stage, lives, health, master state, boss), same frame counts.

### HELL

- VCE (`record11.py`, `analyse.py due`): in every frame of all 11 runs every
  VCE entry 0-239 equals `hell_stage_table($2E5F)` of its RAM colour (the D
  table, with `$094` → `$050` in 1-1) and every entry 240-511 the RAM colour,
  except while uploads are queued. Frames not yet due per run 136, 135, 101,
  122, 74, 124, 143, 170, 4, 122, 117 (1-1 … 6-3): exactly the
  `all-palettes` HELL recording's counts; longest lag 37 frames (3-1, the
  end-of-stage fade), as there. In 1-1, 2,767 of the 2,796 frames whose RAM
  palette holds `$094` below entry 240 are due (so they show `$050`); the
  other 29 are fade frames still queued.
- Gameplay: stage timer, Ryu, camera, area, stage, lives, health, boss and
  sprite table identical to Original mode in every frame of all 11 runs;
  `$2240` turns to 1 one frame later at the cinema after 4-1, 5-3 and 6-3
  (frames 2487, 6768, 5122), the same frames as on `all-palettes` and in the
  HELL record. Against the `all-palettes` HELL recording: sprite table and
  gameplay identical; the game RAM at the frame end differs in 217 frames of
  1-1 and 3-167 of the others: the frame boundary falls inside the vblank
  (the upload, then the sound driver), which now runs a few cycles later
  (`nes-palette/framediff.py`: zero page `$2023`, queue index `$2271`, sound
  driver `$380E`/`$3833`/`$38BF`, the live stack; S at the boundary).
- Unit test in place (`unittest_override.py`, the SMS build's
  `unittest_upload.py` harness and model with `$2E5F` written per case and
  the model taking `hell_stage_table(stage)`; random palettes seeded with
  `$094` and `$194`; stages 1-1, 2-2, 1-2, 6-4C; every mode): 1,096 cases
  (seed 22, 141 of them HELL 1-1 cases with `$094` below entry 240) and
  1,296 (seed 31, 152 such), 0 failures; VCE, queue, options, `$2104`, lock, S, MPR2,
  MPR3 and zero page `$20-$26` as the model says. Negative control: the
  model without the override, 80 failures of 1,096.
- Level Select (`stagestarts11.py`, all 22 entries, 120 frames): every entry
  due from frame 4-10; 1-1 shows the override in its due frames, 2-2 and the
  other stages holding `$094` the table's crimson. 2-3 and 6-2 show one
  more frame with one entry not due (frame 8: entry 149; frame 9) than the
  D build (due from 6 and 5): the emulator's frame boundary falls inside
  that vblank's upload (PC `$7A95` in bank `$43`), which now runs 9 cycles a
  chunk later; the next frame is due (the queue holds 6 entries in those frames).
- 2-2 picture (`pixshare.py`, every gameplay frame of the 2-2 run, 3,946
  frames): against `all-palettes` HELL **1.28% of the picture changed on
  average (1.62% of the playfield; areas 0-2 1.29-1.91%, area 3, the last
  68 frames, 7.98%)**, at most 12.9% (16.3% of the playfield, frame 3912):
  candidate D's columns' edges, the doorway and ridge details. From the
  override: none. Against the D build (no override code) 3,945 of 3,946
  frames are identical; frame 790 (the area change) differs in 8 pixels of
  row 63, the backdrop redraw a moment later (`framediff.py`: picture only,
  then the live stack), not a colour.
- 1-1 picture: against the D build the override changes 3.66% of the
  playfield on average (at most 11.3%); against `all-palettes` 39.4%.

### Timing in HELL

`gb-palette/timing_trace.py` over the 11 runs on the candidate (HELL and
Original) and on `all-palettes` (HELL); `split.py`, `updates.py`:

| | Candidate HELL | `all-palettes` HELL | Original |
| --- | --- | --- | --- |
| Worst vblank upload end (lines after the interrupt) | 19.32 (1-1) | 18.99 | 16.57 |
| VCE writes after line 22 | 2-2's renderer (palette_now from the main loop) in 2 frames, 53.10 and 59.29 | 53.08 and 59.27 | 51.82 and 57.98 |
| HUD split past the cut-off (70.84) | 1-1, 5-3, 6-3 one frame each (the same frames as Original) | the same | the same |
| Largest normal-frame split entry | 70.554 (5-3) | 70.554 | |
| Largest shift against Original, normal frames | +0.600 line (5-2 frame 1435) | +0.565 | |
| 1-1 frame 2844 (a load frame past the cut-off in Original, 74.50) | 78.75 | 78.33 | |

The worst upload end grows by 0.34 line in 1-1 (the override loop) and by
0.04 elsewhere (the loop choice); the HELL record's limit was "none after
line 22" (the display starts about 22.8 lines after the interrupt). Stage
loads from Level Select after the mode has settled
(`gb-palette/entry_timing.py`, all 22, 60 frames after): the same number of
vblanks as Original and as `all-palettes` HELL in every entry; worst upload
end 19.97 (1-1; `all-palettes` 19.77, Original 16.58); no upload after
line 22; 4-3's split entry past the cut-off in all three (Original 74.86,
HELL 75.24 on both builds), no other.

### Menu, boot, stack

- `scripts/check_boot.py`: passed (idle frames 1-899 identical to the
  original, 136 distinct screens, first 1-1 update at frame 163 when mashing
  Run, defaults English, Enhanced, damage on).
- `scripts/check_menu.py` (all parts, music as played; its HELL expectation
  now takes the visible stage's override): **passed**. runs: 140 openings in
  the 11 runs, all exact; sweep: 1,393 Select presses, 726 opened and exact,
  1 opened and differing only by the timer phase (1-1 2829, the one the
  `all-palettes` record lists), 572 refused, 94 not seen; select: all 22
  Level Select entries and Run on the next; options: every row and every
  palette path and cancel case passed (HELL from 1-1 shows exactly the D
  table with the override).
- Stack (`all-palettes/stackguard.py`, HELL, the 11 runs with their stage
  loads): low-water marks equal to `all-palettes`' in every run, lowest
  `$21C2` (5-4); the menu checks `$21C5` at the deepest; the watched margin
  `$2105-$213F` is never reached. The override loops call nothing.

### Screenshots

Private, `build/hell-1-1/shots/` (`shots11.py`, HELL, the same frames on
`all-palettes` and on the candidate; sheets `sheet-1-1.png`, `sheet-2-2.png`,
`sheet-other.png`, `sheet-popup.png`, `sidewalk-vs-bridge.png`): 1-1 frames
98 (start), 1378 (brick), 2723 (skyline); 2-2 frames 60, 1224, 2768 (areas
0-2); 2-1 (Level Select, 300 frames holding right); 4-1 600; 5-3 3000; the
popup in 1-1, 2-2 and 5-3 (PALETTE reads HELL, `$2100` = `$18`). By eye: 1-1's
low wall, pillars, sidewalk and street are in 2-2's bridge and column
golds and no crimson is left in the sidewalk or the skyline (the skyline's
shadow faces are dark gold-brown, the lit faces gold); brick and the windows
stay red. Colours counted in the pictures: 1-1 wall and sidewalk 320 44%,
210 20%, 420 11%, 100 6%, 430 5%; 2-2 bridge and columns 110 26%, 320 17%,
420 11%, 410 6%, 210 3%. The same family; 2-2's darkest large shade is the
olive 110 where 1-1's is 210. 2-2 keeps its crimson ridge; 2-1's walls are
gold; 4-1's water is brown where it was red.

### ROM-free

`python3 -m unittest discover -s tests` (46 tests: the D table, the
override's data checks and equates) and `scripts/audit_public.py`: pass.

## Rerunning

From the repository root, `W=build/hell-1-1` holding `original.pce`,
`seed.state`, `h1.pce` (the candidate), `ap.pce` (`all-palettes`), `d.pce`,
`rec/ap-*` (the `all-palettes` recordings), the emulator environment of
`run-check.sh`, `GB_WORK=$W NES_WORK=$W` and `NG_DEBUGGER_FAST=1`:

```sh
H=research/tools/hell-1-1; S=research/tools/sms-palette; G=research/tools/gb-palette; R=research/tools/hell-palette
python3 $S/runmany.py $W/rec/log h1-orig 4 all $PWD/$H/record11.py $W/h1.pce {run} $W/rec/h1-orig-{run}.json 0
#   and h1-nesa 0x08, h1-nesb 0x28, h1-gb 0x10, h1-sms 0xb8, h1-hell 0x18
python3 $S/analyse.py $W/rec identity ap-orig h1-orig          # and nesa, nesb, gb, sms
python3 $S/analyse.py $W/rec due h1-hell h1-orig
python3 $R/runall.py timing_trace.py $W/h1.pce $W/tt h1-hell 0x18 4   # and ap-hell (ap.pce), h1-orig 0
python3 $G/split.py $W/tt h1-orig h1-hell; python3 $G/updates.py $W/tt h1-hell $W/tt h1-orig
python3 $G/entry_timing.py $W/h1.pce 0x18 60 0,1,...,21 $W/entry-h1-hell.json 30   # and 0; ap.pce 0x18
python3 $H/unittest_override.py $W/h1.pce 300 22               # NO_OVERRIDE_MODEL=1: control
python3 $H/stagestarts11.py $W/h1.pce 0x18 120 all
python3 $H/pixshare.py $W/ap.pce $W/h1.pce 2-2 0x18; python3 $H/pixshare.py $W/d.pce $W/h1.pce 2-2 0x18
python3 $H/upload_cost11.py $W/h1.pce 0x18 0                    # and 3; ap.pce 0
python3 $H/census.py $W/d.pce 0x18 094 15 run:1-1 ls:0:900 ...
python3 research/tools/all-palettes/stackguard.py $W/h1.pce 0x18
FREEWATCH_FLAGS=0x18 python3 $G/freewatch.py $W/ap.pce 1-1 87b4a 87bff
python3 $H/shots11.py $W/h1.pce $W/shots h1-hell 0x18 run:1-1:98 run:1-1:600:menu run:2-2:60 ls:2:300 ...
python3 scripts/check_boot.py --emulator $E --original $W/original.pce --candidate $W/h1.pce --output $W/boot-h1
python3 scripts/check_menu.py --emulator $E --original $W/original.pce --candidate $W/h1.pce --output $W/menu
```

## Not covered

Real hardware; listening to the sound; whole cinemas, the title, the
ending, Continue and Game Over in HELL; the owner's review of the colour
choice (210 against 110, `choose-094.png`). Candidate D changes 4-1's water
(about 16% of its picture) and the indoor stages' walls, as the tuning study
showed; those are D's, reviewed on the tuning sheets, not here.
