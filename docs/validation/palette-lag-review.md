# Palette timing (palette-lag): adversarial review

Reviewed: `3a1dbe4..64173ee`, build `4147a8b1...a8849` ("apocalypse, reset 2,
palette timing"). Emulator evidence only (headless Geargrafx `78fc3d7`), no
real-hardware data. "Verified" = measured or reproduced in this review;
"inferred" = read in the source, not reproduced. The review probes were
scratch scripts built on `scripts/palette_lag.py` (menu route, stored runs);
each is described well enough below to be rebuilt.

## Verdict

**Needs one small fix first (F1), then fit for the hardware test with the
caveats below.** The design holds up: worker, `SHADOW`, `fast_upload`, the
padded NES loaders, the reset order and the RAM claims survived every attempt
except the ones listed. F1 is the owner's reported defect (3-2 loses frames
1033 and 1104) still reachable through one menu route.

## Findings, by severity

### F1 (high, verified): a mapped mode -> NES-A/NES-B at Run still shifts the restart; 3-2 lags again

- What: `preview_palette` (`src/options/main.asm`, "opened in a mapped mode the
  live mode stays") leaves the NES value unapplied until Run, so Run's
  `set_palette` takes the changed path (`QUEUE_ALL` + `PALETTE_CONFIGURE`)
  that Original's Run does not. It is the only palette change left that
  happens at Run instead of in the preview.
- Evidence: probe with two menu sessions (menu 1: Run into 1-1 in mode 1;
  menu 2, opened in that mode's gameplay: 3-2 and mode 2, every variant the
  same number of presses; then 3-2's stored input, 1,200 frames; per frame
  the update counter, Ryu, sound RAM hash, interrupt entry clocks):

  | menu 1 -> menu 2 | 3-2 first update | sound RAM vs ORIGINAL->ORIGINAL | lag frames |
  |---|---|---|---|
  | ORIGINAL -> ORIGINAL, ORIGINAL -> NES-A, GB DMG -> GB DMG, GB DMG -> ORIGINAL | +0 clk | equal in all 1,200 frames | none |
  | GB DMG -> NES-A, SMS -> NES-B, APOCALYPSE -> NES-A | +6,369 clk | differs from frame 0 on | 1033, 1104 |

  Original issues 3-2's music command 2,292 clocks before a vblank on this
  route (the author's own diagnosis), so +6,369 moves it across: the sound
  driver runs one tick off for the stage, exactly the pre-fix defect.
- Scope: one stage attempt (until the next load restarts the music), and
  only when the menu was opened in GB DMG / APOCALYPSE / SMS and NES-A or
  NES-B is run. The author's survey never took this route (every menu was
  opened in Original).
- Smallest fix: let the NES value go live in the preview whatever mode the
  menu opened in (drop the `and #$10` / `beq` special case, 3 instructions),
  so Run finds nothing to change. A previewed mapped -> unmapped change is
  clean at Run (GB DMG -> ORIGINAL above: +0). Cost: while NES-x is
  highlighted in a menu opened in a mapped mode, the screen shows the RAM
  palette unmapped (Original's colours) instead of the opened mode's; the
  menu text and `check_menu.py`'s preview cases need the same change.
  Alternative that keeps the picture: apply the change before
  `close_window` and settle it with the cancel path's wait loop.

### F2 (low, verified race; visible harm inferred): `FASTOK` can be set after the vblank already ran the fallback

- What: the worker's last `$12` test is before the last colour; `lda #1` /
  `sta FASTOK` comes about 180 cycles later (`worker_advance`, `worker_entry`,
  `worker_border`). A vblank in that window runs the fallback (`dec FASTOK`
  -> `$FF`, `stz`), then the worker resumes and writes 1. Second form: a
  vblank during the last colour of any entry whose fallback folds the queue
  to `W_ENTRY + 1` entries or fewer also ends in `worker_border`, with
  entries it never converted.
- Evidence: 2-2, GB DMG, the area change near frame 792 (worker entered
  42,627 clocks before the vblank, real interrupt timing; only the queued
  entry's length was varied, state reloaded per trial). 201-204 colours:
  finished, fast upload. **205, 206, 207 colours: back in the main loop
  (`$E064`) with `FASTOK` = 1, queue count 1, first colour 54, `$2104` =
  `$E0` (left-over)**. 208 and more: aborted, `FASTOK` = 0. The window is 3
  colours (about 600 clocks, 0.17 % of a frame).
- Consequence (inferred): none if the next update reaches `WAITR` before the
  next vblank (the worker's `stz FASTOK`); timing is never affected. If the
  next update spans a vblank with the palette unlocked, `fast_upload` sends
  whatever is queued from `SHADOW`: stale colours for entries queued since,
  and for a left-over entry that wraps past colour 511 a `TIA` that reads
  past `$3FFF` into bank `$46`. Wrong colours stay until re-queued.
- Smallest fix: make completion one instruction. Worker end `inc FASTOK`
  instead of `lda #1` / `sta`; the two fallback exits store `$80` instead of
  `stz` (empty path: `lda #$80` / `sta` / `sax` is the same 10 cycles as
  `stz` / `sax` / `nop`). A vblank in between then leaves `$81`, never 1.

### F3 (low, verified): the mode change relies on the next `WAITR` seeing the queue; GB DMG's black differs around cinemas

- `LIVE` changes only when the worker runs, i.e. when a wait finds queued
  colours. Stage clear -> cinema -> next stage, 4-1 into 4-2 (stored run,
  3,000-frame tail, Run to skip): `LIVE` stays `$10` for 15 cinema frames
  (2487-2501: GB DMG shows its darkest shade where Original is black; the
  author's stated change) and stays 0 for the first 17 gameplay frames of
  4-2 (2729-2745: true black where GB DMG gameplay is its darkest shade),
  then the first fade step arrives one frame late (2746, 342 entries). All
  entries concerned are black in Original; SMS and APOCALYPSE show nothing.
  No Original colour leaked in a mapped mode's gameplay in this transition.
- Inferred weak spot of the same mechanism: an unmapped -> mapped change
  whose 512 queued colours are taken by a vblank's native upload before the
  next `WAITR` (a vblank inside `set_palette`'s `QUEUE_ALL`..configure..wait,
  about 1,200 cycles) leaves Original colours on screen until the game next
  queues a colour. The menu's waits follow at once and `check_menu.py`
  passes, so this needs `close_window`/draw timing to change; not seen.
- Fix if wanted: the empty-queue fallback exit can test `MASTER_STATE` in
  its 10 spare cycles and requeue when the state and `PALETTE_STATE` bit 7
  disagree. Cosmetic; no timing value.

### F4 (note): coverage and tools

- The 11 stored runs contain no death, no Game Over / Continue, one boss
  (5-4) and no ending. Added here: 3-2 with Ryu's health set to 1 at frames
  1000/1500/2000/2500/3000 in every variant (three deaths, Game Over at
  2285, Continue at 3367, 5,537 frames): GB DMG, SMS, APOCALYPSE and NES-A
  equal ORIGINAL in counter, lives, health and state in every frame; sound
  RAM equal (SMS: one frame); interrupt entries within 48 clocks.
- `palette_lag.py busy` does not work on this build: its breakpoint at
  `$37C0` stopped 6-8 times in 6,800 updates (5-3), and each stop desyncs
  the frame steps. Do not cite its "min left". `step_recording` (used by
  `e2e`) has the same step-length hazard after a breakpoint: one variant of
  a probe here ran two frames in one step. Trace-log probes are reliable.
- 1.11-dev ORIGINAL is frame-identical to 1.10 in the runs, not
  clock-identical (the vblank's palette trampoline alone is 76 cycles a
  frame; pre-existing, not from this branch).

## The author's residual risks

1. **Wait-loop phase (mapped modes)**: confirmed bounded and not
   accumulating: the vblank re-synchronises every frame. Measured: at most
   18 clocks over 3,000 frames of cinema + 4-2 (APOCALYPSE differs in 580
   frames, never more), 48 at one Continue reload. Only an update ending
   within ~10 cycles of a vblank could flip. Closing it means padding every
   worker path to a multiple of the wait loop's 10 cycles; not worth it.
2. **Fallback**: in the 11 runs it occurs only at area changes (2-2 x2, 5-2
   x3, 5-3 x6), never in ordinary gameplay. Measured at 5-3's changes
   (instruction traces, frames 5296 and 6495): the two vblanks cost +2,364
   and +16,398 clocks; the updates they delay keep 310,758 / 267,483 and
   308,436 / 286,593 clocks before their vblank. No risk there. Elsewhere it
   needs an update that queues colours and ends later than their conversion
   time before the vblank (16 colours: about 4k clocks; 512: 107k) followed
   by an update within 2k-16k clocks of overrunning: two consecutive
   near-limit updates. Not seen; unmeasured where large palette changes meet
   heavy updates (boss kills, the ending). No cheap closure: the deferred
   colours must be written in some vblank Original does not pay for.
   `palette_now` (+1.6k clocks, 1-1 and 2-2 area starts only) has 42.7k of
   slack.
3. **Cinema entry (+21k in one vblank)**, and the same re-upload at the
   first fade step of the next stage: 4-1 -> cinema -> 4-2 carries nothing
   over: counters equal in all 5,488 frames, sound RAM equal from the frame
   after the entry, interrupt entries within 18 clocks.
4. **Interrupts inside the NES unpack**: NES-A through the cinema and 4-2:
   one frame, 6 clocks. ORIGINAL -> NES-A by the menu (the route of the
   original defect): 0 frames, 0 clocks, first update +0. The claim "NES-A/B
   are clock-identical to ORIGINAL" is sound for a saved mode and for a
   menu opened in Original or NES; false for F1's route.

## RAM claims (`$37C0-$37FD`, `$3C00-$3FFF`)

Static audit of the original ROM (review disassembler, HuC6280 opcode
lengths; recursive descent from the vectors, the master-state table `$E851`
and its jump tables, plus a scan of every byte offset):

- Code runs only from bank 0 (`$E000`), banks 1-3 (gameplay) or 4-6
  (cinema, ending) at `$8000-$DFFF` (`$E7E6`, table `$E851`), the sound
  driver's bank `$38` at `$4000`, and RAM (`$2205`, `$3852`). No traced or
  untraced `jsr`/`jmp` enters `$4000-$7FFF` except `$4000/$4003/$4006`.
- In those eight banks, at **every byte alignment**, 151 byte patterns form
  an absolute, indexed, indirect-jump or block-transfer operand reaching the
  two ranges (index reach 255 included). All 151 were read: tables, text,
  script data or the operand bytes of another instruction. The only real
  one is the reset's clear (`$E025 tii $2000,$2001,$1FFF`).
- Traced code uses `$2000-$3233` and `$3800-$3A94` (+11) by absolute and
  indexed operands, nothing in `$3234-$37FF` or `$3AA0-$3FFF`. The sound
  driver's indirect stores (`sta (<$85),y`) go to per-channel stacks from
  the table at `$50FF/$510B`: `$3A95-$3B19` + 17, top `$3B2A`. Block
  transfers through `$2205` take destinations `$04xx`, `$22xx`, `$2Exx`,
  `$30xx` or the palette (`$2286`, `$2686`).
- Patch modules: no file in `src/` names an address in either range
  outside `src/palette`, `src/nes-palette` and the menu's wait (every
  `$3xxx` literal was listed). In the built ROM the code at the start of
  banks `$40`, `$44-$47` and `$56` was read the same way (nothing); the
  pattern hits in the modules' data banks were not read one by one.
- Runtime, added: in ORIGINAL mode over the death / Game Over / Continue run
  above, `$3234-$37BF`, `$37C0-$37FD`, `$3B40-$3BFF` and `$3C00-$3FFF` never
  change at a frame end (`SHADOW` stays zero).
- Not provable statically: stores through zero-page pointers whose value is
  computed at run time in code only reached by RAM vectors (`$2029`,
  `$2031/$2033`, `$2013`), and reads. Immediate pointer loads name only
  pages `$20`, `$2E`, `$31`. Still unwatched at run time: the ending and the
  bosses other than 5-4's.

## Other questions

- **Concurrency**: besides F2, sound. The worker aborts before each colour;
  a vblank mid-conversion uploads from the RAM palette (correct colours);
  queue edits by the worker's split can only duplicate colours. Interrupt
  code is bank 0 / RAM (`$2E4F-$2E54` hooks: `$FCD2`, `$E435`, `$E493`,
  `$FD8C`) or saves the MPRs (sound), so the worker's MPR2/MPR3 are safe;
  zero page `$20-$26` is saved by both sides. `WAITR`/`ANIMR` are written by
  the reset before `cli` (RAM clear `$E025`, then `$FFE6` -> `$5B00`: the
  settings load, then configure) and by `set_palette`; `$2100` has no other
  writer. `$E061` is the game's only vblank wait.
- **`check_menu.py`**: narrow and justified. `BORDER_MAP`, `$37E4-$37E8` and
  `SHADOW` are written before they are read in the same worker pass; `LIVE`,
  `FASTOK`, `WAITR`, `ANIMR` and `FU_COUNT` are still compared. The one path
  that reads stale `SHADOW` is F2.
- **Regressions**: `src/bram` differs in the trampoline's call only; the
  load-then-configure order is right. `stage61-upload` ends at `$5113`, the
  HUD code occupies `$5120-$51A0`, no module ranges overlap, the new code
  sits on bytes that were `$FF`. `patches/`, `release/`, `VERSION` untouched.
  Cycle counts checked by hand: `palette_entry` (13 / 37 / 46), `ANIMR` (24
  both ways), 1-1's NES copies (580 in every mode), `wait_mapped`'s branches.
- **Hardware**: nothing new in kind: the game already runs RAM code
  (`$2205`, `$3852`); `fast_upload`'s `TIA` is the native one, in the vblank
  handler; the worker and configure use no block transfer. Equality with
  Original rests on identical instruction streams (ORIGINAL, NES, fast
  upload), so the +1 cycle of real VDC/VCE accesses cancels; the measured
  thresholds (107k for 512 colours) will differ a little. The settings load
  at power-on was tested only with this emulator's always-unlocked backup
  RAM (pre-existing caveat). The few-clock residuals are below what a real
  console's reset phase varies by.

## Does any palette mode still risk affecting a speedrunner?

- **Saved mode loaded at power-on, menu never opened**: no measurable risk.
  NES-A/NES-B run Original's clocks; GB DMG, APOCALYPSE and SMS differ by at
  most tens of clocks, plus transition vblanks that have a quarter of a
  frame or more to spare.
- **Chosen in the menu**: clean, except **running NES-A or NES-B from a menu
  opened in GB DMG, APOCALYPSE or SMS** (F1): that stage attempt can run its
  music one tick off and lose frames (3-2: two).
- **Remaining, unmeasured**: the fallback meeting two consecutive near-limit
  updates in a mapped mode (boss kills, the ending).
