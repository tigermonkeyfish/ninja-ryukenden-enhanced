# Combined alignment build (align-combined): start-pos + cinema-lock + exit-frames

Emulator evidence only (Geargrafx `78fc3d7`: headless build for the gates, the
in-process core of `research/longplay/load` for replays); no real hardware.

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


## Whole playthrough, `research/longplay/full-load.json` (verified)

- Headless ORIGINAL (`scripts/longplay_six.py run --mode original`):
  RESULT PASS, 22 of 22 stage starts (1-1 at 0, 1-2 2,832, 2-1 10,136, 2-2
  13,241, 2-3 16,533, 3-1 27,777, 3-2 31,401, 3-3 34,853, 4-1 53,287, 4-2
  57,120, 4-3 60,357, 4-4 64,422, 5-1 70,012, 5-2 73,263, 5-3 77,205, 5-4
  82,881, 6-1 86,506, 6-2 88,444, 6-3 93,808, 6-4A 102,300, 6-4B 106,466,
  6-4C 111,227), end reached at frame 126,001 (master 1, scene 14). Its
  counter, master, stage and area arrays are identical (126,001 frames) to
  the unmodified-ROM headless run and to the `original` run recorded in
  `load-exact` and in `start-pos` (compared byte for byte).
- In-process, six modes against the unmodified ROM (`lx.py`, `cmp7.py`,
  reference `unmod-L.npz` of load-exact): ORIGINAL, NES-A, NES-B: counter,
  master flags, stage and area identical in all 126,001 frames. SMS, GB DMG,
  APOCALYPSE: counter differs in one frame (97,646, the known load-exact
  residual), the rest identical. All six: the 22 stage starts, the 63 area
  changes and the ending cinema (124,184) on the unmodified ROM's frames.
  No other differing frame.

## Start-window survey, 48 events (verified)

`capture.py` (frames EV-4..EV+110, in-process, ORIGINAL, combined ROM against
the unmodified ROM, English by the title switch) and `startwin.py`; game RAM
equal on every captured frame at all 48 events. Dark run identical and start
window identical at every event from the black through the frame before the
camera first moves, except row 36 (6-1, the known 5-pixel horizon item: first
differing frame 86,589). The old-build column of start-pos's table was not
regenerated (no capture of the previous build was made here).

| # | Event | Frame | Camera | Dark run (frames) identical | First visible | Camera first moves | Start window frames | Start window identical | First differing frame from first visible |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 1-1 start | 1 | 0 | 0: yes | 1 | 67 | 66 | yes | 68 |
| 2 | 1-2 a0 | 2846 | 0 | 28: yes | 2873 | not in window | 84 | yes | - |
| 3 | 2-1 a0 | 10151 | 0 | 28: yes | 10178 | not in window | 84 | yes | - |
| 4 | 2-1 a1 | 11343 | 0 | 3: yes | 11345 | 11366 | 21 | yes | - |
| 5 | 2-1 a2 | 12421 | 0 | 4: yes | 12424 | not in window | 108 | yes | - |
| 6 | 2-1 a3 | 12546 | 768 | 3: yes | 12548 | 12579 | 31 | yes | - |
| 7 | 2-2 a0 | 13256 | 768 | 13: yes | 13268 | not in window | 99 | yes | - |
| 8 | 2-2 a1 | 14030 | 768 | 4: yes | 14033 | 14034 | 1 | yes | 14034 |
| 9 | 2-2 a2 | 14671 | 1792 | 3: yes | 14673 | 14674 | 1 | yes | 14674 |
| 10 | 2-3 a0 | 16547 | 0 | 36: yes | 16582 | not in window | 76 | yes | - |
| 11 | 3-1 a0 | 27793 | 0 | 13: yes | 27805 | not in window | 99 | yes | - |
| 12 | 3-2 a0 | 31416 | 0 | 13: yes | 31428 | not in window | 99 | yes | - |
| 13 | 3-3 a0 | 34867 | 0 | 28: yes | 34894 | not in window | 84 | yes | - |
| 14 | 4-1 a0 | 53302 | 0 | 36: yes | 53337 | not in window | 76 | yes | - |
| 15 | 4-1 a1 | 55309 | 0 | 4: yes | 55312 | not in window | 108 | yes | - |
| 16 | 4-1 a2 | 55429 | 0 | 3: yes | 55431 | not in window | 109 | yes | - |
| 17 | 4-2 a0 | 57134 | 0 | 29: yes | 57162 | not in window | 83 | yes | - |
| 18 | 4-3 a0 | 60369 | 0 | 36: yes | 60404 | not in window | 76 | yes | - |
| 19 | 4-3 a1 | 60708 | 0 | 4: yes | 60711 | 60792 | 81 | yes | - |
| 20 | 4-3 a2 | 61795 | 0 | 4: yes | 61798 | 61804 | 6 | yes | - |
| 21 | 4-3 a3 | 63544 | 0 | 4: yes | 63547 | 63554 | 7 | yes | - |
| 22 | 4-4 a0 | 64436 | 0 | 36: yes | 64471 | not in window | 76 | yes | - |
| 23 | 5-1 a0 | 70025 | 0 | 28: yes | 70052 | not in window | 84 | yes | - |
| 24 | 5-2 a0 | 73278 | 512 | 21: yes | 73298 | not in window | 91 | yes | - |
| 25 | 5-2 a1 | 74531 | 0 | 4: yes | 74534 | not in window | 108 | yes | - |
| 26 | 5-2 a2 | 75459 | 512 | 4: yes | 75462 | 75511 | 49 | yes | 75512 |
| 27 | 5-2 a3 | 76157 | 0 | 5: yes | 76161 | not in window | 107 | yes | - |
| 28 | 5-3 a0 | 77219 | 512 | 21: yes | 77239 | not in window | 91 | yes | - |
| 29 | 5-3 a1 | 77972 | 0 | 5: yes | 77976 | 78069 | 93 | yes | 78070 |
| 30 | 5-3 a2 | 78669 | 512 | 4: yes | 78672 | 78773 | 101 | yes | 78774 |
| 31 | 5-3 a3 | 79287 | 0 | 5: yes | 79291 | not in window | 107 | yes | - |
| 32 | 5-3 a4 | 80296 | 256 | 5: yes | 80300 | 80355 | 55 | yes | 80355 |
| 33 | 5-3 a5 | 80630 | 0 | 3: yes | 80632 | not in window | 109 | yes | - |
| 34 | 5-3 a6 | 80887 | 0 | 4: yes | 80890 | 80939 | 49 | yes | 80940 |
| 35 | 5-4 a0 | 82897 | 0 | 21: yes | 82917 | not in window | 91 | yes | - |
| 36 | 6-1 a0 | 86521 | 2048 | 21: yes | 86541 | 86628 | 87 | NO | 86589 |
| 37 | 6-2 a0 | 88458 | 1280 | 36: yes | 88493 | not in window | 76 | yes | - |
| 38 | 6-2 a1 | 90754 | 768 | 3: yes | 90756 | 90757 | 1 | yes | - |
| 39 | 6-2 a2 | 91716 | 0 | 4: yes | 91719 | 91818 | 99 | yes | - |
| 40 | 6-2 a3 | 91820 | 0 | 3: yes | 91822 | 91924 | 102 | yes | - |
| 41 | 6-2 a4 | 92931 | 0 | 3: yes | 92933 | 92940 | 7 | yes | - |
| 42 | 6-3 a0 | 93822 | 0 | 21: yes | 93842 | not in window | 91 | yes | - |
| 43 | 6-3 a1 | 94460 | 0 | 4: yes | 94463 | not in window | 108 | yes | - |
| 44 | 6-3 a2 | 94579 | 1792 | 4: yes | 94582 | 94601 | 19 | yes | 94601 |
| 45 | 6-3 a3 | 96625 | 0 | 5: yes | 96629 | not in window | 107 | yes | - |
| 46 | 6-4A a0 | 102317 | 0 | 36: yes | 102352 | not in window | 76 | yes | - |
| 47 | 6-4B a0 | 106481 | 0 | 36: yes | 106516 | not in window | 76 | yes | - |
| 48 | 6-4C a0 | 111242 | 0 | 21: yes | 111262 | not in window | 91 | yes | - |

