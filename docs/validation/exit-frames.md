# Exit frames: the old area's last picture before an area change's black

Question (from `start-align`): at ten area changes the build and the
unmodified ROM show different pictures on the last 1-3 frames of the OLD
area before the transition black, although game RAM is equal on both ROMs.
Why, which side moves, which build introduced it, would a console show it,
and what is the smallest fix that makes the build show what the unmodified
ROM shows? Owner: "all stages and all substage/middle phases should have the
backgrounds be perfectly aligned. to the original".

Emulator evidence only (Geargrafx 78fc3d7, the in-process core of
`load-exact` with VDC state read out per instruction). No real-hardware
data. Nothing in `src/` was touched.

## Answer

Two unrelated things were mixed in the `start-align` notes:

1. **The backdrop differs in every frame of the old area, not only at the
   exit** (measured). The survey's window began 4 frames before the event,
   so the old area's "last 1-3 frames" were simply all the old-area frames it
   captured. Widening the window to 40 frames before the event: in 9 of the
   12 events every one of those 37-39 old-area frames differs by the same
   amount (2-2 a1 10,077-10,465 px, 4-1 a1 1,158-1,917, 5-2 a2 4,668, 5-3 a1
   796-832, a2 586-600, a3 337-356, a4 3,922-3,927, 6-3 a1 4,295-4,364;
   2-2 a2 9,096-9,244), with every scanline's latched BXR and BG Y offset
   equal on both ROMs. With SMOOTH PARALLAX OFF (options bit 0) none of these
   frames differs at any of the 26 area changes. This is the Enhanced
   backdrop sitting where its own parallax put it, against the native
   screen-locked one: the design of smooth parallax, not an exit effect.
   It is out of scope here (see "Not covered").
2. **One frame per area change can show the whole playfield shifted
   vertically: the area change's first update, where the split interrupt is
   delayed by a native block transfer** (measured). That frame (the update
   that runs `$8490`/`$849B` and sets `$2E63 = $0A`, 2-3 frames before the
   event) saves the RAM palette and blacks it out with two native block
   transfers that cannot be interrupted: `TII $2286,$2686,$0400` at bank 0
   `$F718` (called from bank 1 `$8420`; 18,483 master clocks = 13.5 lines)
   and the RAM routine `TAI $2284,$2286,$0200` at `$2205` (from `$F26F`,
   called at `$8429`; 9,267-9,291 clocks = 6.8 lines). When those 20.3
   lines cover the playfield split's raster interrupt (RCR `$6F`, asserted at
   scanline 63, dot ~297), the handler (`$FD26`) runs only after the
   transfer, so `BYR`/`BXR` are written k lines late: those k lines keep the
   HUD's scroll (BG Y 256..., BXR 0), the playfield starts k lines lower and
   its bottom k lines are cut. The HUD and sprites do not move.

   - **The unmodified ROM does this itself** at 4 of the 26 area changes of
     the playthrough: 2-2 a1 (3 lines), 5-3 a6 (5), 6-3 a1 (4), 6-3 a3 (4).
   - **The build runs the same native code later in the frame**: the Enhanced
     wrapper at `$8457` (`jsr $FE40`: the early hook's 19 saved zero-page
     bytes, the renderer lookup, and with SMOOTH PARALLAX ON the renderer
     itself) runs before the rest of the gameplay update, so every native
     action after it (the exit test `$84AB`, the transition `$8490`,
     `$840A`, the two transfers) happens R later. R was 1.3-1.4 lines in
     2-1, 4-3, 6-2 (no Enhanced renderer: the wrapper alone), 1.6-2.5 in
     2-2, 4-1, 5-2, 6-3, 16.0 in 5-3, and 93.7 at 5-3 a6 (the castle
     renderer's full redraw, 69.5 lines of it in RAM block-transfer
     routines). So the build's split is late where the original's
     is not (5-3 a5, 1-2 lines), on time where the original's is late (5-3 a6,
     6-3 a1, 6-3 a3) and late by a different amount (2-2 a1: 5 lines against
     3).
   - So **the original "moves"** (its one-frame playfield drop is real
     behaviour of the unmodified game) and **the build fails to reproduce
     it**, and once (5-3 a5) adds one the original does not have. RAM is
     equal because the game state is equal; only the raster time of the
     native work differs.

   These are the five frames with a scroll difference among the 26 area
   changes (ON): 14,028, 80,627, 80,884, 94,458, 96,623. With SMOOTH PARALLAX
   OFF four remain (14,028 4 lines late, 80,884 on time, 94,458 5 lines late,
   96,623 6 lines late, against 3, 5, 4, 4): the wrapper alone already
   shifts the native work by 1.2-1.4 lines.

