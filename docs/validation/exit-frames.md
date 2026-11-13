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
     `$840A`, the two transfers) happens R clocks later. R was 0.7 to 2.3
     lines in 2-2, 4-1, 5-2, 6-2, 6-3 and 15-17 lines in 5-3, and 94 lines at
     5-3 a6 (the castle renderer's full redraw, 69.5 lines in RAM block
     transfer routines). So the build's split is late where the original's
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
   shifts the native work by about 1.3-2 lines.

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
unmodified ROM's four cases overlap the interrupt by 3-5 lines (likely on a
console too, medium-high confidence); the build's 5-3 a5 case by ~1.6 lines
(medium) and the build's 6-3 a1 escape by 0.3 line (low: a console could go
either way). It is a whole-frame-buffer effect of per-line rendering, not
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
| 5-3 a6 80,884 | 48.171-62.015 / 62.203-69.137 / **69.137** | 142.072-155.257 / 156.104-163.032 / 64.008 | 93.9 |
| 6-3 a1 94,458 | 47.194-61.037 / 61.225-68.159 / **68.159** | 50.017-63.207 / 64.204-71.132 / 63.299 | 2.5 |
| 6-3 a3 96,623 | 47.309-61.152 / 61.340-68.274 / **68.274** | 49.301-63.144 / 64.132-71.060 / 63.297 | 2.0 |

(Dots run 0-341 per line; 1,365 master clocks a line. 4-1 a1's first TAI
starts on the same line on both: the transfers move by R exactly.)

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

TABLE

## Which build introduced it

HISTORY

## Hardware visibility

HARDWARE

## Fix proposals (not implemented)

FIXES

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
