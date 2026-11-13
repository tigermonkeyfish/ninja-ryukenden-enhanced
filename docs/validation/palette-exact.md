# Palette timing exact (palette-exact): the vblank palette path at 1.10's cycles

The owner: "I do not want palette changes impacting speedrunners." Emulator
evidence only (Geargrafx `78fc3d7`: the headless emulator and the in-process
tracer core of `research/longplay/drift`), no real-hardware data.
**Verified** = measured here; **inferred** = read in code or reasoned, not
measured.

## The defect (diagnosed before, `longplay-code-drift.md`)

1.11-dev palette timing 2 (`abfe6fb8...12f1`) called the trampoline `$FEC0`
from the vblank interrupt (`$FD13 jsr $FEC0`), which mapped bank `$46` and ran
`palette_entry`'s dispatch before the native upload: 76 CPU cycles (228
master clocks) more than 1.10's `jsr $F3B5` at every vblank, in every mode.
The act 3 story scene's update from frame 51,761 reaches its wait 555 clocks
before `$FCEC` in the original game and 1.10; with two vblanks inside it
1.11-dev arrived late and lost a frame, so 4-1 started at 53,288 instead of
53,287 in all six modes.

## Design

`$FD13` now calls `RENT` (`$3740`), the upload in RAM: `jsr $3740` is the
same 7 cycles as `jsr $F3B5`, and what `RENT` holds is decided outside the
vblank (`src/palette`, "Palette timing").

- **Original, NES-A, NES-B** (`$2100` bit 4 clear): `RENT` is the native
  upload `$F3B5-$F421` byte for byte (copied from bank 0, `$F3B5-$F428` so
  the copy has one length in every mode; the bytes after its `rts` are never
  run). Nothing else runs in the vblank. These modes never needed the
  dispatcher: `LIVE` is 0 there and the native code tests the lock itself;
  the one thing the dispatcher did for them, re-queuing all colours after a
  mapped mode (PALETTE_STATE bit 7), is now done by the change itself:
  `set_palette` queues all 512 colours on a mapped -> unmapped change (as
  before) and configure clears bit 7 for these modes.
- **GB DMG, APOCALYPSE (HELL), SMS**: `RENT` is the native upload
  instruction for instruction with a gate. Cycle by cycle against `$F3B5`:

  | Native | Cycles | `RENT`, M form | Cycles |
  | --- | --- | --- | --- |
  | `lda $2260` / `beq` (empty: rts) | 5 + 2/4 | the same | 5 + 2/4 |
  | `lda $2283` / `bne` (locked: rts) | 5 + 2/4 | the same | 5 + 2/4 |
  | `phx` | 3 | `dec FASTOK` (MS) or `lsr FASTOK` (MN) | 7 |
  | `phy` | 3 | `bne dispatch` (not taken) | 2 |
  | `lda #$04` / `sta $2208` | 2 + 5 | `phy` | 3 |
  | `lda #$04` / `sta $2209` | 2 + 5 | `lda #$04` / `sta $2208` / `sta $2209` | 2 + 5 + 5 |
  | `cly`, the entry loop, the border | n | the same (colours from `SHADOW` / `BORDER_MAP` in MS) | n |
  | `ply` / `plx` / `rts` | 4 + 4 + 7 | `ply` / `rts` | 4 + 7 |

  X is never changed by the upload (the TIA leaves registers alone), so the
  native `phx`/`plx` (7) and the second `lda #$04` (2) pay for the gate (9).
  Every path, empty, locked or uploading the same queue, takes the native
  cycles.
  - MS (gameplay): `dec FASTOK`; colours from `SHADOW`, the border from
    `BORDER_MAP`. The worker's `inc` (0 -> 1) arms it; the upload counts it
    to 0. A visit to the dispatcher (gate not open) stores `$80`, so a
    worker interrupted after its last `$12` check ends at `$81` (review F2
    as before) and the gate stays shut until the worker's next `stz`/`inc`.
  - MN (cinemas, the title, the ending, a mapped mode before the worker
    has seen gameplay): `lsr FASTOK` with `FASTOK` 0 stays 0, so every upload
    goes through at native cost, from the RAM palette and `BORDER`: what
    palette-lag's `LIVE` = 0 path did, without its dispatch. Entered only
    while the VCE holds original colours (bit 7 clear): at a cinema's start
    the worker, in the idle time, queues all 512 colours (`$F394`) and
    clears bit 7 itself (the dispatcher's `cinema_requeue` did it in the
    vblank), then switches; a vblank that comes first still re-queues in
    the dispatcher as before.
  - The worker (main loop, idle) switches the form when it sees
    `MASTER_STATE` change (setting `LIVE` first): to MN by writing the source bytes while the MS
    gate is shut (`FASTOK` 0 after its `stz`), then `stz FASTOK` and the
    `lsr` opcode last; to MS by writing the `dec` opcode first (with
    `FASTOK` 0 it is shut), then the source bytes. A vblank at any point
    sees either a whole form or the dispatcher.