Introduced by: the gameplay-loop hook at bank 1 `$8457` (`jsr $FE40`, the
Enhanced renderer before the native update). Its bytes are the same in
1.09, every 1.10 candidate, published 1.10 and all four 1.11-dev builds
checked. Measured: published 1.10, palette timing 2 (first five area changes
only), palette timing 3 and the current build all show the same pattern as
far as each was measured (table below); none of the palette or load timing
changes introduced or removed it.

Real console (inferred, emulator evidence only): HuC6280 block transfers do
not take interrupts until they finish, and the VDC latches a BYR written
after a line's latch point on the next line, so a console would show the
same kind of one-frame drop of the playfield. Whether a given exit shows it
depends on the native update's raster time to within a line: the
unmodified ROM's four cases overlap the interrupt by 3.1-5.5 lines (likely
on a console too, medium-high confidence); the build's 5-3 a5 case by 1.9
lines (medium); the build's 6-3 a1 escape is 0.26 line (low: a console could
go either way). It is a whole-frame-buffer effect of per-line rendering, not
an artefact of how the emulator samples the frame.

Fix, in short: the only way to show exactly the original's frame is to make
the native gameplay update run at the original's raster time, which means
moving the Enhanced per-frame work out from in front of it (proposal 3,
large). Cheaper proposals remove the build's own late splits but cannot
reproduce the original's. Recommended now: record it as a known one-frame
deviation (proposal 1); if the owner wants the build never to add a drop the
original does not have, proposal 2. Details below.

## Settings

- Build: `/workspace/roms/Ninja Ryukenden - Enhanced v1.11-dev (apocalypse, reset 2, palette timing 3, original load timing).pce`
  (SHA-256 `27d1eaa0...dcf0`, the `start-align` build), modes `original`
  (options `0x00`, SMOOTH PARALLAX ON) and `parallax-off` (options `0x01`),
  English, backup RAM with the settings entry (`pe.W`).
- Unmodified ROM: `/workspace/DO_NOT_COMMIT_ROMS/Ninja Ryukenden (J).pce`,
  no backup RAM, English through the title shortcut (`lx.boot`,
  `unmod-en`).
- Other builds: published 1.10 (`... v1.10.pce`, no backup RAM, mode `none`)
  and palette timing 3 (`original`) on `research/longplay/full-exact.json`;
  palette timing 2 (`original`) on `research/longplay/full.json`, area
  changes before 51,760 only (where it leaves that recording, see
  `palette-exact.md`). On `full-exact.json` the area changes after the 5-4
  load are one frame later than on `full-load.json`; each run's own
  transition-start frame was used, and Ryu's position `$2E81/$2E82` and the
  camera at that frame were checked equal to the build's for all 26 (1.10,
  pt3) and 5 (pt2) events.
- Recording `research/longplay/full-load.json` for the unmodified ROM and
  the build (as `start-align`), one fresh power-on and one pass per run.
- Per frame in each window (`research/longplay/exitframes/probe.py`):
  picture; every instruction that writes VDC register 7 (BXR) or 8 (BYR),
  with PC, bank, value, scanline (`vpos`) and dot (`hpos`) before it; per
  scanline the latched BXR and BG Y offset the line was drawn with; hits of
  the IRQ1 vector, split, BYR store `$FD3B`, `$8490`, `$F718`, the vblank
  handler; RAM writes to `$2E4B-$2E4E`; meta (camera, `$2E4B-$2E4E`,
  `$2E63`, stage, area, counter, `$2258`, Ryu `$2E81/$2E82`). Per-instruction
  traces of the transition-start frame of the 12 events on both ROMs
  (`trace.py`, from a state saved 40 frames before the event and replayed
  with the recording's inputs; its IRQ entry scanlines match the probe's).
