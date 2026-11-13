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

## Fix design (palette-lag; emulator evidence, hardware untested)

Goal: no palette mode may change when the game completes its updates. The
design makes every mode run the same cycles as Original wherever the game
does palette work, rather than spending fewer cycles somewhere else.

**Mapped modes (GB DMG, APOCALYPSE/HELL, SMS).** Colours are converted in
the main loop's idle time, not in the vblank interrupt.

- The main loop's only vblank wait (bank 0 `$E061`, native `jsr $FD67`)
  calls `WAITR` (`$37C0`, RAM). In Original, NES-A, NES-B it holds
  `$FD67-$FD6F` byte for byte: identical instructions, identical cycles. In
  a mapped mode, after the same `STZ $12`, `tst #$ff,$2260` / `bne` (10
  cycles, a multiple of the native loop's 10, so the loop's exit after the
  vblank interrupt lands on the same cycle as Original's) skips to the
  native loop when the queue is empty; otherwise it maps bank `$46` and
  calls the worker.
- The worker (bank `$46` `$5Bxx`) sets `LIVE` (`$37E0`: $10 in gameplay, 0
  in a cinema/title/ending), and when the palette is unlocked converts every
  queued colour from `$2286` into `SHADOW` (`$3C00-$3FFF`, the same layout)
  and the border into `BORDER_MAP`, checking `$12` before each colour; done,
  it sets `FASTOK` (`$37E1`). The VCE holding original colours (a cinema or
  the title ended, the mode was chosen) it queues all 512 first, as the old
  upload did. A left-over entry the fallback left (it may wrap past colour
  511) is split at 511 so the native layout can carry it.
- The vblank dispatch (`palette_entry`) tests `LIVE` instead of `$2100`.
  Locked: 13 cycles to the `rts` (as before). `LIVE` = 0: the native upload,
  37 cycles to `$F3B5` (as before; the mode-change requeue as before).
  `LIVE` = $10 and `FASTOK` = 1 (`dec FASTOK` clears it): `fast_upload`,
  the native `$F3B5-$F421` instruction for instruction with the source base
  `SHADOW` (`adc #$00/#$3C` for `adc #$86/#$22`) and the border from
  `BORDER_MAP`, reached in 37 cycles: the vblank costs exactly Original's.
  `FASTOK` = 0 with an empty queue: 46 cycles to the `rts`, Original's empty
  upload. `FASTOK` = 0 with work: the mapped upload of before (fallback).
- The menu's waits call `WAITR` too, so previews convert in idle time.
- Picture: a mapped colour change now reaches the VCE at the same vblank
  as Original's (before: at most 168 colours a vblank, the rest over the
  next vblanks, 16 a vblank when left over).

**NES-A / NES-B.** NES colours are other palette data loaded with the
stage (unchanged); the loads now take Original's cycles exactly:

- `nes_unpack` (the colour-set and sprite-palette loaders' hook, bank
  `$45`): every lookup path is padded to 162 cycles, then `fast_unpack`
  (bank `$45` tail) unpacks the same packed format with the 8 colours of a
  group unrolled; its first two groups are 122 cycles shorter than the
  native 505 (paying for the lookup and banking), the rest padded to 505.
  So hook + unpack = Original's hook (15) + `$F2BE` for every count.
- The NES HUD colours (moved to bank `$45` `$5120-$51FF`, unused tail of
  stage61-upload's old claim, its guard lowered to `$5120`) and 1-1's / 2-2's
  NES palette copies peel their first colours so every mode reaches the
  same cycle.
- The animation-table choice (bank 3 `$CE98`) calls `ANIMR` (`$37EA`, RAM)
  that the palette module's configure writes per mode: 24 cycles to the
  `rts` in every mode and way.

**Configure.** `$5B03` (bank `$46`) writes `WAITR`, `ANIMR`, `LIVE`,
`FASTOK` for `$2100`'s mode. Called by the reset (`src/bram`'s trampoline
now `jsr $5B00`: the settings loader `$4B00`, then configure; A/X/Y/P kept)
and by the menu's `set_palette` after any change of bits 3-5. The harness
(`comparison_video.start_point`) writes Original's `WAITR`/`ANIMR` after
loading a state made from the original game.

## RAM audit (emulator evidence)

