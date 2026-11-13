# Full-playthrough code drift: causes and fix proposals

Diagnosis only: no shipped source changed, no ROM delivered. Emulator evidence only
(Geargrafx 78fc3d7 core), no real-hardware claim. **Verified** = measured here;
**inferred** = read in code or reasoned, not measured.

Builds: unmodified HuCard (`Ninja Ryukenden (J).pce`), published 1.10, 1.11-dev
"apocalypse, reset 2, palette timing 2" (ORIGINAL palette mode). Recordings: the pinned
`full-4bba5f4.json` (= `research/longplay/full.json` at 4bba5f4) and, for the unmodified
ROM and 1.10 past the act 3 scene, the re-aligned `research/longplay/full-unmodified.json`
(0314300; one idle frame fewer at the 3-3 to 4-1 hand-over). Start states: the
`entered.state` files of the `longplay_six.py` cause runs (1-1's first update).

Frame = 358,995 master clocks. The main loop is bank 0 `$E061` (vblank wait: native
`jsr $FD67`, 1.11-dev `jsr $37C0` = WAITR), `$E06C` `inc <$00` (the update counter),
`$E06E` the update. The vblank interrupt (`$FCD7`, vblank path `$FCEC`) uploads the
palette (`$FD13`), ticks the sound driver (`$FD16` -> bank `$38`), reads the pad and sets
`$12` (`$FD1F`). The wait clears `$12` and spins: an update that reaches the wait after a
vblank loses that whole frame. The harness's frame step ends about 8,100 clocks after the
vblank interrupt.

## Summary

| Point | Mechanism (verified unless marked) | Patch code | 1.10 | 1.11-dev | Real time vs original |
| --- | --- | --- | --- | --- | --- |
| 5,668 (1-2, area 0 -> 1) | The native object walker reads bank 0 code `$F1FF-$F42E` as an object list; 1.11-dev changed two of those bytes, so one phantom object is discarded instead of kept | `src/nes-palette`: `jsr nes_unpack_hook` at `$F234` (bytes `$F235-$F236`) | no | yes | 0 frames (same update frames as 1.10 until 51,763) |
| 13,258 (2-2 load) | The 2-2 stage load runs +296k clocks (the Enhanced backdrop drawn during the load); the original load ends 210k before a vblank, so the patched load ends one vblank later | `src/dispatch` `init_background` (`draw_now` for profile `$AC`) -> `src/stage22` | yes | yes | 1 game update inside 2-2; 2-3 started on the same frame in all builds in this run |
| 51,763 (act 3 story scene) | A scene update ends 465 clocks before a vblank in the original and 1.10; 1.11-dev's vblank palette trampoline (+76 CPU cycles = 228 clocks per vblank) adds about 504 and it misses by about 40 | `src/palette`: `$FD13` `jsr $FEC0` (trampoline + `palette_entry` dispatch) | no | yes | +1 frame, carried to every later stage start (4-1 .. 5-4) |
| 65,934 (4-4 end scene, Japanese) | Native: the Japanese text update there costs 488k clocks against 286k in English and overruns; the unmodified ROM loses the same update | none | n/a | n/a | 0 from the patch (the original game itself is 1 update slower in Japanese) |
| 5-4 (load, 1 frame beyond the -1 shift) | The 5-4 load runs +240k clocks (castle Enhanced backdrop drawn during the load); the original load ends 211k before a vblank | `src/dispatch` `init_background` (castle profile) -> `src/castle` | yes | yes | 1 game update inside 5-4 (end of stage not reached in step; recovery not known) |

13,258 and 5-4 share one cause: the load-time Enhanced draw that `init_background`
does at once for three profiles (`$224F` = `$AC`, `$A3`, `$BF`: 2-2, 5-2 and the castle
stages 5-3/5-4). 5-2 and 5-3 also pay it but still fit (table below; 5-3 by 9.6k clocks
in 1.10, 6.9k in 1.11-dev).

## Method and tools

`research/longplay/drift/` (reference probes, not maintained tools; build with its
Makefile against the objects of `research/longplay/fast/`):

- `shim_trace.cpp` + `tracer.py`: the in-process core of `research/longplay/fast` with the
  core's own frame loop copied (same `RunInstruction` / `ClockHardware` sequence, private
  members reached by explicit-instantiation access, no `#define private public`, which
  crashed), plus passive recording: every instruction's master clock, PC and bank
  (`trace_frame`), clocks of watched PCs over many frames (`watch`), and a RAM snapshot at
  the n-th hit of a PC inside a frame (`snap`).
