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