`research/tools/palette-lag/ramaudit.py` (read/write watch, cpu addresses)
on `$3234-$33FF`, `$3400-$37FF`, `$3C00-$3FFF`, on the original ROM and on
the pre-fix 1.11-dev build: cold boot through the title and 3,000 frames of
attract mode into 1-1 (watch armed after the reset's RAM clear), the 11
stored runs each with a 1,500-frame tail (stage clears into their cinemas),
and the 22 Level Select entries (200 frames right, 40 right+II, 200 left,
300 idle). No access in any of the 34 scenarios on either ROM (positive
control: the pad bytes `$2E55-$2E5E` stop at once). Not covered: the
ending, Continue / Game Over, bosses not in the stored runs, and stages
without a stored run beyond 740 frames. Static scan: absolute operands into
`$3C00-$3FFF` exist in ROM bytes (data or code not reached in these
scenarios cannot be ruled out); this is the open risk of the RAM claim.

## Results on the fixed build (emulator evidence)

Build under test: `4147a8b1...a8849` (source `palette-lag`, see the
report's commit list; "fix8" in `/workspace/build/palette-lag`). Load
timing and the NES loader probe ran on "fix7", which differs from it only
in `src/options` (1,192 bytes, all in the options module's ranges; neither
probe runs menu code). Pristine identity: the pre-fix source (3a1dbe4)
rebuilds to `cec5f7b3...8059`; `project.py apply` still reproduces 1.10
(`3d5c05df...bbf6`); `patches/`, `release/` and `VERSION` (1.11-dev)
unchanged.

### Survey (`palette_lag.py survey` + `report`, 11 runs x 9 variants)

Every mode equals ORIGINAL and 1.10 in update-counter deltas and every
gameplay field (SAT hash, Ryu, timer, camera, health, lives, stage, area)
in all 11 runs, the tails included, except one transition sample:

| run | variants | first difference | what it is |
|---|---|---|---|
| 6-3 | APOCALYPSE, SMS, GB DMG | frame 5138 (16 frames after the stage end flag, cinema state) | the cinema-entry re-upload (all 512 colours in original, below): the update's counter increment falls after the frame step's end (delta 0 then 2); no update overruns |

3-2 reaches its stage-end flag in every mode (pre-fix: NES-A, NES-B, SMS,
GB DMG lost frames at 1033 and 1104 and ended one step short). 4-1, 5-3:
the pre-fix stage-clear 0/2 samples are gone.

### Interrupt-level comparison (`palette_lag.py events`)

The master clock of every interrupt entry, pad read and VCE register write,
per frame, against ORIGINAL (the same menu route):

| run | APOCALYPSE | SMS | GB DMG | NES-A | NES-B |
|---|---|---|---|---|---|
| 3-2 (3,197 frames) | 29 frames, max 15 clk | 28, 15 | 29, 15 | 0 | 0 |
| 2-2 (4,006) | 51, max 16,398 (frame 795) | 43, 16,398 | 48, 16,401 | 1, 9 clk | 1, 9 |
| 4-1 (2,548) | 33, max 21,042 (2503, cinema) | 32, 21,042 | 35, 21,042 | 0 | 0 |
| 6-3 (5,183) | 1,402, max 15 clk in gameplay; 5138 cinema | 1,350 | 65 | 2, 9 clk | 2, 9 |

Pre-fix (3-2, SMS): every one of the 3,197 frames differs.

### End to end with saved settings (`palette_lag.py e2e`)

Power-on with backup RAM holding each mode's settings (`SETTINGS LOADED`,
status 9; the menu never opened), the title left with Run, the game's own
start into 1-1, then the 1-1 run's input; every sound-driver command
(`$38:$4006`) from power-on, with its master clock (56 in each mode):

| mode | first update of 1-1 | sound commands at another clock than ORIGINAL | gameplay fields |
|---|---|---|---|
| NES-A, NES-B | equal | none | equal in all 2,903 frames |
| SMS | equal | 3 (-202: +12 clk; 1027: -9; 1716: +15) | equal |
| GB DMG | equal | 4 (max 18 clk) | equal |
| APOCALYPSE | equal | 3 (max 12 clk) | equal but frame 1858: one counter sample (next frame equal) |
| pre-fix SMS | +5,100 clk | 52 of 56 (up to +24,387) | first difference at frame 1680 |
| pre-fix NES-A | equal | 10, 7 extra commands (+87,630 at 1779) | first difference at 1550 |

The smallest margin of any sound command to the next vblank in these runs:
166,590 clocks.

### Stage loads (`loadtime`, all 22 Level Select entries; the mode written and configured, settled 60 updates)

ORIGINAL's sound-command margin to the next vblank: 38,118 (3-1) to 298,329
(5-1) clocks; the first update 339,483 to 347,493.

| build | worst delay of the sound command / first update vs ORIGINAL | a load landing in another vblank |
|---|---|---|
| pre-fix | APOCALYPSE 5,220, SMS 5,133, GB DMG 5,043, NES-A 7,392, NES-B 7,386 | none |
| fix | 0 in every mode and stage (both events at ORIGINAL's master clock) | none |

### Picture (`research/tools/palette-lag/picture.py`)

The VCE of every frame (whole contents where it changed) against ORIGINAL's
in the same frame, mapped by the mode's table in gameplay, as it is in
cinemas:

- ORIGINAL equals the pre-fix build in every frame of the 11 runs; NES-A and
  NES-B too, except 3-2 from 3078 (the pre-fix NES modes were one update
  behind there).
- APOCALYPSE, SMS, GB DMG equal ORIGINAL's colours in their mode in every
  gameplay frame except where the worker had no time (the fallback,
  below): 2-2 793-794 and 1660-1661 (127 colours one frame late), 5-2
  (APOCALYPSE) 555, 1204, 1825, 5-3 (APOCALYPSE) 714, 1428, 2376 and others
  (13 frames), 5-3 (SMS, GB DMG) 5299, 6498. Cinema starts: one frame (the
  first cinema colours sampled while the re-upload is under way: 4-1 2502,
  5-3 6783, 6-3 5138); GB DMG only: the black after a stage clear stays its
  darkest shade until the cinema queues its first colours (4-1 2487-2501,
  6-3 5122-5137, 5-3 6768-; pre-fix switched to black at the first cinema
  vblank). The pre-fix build differs from the fix in 4-218 frames a run:
  its mapped upload took at most 168 colours a vblank (16 for a left-over),
  so changes arrived over several frames; the fix uploads them in
  ORIGINAL's frame.

### Checks

`python3 -m unittest discover -s tests` (54 pass), `audit_public.py` (pass),
`check_boot.py` (pass), `check_menu.py --only options --only reset` (64 of
64 after adding the worker scratch, `BORDER_MAP` and `SHADOW` to the
preview scratch list), `check_menu.py --only select` (23 of 23),
`check_bram.py --only cycle` (17 of 17, PASS). Not run: `check_bram.py
--only matrix` (only the trampoline's call changed in `src/bram`),
`check_menu.py` sweep, the lock-modelling emulator, the stored routes'
videos, real hardware, audio.

## Residual differences (what is not zero)

1. **Wait-loop phase (mapped modes).** After a frame where the worker ran,
   the native wait loop starts at another cycle than Original's, so the next
   vblank interrupt is taken up to a cycle earlier or later and the next
   update starts up to 5 CPU cycles (15 master clocks measured; 9 at most by
   the loop's 10-cycle period plus the interrupt's entry) off. Interrupts
   landing inside the worker or the NES unpack enter 1 cycle apart (pad read
   9 clocks). It can change a frame only for an update ending, or a sound
   command landing, within ~15 clocks of a vblank (the measured margins:
   >= 5,772 clocks for the busiest 3-2 updates, >= 38,118 for load sound
   commands, >= 166,590 for the e2e run's sound commands).
2. **Fallback (mapped modes).** When an update queues more colours than the
   idle time before the vblank can convert (2-2's area change queues all 512
   43,000 clocks before the vblank; converting 512 needs about 107,000), the
   old mapped upload runs: +2,500 clocks at that vblank and +16,400 at the
   next (2-2 frames 793-795, 1660-1661; 5-2 and 5-3 likewise), and the
   colours arrive a frame late. `palette_now` (1-1's and 2-2's area
   backdrops, written to the VCE in the update) still maps in the main loop:
   +1,600 clocks on 2-2's area-change update (which keeps 42,700 clocks of
   slack). No frame was lost by either in the 11 runs.
3. **Cinema entry (mapped modes).** The first cinema update with palette
   work re-uploads all 512 colours in original (as before the fix, which did
   it at the first cinema vblank): +21,000 clocks in one cinema vblank. No
   update overruns (cinema updates are light; the next stage load starts
   the music afresh).
4. **Boot.** `palette_boot`/configure take the same cycles in every mode
   (branch-free); against the pre-fix ORIGINAL the reset is longer, which
   moved one title-screen sound command by 60 clocks in the e2e run (1-1's
   commands and gameplay unchanged).
5. **RAM claim.** `$37C0-$37FD` and `$3C00-$3FFF` passed the watch audit
   above but not the ending, Continue/Game Over or unreplayed bosses.

## Review follow-up (palette-lag review F1-F4; emulator evidence)

Closes the findings of [palette-lag-review.md](palette-lag-review.md).
Headless Geargrafx `78fc3d7` only; no real-hardware data. Builds: "fix8" =
`4147a8b1...a8849` (the build reviewed, rebuilt from `cc4d77f`); "fix9"
(`f76fcd87...f8f2`, F1 + F2 as the review proposed it); "fix10"
(`abfe6fb8...12f1`, F2's empty exit as fix8's; the delivered build).

### Changes

- **F1** (`src/options`): `preview_palette` makes every highlighted value
  live, NES-A/NES-B included, whatever mode the menu opened in (the
  `OPENED_OPTIONS` / `and #$10` special case is gone). Run's `set_palette`
  therefore always finds the mode unchanged and returns at once, as in
  Original. Visible change: while NES-A or NES-B is highlighted in a menu
  opened in GB DMG, APOCALYPSE or SMS, the screen shows the RAM palette
  unmapped (Original's colours) until Run or until a mapped value is
  highlighted again; opened in Original, NES-A or NES-B nothing changes on
  screen (as before). `docs/OPTIONS.md` and ARCHITECTURE say so;
  `check_menu.py --only options` gained four cases that check the NES value
  live in the preview from GB DMG, SMS and APOCALYPSE and exact after Run.
- **F2** (`src/palette`): the worker ends with `inc FASTOK` (was `lda #1` /
  `sta`, same 7 cycles); the fallback with work stores `$80` (was `stz`). A
  vblank between the worker's last `$12` check and its end now leaves
  `$81`, which the next dispatch's `dec` cannot turn into 0. The
  fallback-with-work path is 2 cycles longer (it was never Original-equal:
  it is the mapped upload). The empty-queue exit keeps `stz` (46 cycles,
  fix8's instructions): the review proposed `$80` there too, and "fix9"
  did so, but the worker runs only with work queued and only an upload
  empties the queue, so that exit never meets a worker under way; with
  `$80` there `FASTOK` read `$80` instead of 0 after every empty mapped
  vblank, an equivalent value (the next `dec` is not 0 either way, the
  worker starts from `stz`) that `check_menu.py --only options --only reset`
  reported as RAM differing from the run without the menu in 9 cancel cases
  opened in a mapped mode. "fix10" (the delivered build) keeps `stz` there;
  the measurements below were repeated on it.
- **F3** not fixed: the empty fallback path's 10 spare cycles are now F2's
  store, and the locked (13), plain (37), fast (37) and empty (46) paths
  have no other spare cycles; any other place would change a timed path.
  Cosmetic, GB DMG only (the review's 15 + 17 frames around a stage clear).
- **F4** (`scripts/palette_lag.py`): `busy` removed (its RAM breakpoint
  desynchronised the frame steps). Cause of the step hazard, read in the
  emulator (`platforms/shared/desktop/emu.cpp`): a sync `debug_step_frame`
  adds its frames to a pending count that only a completed frame
  decrements; a breakpoint stop leaves 1 pending, so the next step(1) asks
  for 2 and the emulator runs a second frame on its own, with the same
  input. Reproduced: the first `fastok` attempt stopped once at the worker
  and its next step ended exactly 358,995 clocks (one frame) late. Only a
  `debug_pause` served during an active frame step clears the count, so
  `resume_step` sends the step and a pause in one write (the pause is served
  at the frame end; one more instruction runs), and `step_with_stops`
  (used by `step_recording`, hence `e2e`, and by `fastok`) checks by
  master clock that every step with a stop ends inside its own frame
  (`StepError` otherwise). New subcommands: `pairs`, `fastok`, `dispatch`.

### F1: the two-menu pair matrix (`palette_lag.py pairs`)

Route (the review's): menu 1, opened in 1-1's Original gameplay, Runs into
1-1 in mode 1; 30 frames later menu 2, opened in mode 1, chooses 3-2 and
mode 2 (Right presses from mode 1, padded to five on the reset row: every
pair presses the same buttons the same number of times) and Runs; then 3-2's
stored input for 1,200 frame steps. Per pair against ORIGINAL -> ORIGINAL:
the master clock of 3-2's first update (`$8457`), the sound driver's RAM
(`$2080-$208F`, `$3800-$3BFF`) every frame, update counter / Ryu / stage /
master state every frame, lag frames, and every interrupt entry's master
clock.

| build | pairs equal to ORIGINAL -> ORIGINAL in every measure | pairs that differ |
|---|---|---|
| fix8 (reviewed) | 30 of 36 | GB DMG, SMS, APOCALYPSE -> NES-A and -> NES-B (6): first update +6,369 clk, sound RAM differs from frame 0 on, lag frames 1033 and 1104, counter/Ryu differ in 167 frames from 1033, interrupt entries moved in 907 frames (max 9,246 clk) |
| fix9, fix10 | **36 of 36** (each build): first update +0 clk, sound RAM equal in all 1,200 frames, no lag frame, counter/Ryu/stage equal, interrupt entry clocks equal in all 1,200 frames (no wait-loop phase difference on this route either) | none |

The review named three of the six failing pairs (GB DMG -> NES-A, SMS ->
NES-B, APOCALYPSE -> NES-A); the matrix shows the other three fail the
same way on fix8.

### F2: the reproduction (`palette_lag.py fastok`)

2-2 in GB DMG through the menu, replayed to the worker call of the area
change (frame 793, 512 colours queued in one entry, worker entered 42,627
clocks before the vblank, as in the review), saved there; per trial the
entry cut to N colours, run on to the main loop's return from the wait
(`$E064`), instruction trace of the way:

| N colours | fix8 | fix9, fix10 (identical) |
|---|---|---|
| 195-204 | fast upload (37 cycles), `FASTOK` 0, queue 0 | the same |
| 205, 206, 207 | fallback, then the worker's `sta`: **`FASTOK` = 1** with queue 1 (first colour 54, `$2104` = `$E0`) | fallback (`FASTOK` `$80`), then the worker's `inc`: **`$81`**, queue 1 |
| 208-215 | fallback, worker aborted: `FASTOK` 0 | fallback, worker aborted: `$80` |

So `FASTOK` = 1 now occurs only after a worker that finished before the
vblank (fast upload taken, queue 0); after any fallback it is `$80`/`$81`
and the next vblank's `dec` leaves it non-zero (no fast upload).

### Dispatch path cycles (`palette_lag.py dispatch 2-2 785 16`)

CPU cycles from `palette_entry` to its `rts` or to the upload it jumps to,
every vblank of 2-2 frames 785-800 (the area change), instruction traces:

| path | fix8 | fix9, fix10 (identical) |
|---|---|---|
| locked | 13 | 13 |
| plain (ORIGINAL, NES-A) | 37 | 37 |
| fast | 37 | 37 |
| empty | 46 | 46 |
| fallback with work | 58 (GB DMG), 60 (APOCALYPSE, SMS) | 60, 62 |

### The three trace windows (`palette_lag.py itrace`, `research/tools/palette-lag/clockcmp.py`)

3-2 frames 1031-1033 and 1101-1104, 4-1 frames 2485-2489 (the busiest 3-2
updates and the stage-clear transition), every CPU instruction and
interrupt, against fix8, all six menu modes: fix10 has **every line at the
same master clock and the same instruction** in all 18 traces
(83,409-167,332 lines each; interrupt entries 9-15, none moved); fix9 the
same clocks, with its empty-path filler reordered at equal length. So the
earlier results of these windows against ORIGINAL carry over unchanged.

### Regression (fix10; fix9 gave the same where it was run)

- **Survey** (`survey` + `report`, 11 runs x 9 variants, traces in
  `/workspace/build/palette-lag/f10/traces`): the report is identical to
  fix8's line for line (every mode equal to ORIGINAL and 1.10 in all 11
  runs; the one 6-3 cinema-entry sample at 5138 as before). Every field of
  every frame of all 77 traces (counter, `$12`, SAT/VCE hashes, Ryu, timer,
  stage, area, lives, health, camera, master state, boss, options) equals
  fix8's.
- **Picture** (`research/tools/palette-lag/picture.py`, fix8's traces as
  the baseline): the VCE equals fix8's in every frame of all 66 run x mode
  traces (0 frames differ); the per-mode differences from ORIGINAL's colours
  are fix8's exactly (the fallback frames, cinema starts, GB DMG's black
  around stage clears: F3). The F1 change acts only inside the menu while
  NES-x is highlighted, which the stored routes do not do.
- **Load timing** (`loadtime`, 22 Level Select entries x 6 modes): every
  sound command and first update at ORIGINAL's master clock (264 cells,
  all +0), no load in another vblank; the log equals fix7's line for line.
- **Saved-palette power-on** (`e2e`, each mode loaded from backup RAM,
  status 9, menu never opened, 1-1's run), with the corrected
  `step_recording`: first update +0 clk in every mode; gameplay fields equal
  to ORIGINAL in all 2,903 frames in every mode; 96 sound commands in each
  mode (NES-A/B at ORIGINAL's clocks; APOCALYPSE 7 at other clocks, max 54
  clk; SMS 6, max 18; GB DMG 6, max 18); smallest margin of a sound command
  to the next vblank 145,875 clocks. fix8 rerun with the same tool: hits and
  traces identical to fix10's (and fix9's) in all six modes. (fix8's recorded e2e, made
  with the old `step_recording`, counted 56 commands and 478 boot frames:
  inferred, the frame-step hazard ran unrecorded frames there; its
  mode-to-mode comparison was still like with like, and its conclusions
  hold with the corrected tool.)

### Checks (fix10)

`python3 -m unittest discover -s tests` (54 pass), `audit_public.py`
(pass), `check_boot.py` (pass), `check_menu.py --only options --only reset`
(68 of 68: the 64 before and the 4 new NES-preview cases), `check_menu.py
--only select` (23 of 23), `check_bram.py --only cycle` (17 of 17, PASS;
baseline `cec5f7b3...8059`). fix9 failed 9 cancel cases of the options /
reset part on `FASTOK` (`$80` against 0, see F2), which led to fix10.
Pristine identity: `cc4d77f` rebuilds to `4147a8b1...a8849`;
`project.py apply` reproduces 1.10 (`3d5c05df...bbf6`); `patches/`,
`release/` and `VERSION` (1.11-dev) untouched. Not run: `check_menu.py`
`runs` / `sweep` parts and the `--preview` runs, `check_bram.py --only
matrix` (no `src/bram` change), the lock-modelling emulator, `events`,
`margin`, the stored routes' videos, audio, real hardware. The menu's
`1.11-dev` text is checked by `check_menu.py` (window text), not by eye.

### Remaining risk (unchanged by this follow-up unless said)

- F3 (cosmetic, GB DMG): darkest shade / true black around stage clears.
- The fallback meeting two consecutive near-limit updates in a mapped mode
  (boss kills, the ending): not measured.
- RAM claim: the ending and the bosses other than 5-4's not watched.
- The pair matrix covers one route (1-1 then 3-2) and 1,200 frames; the
  menu's other routes are covered by the Run-path argument (Run never
  changes the mode now), not by measurement.
- Emulator only.

### Delivered (fix10, source `palette-lag`)

In `/workspace/roms/` (new names; nothing there was changed):

| File | SHA-256 |
| --- | --- |
| `Ninja Ryukenden - Enhanced v1.11-dev (apocalypse, reset 2, palette timing 2).pce` | `abfe6fb887f0c19846cd3d5d500168573b838e15f146e09e80695c0fcc5b12f1` |
| `ninja-ryukenden-enhanced-v1.11-dev-apocalypse-reset-2-palette-timing-2.bps` (headered original) | `310b82056f6299730d719af183cf623156213cb39b4519928e3196e073f6746c` |
| `ninja-ryukenden-enhanced-v1.11-dev-apocalypse-reset-2-palette-timing-2-headerless.bps` | `bc5796ee0af8e4498504dd0f740b69e81643e5cfcdf69edcd6dc596183d06407` |

Both patches applied with `scripts/bps.py apply` to their originals give
the ROM above; the build from either original is the same ROM.

### Rerunning

```sh
export LD_LIBRARY_PATH=/workspace/build/toolchain/sdl3/lib
R=<fix10 rom>
python3 scripts/palette_lag.py pairs --rom $R --out <dir>          # 36 pairs (ORIGINAL -> ORIGINAL first)
python3 scripts/palette_lag.py fastok --rom $R --lengths $(seq 195 215)
PALETTE_LAG_ROM=$R python3 scripts/palette_lag.py dispatch 2-2 785 16 --variants original 'gb dmg' apocalypse sms nes-a
PALETTE_LAG_ROM=$R python3 scripts/palette_lag.py itrace 3-2 sms 1031 3 a.gz   # then research/tools/palette-lag/clockcmp.py OLD.gz a.gz
PALETTE_LAG_ROM=$R PALETTE_LAG_TRACES=<dir> python3 scripts/palette_lag.py survey   # then report
python3 scripts/palette_lag.py loadtime --rom $R
python3 scripts/palette_lag.py e2e --rom $R --out <dir>
```