- **configure** (the menu's `set_palette`): rewrites `RENT` for the mode
  behind a routed entry: the `beq` at `RENT+3` becomes a `bra` to an `rts` at
  `RENT+$74` (written first), the body is copied, then the real `beq`
  offset and opcode are written last. A vblank inside that window uploads
  nothing and the queue waits one vblank (menu only).
- **Reset**: `palette_boot` writes `RENT` as `jmp $FEC0` (three bytes), so
  the reset takes exactly the cycles it took before: configure's copy loops
  now count down (2 cycles a byte less), which pays for the `jmp`, and a
  6 x 6-cycle delay makes up the rest (measured below). The first unlocked
  vblank (at the reset's `cli`, `LIVE` 0) reaches `vblank_plain`, which sees
  the `jmp` and writes `RENT` (`rent_install`), then uploads as before.
- The dispatcher (`palette_entry` from `$FEC0`) is reached only from MS's
  gate and the reset's `jmp`; `fast_upload` (the ROM copy reading `SHADOW`)
  is gone, `RENT` replaced it.

Size: bank `$46` `$5B00-$5FFF` (the palette module's range, 2 bytes left),
`$5000-$53FF` (the dispatcher). RAM `$3740-$37B4` (`$37B5-$37BF` reserved).
Bank 0 is unchanged except `$FD13`'s operand.

## Build

`a0019797765ff24e2266911ea9ad3f063652b8a135f393cbfe87691af52d2621`, the same
from either original (source: branch `palette-exact`; deliverables below).
Pristine identity: the parent source (`6503e9a`) rebuilds to palette timing
2 (`abfe6fb8...12f1`); `project.py apply` still gives 1.10
(`3d5c05df...bbf6`); `patches/`, `release/` and `VERSION` (`1.11-dev`, shown
in the menu: `check_menu.py` reads the window) unchanged.

## Tools

- `research/longplay/drift/` (reference probes): `shim_watch.cpp` +
  `pe.py` (Makefile target `watch`, `libgxw.so`): the tracer core rebuilt
  from a private copy of the Geargrafx source whose `Memory::Read` and
  `Memory::Write` call a hook for RAM offsets in a range (two inserted
  lines, nothing else changed), plus power-on with backup RAM forced and
  filled (Geargrafx enables it only for CD media unless forced). `pe_run.py`
  powers on with a mode's settings entry, leaves the title as
  `longplay_lib.boot_to_first_update` does, stops at 1-1's first update,
  saves and reloads there, then replays a recording as one input list and
  records per frame the counter, flags, stage, area, fingerprints, `RENT`'s
  gate byte and `LIVE`; the clocks of `$E06C`, `$E061`, `$FCEC`, `$FD13`,
  `$FD16`, `RENT`'s body and dispatch and `palette_entry`; and every access
  to the watched RAM with the accessing PC and bank. `pe_cmp.py` compares
  runs (per-vblank palette path cost `$FD13` -> `$FD16` frame by frame;
  counters; stage starts; lost updates = vblanks inside updates, as in
  `longplay-code-drift.md`; RAM writers). `pe_menu.py`: the same cost with
  the menu open.
- Check of the tool: the in-process power-on reaches 1-1's first update at
  the same master clock as the headless `longplay_six.py` (201,402,480) and
  its per-frame counters equal the headless runs' (palette timing 2 ORIGINAL,
  `full/raw/original.cnt.bin`, 5,000 frames; and the six headless runs on
  the old recording below, 57,500 frames each, against the in-process 1.10).
- Headless: `scripts/longplay_six.py` (WIDE now also leaves out `RENT`),
  `longplay_check.py`'s criteria; the gates below.
- `scripts/comparison_video.start_point` writes Original's `RENT` (the
  native upload and the `rts`) after loading a state made from the original
  game, as it writes `WAITR`/`ANIMR`; without it `check_menu.py` and
  `palette_lag.py pairs` (seed states) could not run.

## Proof 1: per-vblank cost (verified)

Clocks from `$FD13` (the palette call) to `$FD16` (its return) at every
vblank, the new build against 1.10 frame by frame, in the whole recorded
playthrough (power-on, title, 22 stages, every story scene, every stage
load, bosses, the ending: `full-exact.json`, 126,002 frames; 1.10 booted
without backup RAM) and on the old recording (126,003 frames; both builds
die the same way after 4-1, see proof 2). The rest of the vblank handler is
the native code in both.

| Mode | Vblanks (exact / old rec.) | Equal to 1.10 | Different |
| --- | --- | --- | --- |
| ORIGINAL | 126,002 / 126,003 | all / all | 0 |
| NES-A | 126,002 / 126,003 | all / all | 0 |
| NES-B | 126,002 / 126,003 | all / all | 0 |
| SMS | 126,002 / 126,003 | 125,984 / 125,996 | 18 / 7 |
| GB DMG | 126,002 / 126,003 | 125,984 / 125,996 | 18 / 7 |
| APOCALYPSE | 126,002 / 126,003 | 125,970 / 125,996 | 32 / 7 |

Palette timing 2 against 1.10 on the same frames: +228 at every vblank in
every mode (+108/+129 on a few paths, measured in SMS over 20,000 frames).
The costs seen include empty queues (69 clocks), locked queues (90), every
upload size up to 512 colours (22,179) and story scenes; the act 3 scene's
two-vblank update at 51,761 now spends exactly 1.10's clocks (it reaches
its wait 555 clocks before `$FCEC`, as in 1.10 and the original).

