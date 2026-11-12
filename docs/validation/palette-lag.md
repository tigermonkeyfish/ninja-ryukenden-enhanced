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

## Diagnosis (palette-lag branch, second worker; emulator evidence)

Tools added to `scripts/palette_lag.py`: `itrace RUN VARIANT START FRAMES OUT`
(every CPU instruction and interrupt of FRAMES frame steps from START, gzip),
`loadtime` (Level Select entry with the mode set and settled 60 updates
before the load; master clock of each sound-driver command call `$38:$4006`
and of the stage's first update `$8457`, per vblank). The vblank interrupt
is taken at master clock 350,895 mod 358,995 (+0-9 jitter); the frame step
of the harness ends at phase 0, i.e. **8,100 clocks after the vblank
interrupt**.

### (a) 3-2 frame 1032: the sound driver, not palette code

Exact accounting from `itrace 3-2 * 1031 3` (each instruction charged its own
clocks; update = waking vblank interrupt entry to `STZ $12`):

| | main loop | waking vblank handler | other IRQs | busy | left before next vblank |
|---|---|---|---|---|---|
| ORIGINAL | 338,943 | 12,519 | 642 | 352,104 | +6,894 |
| 1.10 | 338,919 | 12,291 | 651 | 351,861 | +7,134 |
| NES-A | 339,045 | 20,484 | 639 | overrun | -1.2k |
| SMS | 339,066 | 20,592 | 639 | overrun | -1.4k |

The waking vblank handler by code page: palette code (`$FD13`, banks
`$46`/`$3B`/`$F3xx`) costs the same within ~130 clocks in every mode
(ORIGINAL 111+48 at `$46:$5000`/`$F3-$F4`, NES-A identical, SMS 267); the
whole +7,965 is in the sound driver's tick (`$FD16` -> bank `$38`, pages
`$45-$4F`, e.g. `$46xx` 0 -> 3,393, `$4Fxx` 855 -> 4,194). Main loop +102.

Why the sound tick differs: the sound driver's state (zero page `$83`,
`$3822-$3827`, `$38BB-$38E4` envelope counters) differs from ORIGINAL's at a
fixed point (the `STZ $12` after replay step 500) in the menu routes of
NES-A, NES-B, SMS and GB DMG for 3-2, and equals ORIGINAL's for APOCALYPSE,
1.10 and the unpatched ROM: the music runs one driver tick off for the whole
stage. Cause: after the menu's Run the stage restart issues the music
command (`$38:$4006`, main loop) close to a vblank. ORIGINAL issues it
2,292 clocks before vblank 111 of the route, APOCALYPSE 1,683 before
(-609), SMS 17,511 after it, NES-A 39,015 after it: the extra CPU time between
Run and that call (mapped uploads of the menu preview's left-over queue and
of the restart's palettes in the vblanks; in NES-A the APOCALYPSE preview's
upload and the NES colour-set lookups of the reload) moves the call across
the vblank, so the driver's first tick of the new music comes one vblank
later.

Swap test (menu route of one mode, then `$2100` set to another mode's bits
before frame 0, replay to 1120): SMS route with ORIGINAL bits -> lag at 1033
and 1104; NES-A route with ORIGINAL bits -> lag at 1033 and 1104; ORIGINAL
route with SMS bits ($B8) or GB DMG bits ($10) -> no lag. Level Select entry
(no menu) with each of the six modes set before the load: the sound state at
step 500 equals ORIGINAL's in all six. So in 3-2 the lost frames follow the
route into the stage, not the palette mode played with; the palette modes'
part is the extra CPU time they add before the music command.

### (c) Stage-clear transitions: no lost frame

`itrace 4-1 * 2485 5`: the update woken at frame 2488 has busy 237,561
clocks in ORIGINAL and 260,046 in SMS (APOCALYPSE 260,052), left before the
next vblank 121,434 and 98,952: no update overruns. The SMS/APOCALYPSE
waking vblank handler costs 25,635 clocks (ORIGINAL 3,213): the mapped
upload of the stage-clear fade step. The main loop's update counter
(`INC $00` at `$E06C`, right after the wait) therefore runs after the frame
step's end (vblank + 8,100) instead of before it, so the per-step counter
shows 0 then 2. It is a sampling artefact of the step boundary, not a lost
frame (NES-A/B use the native upload, 3,213 clocks, and show nothing).

### Load timing (Level Select entry, mode set 60 updates before the load)

| stage | mode | music command vs ORIGINAL | first update vs ORIGINAL |
|---|---|---|---|
| 3-2 | APOCALYPSE / SMS | +375 / +198 clk | +5,115 / +5,121 clk (same vblank) |
| 3-2 | NES-A | +5,850 | 0 |
| 1-1 | APOCALYPSE / SMS | +357 / +213 | +5,220 / +5,100 |
| 1-1 | NES-A | +5,322 | 0 |

With the mode set just before the load (no settling) the mapped modes'
music command is +25k later (the mode change's full re-upload), NES +5.3k to
+5.8k. The ORIGINAL music command lands 49k (3-2) and 87k (1-1) clocks
before the next vblank, so these loads do not flip; a load whose ORIGINAL
margin is smaller than the mode's delay does.

### Gameplay palette uploads (survey traces, 11 runs, gameplay frames)

Frames whose VCE changed / colours changed: ORIGINAL 2,412 / 38,787
(153 frames of 100+ colours), NES-A 1,976 / 33,635, APOCALYPSE 2,293 /
26,003, SMS 2,120 / 14,821, GB DMG 1,916 / 13,088 (mapped modes cap their
per-vblank upload, so their changes are spread over more, smaller frames).