- Check of the tool: replays of the pinned recording from the four `entered.state` files
  gave the per-frame update counter identical to the headless `longplay_six.py` arrays in
  all 70,100 frames for 1.11-dev English, 1.11-dev Japanese, 1.10 and the unmodified ROM
  (`full/raw/original`, `cause/raw/patched-japanese`, `cause/raw/v110`, `full/raw/unmodified`).
  The re-aligned unmodified English run reproduces the coordinator's 4-1 .. 5-4 load frames.
- `watchrun.py` (per update: start `$E06C`, wait `$E061`, every vblank `$FCEC`, sound
  command `$38:$4006`), `upd.py`/`cmp.py` (update tables), `segprof.py` (clock cost by bank
  of the longest main-loop stretch between two waits), `irqlist.py` (interrupts inside an
  update), `snapdiff.py`/`snapat.py`/`bisect_snap.py` (RAM compared at update starts, at a
  PC, bisected over the hits of a PC), `div2.py` (first divergence of instruction streams),
  `hdis.py` (HuC6280 disassembler from Geargrafx's opcode table).
- Scratch outputs (not committed): `/workspace/build/longplay-drift/` (`watch/*.npz`,
  `states/`). About 1,000 frames/s per run; at most two cores at once; no headless
  emulator was used.

A finding about the measure itself: RAM read at the harness's frame end is taken in the
middle of the vblank interrupt (the step ends ~8,100 clocks after it). 1.11-dev's
interrupt runs 228 clocks later, so the sound driver is cut at a different instruction:
the sound bytes (`$2083-$2088`, `$38xx-$39xx`) that differ between 1.10 and 1.11-dev at
frame ends from frame 4 on are this sampling, not a driver tick offset. Compared at every
update start (`snapdiff.py`), 1.10 and 1.11-dev RAM is identical up to frame 5,668
(patch-owned bytes excluded). Likewise the per-frame "lag frames" of the counter arrays mix
real lost updates with updates that start just before or after the step boundary; below,
"lost" means an update that reached the wait after a vblank (counted from clocks).

## 5,668: phantom object list read from fixed-bank code (1.11-dev only)

Verified:

- RAM at every update start is identical in 1.10 and 1.11-dev up to and including the
  update of frame 5,668; the main-loop instruction streams are identical until bank 2
  `$A549` in that update (`lda $30DF,y / cmp #$D0`: 1.10 keeps the object, 1.11-dev jumps
  to `$A3E4`, which frees the slot: `$30B7,y` = `$FF`, `dec $30B5`).
- Bisected over the 140 passes of the walker loop (bank 2 `$A598`, entry read `$A5B3`:
  four bytes from `[<$45]` into `$3107-$310A`): RAM is equal after pass 14 and differs
  after pass 15, in `$3109/$310A` (190/242 vs 224/127) and the new object's fields. The
  pointer walks `$F1FF, $F203, ... $F42B`: bank 0 code (the colour-set loader `$F211`,
  `$F23C`, the unpack `$F2BE`, the queue `$F350`, the upload `$F3B5`) read as 4-byte entries,
  in the original ROM too. The entry at `$F233` reads `$18 $20 $BE $F2` in the original
  and 1.10, `$18 $20 $E0 $7F` in 1.11-dev: `jsr $F2BE` became `jsr $7FE0`
  (`src/nes-palette`, `.org $f234 / jsr nes_unpack_hook`). Within `$F1FF-$F42E` only
  `$F235-$F236` differ (1.11-dev); 1.10 is byte-identical there.
- Entries create objects in 8 free slots (`$F1FF, $F203, $F217, $F21B, $F22F, $F233,
  $F24F, $F253`); later accepted entries find no free slot. The `$F233` object then fails
  the `$30DF,y` < `$D0` test in 1.11-dev (`$E0` = 224) and is removed; the original keeps it
  (`$BE` = 190).
- Effect: bytes `$3099, $30B5, $30BC, $30D4, $30E4` (and for one frame some sprite-buffer
  bytes) differ from 5,669 until the 2-1 load re-initialises them (10,152); nothing else in
  RAM differs at any update start over 5,669-10,151. Update durations in 1-2 area 1 differ
  by +8 clocks on average (at most +2,637); the same updates are lost in both builds; the
  update frames stay identical to 1.10 until 51,763.

Answer to the lifecycle question: the patch does not write game RAM it should not. The RAM
difference is the original game's own object code acting on ROM bytes the patch changed
(fixed-bank code that the original reads as data in this area). It is a fidelity
difference, not an overlap: in 1-2 area 1 the original keeps an invisible-or-unused phantom
object in slot 5 (inferred: nothing visible was checked), 1.11-dev frees that slot. With
a busier slot table a freed slot could let a real object spawn that the original would
not spawn; not seen in this run.

Rule this adds (inferred, general): bank 0 `$F1FF-$F42E` is data to the original game in
1-2 area 1; any byte changed there changes that area's objects. Other areas' walks were
not surveyed.

Fix proposal: restore `$F234-$F236` (`jsr $F2BE`) and take the NES colour-set substitution
elsewhere. The colour-set loader `$F211` is reached by 19 call sites (bank 1: 4 `jsr`,
14 `jmp`; bank 4: 1 `jsr`); the sprite-palette hook `$F1DC` is outside the walked range
and can stay. Options: (a) redirect the 19 call sites to a fixed-bank wrapper (free
`$FECF-$FEDF`, 17 bytes) that runs the NES loader in NES modes and `jmp $F211` otherwise;
cost about 20 cycles per colour-set load (stage loads only), which must be checked against
the load margins below and against the sound-command-across-vblank hazard
(`palette-lag.md`); (b) keep the hook but choose a target address whose low/high bytes
equal `$BE $F2` (only `$F2BE` itself, inside the range: not possible without moving the
unpack). Size small (2 bytes x 19 + wrapper), risk low-moderate (call-site audit, NES
colours re-tested in every stage). Verification: `snapdiff.py` unmodified vs fixed build
over 5,600-10,200 must show no object bytes.

## 13,258 and 5-4: the load-time Enhanced draw

Verified (`segprof.py`, longest main-loop stretch between two vblank waits; the stage load
runs with no wait at all for 14-18 vblanks):

- 2-2 load (unmodified frame 13,240): unmodified 5,796,198 clocks, 1.10 6,080,664,
  1.11-dev 6,084,390. The whole difference is in Enhanced banks `$46`, `$56-$65`
  (stage22: 1,272 + 86,265 + 69,255 + 22,809 + 11,988 + 29,625 + 15,522 + 12,864 + 13,014
  + 10,131 + 10,218 clocks in 1.10) = the `init_background` draw. The original load ends
  210,045 clocks before its 17th vblank; the patched one crosses it (17 vblanks instead
  of 16), so the first gameplay update (the fade step, 471k clocks in every build) starts
  one frame later. This is the update counter's 74 vs 73 at 13,258.
- 5-4 load (unmodified frame 82,880): unmodified 6,138,759, 1.10 6,366,264, 1.11-dev
  6,367,146; the difference is castle bank `$7C` (127,077 clocks) and RAM code (bank `$F8`,
  the game's block-transfer trampoline: 114,039 against 19,362) plus `$46`. The original
  ends 210,909 clocks before its 18th vblank, the patched loads take 18. That is the
  coordinator's 5-4 point: the patched game is one more frame behind from 82,899 (unmodified
  numbering), so the boss spawns 2 frames later than the unmodified (82,965 vs 82,967,
  of which 1 is the earlier shift).
- Every stage load to 5-4 (whole load update, interrupts included; unmodified English
  re-aligned run, 1.10 on the same input, 1.11-dev on the pinned recording):

| Load | Unmodified frame | Unmodified: clocks / vblanks / left before the next | 1.10: extra / vblanks / left | 1.11-dev: extra / vblanks / left |
| --- | --- | --- | --- | --- |
| 1-2 | 2,831 | 5,128,752 / 14 / 250,605 | +357 / 14 / 250,245 | +2,619 / 14 / 247,755 |
| 2-1 | 10,135 | 5,482,191 / 15 / 256,065 | +240 / 15 / 255,825 | +2,877 / 15 / 252,975 |
| **2-2** | 13,240 | 5,887,305 / 16 / 210,045 | **+295,824 / 17** / 273,210 | **+301,569 / 17** / 267,228 |
| 2-3 | 16,532 | 5,086,410 / 14 / 292,920 | +1,629 / 14 / 291,318 | +3,771 / 14 / 288,948 |
| 3-1 | 27,777 | 5,844,528 / 16 / 254,109 | +246 / 16 / 253,857 | +3,129 / 16 / 250,749 |
| 3-2 | 31,400 | 5,984,358 / 16 / 112,965 | +375 / 16 / 112,599 | +2,757 / 16 / 109,989 |
| 3-3 | 34,852 | 5,183,172 / 14 / 196,125 | +390 / 14 / 195,789 | +2,658 / 14 / 193,299 |
| act 3 scene | 36,497 | 2,262,750 / 6 / 212,625 | -72 / 6 / 212,625 | +1,311 / 6 / 211,029 |
| 4-1 | 53,286 | 5,728,017 / 15 / 10,485 | +294 / 15 / 10,245 | +2,937 / 15 / 7,395 |
| 4-2 | 57,119 | 5,728,932 / 15 / 9,519 | +399 / 15 / 9,129 | +2,997 / 15 / 6,297 |
| 4-3 | 60,356 | 4,617,090 / 12 / 44,259 | +240 / 12 / 44,037 | +2,286 / 12 / 41,769 |
| 4-4 | 64,421 | 5,079,711 / 14 / 299,628 | +246 / 14 / 299,388 | +2,604 / 14 / 296,796 |
| 5-1 | 70,012 | 4,595,955 / 12 / 66,699 | +345 / 12 / 66,357 | +2,352 / 12 / 64,119 |
| 5-2 | 73,262 | 5,851,053 / 16 / 246,279 | +213,444 / 16 / 32,859 | +216,351 / 16 / 29,715 |
| 5-3 | 77,204 | 5,523,705 / 15 / 214,635 | +205,002 / 15 / 9,645 | +207,480 / 15 / 6,939 |
| **5-4** | 82,880 | 6,245,427 / 17 / 210,909 | **+239,733 / 18** / 330,156 | **+242,862 / 18** / 326,808 |

  (1.11-dev frames are one later from 4-1 on.) Only the three draw-at-load profiles pay
  hundreds of thousands of clocks; the other loads pay a few hundred (1.10) and 2-4k
  (1.11-dev: 228 clocks for each vblank inside the load, see 51,763). Near misses for
  later changes: 5-3 (9.6k / 6.9k clocks), 4-1 and 4-2 (about 10k in the original, 6-7k in
  1.11-dev; those loads are native work only).
- Real time: in this recording the 2-2 loss did not reach the next stage: 2-3 starts on
  frame 16,533 in all builds (2-2 is played with one update fewer in the same 3,292
  frames; what absorbs it at the stage end is not identified). The 5-4 loss puts the boss
  one more frame behind; whether the end of 5-4 absorbs it is unknown (the run breaks).
- The coordinator's 10 extra lag frames (1-82,881): the clock count gives real lost
  updates of unmodified 653, 1.10 654, 1.11-dev 655 before the 5-4 load. 1.10's one is the
  2-2 load; 1.11-dev's two are the 2-2 load and 51,763. The other 8 of the 10 are counter
  sampling: after 51,763 the act 3 scene's long updates (every 6 frames at 53,218-53,261,
  also 51,764-51,765, 52,316-52,327) start on the other side of the step boundary, giving
  8 extra 0-update frames paired with 8 extra 2-update frames (685 vs 677). 1.10 and
  1.11-dev per-frame counter deltas are identical everywhere else to 53,300 and on 4-1 ..
  5-4 (shifted by the one frame). So none of the 10 is the 5-4 load (it lies after 82,881),
  and only one besides the 2-2 load is a lost update.

