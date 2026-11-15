# Known deficiencies (1.11-dev)

Recorded on the maintainer's instruction (2026-11-13): every known difference
from the unmodified ROM, and every known defect, in the current development
build. Nothing here blocks the hardware test.

- Build: `timing-cleanup` (ROM SHA-256 `ea176297…3ace1`, "…original load
  timing, 2-2 start, cinema lock, timing cleanup", code commit `846e0b9`).
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
| D3 (residual) | Mapped modes: `draw_all` still writes palettes 13-14 to the VCE mid-frame after `cache` at 2-2's area changes (HUD and sprites untouched; console behaviour inferred). The 1-line dash in `14,672` is eliminated. | 2-2 | `timing-cleanup` | `validation/timing-cleanup.md` |
| D6 | Options menu opened and cancelled on the last gameplay frame before 2-2's first area change (1 of 727 openings, frame `788`): `WAITR` polling jitter (`3` VDC dots = `12` master clocks relative to `y=0`, inside the `30`-clock loop) straddles the `42`-clock write of VCE word `0xae` (`+8,103..+8,145` clocks post-`IRQ1`), leaving one colour entry differing at frame 0 end. | 2-2 | palette timing 3 or earlier | review F3, `validation/timing-cleanup.md` |
| D7 | Mapped modes: one frame-counter sample differs at one cinema entry (frame `97,646`, 6-3 to 6-4: `$2000 = 56` vs `57` in `original`; `97,647` is `57 = 57`). `RENT` MN uploads 512 colours (`22,179` clocks vs `717`), so `$00:E06C` runs in frame `97,647` at `+17,229` clocks (`322,809` clocks spare before `97,647` vblank; zero updates lost). 18 (SMS, GB DMG) / 32 (APOCALYPSE) transition vblanks cost more than 1.10's. | cinema starts, transitions | palette-exact | `validation/palette-exact.md`, `validation/timing-cleanup.md` |
| D8 | 5 pixels differ on the 6-1 horizon at the stage load (the Enhanced backdrop omits a star). | 6-1 | Enhanced backdrop | `validation/start-align.md` |
| D9 | Level Select loads show the new stage in the old colours for 13-17 frames (black backdrop band) before the fade-out. Enhanced-only feature; no unmodified reference. | Level Select | earlier builds | review F6, `validation/start-pos.md` |
| D10 | The NES palette hook changes bytes `$F235-$F236`, inside a range the original reads as a phantom object list at the 1-2 area change. No frame or picture effect found. Proposed fix (wrapper at `$FECF-$FEDF`) not done. | 1-2 | 1.11-dev (`src/nes-palette`) | `validation/longplay-code-drift.md` |
| D12 | SMOOTH PARALLAX OFF: 833 of 14,702 compared pictures differ as single frames at native tile redraws; game fields and timing equal. | 2-2, 5-2 to 5-4 | before these changes | review Q7 |
| D13 | 5-4 post-boss timer-to-score countdown: `88` frames (`83,621..84,289`, every 4th frame; `0` diffs in `82,800..83,620`) differ by `1-27` px in HUD score digit rows `19..25`, cols `72..102`; game fields equal. `$01:8457` (`jsr $FE40`) + `$01:8472` (`jsr $FF00`) shift `$01:845D..$00:E061` by `~20.8k` clocks (`~15.2` scanlines) across rasterized HUD lines `33..39`. | 5-4 | 1.09 (`$8457` hook) | `validation/timing-cleanup.md` |
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
| D19 | Only 7 free bytes remain in dispatch's fixed-bank range (`$FF69-$FF6F`) and 2 in bank `$46`'s palette timing section (`$5FFE-$5FFF`). | `timing-cleanup` |

## Fixed in `timing-cleanup` (since `align-combined`)

- **D2:** Mapped-mode 1-frame black foreground on 5-3 area changes and respawns fixed via `worker_convert` (`src/palette/main.asm` Option A, 58/60 cyc/col, zero new RAM; `validation/timing-cleanup.md`). All 60 outside-`2-2/5-2/5-3/5-4` transition windows also verified with `0` D2 anomalies.
- **D3 (1-line dash):** Eliminated (`0` extra px on frame `14,672`) by running `jsr cache` before `jmp $febe` in mapped modes (`src/stage22/main.asm` Option 2A-1; mid-frame VCE write of palettes 13-14 remains in mapped modes as D3 residual).
- **D4 + D5:** `deferred_draw` (`src/dispatch/main.asm`) rewritten (`inc a / bpl`), removing the +6-cycle per-update overhead and passing `check_menu.py --only runs --parallax-off` `140/140` including 4-1 frame `1,664`.
- **D11:** Resolved on `align-combined` (`4-3` frames `60,700..60,715`: `0` CORE diffs across `original`, `apocalypse`, `sms`, `gbdmg`; `$2EA0` is `20` at `60,707` and `190` at `60,708..60,709`).

## In published 1.10 (corrected in 1.11-dev)

- The 2-2 and 5-4 stage loads each take one vblank more than the original's.
- Backdrop stripes in both black frames at 2-2's area changes.

## Not covered by any test

Real hardware; routes other than the recorded one; deaths, Continue and Level
Select in NES-A and NES-B; deaths with the camera moving; Japanese and Chinese
text past frame 65,933 of the recorded route; sound beyond the PSG registers
the menu gates compare.