- Windows: the 12 events EV-40..EV+6; all 26 area changes EV-6..EV+2
  (EV-8..EV+4 for the `full-exact`/`full.json` runs).
- `vpos` is the VDC's line counter; picture row = vpos - 14. The split's
  BYR store lands at scanline 64 when on time (dot 17-23 normally).

## Mechanism, with trace evidence

Gameplay update order (bank 1 `$8457-$8498`, unmodified ROM): `jsr $E3F2`,
`jsr $ABD7`, `$9B95`, `$8DD7`, `$AAE1`, `$CED7`, `$9C53`, `$A400`, `$A2C2`,
`$8097`, then `$8485` `jsr $84AB` (Ryu inside the exit box) -> `$8490`
(`inc $2E60`) -> `$8503` -> `$840A` (`$2E63 = $0A`, `$9C0A`, `$A3C9`,
`$A2A7`) -> `$8420 jsr $F718` (TII, palette to its backup `$2686`) ->
`stz $2284/$2285` -> `$8429 jsr $F26F` (fills colours 0-255 of `$2286` with
`$2284/$2285` through the RAM `TAI` at `$2205`, queues the upload) ->
`$83C3`. The build replaces `$8457-$845C` with `jsr $FE40` + 3 NOPs; `$FE40`
makes the two calls, saves 19 zero-page bytes, runs the renderer
(`$FE00` -> lookup -> renderer bank) and restores them. Everything after it
runs R master clocks later.

Transition-start frame, block transfers and IRQ1 entry (trace, scanline.dot
before the instruction; the IRQ normally enters at 63.297):

| Event | Unmodified: TII / TAI / IRQ1 | Build ON: TII / TAI / IRQ1 | Shift R (lines) |
| --- | --- | --- | --- |
| 2-2 a1 14,028 | 46.040-59.225 / 60.072-67.006 / **67.006** | 48.076-61.267 / 62.123-69.057 / **69.057** | 2.1 |
| 2-2 a2 14,668 | 19.233-33.076 / 33.264-40.192 / 63.297 | 21.290-35.133 / 35.321-42.249 / 63.299 | 2.0 |
| 4-1 a1 55,307 | 19.330-33.173 / 34.020-40.289 / 63.298 | 21.202-35.045 / 35.234-42.162 / 63.299 | 1.6 |
| 5-2 a2 75,456 | 25.225-39.069 / 39.257-46.185 / 63.297 | 27.144-40.328 / 41.175-48.103 / 63.297 | 1.8 |
| 5-3 a1 77,970 | 24.293-38.136 / 38.324-45.252 / 63.297 | 40.279-54.122 / 54.310-61.238 / 63.303 | 16.0 |
| 5-3 a2 78,666 | 23.189-37.033 / 37.221-44.149 / 63.297 | 39.180-53.024 / 53.212-60.140 / 63.298 | 16.0 |
| 5-3 a3 79,285 | 25.175-39.018 / 39.207-46.135 / 63.297 | 41.163-55.006 / 55.195-62.123 / 63.300 | 16.0 |
| 5-3 a4 80,294 | 24.133-37.318 / 38.165-45.093 / 63.300 | 40.127-53.312 / 54.159-61.087 / 63.300 | 16.0 |
| 5-3 a5 80,627 | 36.078-49.263 / 50.110-57.038 / 63.298 | 52.073-**65.264** / 66.245-73.173 / **65.264** | 16.0 |
| 5-3 a6 80,884 | 48.171-62.015 / 62.203-69.137 / **69.137** | 142.072-155.257 / 156.104-163.032 / 64.008 | 93.7 |
| 6-3 a1 94,458 | 47.194-61.037 / 61.225-68.159 / **68.159** | 50.017-63.207 / 64.204-71.132 / 63.299 | 2.5 |
| 6-3 a3 96,623 | 47.309-61.152 / 61.340-68.274 / **68.274** | 49.301-63.144 / 64.132-71.060 / 63.297 | 2.0 |

(Dots run 0-341 per line; 1,365 master clocks a line. The two transfers
take the same 13.5 + 6.8 lines on both ROMs; only their start moves, by R.)