Fix proposal (one design for 2-2, 5-2, 5-3, 5-4):

- The load has no idle time: it is 14-18 frames of pure CPU, and the draw can only use the
  210k clocks the original leaves at its end (296k needed in 2-2, 240k in 5-4).
- Measured idle time after each of these loads in the original: the first update is the
  first fade step (471-475k clocks, a native overrun, ending 230-235k clocks before the
  vblank after next), then six short updates (10.5k) with 313k-337k clocks left each, then
  the next fade step. Same pattern after all four loads.
- Proposal A (deferral, preferred): do what 1.08-dev did for area changes and 1.07-dev for
  6-1: `init_background` marks these profiles pending (`$2258 = $FE`) instead of drawing,
  and the draw runs in the main-loop hook in idle frames of the fade-in, split in two
  (about 150k + 150k for 2-2, 120k + 120k for the castle) or whole in the first short
  frame (313k available; 2-2's 296k leaves only 17k, too tight). The renderers already
  initialise from `$FF` on their first update. Cost: none in time if the pieces fit the
  measured idle (verify with `watchrun.py`: the load and fade frames must match the
  original's vblank counts); risk: picture. Until the draw completes, the native backdrop
  that `$80AB` draws during the load is what the dim first fade step shows. Whether that
  is visible was not checked (no screenshots taken); if it is, draw in the frame before
  the first fade step brightens the screen enough to see, or blank the backdrop rows.
  Size: the dispatcher's pending path exists; splitting the 2-2 and castle draws into two
  calls is new renderer code (moderate).
- Proposal B (speed): make the load-time draws fit 210k with margin (2-2 needs at least
  -90k, 30% faster; castle 5-4 -30k; 5-3 has 9.6k of margin and needs headroom too).
  Harder: the per-update renderer is already tuned (Redraw cost, 1.06-dev).
- Either way, 4-1 and 4-2 (native loads 10k from a vblank) and 5-3 show how little room
  some loads have: any added load-time work should be measured against this table.

## 51,763: vblank trampoline pushes a scene update past a vblank (1.11-dev only)

Verified (`cmp.py`, `irqlist.py`, `segprof.py`):

- The act 3 story scene (master 1, scene 5) runs updates of about 694k clocks (two
  frames each). In the original and 1.10 the update starting at frame 51,761 reaches the
  wait 465 clocks before the vblank interrupt (555 before `$FCEC`); it is the closest
  call of the whole run to 5-4 in both builds (next closest: 2,415 at 47,884).
- 1.11-dev: main-loop work in that update is the same (675,594 vs 675,552 clocks), but it
  starts 234 clocks later (its waking vblank handler is 228 longer: 17,766 vs 17,538) and
  the vblank inside it is again 228 longer (16,245 vs 16,017). 465 - 234 - 228 - 42 < 0:
  the wait is reached about 33 clocks after the interrupt, the update spans 2 vblanks
  instead of 1 and the game loses that frame (counter 209 vs 210). The scene then runs one
  frame late and 4-1 starts at 53,288 instead of 53,287; every later stage start through
  5-4 stays one frame later than the original and 1.10.
- The 228 clocks are the 1.11-dev vblank palette path in ORIGINAL mode: `$FD13`
  `jsr $FEC0` (trampoline `clc`, `tma #2`, `pha`, `lda #$46`, `tam #2`, `jsr $5000`,
  `pla`, `tam #2`, `rts`) and `palette_entry` / `vblank_plain` (lock, `LIVE`,
  `PALETTE_STATE` tests and `jmp $F3B5`) around the native upload = 76 CPU cycles
  (palette-lag review: "the vblank's palette trampoline alone is 76 cycles a frame"). 1.10
  calls `$F3B5` directly (`$FD13` = `jsr $F3B5`, read in the ROM). Every 1.11-dev update
  therefore ends 228 clocks later per vblank it contains plus the one that woke it.
- Exposure in this run: across 1.10's updates to 5-4 only this one ended within 1,000
  clocks of a vblank; in 1.11-dev the closest remaining are 47,884 (1,815 clocks; 2,415
  in 1.10) and the 4-1/4-2/5-3 loads (6-7k).

Fix proposal: make ORIGINAL and NES-A/B pay nothing in the vblank. These modes never need
the dispatcher (`LIVE` stays 0; the native upload tests the lock itself); only a change
from a mapped mode needs the full re-queue, which configure can do when it switches mode.

- Zero-cost form: point `$FD13` at a RAM entry, as WAITR does for the wait. In ORIGINAL /
  NES that RAM holds a byte-for-byte copy of the native upload `$F3B5-$F421` (about 109
  bytes; same instructions, so the same cycles, assuming RAM and ROM accesses cost the same
  on the HuC6280: inferred, to verify with a trace); in GB DMG / HELL / SMS it holds
  `jmp $FEC0` (unchanged behaviour there). Configure and the reset trampoline write it
  before interrupts are enabled, as for WAITR. RAM: 109 bytes in `$3234-$37BF`, which the
  palette-lag review's static audit and run-time check found unused by the game; it needs
  the project's lifecycle/overlap audit before it is claimed (AGENTS.md).
- Cheaper but not zero: a 3-byte RAM vector (`jmp $F3B5` or `jmp $FEC0`) costs +4 cycles
  (12 clocks) per vblank instead of 76; it would have passed here (465 - 2 x 12 - start
  shift), but leaves a residual.
- Risk: moderate (vblank path, mode switching, menu preview; `check_menu.py` and the
  palette-lag runs must be repeated); size small. Verification: `watchrun.py` on the
  pinned recording must give the 1.10 update frames at 51,763 and 4-1 at 53,287.
- The mapped modes cost the same 76 cycles plus their own work; making them equal to
  ORIGINAL is a separate question (palette-lag design).

## 65,934: native, Japanese text (no patch cause)

Verified: on the same re-aligned input the unmodified ROM in Japanese (`entered` state
with language 0) and in English (native title shortcut) differ from unmodified frame
65,932 (patched 65,933): the 4-4 end scene update takes 487,989 clocks in Japanese and
285,969 in English; the Japanese one spans a vblank and loses a frame. Text updates
differ by language much earlier too (from 1-2's frame 5,920 on, for example 174,870 vs
50,139 clocks) without ever crossing a vblank before this one. 1.11-dev Japanese vs English: 488,145 vs 285,885 at the same update, the same
loss. The unmodified Japanese run then starts 5-1 at 70,017 against 70,012 in English.

So the earlier statement "language does nothing in the original code" holds only to frame
53,287, where the earlier unmodified runs left the recording; the 4-4 end scene had never
been replayed on the unmodified ROM. The patch adds nothing here; a Japanese run of the
original game is one frame slower at this scene. No fix (it is the game's own cost).

## What is not established

- Real hardware: everything is emulator evidence; the 465-clock margin at 51,763 and the
  load margins are emulator timings.
- Whether the 2-2 loss is absorbed at every 2-2 clear (here it was, mechanism not found),
  and whether the 5-4 loss is absorbed at 5-4's end.
- 6-1 to the ending: not compared against the original (the unmodified replay does not get
  there). Other draw-at-load stages beyond 5-4 (6-1 draws on its first update by design)
  were not measured.
- Whether the 1-2 phantom object is visible or affects play in other routes; other areas'
  object walks reading changed bytes were not surveyed.
- Loads after a death (respawn) were not in the recording.
- The fix proposals are not implemented or measured.
