# Known deficiencies (1.11-dev)

Recorded on the maintainer's instruction (2026-11-13): every known difference
from the unmodified ROM, and every known defect, in the current development
build. Nothing here blocks the hardware test.

- Build: `align-combined` (ROM SHA-256 `2f134a80…8880`, "…original load
  timing, 2-2 start, cinema lock").
- Evidence: emulator only (Geargrafx `78fc3d7`), one recorded no-death
  playthrough (`research/longplay/full-load.json`) plus the probes named in
  each source record. No real-hardware data.
- Palettes: ORIGINAL, APOCALYPSE, NES-A, NES-B, SMS, GB DMG. "Mapped modes"
  means APOCALYPSE, SMS and GB DMG.

## What matches (for reference)

The 22 stage starts, 63 area changes and the ending fall on the unmodified
ROM's frames in all six palettes. In ORIGINAL, NES-A and NES-B every game
update starts on the unmodified ROM's frame. All 48 stage starts and area
changes are pixel-identical from the black through the frame before the
camera first moves (ORIGINAL), apart from D8.

## Differences from the unmodified ROM

| ID | Deficiency | Where | Since | Source |
| --- | --- | --- | --- | --- |
| D1 | One-frame playfield drop at an area change differs at 5 of 26 area changes. The original drops the playfield 3-5 lines for one frame at four of them (2-2 a1: 3, 5-3 a6: 5, 6-3 a1: 4, 6-3 a3: 4); the build drops 5 lines at 2-2 a1, does not drop at the other three, and adds a 1-line drop at 5-3 a5. Timing unaffected. | 2-2, 5-3, 6-3 | 1.09 (`$8457` hook) | `validation/exit-frames.md` |
| D2 | Mapped modes: the first visible frame after some 5-3 area changes shows the foreground black for one frame (backdrop complete). APOCALYPSE: all six; SMS and GB DMG: areas 4 and 6. Also at respawns into those areas. Other stages not checked by picture. | 5-3 | palette timing 3 or earlier | `validation/align-combined-review.md` F1 |
| D3 | Mapped modes: a one-line dash (24-32 px) in the last black frame before 2-2's second area; two palettes are written to the video chip mid-frame at 2-2's area changes (a console may show stray dots; inferred). A 3-byte fix exists in scratch only, not gated. | 2-2 | 1.10 (stripes in both black frames there) | `validation/start-pos.md`, review F4/F5 |
| D4 | `deferred_draw` costs 6 CPU cycles (18 clocks) more per update in stages without an Enhanced backdrop (1-2, 2-1, 2-3, 3-3, 4-3, 4-4, 5-1, 6-2, 6-4 A-C), and with SMOOTH PARALLAX OFF until the first native redraw. No update gains a frame; tightest update keeps 5,919 clocks (unmodified 7,635). | those stages | load-exact | review F2 |
| D5 | Options menu, SMOOTH PARALLAX OFF, 4-1, one specific frame (1 of 140 openings): after the menu is cancelled one music channel's next note is written one frame late; in step from the next frame. Link to D4 is inferred. | 4-1 | load-exact | review F2 |
| D6 | Options menu opened and cancelled on the last gameplay frame before 2-2's first area change (1 of 727 openings): the old picture stays one frame longer or shorter before the black; one colour entry differs for that frame. | 2-2 | palette timing 3 or earlier | review F3 |
| D7 | Mapped modes: one frame-counter sample differs at one cinema entry (frame 97,646, 6-3 to 6-4); no update lost (322,809 clocks spare). 18 (SMS, GB DMG) / 32 (APOCALYPSE) transition vblanks cost more than 1.10's. | cinema starts, transitions | palette-exact | `validation/palette-exact.md`, review Q5 |
| D8 | 5 pixels differ on the 6-1 horizon at the stage load (the Enhanced backdrop omits a star). | 6-1 | Enhanced backdrop | `validation/start-align.md` |
| D9 | Level Select loads show the new stage in the old colours for 13-17 frames (black backdrop band) before the fade-out. Enhanced-only feature; no unmodified reference. | Level Select | earlier builds | review F6, `validation/start-pos.md` |
| D10 | The NES palette hook changes bytes `$F235-$F236`, inside a range the original reads as a phantom object list at the 1-2 area change. No frame or picture effect found. Proposed fix (wrapper at `$FECF-$FEDF`) not done. | 1-2 | 1.11-dev (`src/nes-palette`) | `validation/longplay-code-drift.md` |
| D11 | APOCALYPSE: at frame 60,709 (4-3) Ryu's y byte read 190 against 20 for one frame. Unexplained; seen on "palette timing 2", not re-checked since. | 4-3 | unknown | `validation/longplay-timing.md` |
| D12 | SMOOTH PARALLAX OFF: 833 of 14,702 compared pictures differ as single frames at native tile redraws; game fields and timing equal. | 2-2, 5-2 to 5-4 | before these changes | review Q7 |
| D13 | 5-4 boss fight: single frames differ by 1-14 pixels of one HUD digit; game fields equal. Not investigated. | 5-4 | unknown | review, "seen and left alone" |
| D14 | Area-0 timer death in 2-2: the lives byte shows one frame-end sample later than on the original; no frame lost. | 2-2 | before start-pos | `validation/start-pos.md` |

By design, not a deficiency: with SMOOTH PARALLAX ON the Enhanced backdrop
scrolls smoothly once the camera moves, where the original's stays
screen-locked and jumps a whole tile (8 px).

## Other known defects and limits

| ID | Item | Source |
| --- | --- | --- |
| D15 | A save state made on an older build freezes on this ROM (the vblank routine in RAM at `$3740` is missing from the state). Inferred. Do not load old EverDrive states. | `validation/palette-exact-review.md` F4 |
| D16 | Changing ORIGINAL/NES to a mapped mode in the menu shows unmapped colours if a vblank lands inside the change. Only produced with forced vblanks; not reachable in normal use. | palette-exact review F3 |
| D17 | The first vblank after power-on costs +6,516 (ORIGINAL/NES) or +6,756 (mapped) clocks more than 1.10's. No consequence found. | palette-exact review F2 |
| D18 | `mapped_upload`'s idle test still looks for `$FD67-$FD6F` and is dead code since palette-lag. | palette-exact review F6 |
| D19 | Only 3 free bytes remain in dispatch's fixed-bank range (`$FF6D-$FF6F`) and 22 in bank `$46`'s palette timing section (`$5FEA-$5FFF`). | reviews |

## In published 1.10 (corrected in 1.11-dev)

- The 2-2 and 5-4 stage loads each take one vblank more than the original's.
- Backdrop stripes in both black frames at 2-2's area changes.

## Not covered by any test

Real hardware; routes other than the recorded one; deaths, Continue and Level
Select in NES-A and NES-B; deaths with the camera moving; Japanese and Chinese
text past frame 65,933 of the recorded route; sound beyond the PSG registers
the menu gates compare; mapped-mode first frames outside 2-2, 5-2, 5-3, 5-4.