In the 5-3 a6 frame the build spends, before the native work, 6.0 lines in
renderer bank `$7C` `$4Bxx`, 14.1 lines in `$4Axx` and 69.5 lines in RAM
code at `$20xx` (the castle module's block-transfer routines): the
renderer's full redraw on that update. The rest of the native update costs
exactly the original's clocks (same per-routine sums: bank 7 `$60xx` 16,248,
`$61xx` 4,833, bank 1 `$9Cxx` 5,862, ...).

Per-line scroll on 5-3 a6, frame 80,884, scanlines 64-71 (BXR, BG Y):

```
unmodified  64:(0,255) 65:(0,256) 66:(0,257) 67:(0,258) 68:(0,259) 69:(0,260) 70:(185,1) 71:(185,2)
build       64:(0,255) 65:(185,1) 66:(185,2) 67:(185,3) 68:(185,4) 69:(185,5) 70:(185,6) 71:(185,7)
```

The unmodified ROM's split BYR store executes at 69.198 (normally 64.017-
64.023); the build's at 64.069. Every other scanline of that frame and both
neighbouring frames are equal.

## All 26 area changes

Transition-start frame (first frame with `$2E63 = $0A`) of every surveyed
area change. Cells: the split's BYR store as scanline.dot (on time =
64.017-64.023; **late** = a later scanline), and in brackets the scanline at
which the native palette save (TII `$F718`) starts. The unmodified ROM's
split is late exactly when that TII starts between about scanline 43.5 and
63.9, i.e. when the 20.3 lines of the two transfers cover the interrupt at
63.297. ON / OFF = the current build with SMOOTH PARALLAX on / off, same
recording and frame as the unmodified ROM; 1.10 and pt3 on
`full-exact.json`, pt2 on `full.json` (first five only), at their own
transition-start frame (the same frame up to 5-3; one later from 6-2 on), with
Ryu's position and the camera equal to the build's in every row. Last
column: differing pixels of that frame against the unmodified ROM; `S` = some
visible scanline's latched BXR or BG Y differs (the drop); without `S` the
difference is the parallax backdrop of finding 1.