The differing vblanks in the mapped modes, all in the mapped modes'
transitions, none in ordinary play:

- Cinema entries (10 on the playthrough, the same frames in the three
  modes): the VCE holds mapped colours and the cinema shows original ones,
  so all 512 are uploaded once: 22,179 clocks (MN: native cost per colour)
  where 1.10 uploads fewer colours that frame; +6,468 to +21,462. Palette
  timing 2 did the same upload through the dispatcher in the vblank:
  22,617 at 5,748 against 22,179 now (in-process SMS).
- Fallbacks (the worker did not convert the queued colours before the
  vblank: area changes in 2-2, 5-2, 5-3; SMS and GB DMG 4 pairs, APOCALYPSE
  11 pairs): +2,658 to +2,871 at the first vblank, +16,398 at the next.
  Against palette timing 2: the first vblank +54 clocks (18 cycles: the
  gate and the `jmp` to the dispatcher before it decides, where palette
  timing 2 decided in the dispatcher), the second -228.
- Nothing else: the 9,559 uploads through `RENT`'s M form (MS from
  `SHADOW`, MN in cinemas) cost 1.10's clocks to the clock, so the gate
  costs nothing (in Geargrafx RAM and ROM accesses cost the same: measured,
  not assumed; real-hardware VDC/VCE waits are the same instructions).

Menu open (`pe_menu.py`: 1-1 at frame 1,500 of the recording, Select, 150
frames open, Select, 100 frames): the 159 vblanks from the opening to the
closing cost exactly 1.10's in all six modes (palette timing 2: +228 each).
After the close the 1.11-dev menu's own return puts the game's palette
uploads one frame from 1.10's (the same in palette timing 2, so not a
palette effect; `check_menu.py` covers the close). The menu's palette
preview has no 1.10 counterpart: a mode change re-queues 512 colours and
rewrites `RENT` behind its routed entry (a vblank inside that window
uploads nothing; the queue goes at the next).

Stage loads: the 22 loads of the playthrough are in the table above
(equal); `palette_lag.py loadtime` (22 Level Select entries x 6 modes, the
sound command and first update clocks): every mode equal to ORIGINAL's (+0)
in all 132.

## Proof 2: the act 3 frame is kept (verified)

The old recording `full-4bba5f4.json`, plain replay from power-on with
each mode's settings in backup RAM, menu never opened:

- In-process, whole recording, all six modes: 4-1 starts at **53,287**
  (palette timing 2: 53,288), and the update counter, stage, area and
  master flags equal 1.10's in **every one of 126,003 frames** (after 4-1
  both 1.10 and the new build leave the recording, which was made one
  frame later, the same way: 4-2 is never reached).
- Headless `longplay_six.py` (one emulator at a time), the recording cut at
  57,500 frames: 4-1 gameplay from 53,287 in all six modes; counters equal
  to the in-process 1.10 in all 57,500 frames.
