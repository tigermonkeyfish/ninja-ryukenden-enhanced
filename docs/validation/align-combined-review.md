# Combined alignment build (align-combined): adversarial review

**In progress (checkpoint): no verdict yet.** Emulator evidence only
(Geargrafx `78fc3d7`), no real-hardware data.

Reviewed: `3379c90..48beea8` (`src/dispatch`, `src/stage22`, `src/stage52`,
`src/castle`, `src/palette/main.asm`; the three records `load-exact.md`,
`start-pos.md`, `cinema-lock.md` and the gate record `align-combined.md`),
build `2f134a80...8880` ("apocalypse, reset 2, palette timing 3, original
load timing, 2-2 start, cinema lock"), against the unmodified HuCard.

## Checkpoint notes (static reading, before the probes finished)

- Build identity: the ROM in `/workspace/roms/` has SHA-256 `2f134a80...8880`
  and equals `/workspace/build/align-combined/rom.pce` (verified).
- Record correction (verified, bytes): load-exact's new fixed-bank bytes are
  **six, `$FF67-$FF6C`**, not the four `$FF67-$FF6A` its record and the brief
  name (`cmp #$fc` / `bcc` and a second `bcc`: 6 bytes; `draw_done`'s `rts` is
  at `$FF6C`). `$FE00-$FFF5` is `$FF` in the original, the range is inside
  dispatch's `$FF2C-$FF6F`, the guard is `init_hook_end > $ff70`; 3 bytes
  (`$FF6D-$FF6F`) are left before the Select hook.
- Native code read (original ROM, bank 1): `$80C2` saves MPR5 in `$2257` and
  MPR6 in `$2258` and `$80D4` puts them back, inside one call; no other
  native code touches `$2257/$2258` (byte search for absolute operands).
  `$2E63` is written at `$82D2` (`$3A`, stage load), `$840C` (`$0A`, area
  change and respawn), `$8447` (1), `$851A` (`$3A`, the stage-end fade-out),
  `$85ED`/`$865C`/`$86C4` (`$40`, death, game over, continue screen) and
  `$862C` (1); only `$83FF` decrements it.

(Findings, answers, verdict and checklist follow when the probes are done.)

## Checkpoint 2 (interim results; the final text replaces this section)

Own probes (scratch `/workspace/build/align-combined-review/`, a private copy
of the in-process core with a render flag; `full-load.json` from power-on,
126,001 frames, one input list):

- ORIGINAL, NES-A against the unmodified ROM: update counter, master flags,
  stage, area, camera, lives, health, Ryu's state and `$2E63` identical in
  every frame; every one of the 124,958 updates on the same frame with the
  same number of vblanks (own count from the `$E06C` / `$FCEC` hits). SMS,
  GB DMG, APOCALYPSE: the same except the one update whose start is sampled a
  frame later at 97,646 (it still ends 322,809 clocks before its vblank).
- `$2258` markers: `$FD` only with `$2E63` `$3A`-`$38`, `$FC` only with `$37`,
  at the four changed loads; never pending on a frame where the menu could
  open (60,096 such frames per run).
- ORIGINAL pictures against the unmodified ROM, the 15 changed-stage events
  (windows of 16 / 34 frames): identical from the event through the frame
  before the camera first moves, the black frames included.
- Deaths (15: every 2-2 and 5-2 area, six 5-3 areas, 5-4), Game Over ->
  Continue (4) and Level Select (7) branches: game fields equal to the
  unmodified ROM's, pictures identical from the respawn / reload on, the two
  load pieces at `$38` / `$37` in single-colour frames, no fallback draw.
- Found so far: (a) mapped modes show the first visible frame of some 5-3
  area changes with foreground palettes still black for one frame (SMS, GB
  DMG: areas 4 and 6; APOCALYPSE: all six) - being compared with palette
  timing 3; (b) `check_menu.py --only sweep` at step 1 fails one opening
  (stored 2-2 run, frame 788, the frame before the first area change) -
  being compared with palette timing 3.
- Gates on the combined ROM so far: `check_menu.py --only runs --preview`
  pass; `check_bram.py` matrix (211 images) PASS, cut PASS, timing rc 0.
