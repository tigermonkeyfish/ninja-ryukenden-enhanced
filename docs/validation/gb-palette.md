# Palette modes: GB DMG (1.11-dev)

Emulator evidence (headless Geargrafx `78fc3d7` with the headless-fast patch,
binary SHA-256 `2de50e51…85e9`), not a hardware report. Builds:

| Build | SHA-256 | Source |
| --- | --- | --- |
| Before (`fire-wheel-fix`) | `4b07211b…8707` | commit `3fe658a` |
| GB palette | `1c3d4cae…6749` | branch `gb-palette`, commit `8dcd0f9` (same bytes from the headered and the headerless original) |

Method ([EMULATOR.md](../pc-engine/EMULATOR.md)): one start state, a cold boot
of the original saved at the 1-1 main-loop hook; every replay is a fresh
session that loads it, writes `$2100`/`$2101` (0 = Original, `$10` = GB
DMG), enters the stage as Level Select does and steps one frame at a time.
Probes: [`research/tools/gb-palette/`](../../research/tools/gb-palette)
(`record.py` per-frame hashes and VCE-against-RAM checks, `timing_trace.py`
hardware-event trace of vblank and scanline interrupts and every VCE write,
`unittest_upload.py`, `switch.py`, `stagestarts.py`, `entry_timing.py`,
`cinema.py`, `menu_shot.py`, `guard.py`, `freewatch.py`). Lines are counted
after the VDC vblank interrupt, 1365 master clocks each.

## Facts the design rests on

- Only `$F3B5` (vblank, `$FD13`) writes the VCE in the original game (VCE
  write watch over the study's boot and 1-1); Enhanced adds 1-1 (palette 1)
  and 2-2 (palettes 13-14), found by scanning the built ROM for VCE port
  stores outside the original's bytes.
- `$2240` is 1 during the publisher scene, intro and title and in cinemas, 0
  in gameplay, and 0 for the first five frames after power-on, when nothing
  is queued (`bootstates.py`, cold boot with Run pressed).
- `$2205-$220B` is a TIA shared with main-loop code; the mapped upload does
  not use it. `$F350` drops an entry when 8 are queued; the original fills
  the queue in area changes (2-2, 3-1, 4-1, 5-2, 5-3, 6-3).
- Costs (`upload_cost.py`): the native TIA uploads a colour in 42 master
  clocks (512 colours end 16.5 lines after vblank); the mapped loop takes
  152-156, plus about 600 per further queue entry. The scanline interrupt
  (RCR `$6F`, display line 47) is raised 69.78 lines after vblank, so the
  display starts about 22.8 lines after it.

## a. Original mode against `fire-wheel-fix`

`scripts/check_boot.py`: passed (idle frames 1-899 identical to the
original, first 1-1 update at frame 163 when mashing Run, defaults English,
Enhanced, No Damage off). `scripts/check_menu.py`: see the report in the
branch's final notes.

All 11 stored runs (35,084 frames) recorded on both builds (`record.py`,
`analyse.py identity`): every gameplay field (Ryu, stage timer, camera,
area, stage, lives, health, boss) and the sprite table are identical in
every frame. Differences:

| Run | Frames | What |
| --- | --- | --- |
| 1-1 | 2766-2821 picture, 2765-2821 VCE | Intended. Before, 1-1's merged palette 1 existed only in the VCE; the native full re-queue when area 1 fades in (frame 2764) put the native palette 1 back, and the Enhanced backdrop showed red and white towers instead of the blue skyline for the rest of the stage. It now lives in the RAM palette and survives. |
| 2-2 793, 1660; 6-3 1173 | 1 frame each | Area-change frames whose vblank upload of 264 colours straddles the frame-step boundary: the sample catches VCE entries 170-174 not yet written (the upload starts about 50 CPU cycles later through the trampoline); the next frame's VCE and picture are identical. |
| 5-3 2770, 3019; 5-4 998; 6-3 2220, 2740, 3000 | 1 frame each | 1-7 HUD pixels, VCE identical: sub-frame timing of a HUD VRAM write (the main loop resumes about 50 cycles later). |
| 3-1, 3-2, 4-1, 4-2, 5-2, 6-1 and the above | single frames, VCE only | Fade-step frames sampled mid-upload, picture identical. |

Game RAM differs in 1-1 (palette 1 in `$2286` now holds the merged colours)
and in the sound driver's workspace (`$38xx`), which follows the interrupt's
timing, as for the NES Firewheel hooks.

HUD split (`split.py`, scanline-interrupt CPU entry): per run the maximum is
within 0.2 line of the old build's (worst normal-frame entry 70.43, cut-off
about 70.84); the frames past the cut-off are the same load frames in both
builds (1-1, 2-2, 5-3 and 6-3: one each).