## Cinema check (verified)

`cl_run.py` of cinema-lock (copied to scratch, output path changed), full
recording from power-on, combined ROM, all six modes; analysis `cl_an.py`
against palette timing 2 and `cl_cmp.py` against cinema-lock's `c1` runs
(mapped modes) and the load-exact `base` runs (ORIGINAL, NES).

- Act 5 scene start (cinema start 65,903, the upload frame 65,926) in GB
  DMG, SMS and APOCALYPSE: queue 1, lock 0, the worker re-queues; the update
  costs 22,179 clocks = all 512 colours; VCE entries 272-511 against pt2
  differ in 0 frames over the scene (4,109 frames), and over all 11 cinema
  scenes in each of the three modes (0 / 0 everywhere).
- Against `c1` (cinema-lock without start-pos) in the three mapped modes:
  counter/master/stage/area differ in 0 frames, the per-vblank palette path
  cost equal at all 126,477 vblanks; frame-end clocks equal except one
  (GB DMG 14,672, -9 clocks; the 2-2 draw change); SMS and APOCALYPSE equal
  everywhere.
- ORIGINAL, NES-A, NES-B against `base`: per-vblank palette path cost equal at
  all 126,477 vblanks (0 different); arrays identical; frame-end clocks
  differ only at 14,032 and 14,672 (+-12, the 2-2 area-change draw).
  Smallest wait margin 735 clocks, as in cinema-lock.

## Deliverables

In `/workspace/roms/` (nothing overwritten):

| File | SHA-256 |
| --- | --- |
| `Ninja Ryukenden - Enhanced v1.11-dev (apocalypse, reset 2, palette timing 3, original load timing, 2-2 start, cinema lock).pce` | `2f134a801b0e4378b69938793bdf0d94f391496507bdad1d1c5d583599648880` |
| `ninja-ryukenden-enhanced-v1.11-dev-apocalypse-reset-2-palette-timing-3-original-load-timing-2-2-start-cinema-lock.bps` (headered original) | `ab92be065a7bc9298ae77a32816f64c4fffd188bc82763bad29035428242fba1` |
| `ninja-ryukenden-enhanced-v1.11-dev-apocalypse-reset-2-palette-timing-3-original-load-timing-2-2-start-cinema-lock-headerless.bps` | `cd0a5ca0b46f9640938ec6f297d8d30794e64996a189d778f51682c4d49a2629` |

`patches/`, `release/` and `VERSION` unchanged.

## Not run

Real hardware; a real-time core; the survey against the previous build
(start-pos's old column); the cinema-lock fuzz/dispatcher probes
(`cl_fuzz_worker.py`, `cl_mech.py`, `cl_disp.py`) and the other cinema-lock
proofs (only the colour/cost check was repeated); start-pos's respawn and
other-mode picture checks; Japanese/Chinese language paths beyond the menu
gates.