- Lost updates by clock before the 5-4 load (frame 82,880), on the adjusted
  recording (the old one does not reach 5-4 for any build that keeps the
  frame; 1.10's 654 was measured there too): **654 in all six modes**, =
  1.10 (654; unmodified 653; palette timing 2 655). Over the whole
  playthrough: 1,044 in every mode and in 1.10. Closest calls, the same in
  every mode as in 1.10: 51,761 (555 clocks before `$FCEC`), 47,884
  (2,415), 51,759 (4,545).

## Proof 3: a full no-death playthrough for the new build (verified)

`research/longplay/full-exact.json`: `full.json` with one idle frame removed
at the 3-3 -> 4-1 hand-over (`scripts/longplay_realign.py build`, adjustment
`{"frame": 53288, "frames": -1}`; the same segments as
`full-unmodified.json`; gameplay inputs unchanged). Cold power-on (backup
RAM with the mode), the whole file as one input list, no re-syncing:

HEADLESS_EXACT_PLACEHOLDER

In-process, all six modes: the same 22 starts and the ending (master 1,
`$2241` = 14 at frame 126,002).

## Proof 4: against published 1.10 on the adjusted recording (verified)

1.10 booted as the tools boot it (no backup RAM, `--mode unmodified`):

V110_PLACEHOLDER

- ORIGINAL, NES-A, NES-B: update counter, stage, area and master flags
  equal to 1.10's in all 126,002 frames; all 22 stage starts identical
  (1-1 1, 1-2 2,832, 2-1 10,136, 2-2 13,241, 2-3 16,533, 3-1 27,777, 3-2
  31,401, 3-3 34,853, 4-1 53,287, 4-2 57,120, 4-3 60,357, 4-4 64,422, 5-1
  70,012, 5-2 73,263, 5-3 77,205, 5-4 82,881, 6-1 86,507, 6-2 88,445, 6-3
  93,809, 6-4A 102,301, 6-4B 106,467, 6-4C 111,228; first gameplay frame of
  each stage, which `longplay_check` reads one frame later as its marker
  where the two differ).
- GB DMG, APOCALYPSE, SMS: the same 22 starts, the ending, and the same
  lost-update count (1,044); the counter differs in one frame, 97,647: the
  6-3 -> 6-4 cinema's entry re-uploads all 512 colours (22,179 clocks
  against 1.10's 717), the update ends after the frame step's sample and
  the next frame is equal again (a sampling shift, no update lost). The
  CORE fingerprint differs from ORIGINAL's in 5-6 frames (60,708 in SMS;
  97,647; 106,198-106,216 every 6 frames), all single-frame samples; from
  5,668 on CORE differs from 1.10 in every mode, ORIGINAL too: the 1-2
  phantom object of `longplay-code-drift.md`, left alone by this branch.

## Proof 5: gates (verified, emulator)

| Gate | Result |
| --- | --- |
| `python3 -m unittest discover -s tests` | 54 OK |
| `scripts/audit_public.py` | pass (457 files) |
| `check_boot.py` | pass: every frame from power-on through the title equals the original; the reset's length is unchanged too: palette timing 2 and this build reach `NATIVE_INIT` (153,726), the timer start `$EA43` (2,076,090) and the `cli` (2,092,014) at the same master clocks (tracer, no backup RAM) |
| `check_menu.py --only options --only reset` | 68 of 68 |
| `check_menu.py --only select` | 21 Level Select entries and the language row, pass |
| `check_bram.py --only cycle` | 17 of 17, PASS |
| `palette_lag.py pairs` (36 opened/chosen pairs, 3-2, 1,200 frames) | all 36: first update +0 clk, sound RAM, counter, Ryu and stage equal, no lag frame, interrupt clocks equal (review F1 holds: mapped -> NES-A/B included) |
| `palette_lag.py loadtime` (22 x 6) | 132 of 132 equal to ORIGINAL (+0) |
| `palette_lag.py e2e` (saved mode at power-on) | all six: first update +0, gameplay fields equal in all 2,903 frames, 96 sound commands; NES-A/B every command at ORIGINAL's clock; GB DMG 6, APOCALYPSE 8, SMS 5 commands within -12..+60 clocks (the wait loop's exit after a worker run, palette-lag residual 1; min margin to the next vblank 146,208) |
| `palette_lag.py fastok` (review F2, 195-215 colours) | holds: a vblank after the worker's last `$12` check runs the fallback and leaves `FASTOK` `$81` (205-208 colours) or `$80`, never 1 |

## RAM audit

`RENT` takes `$3740-$37B4` (`$37B5-$37BF` reserved with it). Lifecycle:
zero from the reset's RAM clear (`$E025`); `palette_boot` writes `$3740-$3742`
(the `jmp`) before the `cli`; the first unlocked vblank writes `$3740-$37B4`
(`rent_install`); after that only configure (menu mode changes) and, in the
mapped modes, the worker's form switches (`rent_mn`, `rent_ms`: seven bytes)
write it; only the vblank's `jsr` runs it.

