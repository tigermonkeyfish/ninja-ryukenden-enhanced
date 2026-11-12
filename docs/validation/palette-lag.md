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

Build `fix5` (see "Delivered" for its SHA-256). Pristine identity: the
pre-fix source (tip 3a1dbe4) rebuilds to `cec5f7b3...8059`, the build
under test; 1.10's bytes are untouched (`release/`, `patches/` unchanged).

### Margins of the three windows (itrace, exact accounting)

Update woken at the given frame; busy = vblank interrupt entry to the
update's `STZ $12`; left = clocks before the next vblank interrupt.

| window | build | ORIGINAL | APOCALYPSE | SMS | GB DMG | NES-A | NES-B |
|---|---|---|---|---|---|---|---|
| 3-2 damage (1032) | pre-fix | 352,104 / +6,894 | 352,482 / +6,510 | 372,927 / overrun | 372,705 / overrun | 372,681 / overrun | (as NES-A) |
| 3-2 damage (1032) | fix | 352,104 / +6,894 | same | same | same | same | same |
| 3-2 frame 1104 | pre-fix | 353,232 / +5,772 | - | 393,168 / overrun | - | - | - |
| 3-2 frame 1104 | fix | 353,232 / +5,772 | same | same | same | same | same |
| 4-1 stage clear (2488) | pre-fix | 237,561 / +121,434 | 260,052 / +98,952 | 260,046 / +98,952 | - | 237,561 / +121,434 | - |
| 4-1 stage clear (2488) | fix | 237,561 / +121,434 | same | same | same | same | same |

"same": every number (busy, left, main-loop clocks, vblank-handler clocks)
equal to ORIGINAL's to the master clock. (The 1104 window holds the input
change at 1103; `itrace` replays the stored input frame by frame, so the
spurious overrun of the first worker's margin tool does not apply.)

### Stage loads (`loadtime`, all 22 Level Select entries, mode set and settled before the load)

ORIGINAL's sound-command margin to the next vblank: 38,118 clocks (3-1) to
298,329 (5-1); first update 339,483 to 347,493 before the next vblank.

| build | worst delay of the sound command / first update vs ORIGINAL | loads where either lands in another vblank |
|---|---|---|
| pre-fix | APOCALYPSE 5,220, SMS 5,133, GB DMG 5,043, NES-A 7,392, NES-B 7,386 clocks | none |
| fix | 0 in every mode and stage (both events at ORIGINAL's master clock) | none |

(Pre-fix, settled modes in a Level Select load did not flip; the 3-2 menu
route did, by the preview's re-uploads and the NES colour lookups.)

### NES loaders (`research/tools/palette-lag/nes_cycles.py`)

992 calls of `$F1C0` (sprite palettes 0-159) and `$F211` (sets 0-21 in
stages 1-1, 3-1, 3-2, 4-1), master state 0 and 1, NES-A and NES-B, from one
saved state with interrupts off: every call takes exactly Original's
clocks (pre-fix: +138 to +702); the RAM palette, backup and queue equal
the pre-fix build's in every case; Original's calls are unchanged in clocks
and results. (Zero page `$29` differs in the 3-2 variant case: the variant
data moved address in bank `$45`; the colours are equal.)