| Event | Area | Start frame | UNMOD | ON (new) | OFF (new) | 1.10 | pt3 | pt2 | px vs UNMOD, ON / OFF (S = scroll differs) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 11343 | 2-1 a1 | 11340 | 64.022 (TII 31.8) | 64.022 (TII 33.2) | 64.022 (TII 33.1) | 64.022 (TII 33.1) | 64.022 (TII 33.2) | 64.018 (TII 33.3) | 0 / 0 |
| 12421 | 2-1 a2 | 12419 | 64.019 (TII 25.6) | 64.018 (TII 26.9) | 64.018 (TII 26.9) | 64.017 (TII 26.9) | 64.019 (TII 26.9) | 64.018 (TII 27.1) | 0 / 0 |
| 12546 | 2-1 a3 | 12543 | 64.018 (TII 21.6) | 64.018 (TII 22.9) | 64.018 (TII 22.9) | 64.017 (TII 22.9) | 64.019 (TII 22.9) | 64.018 (TII 23.1) | 0 / 0 |
| 14030 | 2-2 a1 | 14028 | 67.067 **late** (TII 46.0) | 69.118 **late** (TII 48.1) | 68.162 **late** (TII 47.2) | 68.194 **late** (TII 47.3) | 68.200 **late** (TII 47.3) | 68.257 **late** (TII 47.5) | 24846 S / 18571 S |
| 14671 | 2-2 a2 | 14668 | 64.018 (TII 19.5) | 64.019 (TII 21.7) | 64.019 (TII 20.9) | 64.018 (TII 21.7) | 64.019 (TII 21.7) | 64.020 (TII 21.9) | 9244 / 0 |
| 55309 | 4-1 a1 | 55307 | 64.018 (TII 19.8) | 64.019 (TII 21.4) | 64.018 (TII 21.1) | 64.018 (TII 21.4) | 64.019 (TII 21.4) | - | 1685 / 0 |
| 55429 | 4-1 a2 | 55426 | 64.020 (TII 14.3) | 64.017 (TII 16.5) | 64.020 (TII 15.6) | 64.017 (TII 16.5) | 64.017 (TII 16.5) | - | 0 / 0 |
| 60708 | 4-3 a1 | 60706 | 64.020 (TII 20.3) | 64.020 (TII 21.6) | 64.019 (TII 21.6) | 64.019 (TII 21.6) | 64.020 (TII 21.6) | - | 0 / 0 |
| 61795 | 4-3 a2 | 61793 | 64.020 (TII 18.8) | 64.018 (TII 20.1) | 64.018 (TII 20.0) | 64.018 (TII 20.1) | 64.018 (TII 20.1) | - | 0 / 0 |
| 63544 | 4-3 a3 | 63542 | 64.018 (TII 28.2) | 64.021 (TII 29.5) | 64.019 (TII 29.5) | 64.018 (TII 29.5) | 64.019 (TII 29.5) | - | 0 / 0 |
| 74531 | 5-2 a1 | 74528 | 64.020 (TII 28.5) | 64.022 (TII 30.9) | 64.020 (TII 29.8) | 64.022 (TII 30.9) | 64.022 (TII 30.9) | - | 0 / 0 |
| 75459 | 5-2 a2 | 75456 | 64.018 (TII 25.5) | 64.018 (TII 27.3) | 64.018 (TII 26.8) | 64.018 (TII 27.3) | 64.018 (TII 27.3) | - | 4668 / 0 |
| 76157 | 5-2 a3 | 76155 | 64.020 (TII 21.9) | 64.020 (TII 24.3) | 64.019 (TII 23.2) | 64.020 (TII 24.3) | 64.020 (TII 24.3) | - | 0 / 0 |
| 77972 | 5-3 a1 | 77970 | 64.017 (TII 24.7) | 64.023 (TII 40.7) | 64.020 (TII 26.0) | 64.019 (TII 40.7) | 64.023 (TII 40.7) | - | 796 / 0 |
| 78669 | 5-3 a2 | 78666 | 64.018 (TII 23.4) | 64.018 (TII 39.4) | 64.019 (TII 24.7) | 64.019 (TII 39.4) | 64.018 (TII 39.4) | - | 590 / 0 |
| 79287 | 5-3 a3 | 79285 | 64.018 (TII 25.4) | 64.020 (TII 41.3) | 64.018 (TII 26.6) | 64.020 (TII 41.3) | 64.020 (TII 41.3) | - | 337 / 0 |
| 80296 | 5-3 a4 | 80294 | 64.020 (TII 24.2) | 64.021 (TII 40.2) | 64.021 (TII 25.5) | 64.020 (TII 40.2) | 64.021 (TII 40.2) | - | 3926 / 0 |
| 80630 | 5-3 a5 | 80627 | 64.018 (TII 36.1) | 65.325 **late** (TII 52.0) | 64.017 (TII 37.4) | 65.325 **late** (TII 52.0) | 65.325 **late** (TII 52.0) | - | 23993 S / 0 |
| 80887 | 5-3 a6 | 80884 | 69.198 **late** (TII 48.3) | 64.069 (TII 142.1) | 64.020 (TII 49.7) | 64.045 (TII 142.0) | 64.069 (TII 142.1) | - | 30735 S / 30735 S |
| 90754 | 6-2 a1 | 90751 | 64.018 (TII 27.5) | 64.018 (TII 28.8) | 64.018 (TII 28.8) | 64.019 (TII 28.8) | 64.018 (TII 28.8) | - | 0 / 0 |
| 91716 | 6-2 a2 | 91714 | 64.018 (TII 39.0) | 64.020 (TII 40.3) | 64.021 (TII 40.3) | 64.019 (TII 40.3) | 64.019 (TII 40.3) | - | 0 / 0 |
| 91820 | 6-2 a3 | 91817 | 64.018 (TII 15.1) | 64.017 (TII 16.4) | 64.020 (TII 16.3) | 64.020 (TII 16.4) | 64.017 (TII 16.4) | - | 0 / 0 |
| 92931 | 6-2 a4 | 92928 | 64.019 (TII 21.6) | 64.018 (TII 22.9) | 64.018 (TII 22.9) | 64.018 (TII 22.9) | 64.018 (TII 22.9) | - | 0 / 0 |
| 94460 | 6-3 a1 | 94458 | 68.221 **late** (TII 47.4) | 64.019 (TII 49.9) | 69.314 **late** (TII 48.6) | 64.019 (TII 49.9) | 64.019 (TII 49.9) | - | 33893 S / 28734 S |
| 94579 | 6-3 a2 | 94576 | 64.020 (TII 22.1) | 64.020 (TII 24.0) | 64.019 (TII 23.3) | 64.020 (TII 24.0) | 64.020 (TII 24.0) | - | 0 / 0 |
| 96625 | 6-3 a3 | 96623 | 68.336 **late** (TII 47.8) | 64.017 (TII 49.7) | 70.086 **late** (TII 49.0) | 64.017 (TII 49.7) | 64.017 (TII 49.7) | - | 22701 S / 19809 S |