Write watch (every write, with the writer's PC; `--reads` also every read)
on `$3740-$37BF`:

| Build, recording | Accesses after the RAM clear |
| --- | --- |
| 1.10, `full-exact.json` from power-on to the ending (reads and writes) | none (only the clear: 128 reads, 128 writes at `$E025`) |
| unmodified HuCard (Japanese, its power-on default), `full-unmodified.json` from power-on through 1-1 .. 5-1 (it leaves the recording in 5-1: the Japanese 4-4 scene is one frame slower, `longplay-code-drift.md`), 126,002 frames (reads and writes) | none (only the clear) |
| this build, six modes x two recordings | writes only from `src/palette` (bank `$46` `$5B0D-$5B17` the reset's `jmp`, `$5BBF-$5C12` `rent_install`, `$5C18-$5C39` `rent_mn`, `$53D2-$53F0` `rent_ms`); no other writer |

The playthrough covers boot, title, attract-free start, all 22 stages,
every story scene, every boss (5-4's, the three 6-4 forms) and the ending
cinema; not covered: deaths, Continue / Game Over, the menu (its `RENT`
writes are configure's; `check_menu.py` compares RAM around it), Japanese
and Chinese text paths, and stages off the route. Static: no file in
`src/` other than `src/palette` names an address in `$3740-$37BF`; the
palette-lag review's byte-pattern scan of the original ROM's code banks
found no operand into `$3234-$37FF` except the RAM clear.

## Residuals

- Mapped modes, per vblank: cinema entries (one 512-colour re-upload per
  cinema, native cost per colour, +6.5k to +21.5k clocks against 1.10 at
  that vblank) and fallbacks at area changes (+2.7k then +16.4k) remain, as
  in palette timing 2, the first fallback vblank 54 clocks longer than
  there; none lost an update in the playthrough (lost-update count = 1.10's
  in every mode; one counter sample moved at 97,647).
- Mapped modes, main loop: the worker in the wait (palette-lag) still moves
  the wait loop's exit by a few to 60 clocks after it runs (e2e above).
- A cinema reached with no worker run between its start and a vblank with
  colours queued still takes the dispatcher at that vblank (+113 cycles,
  measured once at 6,847 in a build before the worker re-queued; not seen
  in this build's playthrough).
- configure's routed window: a vblank there uploads nothing (menu only).
- NES-A/B and ORIGINAL: none found.

## Verified / inferred / not run

- Verified (emulator, Geargrafx `78fc3d7`): everything in the tables above.
- Inferred: that RAM and ROM instruction fetches cost the same on a real
  HuC6280 (no wait states for either; the instruction streams are the same,
  so the VDC/VCE access penalty applies equally); that the bank `$3B` copy
  of `rent_ms` is never run (only reached through bank `$46`).
- Not run: real hardware; the `check_menu.py` runs/sweep parts and
  `--preview`; `check_bram.py` matrix/cut/timing/lock; the lock-modelling
  emulator; deaths and Continue in the playthrough; the Japanese and
  Chinese languages over the playthrough.

## Deliverables

In `/workspace/roms/` (not in the repository):

| File | SHA-256 |
| --- | --- |
| `Ninja Ryukenden - Enhanced v1.11-dev (apocalypse, reset 2, palette timing 3).pce` | `a0019797765ff24e2266911ea9ad3f063652b8a135f393cbfe87691af52d2621` |
| `ninja-ryukenden-enhanced-v1.11-dev-apocalypse-reset-2-palette-timing-3.bps` (headered original) | `42cf0e9f99bfd7703bdc3193a3507454a25b3cf8124ad26528036e7a8d83870a` |
| `ninja-ryukenden-enhanced-v1.11-dev-apocalypse-reset-2-palette-timing-3-headerless.bps` | `bec6e9b81fedf1ff220473f7e7b2060750395c307c8cd6bdc0d0b3813a81ac6c` |

Both patches applied with `scripts/bps.py apply` to their originals give the
ROM above (checksums verified); the build from either original is that ROM.

## Rerunning

```sh
cd research/longplay/drift && make watch      # libgxw.so (see the Makefile for the core copy)
python3 pe_run.py TAG ROM MODE RECORDING OUTDIR [--reads]
python3 pe_cmp.py vblank V110.npz NEW.npz ; python3 pe_cmp.py lost NEW.npz 82880 ; python3 pe_cmp.py starts NEW.npz
python3 pe_menu.py ROM MODE research/longplay/full-exact.json
LD_LIBRARY_PATH=/workspace/build/toolchain/sdl3/lib python3 scripts/longplay_six.py run --mode MODE --rom ROM --file research/longplay/full-exact.json --out DIR
```
