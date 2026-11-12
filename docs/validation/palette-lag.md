# Palette modes and game timing (lag frames)

Emulator evidence only (headless Geargrafx `78fc3d7`, `NG_DEBUGGER_FAST`), no
real-hardware data. Tool: `scripts/palette_lag.py`. Rerun:

    python3 scripts/palette_lag.py survey        # 11 runs x 9 variants -> /workspace/build/palette-lag/traces
    python3 scripts/palette_lag.py report        # the table below, one row per run x variant
    python3 scripts/palette_lag.py margin 3-2 sms 1023 14   # per-update busy time and margin before vblank

## Method

One fresh session per (run, variant): load one start state made from the
original ROM, then either enter the stage with the Level Select code path
(`start_stage`: original ROM, 1.10, 1.11-dev "nomenu") or through the in-game
menu with the palette set as the video scripts do (`palette_video.enter_stage`,
six modes of 1.11-dev (apocalypse, reset 2), SHA-256 cec5f7b3...8059). The
stored input is replayed one `debug_step_frame` per frame plus a 60-frame
idle tail. The game-update counter is RAM `$2000` (CPU zero page `$00`): it
increments once per main-loop update. A lag frame is a frame step in which it
did not advance (delta 0); delta 2 = a catch-up. Vblank handler `INC $12` is at
`$FD1F`, the wait routine's `STZ $12` at `$FD67` (`STZ`, then spin until `$12 >= 1`): an update that has not
reached the `STZ` when the next vblank fires loses the whole next frame.

## Results (verified)

Every one of the 11 runs x 9 variants was replayed. Original ROM, published
1.10, 1.11-dev without the menu, and 1.11-dev ORIGINAL through the menu are
identical frame for frame in every gameplay field (SAT hash, Ryu, timer,
camera, health, lives, stage, area, update-counter deltas) over all 11 runs
(only the absolute counter value differs for the menu route: the menu path
starts later). So 1.11 ORIGINAL is not slower than 1.10 or the unpatched game
in any stored run. Every run finishes its stage in all builds.

Lag frames that occur identically in all builds (native game lag: loads, area
changes, end-of-stage fade steps every 8th frame): 1-1 8, 2-2 12, 3-1 8, 3-2 8,
4-1 12, 4-2 8, 5-2 17, 5-3 25, 5-4 0, 6-1 8, 6-3 16 (counted up to the
stage-end flag; see the first-lag columns of `report` output).

Differences in the four mapped modes (APOCALYPSE and NES-A/NES-B/GB DMG/SMS
only where listed; ORIGINAL = reference):

| run | SMS | GB DMG | NES-A | NES-B | APOCALYPSE |
|---|---|---|---|---|---|
| 3-2 | lag at 1033 and 1104, one update behind from 1032 on, never recovers (run ends 1 step short of the stage-end flag) | same | same | same | identical to ORIGINAL |
| 4-1 | identical until frame 2488 (first tail frame after the input ends = stage-clear transition): that frame delta 0, next delta 2, re-synchronised | same | identical | identical | same as SMS |
| 5-3 | same pattern at 6769 | same | identical | identical | same |
| 6-3 | same pattern at 5123 | same | identical | identical | same |
| 1-1, 2-2, 3-1, 4-2, 5-2, 5-4, 6-1 | identical | identical | identical | identical | identical |

Note NES-A/B drift only in 3-2 and APOCALYPSE only at the three stage-clear
transitions; SMS and GB DMG do both. Transition frames: `master` flag set, the
fade begins (VCE changes of 165/347 words on 5-3 6769/6770 in GB DMG).

## 3-2 frame 1032 (reproduced)

Update counter / `$12` after each frame step, ORIGINAL vs SMS (GB DMG, NES-A,
NES-B identical to SMS):

    frame  ORIGINAL c,$12   SMS c,$12
    1031   211,0            211,0
    1032   212,0            212,1     (hp 10->9 in both: damage update ran, $12 left set)
    1033   213,0            212,0     <- no update completed: lag frame
    1034   214,0            213,0     one update behind from here
    1103   27 ,0            26 ,1     second lag at 1104 (Ryu pressing II)
    1104   28 ,0            26 ,0

Also in the original ROM and 1.10 the 1032 frame is the busiest of the area.

## Margin (3-2, frames 1023-1037, constant input `right`; verified)

Per update: master clocks (1365 = one line; frame 358,995) from the waking
vblank (`INC $12`) to the update's `STZ $12`, and clocks left before the next
vblank. Update that handles frame 1032 (damage, counter 212 in ORIGINAL/208 offset):

| build / mode | busy (clk / lines) | left before vblank |
|---|---|---|
| original ROM / 1.10 / 1.11 nomenu / 1.11 ORIGINAL / APOCALYPSE | 339.7k-339.9k / 249 | +19.6k to +19.8k (14.5 lines) |
| SMS | 352,467 / 258.2 | -1,434 (-1.1 lines) OVERRUN |
| GB DMG | 352,320 / 258.1 | -1,293 OVERRUN |
| NES-A, NES-B | 352,329 / 258.1 | -1,302 OVERRUN |

All other updates in the window are within a few hundred clocks of ORIGINAL
(busy +10-130 clk, noise of the interrupt phase), i.e. the extra cost is
about 12,500 master clocks (about 4,200 CPU cycles, 9 lines) on that update
only. The same update in ORIGINAL had 14.5 lines of slack, so the mapped modes
cross the vblank by about one line. The 1104 lag was not measured (the input
changes at 1103; see below). The 3-2 damage frame is also the one that has the
least slack (14.5 lines) of any frame in 1023-1037 of ORIGINAL.

## Characterisation

Frame 1032 is the frame Ryu is hit (health 10 to 9, knockback, hurt state).
Palette writes: the VCE content does not change on frames 1032/1033/1103/1104
(0 words changed) in any mode and NES modes change the VCE 0 times in the
whole run (14 SMS, 24 ORIGINAL, 69 APOCALYPSE frames of 3197 change it), yet
NES-A/B lag too: so the extra ~12,500 clocks are not explained by VCE changes.
Inference (not verified): NES modes use the unmapped palette path, so the cost is probably elsewhere in the shared
hook code run on damage (not diagnosed here). The three stage-clear
laggards coincide with the stage-clear fade start (palette writes: yes on 5-3
GB DMG, 165 words at 6769, 347 at 6770), but 4-1 and 6-3 show no VCE change at
that frame.

## Not measured

- The margin of the 1104 lag (input changes there; the margin harness holds one
  input) and of the stage-clear frames 2488 / 6769 / 5123.
- Which code costs the extra clocks (not diagnosed).
- Other stored routes: `research/palette-video/2-2-firewheel.json` (NES Firewheel option) not run.
- Real hardware; audio.