Summary (transition-start frame, 26 area changes):

| ROM | Late splits | Same scroll as the unmodified ROM on all lines |
| --- | --- | --- |
| Unmodified | 4: 2-2 a1 (3 lines), 5-3 a6 (5), 6-3 a1 (4), 6-3 a3 (4) | - |
| Build, SMOOTH PARALLAX ON | 2: 2-2 a1 (5), 5-3 a5 (1-2) | 21 of 26 |
| Build, SMOOTH PARALLAX OFF | 3: 2-2 a1 (4), 6-3 a1 (5), 6-3 a3 (6) | 22 of 26 |
| Published 1.10 | 2: 2-2 a1 (4), 5-3 a5 (1-2) | 21 of 26 by split position |
| Palette timing 3 | 2: 2-2 a1 (4), 5-3 a5 (1-2) | 21 of 26 by split position |
| Palette timing 2 (first five) | 1: 2-2 a1 (4) | 4 of 5 by split position |

The native work's shift (TII line, build minus unmodified): 1.3-1.4 lines
in stages without an Enhanced renderer (2-1, 4-3, 6-2: the wrapper and
the lookup), 1.6-2.5 in 2-2, 4-1, 5-2, 6-3, 16.0 in 5-3, 93.7 at 5-3 a6
(full castle redraw on that update). With SMOOTH PARALLAX OFF: 1.2-1.4
lines everywhere (5-3 1.3). Per-routine clock sums before the TII (trace,
12 events) are equal on both ROMs for all native code except the routine
the build skips when it renders (bank 1 `$80xx`/`$81xx`, the native
backdrop work behind `$8472`: 48-846 clocks) and a few clocks of VDC
access waits; the rest of the shift is Enhanced code (bank 0 `$FE`/`$FF`
hooks, bank `$46` lookup, renderer banks, RAM routines).

## Which build introduced it

- The cause is the `$8457` hook (`jsr $FE40`): it is in every Enhanced
  build checked (bytes `20 40 FE EA EA EA` in 1.09, the 1.10 candidates 1-5,
  1.10-dev, published 1.10, and the four 1.11-dev builds in
  `/workspace/roms/`). Measured behaviour: 1.10, palette timing 3 and the
  current build put the split on the same scanline at 25 of 26 area changes
  (dots within 4, 24 at 5-3 a6) and the same late/on-time pattern at all 26.
- Palette timing 2 (vblank +228 clocks) moves the native update 0.17 line
  later than 1.10 (TII 33.3 / 27.1 / 23.1 / 47.5 / 21.9 against 33.1 /
  26.9 / 22.9 / 47.3 / 21.7): no change in which exits drop on this route.
  Palette timing 3 and original load timing restored and kept 1.10's
  vblank cost.
