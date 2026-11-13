# Cinema start under the palette lock (cinema-lock): review F1 of palette-exact

Fixes F1 of [palette-exact-review.md](palette-exact-review.md) (branch
`palette-exact`, `3379c90`): in a mapped mode (GB DMG, APOCALYPSE, SMS) the
palette worker's cinema re-queue was lost when the game held the palette
lock at a cinema's start. Emulator evidence only (Geargrafx `78fc3d7`: the
review's in-process probe core `libgxr*.so` and the headless emulator for
the gates), no real-hardware data. **Verified** = measured here;
**inferred** = read in code or reasoned, not measured.

Builds: "base" = the tip of `load-exact` (`dfd4a22`,
`27d1eaa0…dcf0`, "palette timing 3, original load timing"); "new" = this
branch (`228b741d…59d5`); "pt2" = palette timing 2 (`abfe6fb8…12f1`) as the
reference for the colours. Recording `research/longplay/full-load.json`
(base and new; up to frame 82,963 it is `full-exact.json` byte for byte, so
the F1 frame is 65,923 here too); pt2 on `full.json` (the review's runs),
aligned frame + 0 up to 51,762, + 1 to 82,963, + 2 after (pt2's act 3 frame
and the two idle shifts; checked: the 11 cinema starts fall on exactly
those offsets).

## Mechanism (verified, base build, GB DMG; the same in SMS and APOCALYPSE)

Writes to `$2260` (queue count) and `$2283` (lock) with the writing PC, and
the RAM state at every `$FD13`, frames 65,921-65,927 (the 4-4 clear into the
act 5 scene, master 1 from 65,903):

| Frame | What happens |
| --- | --- |
| 65,922 | the game sets the lock (bank 4 `$8203`) |
| 65,923 | the game queues an entry (`$F350`); the worker sees `$2240` = 1 and `$2104` bit 7 set, runs `QUEUE_ALL` (`$F394`, keeps the lock as it was), clears bit 7 and switches `RENT` to MN. The vblank: locked, nothing uploaded (90 clocks) |
| 65,924-65,925 | a second entry queued; locked vblanks |
| 65,926 | `$F450` calls `$F345` (`stz $2260` and a `tii` over the queue table: the 512-colour entry is gone) and clears the lock (`$F456`); the scene queues its own palettes (272 colours) under the lock (`$F4ED`, `$F350`) and unlocks (`$F564`). The vblank uploads those 272 (12,099 clocks) |
| after | bit 7 clear, `RENT` MN: nothing queues the other 240 colours again; GB DMG's VCE entries 272-511 keep `$040` where pt2 has `$000` for 737 frames (65,927-66,663), until the scene loads them |

The review's description is right. Of the 11 cinema starts of the
playthrough this is the only one where the worker meets the lock (the other
ten re-queue with the lock clear and upload 512 colours at the next
vblank).

## Change

`src/palette/main.asm`, `worker`, cinema branch (only change): after `lda
PALETTE_STATE` / `bpl worker_cinema_original` (bit 7 set: the VCE holds
mapped colours),

```
 lda PALETTE_LOCK
 bne worker_cinema_done
worker_requeue:
 jsr QUEUE_ALL
```

(plus the label `worker_requeue`, which emits nothing, and a comment).
While the lock is held the worker leaves everything as it is: bit 7 set,
`LIVE` 0 (its `stz` comes first) and `RENT` in MS with its gate shut (the
worker's `stz FASTOK`). The re-queue cannot be lost, because nothing clears
bit 7 without queuing all 512 colours (inferred, by reading every writer:
`plain_requeue`, `cinema_requeue`, this branch, and configure, whose caller
`set_palette` queues them), and `RENT` is never MN while bit 7 is set
(`rent_install` installs MN only with bit 7 clear and `LIVE` 0; bit 7 is
set only by the gameplay paths, after the worker's switch to MS). So the
re-queue happens at whichever comes first:

- the worker's next run with the lock clear (`WAITR` calls it whenever the
  queue is not empty): re-queue, clear bit 7, MN, and the next vblank
  uploads 512 colours at the native cost; this is what happens at 65,926;
- a vblank with colours queued and the lock clear before that: MS's gate
  (`dec` 0 -> `$FF`) sends it to the dispatcher, `LIVE` 0 -> `vblank_plain`
  -> `plain_requeue` (bit 7 clear, `QUEUE_ALL`, native upload, +113 cycles),
  as pt2 did at its first unlocked vblank. Exercised by the forced vblanks
  below, not by the recorded route.

The gameplay branch already tested the lock (`worker_ms`); the
dispatcher's `palette_vblank` returns on the lock before any re-queue. Bit
7 clear with the lock held (a cinema reached from the title, or after the
re-queue) still switches to MN as before: nothing is queued there, so
nothing can be lost.

Size: 5 bytes (`lda abs`, `bne`). Bank `$46` `$5B00-$5FFF` (the palette
module's timing section): used to `$5FE9`, **22 bytes left** (`$5FEA-$5FFF`,
`$FF`; base: to `$5FE4`, 27 left). No new RAM; no other bank changes. The
ROM differs from base in 689 bytes, all in bank `$46` `$5D1B-$5FE9`:
the 5 inserted bytes, the code after them moved by 5, the two branch
offsets over them (`beq worker_gameplay`, `bpl worker_cinema_original`) and
5 absolute operands into the moved code; nothing outside refers to the
moved code (verified byte by byte against the listing; `wait_mapped`'s
`jsr worker` is unchanged, `worker` stays at `$5D12`). Cost in the main loop: 7
cycles more in the worker at each of the other ten cinema starts (idle
time in the wait).

## Proof 1: all 11 cinema starts, the colours (verified)

In-process, cold power-on with the mode in backup RAM, title left as
`longplay_lib`, then `full-load.json` as one input list (126,001 frames);
RAM state at every `$FD13`, the worker's entry and `worker_requeue`, `RENT`
hashed at every vblank, the VCE colour table at every frame end
(`tools/cl_run.py`, the review's `rv_run.py` with this build's symbols).

The F1 start, new build (GB DMG, SMS and APOCALYPSE identical):

| Frame | Queue, lock, `$2104`, `RENT` gate, `LIVE` at `$FD13` | Palette path clocks: new / base / pt2 (its frame + 1) | Worker |
| --- | --- | --- | --- |
| 65,923 | 1, 1, `$C0`, `dec` (MS), 0 | 90 / 90 / 198 | locked: leaves all as is |
| 65,924-65,925 | 2, 1, `$C0`, MS, 0 | 90 / 90 / 198 | locked: the same |
| 65,926 | 1, 0, `$40`, `lsr` (MN), 0 | **22,179** / 12,099 / 22,617 | unlocked: re-queues 512, MN |
| 65,927 on | 0, 0, `$40`, MN | 69 / 69 / 297 | - |

22,179 clocks is 512 colours at the native cost, what the other ten cinema
starts pay; pt2 paid 22,617 (its dispatch). The re-queue now comes 3
frames later than base's (65,926 instead of 65,923), in the same frame as
pt2's.

VCE against pt2 over each whole scene (start of master 1 to the next
gameplay frame), entries 272-511 and all 512; frame-end samples that fall
inside an upload (at most 12 entries, each either the value of the frame
before or the value pt2 reaches a frame later: the review's criterion) set
aside:

| Cinema start (frame, stage before) | Scene frames | GB DMG new: frames with 272-511 different / any entry | GB DMG base | SMS new | APOCALYPSE new |
| --- | --- | --- | --- | --- | --- |
| 5,735 (1-2) | 4,400 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| 18,183 (2-3) | 9,594 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| 36,490 (3-3) | 16,796 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| 56,013 (4-1) | 1,106 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| **65,903 (4-4)** | 4,109 | **0 / 0** | **737 / 737** (max 240 entries) | 0 / 0 | 0 / 0 |
| 81,159 (5-3) | 1,721 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| 84,385 (5-4) | 2,121 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| 97,630 (6-3) | 4,670 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| 103,948 (6-4A) | 2,518 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| 108,456 (6-4B) | 2,771 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| 113,212 (6-4C, the ending) | 12,790 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |

(SMS and APOCALYPSE base: also 0 / 0 at 65,903, as the review found: the
lost entries are equal by value there; the upload itself was lost in all
three modes.) The worker's re-queue (`worker_requeue`) runs at 11 cinema
starts in every mapped mode: 5,748, 18,200, 36,504, 56,028, **65,926**,
81,174, 84,398, 97,646, 103,964, 108,471, 113,229 (base: the same with
65,923); the dispatcher's `plain_requeue`/`cinema_requeue` never run on the
route.

## Proof 2: timing (verified)

Same in-process runs for both builds in all six modes, compared frame by
frame (126,001 frames, 126,477 vblanks with the boot):

| Mode | Update counter, master flags, stage, area | Palette path cost per vblank | Frame-end clock |
| --- | --- | --- | --- |
| ORIGINAL, NES-A, NES-B | identical | identical at all 126,477 | identical |
| GB DMG, SMS, APOCALYPSE | identical | identical except **65,926: +10,080** (12,099 -> 22,179) | identical except 20 frames, -6 to +15 clocks (the wait loop's exit after the worker's 7 extra cycles at the ten other cinema starts and its run at 65,926) |

- The counter/master/stage/area arrays of the new build equal the
  load-exact record's in-process runs (`c2L-*`, `c2-L`) in all 126,002
  entries in GB DMG, SMS, APOCALYPSE, ORIGINAL and NES-A, so the 22 stage
  starts (1-1 0 ... 6-4C 111,227), the 63 area changes and the ending
  (126,001, master 1, scene 14) are on the same frames.
- Headless (`scripts/longplay_six.py run --mode original`, one emulator):
  **RESULT PASS**, 22 of 22 starts at the load-exact frames, the end at
  126,001; its `cnt/mas/m2/stg/are/bos/core/wide` arrays are byte-identical
  to load-exact's headless ORIGINAL run.
- ORIGINAL and NES never call the worker (`WAITR` is the native wait there),
  so the change cannot reach them; measured: equal to base at every vblank.
  Against published 1.10 (the review's `v110` run on `full-exact.json`,
  the same inputs to 82,963): equal at every vblank except the boot's first
  (+6,516, review F2, unchanged) and the 2-2 and 5-4 load fades
  (13,257-13,316, 82,899-82,957), which are load-exact's one-frame-earlier
  loads, not this change.
- Margin at the affected update (wait call `WAITR` to the next vblank):
  the update after 65,926's vblank reaches its wait 313,575 clocks before
  the next vblank (base 324,240: -10,665, the longer upload); the update
  before it 79,797 (unchanged). Over the whole run only three waits moved
  by more than 60 clocks: 65,927 (-10,665), 65,928 (+72), 97,647 (-90), all
  with more than 313,000 clocks left. Smallest margin of the run 735
  clocks (51,762's act 3 scene) in both builds. No update is lost (counter
  identical).

## Proof 3: vblank safety (verified)

- `RENT` at every vblank of the six runs, hashed and classified (the
  review's classes): GB DMG, SMS, APOCALYPSE: MN 63,077, MS 63,399, the
  reset stub once (base: MN 63,080, MS 63,396: the three locked vblanks
  65,923-65,925 are now MS, locked, 90 clocks either way); ORIGINAL, NES-A,
  NES-B: N 126,476 and the stub once. No other content, no `brk` executed in
  RAM in any run.
- Forced vblanks (the review's `rv_fuzz_worker.py` as `cl_fuzz_worker.py`,
  core `libgxr3.so`): a vblank handler call forced at every instruction
  from 12 before the worker's entry to 6 after its return (every 53rd past
  the first 260), at the worker's runs in frames 5,748 (a cinema start),
  10,153 (a gameplay start), 65,923 (the new locked path: 13 instructions),
  65,924 (locked again) and 65,926 (the re-queue after the unlock, and,
  forced before the worker, the dispatcher's `plain_requeue`), in GB DMG,
  SMS and APOCALYPSE; each run on 200 frames and compared with the unforced
  run (VCE where the RAM palette agrees, `RENT`'s form, `brk`). Results:

  | Frame (worker run) | Worker instructions | Forced calls, GB DMG / SMS / APOCALYPSE | Returned, no `brk` | Flagged |
  | --- | --- | --- | --- | --- |
  | 5,748 (cinema start, re-queue) | 51 (palette-exact: 49) | 69 / 69 / 69 | all | 6 / 6 / 6, form only |
  | 10,153 (gameplay start, `rent_ms`) | 8,979 / 8,982 / 13,680 | 443 / 443 / 532 | all | 0 |
  | 65,923 (locked: the new branch) | 13 | 31 / 31 / 31 | all | 0 |
  | 65,924 (locked) | 13 | 31 / 31 / 31 | all | 0 |
  | 65,926 (unlocked: re-queue, `rent_mn`) | 51 | 69 / 69 / 69 | all | 0 |

  2,018 forced calls in all. The 18 flagged points are the review's
  residual, the same 6 per mode as in its run on palette-exact: a vblank
  forced 7 to 12 instructions before the worker's entry at 5,748 re-queues
  in the dispatcher, the queue is then empty, the worker is not called and
  `RENT` stays MS for that scene; the VCE equals the unforced run's in
  every compared frame (0 mismatching, 0 unmatched). Every point forced
  inside the new instructions (65,923/65,924: the whole 13-instruction run;
  65,926 and the ten others: the not-taken `lda`/`bne`) left `RENT` a whole
  form and the colours right.
- The dispatcher path, separately (`cl_disp.py`, GB DMG): at 65,926 a
  vblank forced 1, 5 and 12 instructions before the worker's entry (queue
  1, lock 0, `$2104` `$C0`, `RENT` MS, `FASTOK` 0, `LIVE` 0): the handler
  returns, `$2104` becomes `$40`, the queue is empty, `FASTOK` `$80`, `RENT`
  still MS, and the VCE equals the RAM palette (unmapped) in 512 of 512
  entries: `plain_requeue` uploaded all 512 colours. No `brk`.

## Proof 4: gates (verified, emulator)

Headless, one at a time (`tools/gates.sh`, load-exact's gate script on this
branch), new build:

| Gate | Result |
| --- | --- |
| `python3 -m unittest discover -s tests` | 54 tests OK |
| `scripts/audit_public.py` | passed |
| `scripts/check_boot.py` | pass: idle frames 1-899 identical to the original |
| `scripts/check_menu.py --only options --only reset` | passed, 68 of 68 ok; the menu shows `V1.11-DEV` |
| `scripts/check_menu.py --only select` | passed (level select 0-20 ok) |
| `scripts/palette_lag.py pairs` | 36 of 36 pairs: first update +0 clocks, no lag frame, irq clocks equal; output identical to load-exact's |
| `scripts/palette_lag.py fastok` (195-215 colours) | output identical to load-exact's (195-196 end `$00` with the queue done, 197-199 `$81`, 200-215 `$80`; never 1 after a fallback) |

## Not covered

Real hardware. A cinema reached with the lock held and the queue then left
empty after the unlock (the re-queue then waits for the scene's first
queued colours; with nothing queued the VCE is not changed either; not
seen on the route). The dispatcher re-queue path (`plain_requeue` after a
locked start) only under forced vblanks, not on a recorded route.
Japanese and Chinese text, stages off the route, deaths and Continue,
`check_bram.py`, `palette_lag.py e2e/loadtime` (the save, reset and menu
code is unchanged; not re-run). Rendered pictures (the VCE comparison
stands in for them; the review found the F1 entries were not drawn).

## Rerunning

Probes in `/workspace/build/cinema-lock/tools/` (scratch, not committed;
they use the review's core in `/workspace/build/palette-exact-review/lib`):

```sh
python3 tools/asm.py WORKTREE OUT                              # listing + symbols of src/palette
python3 tools/cl_run.py TAG ROM MODE research/longplay/full-load.json OUT/main.sym
python3 tools/cl_an.py TAG t2-MODE                              # cinema starts, VCE against pt2
python3 tools/cl_cmp.py TAG BASETAG                             # arrays, per-vblank cost, margins
python3 tools/cl_mech.py ROM MODE 65921 65927                   # queue/lock writers
RV_LIB=.../libgxr3.so python3 tools/cl_fuzz_worker.py ROM MODE 5748 10153 65923 65924 65926
```

The ROM is not in `/workspace/roms/` (to be built with `start-pos`).