## b. GB DMG colours

- In-place unit test of the upload against an independent Python model
  (`unittest_upload.py`): 510 cases (queues of 1-8 entries, the cap, the
  fold, wrapping left-over entries, the lock, every mode and state bit,
  busy and idle main loop, cinema state, `palette_now`), 0 failures; with
  the model's cap set one lower, it reports failures (negative control).
- All 11 runs in GB DMG (`record.py`): every VCE entry equals the table value
  of its RAM colour except while uploads are still queued. The longest a
  single entry lags its RAM colour is 14-46 frames (`lag.py`: 44-46 in the
  end-of-stage fades of 1-1, 2-2, 3-1, 3-2, 4-2, 5-2, 6-1; 19-29 in 4-1,
  5-3, 6-3); the original's own lag (lock held across loads) is up to 13.
  Fades therefore run a step or two behind on some palettes.
- All 22 Level Select entries (`stagestarts.py`, 120 frames): every entry
  matches within 13-25 frames of the first update; afterwards only
  palette-animation colours lag for a few frames.
- Screenshots: [`build/gb-palette/shots/`] (private): `start-1-1-gb.png`,
  `start-2-2-gb.png`, `start-4-1-gb.png`, `start-5-3-gb.png`,
  `menu-2-2-gb.png`, `switch-1-1-paused-*.png`, `cinema-after-4-1-*.png`.

## c. Timing in GB DMG mode

- Worst mapped upload end over the 11 runs: 18.16 lines (`timing_trace.py`);
  over all 22 stage loads: 19.55 (1-1) and otherwise 17.8-18.3; the first
  display line is at about 22.8. No upload ends after line 22.
- Updates: stage timer, Ryu, camera, area and sprite table identical to
  Original mode in every frame of all 11 runs. `$2240` turns to 1 one frame
  later at the cinema after 4-1, 5-3 and 6-3 (the cinema starts a frame
  later; its frames are the same, shifted). Stage loads from Level Select
  after the mode has settled (`entry_timing.py`, 60 frames): the same number
  of frames as Original mode in 21 of 22 entries; 4-4 takes one more.
- HUD split: scanline-interrupt entries past the cut-off in the same load
  frames as Original mode (1-1, 5-3, 6-3); 2-2 none (Original one). In
  normal frames the largest shift against Original mode is +0.57 line, the
  maximum 70.44.
- The cap: 192 colours ended at 23.4 lines and 176 at 21.8 (synthetic
  queues), so the cap is 168 colours less 6 per further entry. The real
  limit turned out to be the main loop's slack: in the frames around an area
  change the native game has under a line to spare (6-3), so new entries get
  no more time than the native upload of them would take (0.266 mapped
  colours per native one), left-over work 16 colours a vblank and only after
  two vblanks with the main loop idle.

## d. Switching

`switch.py` (1-1 and 5-3): with the game paused, writing bits 3-4 = 10 and
calling `$F394` gives every VCE entry its GB value after 25 frames; back to
00 and `$F394`, the VCE equals the paused snapshot exactly after 2 frames;
the game stays paused. During the fade at the end of 1-1 (frame 2768) and
5-3 (6720): after switching back the VCE equals an Original-mode replay of
the same frames from the second frame on, and the stage timers stay equal.
(The module also re-queues by itself when the mode changes: `$2100` bit 7.)

## e. Queue

The queue is full (8 entries) at the same frames in GB DMG as in Original
mode in every run except 6-3 1543 (GB only; the left-over entry plus 7 new
ones). A full queue may have lost an entry in `$F350`, so the module leaves
all 512 colours over in that case. Not covered: cinemas (original colours by
design), Continue and Game Over screens, a boss room other than those in the
5-4 run and the stage ends.

## f. Space and stack

| Region | Use | Free |
| --- | --- | --- |
| Fixed bank `$FD13-$FD15` | hook (replaces `jsr $F3B5`) | |
| Fixed bank `$FEBE-$FECE` | trampoline, 17 bytes | `$FECF-$FEDF` (17), `$FFEE-$FFF5` (8) |
| Bank `$46` `$5000-$537C` | code, 893 bytes (claimed `$5000-$53FF`) | 131 bytes |
| Bank `$46` `$5400-$57FF` | GB table, 1 KiB | |
| Bank `$46` | | `$4100-$42FF` (512), `$4400-$4FFF` (3 KiB, contiguous) |

Read/execute watch over the claimed ROM on the old build (`freewatch.py`):
see the branch's final notes. Stack (`guard.py`, 2-2 with the menu opened
four times and a full palette re-queue forced while it was open): low-water
mark `$215A` in GB DMG mode (26 bytes above the watched margin), `$215B` in
Original mode and on the old build.