- 2-2 a1 is 68.19x in 1.10 / pt3 and 69.118 in the current build. That is
  not new code: pt3 and 1.10 run the 2-2 entry one update longer
  (`load-exact`), and on this frame the native object routine `$ABD7`
  (bank 2 `$ABxx`/`$ACxx`) costs 1,038 clocks less there than in the
  current build and the unmodified ROM (per-routine sums of the traces;
  the current build matches the unmodified ROM's native costs).
- So no palette or load-timing change introduced it; the Enhanced renderer
  hook did, and SMOOTH PARALLAX OFF does not remove it (the wrapper still
  runs first).

## Hardware visibility

Inferred from emulator evidence and the documented hardware behaviour;
nothing measured on a console.

- Block transfer instructions (TII/TDD/TIN/TIA/TAI) do not let an interrupt
  in until they finish; this is the HuC6280 behaviour the project's
  "one 32-byte TIA" rule already depends on (`PARALLAX.md`). A VDC raster
  interrupt asserted during the 20.3 lines of `TII $F718` + `TAI $2205` is
  taken when they end, so the split handler's BYR/BXR stores land late, and
  the VDC applies them from the following line. Lines in between are drawn
  with the HUD's Y counter and BXR 0. Geargrafx renders each line with the
  scroll state latched for it, as the console does: the drop is in the
  picture, not an artefact of how the emulator samples the frame.
- Which exits drop on a console depends on the native update's raster time
  to within a line, i.e. on Geargrafx's cycle timing over the ~45-50 lines
  of the update before the transfer. The unmodified ROM's four drops overlap
  the interrupt by 3.1-5.5 lines (medium-high confidence a console shows
  them on this route). The build's 5-3 a5 drop: the TII ends 1.9 lines
  after the interrupt (medium). The build's 6-3 a1 escape: its TII ends 90
  dots (0.26 line) before the interrupt (low: a console could drop there).
  2-2 a1: both drop; depths 3 against 5 lines could differ by a line on a
  console.
- What a player sees: for one frame, just before the 4-5 black frames, the
  whole playfield (backdrop and foreground, not sprites or HUD) is drawn
  3-5 px lower, with 3-5 lines of other map rows above it. At 60 Hz this is
  a single-frame twitch; easy to miss, visible in a frame-by-frame capture.

## Fix proposals (not implemented)

None implemented. "Exact" below means: the build's split lands where the
unmodified ROM's does at every area change.

1. **Record it, change nothing (recommended now).** The difference is the
   original's own one-frame split drop, which the build reproduces only when
   its native update runs at the same raster time; it does so at 21 of 26
   area changes on this route (22 with SMOOTH PARALLAX OFF). Cost and risk:
   none. Add it to the known deviations with the evidence above; tell the
   owner it is the original glitching, the build not.

2. **Never drop in the build (small, not exact).** In the build's area
   change path only, replace the two uninterruptible transfers by
   interruptible equivalents, so the split is at most one 32-byte block
   late (as the renderers' rule already allows):
   - bank 1 `$8420 jsr $F718` -> `jsr SAVE`: 32 x `TII $2286+32i,$2686+32i,32`
     each followed by `nop` (256 bytes unrolled) + `rts`.
   - bank 1 `$8429 jsr $F26F` -> `jsr FILL`: do what `$F26F` does except the
     RAM `TAI`: set `<$15/<$16 = 0`, `<$17/<$18 = $0100`, `jsr $F350` (queue
     colours 0-255), leave `<$15/<$16 = $2286`, `<$17/<$18 = $0200` and the
     trampoline bytes `$2205-$220B` (`F3 84 22 86 22 00 02`) as the native
     routine leaves them, then 16 x `TAI $2284,$2286+32i,32` + `nop` (128
     bytes) and `rts`. (`$2284/$2285` are zero here: `$8423`/`$8426`.)
   - Only the two 2-byte call operands in bank 1 change (ROM offsets
     `0x2421-0x2422`, `0x242A-0x242B`); about 400 bytes of code in a bank with
     free space and a ~16-byte bank-0 far-call stub (map the bank into
     MPR2 and back, as `lookup_wrapper` does), placed by `project.py`'s
     free-range audit. No new RAM. `$F718` and `$F26F` themselves stay
     native (other callers unaffected).
   - Cost: about +950 CPU cycles (~2.1 lines) in the transition-start
     update only; measured spare time in that update is at least 111,375
     master clocks (82 lines, 5-3 a6 ON) and 233,319 elsewhere, so the
     vblank count should not change (re-run the `load-exact` survey to
     verify). The entry contract check of `EMULATOR.md` (registers, MPRs,
     zero page, RAM equal to the native routines' after the call) applies.
   - Effect on this route: the build's split on time at all 26; matches the
     unmodified ROM at 22 of 26 (today 21; with OFF 22 today); still differs
     at the original's four drops, which the build would then never show.
     Risk: low (one transition frame; palette RAM contents identical).

3. **Run the native update at the original's raster time (exact as far as
   possible, large).** Restore `$8457-$845C` to the original `jsr $E3F2 /
   jsr $ABD7` and call the per-update Enhanced work (`$FE46`, with its
   zero-page save) after the native gameplay update instead, e.g. from the
   end of the update (`$8475 jmp $8485` routed through a stub that runs the
   exit tests `$84AB`/`$84D9` first and renders only on the normal return;
   an area change's first update then skips the renderer: its picture goes
   black on the next vblank). The `$83F3` selector hook and the `$8472`
   late hook would also have to cost what the native code costs, or move.
   Limits and risks:
   - Not cycle-exact in Enhanced stages: with a renderer, the build skips
     the native `$8097` backdrop work at `$8472` (48-846 clocks in these
     frames, state-dependent), so the native update would still be off by up
     to ~0.6 line unless that cost is reproduced. Exact only where the
     original's transfer overlaps the interrupt by more than that (all four
     measured drops: 3.1-5.5 lines).
   - The renderer would read the camera and upload phase tiles later in the
     frame than today (after the whole update instead of after `$E3F2`/
     `$ABD7`): the backdrop/foreground timing that `start-align` verified
     (45 of 48 starts identical), the beam-racing order of uploads and the
     castle/2-2 full-redraw frames all need re-measuring; a camera snapshot
     to keep today's semantics costs cycles before the native code again.
   - Vblank counts: the update plus renderer is the same sum, so the
     `load-exact` counts should hold; verify.
   - Benefit beyond this question: every native raster-timed effect in
     gameplay (not only this exit frame) would happen at the original's
     time.

Overlap with `start-pos` (2-2 area-start backdrop offset, `src/stage22`,
`src/dispatch`): proposal 2 touches neither (bank 1 call operands plus new
code), but competes for free ROM in bank 0 (`src/dispatch` reserves
`$FF2C-$FF6F`; `$FECF-$FEDF` is held for the 1-2 fix) and should be placed
after `start-pos` is merged. Proposal 3 rewrites the `$8457` hook and the
`early`/`multi_late` wrappers in `src/dispatch` and changes when the 2-2
renderer runs, so it directly overlaps `start-pos` and would invalidate its
measurements; it must come after `start-pos` and redo them.

## Not covered

- The backdrop's own parallax difference through each area (finding 1):
  that is the SMOOTH PARALLAX design; aligning it mid-area to the native
  8 px stepped backdrop is a different question.
- Stage loads, death respawns, Continue/Game Over, Level Select entries and
  the cinemas: same mechanism possible wherever native code runs a long
  block transfer near scanline 64 after the `$8457` hook; not surveyed.
- Other routes, speeds and arrival positions (the original's drop depends on
  how much the update did before the exit test), other palette modes and
  languages, 1.09 and earlier (hook bytes checked only).
- Real hardware; a real-time core.
- Audio not compared.

## Commands

```sh
export LD_LIBRARY_PATH=/workspace/build/toolchain/sdl3/lib
cd research/longplay/exitframes
make                                     # libgxe.so in /workspace/build/exit-frames/lib
U="/workspace/DO_NOT_COMMIT_ROMS/Ninja Ryukenden (J).pce"; B=".../...original load timing).pce"
python3 probe.py "$U" unmod-en /workspace/build/exit-frames/p-unmod --states        # 12 events, EV-40..EV+6
python3 probe.py "$B" original /workspace/build/exit-frames/p-new --states
python3 analyze.py /workspace/build/exit-frames/p-unmod /workspace/build/exit-frames/p-new out.json
python3 probe.py "$U" unmod-en DIR --area --pre 6 --post 2                           # all 26 area changes
python3 probe.py "$B" original|parallax-off DIR --area --pre 6 --post 2
python3 probe.py ".../v1.10.pce" none DIR ../full-exact.json --area --pre 8 --post 4
python3 probe.py ".../palette timing 3).pce" original DIR ../full-exact.json --area --pre 8 --post 4
python3 probe.py ".../palette timing 2).pce" original DIR ../full.json --events 11343 12421 12546 14030 14671 --pre 8 --post 4
python3 table.py UNMOD ON OFF V110 PT3 PT2
python3 trace.py "$U" unmod-en p-unmod/ev-80887.state 80847 80884 --save tr.npy     # per-instruction raster trace
```

Each probe is one power-on and one pass over the recording (3-4 minutes).
