# Combined alignment build (align-combined): start-pos + cinema-lock + exit-frames

PARTIAL (checkpoint): emulator evidence only (Geargrafx), no real hardware.

Branch `align-combined` = `start-pos` (bb7439e) + merge of `cinema-lock`
(5a49712) + merge of `exit-frames` (1d5e0b8); no conflicts, no `src/` change
of its own.

## Build (verified)

Built with `scripts/project.py build` and pceas from the original ROM, from
the headered original (`Ninja Ryukenden (J).pce`) and the headerless one
(its last 524,288 bytes): the same ROM, and the same bytes on a second build.

- ROM SHA-256 `2f134a801b0e4378b69938793bdf0d94f391496507bdad1d1c5d583599648880`
- BPS patches: headered `ab92be065a7bc9298ae77a32816f64c4fffd188bc82763bad29035428242fba1`,
  headerless `cd0a5ca0b46f9640938ec6f297d8d30794e64996a189d778f51682c4d49a2629`
  (each applied back with `scripts/bps.py apply`: checksums verified).

## Byte comparison (verified)

- Against the start-pos ROM (`888a8730...d1f9`): one range, 689 bytes differ,
  file `0x08DD1B-0x08DFE9` = bank `$46`, `$5D1B-$5FE9` (the cinema-lock change).
- Against cinema-lock's `c1.pce` (`228b741d...5d5`): two ranges in bank `$56`
  (stage 2-2): `0x0ACCF0-0x0ACE15` (275 bytes) and `0x0ACE28-0x0ACE6C` (45
  bytes) (start-pos's change). Nothing else.

## Gates finished so far (combined ROM, one emulator at a time)

| Gate | Result |
| --- | --- |
| unit tests | 54 OK |
| `audit_public.py` | passed, 494 files |
| `check_boot.py` | idle frames 1-899 identical to the original |
| `check_menu.py` options + reset | 68 of 68 ok, passed |
| `check_menu.py` select | 21 entries ok, passed |
| in-game menu | shows `V1.11-DEV` (reset-menu screenshot) |
| `check_bram.py` cycle | 17 of 17, PASS |
| `palette_lag.py pairs` | 36 of 36: first update +0, no sound RAM/counter/Ryu/stage difference, no lag frame, interrupt clocks equal |
| `palette_lag.py loadtime` | 132 of 132 (+0) |
| `palette_lag.py e2e` | six modes, first update +0, no differing frame in 2,903, 96 sound commands; GB DMG 6, APOCALYPSE 8, SMS 5 differing clocks within -202..+60 (as start-pos) |
| `palette_lag.py fastok` | 195-215 colours run; no FASTOK 1 |

Still to come: replays, survey, cinema check, deliverables.
