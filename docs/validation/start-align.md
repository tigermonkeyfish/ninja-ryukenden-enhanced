# Start alignment: backdrop position against the unmodified ROM at every stage start and area change

Question (owner): "stage start should appear like the orginal. all stages and all substage/middle phases should have the backgrounds be perfectly aligned. to the original"; "the goal is for all of the background position starts to match the unmodified rom."

Emulator evidence only (Geargrafx in-process tracer core, the one `load-exact` used), no real-hardware data. Nothing in `src/` was touched.

## Answer

Of the 48 events (the 47 surveyed loads and area changes plus the 1-1 start at frame 1):

- **45 match**: the whole picture is pixel-identical to the unmodified ROM from the first visible frame through the end of the start window (loads: first visible frame through the end of the fade-in plus 8 frames; area changes: the 8 frames after the transition black). All 21 stage loads after 1-1 (this includes the first black/fade frames: every frame from 4 frames before the load is identical) and 24 of the 26 area changes.
- **2 area changes have the backdrop at a different position**: 2-2 area 1 (event 14,030) and 2-2 area 2 (event 14,671). From the first visible frame the build's backdrop (mountains and the cloud band, rows 84-177) is displaced to the right by 8 px at the first frame (then 7, 5, ... 2 px: it drifts, the residual is 2-7 percent of the differing pixels). Camera, `$2E4B-$2E4E` and all other sampled RAM are equal on every frame, so it is the backdrop's own scroll, not the game state. Foreground, sprites and HUD are identical.
- **1 stage start matches only at first**: 1-1 is identical for frames 1-67; from frame 68 (the camera starts to move, camera 2 -> 3 ...) the skyline between the buildings (rows 53-145) is horizontally displaced by 2-9 px against the original (residual 2-15 percent) for the rest of the window. This is the Enhanced backdrop moving by its own formula against the native 8 px stepped one; it is not a start-position difference.
- Not backdrop: 6-1 has one 3x3 pixel region (5 pixels, rows 168-170, cols 210-212) differing from frame 86,589 (56 frames after the first visible frame); it is a foreground pixel cluster, not a backdrop shift.
- Also outside "the start": the last 1-3 frames of the OLD area just before the transition black differ in some area changes (2-2 a1 and a2, 4-1 a1, 5-2 a2, 5-3 a1 to a6 except a3 where only the old area differs; see the table), and later in the window frames differ where the Enhanced backdrop has moved differently from the native one (5-2 a2 from +50, 5-3 a1/a2/a4/a6 from +94..+100, 6-3 a2 from +19, 6-1 from +98, 2-2 from +9). They are listed in the table notes with their offsets. A few are one-frame, whole-screen vertical offsets at the last frame before the black (5-3 a5 1 px, a6 5 px, 6-3 a1 4 px, a3 4 px, 2-2 a1 2 px).

So, for the question "does the background position at every start match the unmodified ROM": yes for 45 of 48 events including every stage load; no for the two 2-2 area starts (8 px at the first visible frame), and the 1-1 skyline differs from frame 68 once movement begins. Where a shift number is given it is the build's displacement relative to the original (positive x = build to the right).

## Settings

- Build under test: `/workspace/roms/Ninja Ryukenden - Enhanced v1.11-dev (apocalypse, reset 2, palette timing 3, original load timing).pce` (SHA-256 `27d1eaa0c51b57c9939c6c268f05d066968c90d5769b35ac44e7b52a2c8ddcf0`, `load-exact` tip `dfd4a22`), mode `original`: backup-RAM settings entry with options byte `0x00` and language 1 (English). From `docs/OPTIONS.md` the options bits at 0x00 are the defaults: palette Original, smooth parallax ON (the Enhanced backdrop), No Damage OFF, NES Firewheel OFF. The menu is never opened.
- Unmodified ROM: `/workspace/DO_NOT_COMMIT_ROMS/Ninja Ryukenden (J).pce`, no backup RAM, English through the native title shortcut (hold I + II and tap Select), `mode unmod-en` (`lx.boot`, as `longplay_six.py --shortcut`). Language byte read back = 1 in both runs.
- Recording: `research/longplay/full-load.json`, 126,001 frames after a 480-frame boot; both ROMs replay it frame for frame (counter, stage, area equal), so frame N is the same game state on both.
- Events: the 47 rows of the `load-exact` survey table (`docs/validation/load-exact.md`: 21 stage loads + 26 area changes by that table's own rows; its prose says 22 + 25, because it counts the 1-1 start, frame 1, among the 22 starts; the survey table has no 1-1 row, so it is added here as event 1). The "63 area changes" in that document's proof A are all area-byte changes seen by the counter/stage/area comparison (including ones that are not an area transition with the black/stage-entry as the survey defines it); the 26 survey rows are the ones that call the native `$80AB` background initialization from the area change (`$85B4`) and are what was used here.
- Window per event: frames EV-4 .. EV+110 (115 frames; event 1: frames 1..111). Frame size 256x242.
- Picture = the core's frame buffer after `gx_run(1, 1)`, one frame at a time (not `--testrunner`). Per frame also recorded: camera `$220F-$2210`, `$2E4B-$2E4E`, `$2E63`, stage `$2E5F`, area `$2E60`, counter `$2000`. These were equal on both ROMs in every captured frame of every event. The VDC BXR/BYR registers themselves were not read out (the in-process shim does not expose them); `$2E4B-$2E4E` (what the scanline handler writes to them) is what was compared.
- Compare: whole-frame equality, difference bounding box, and a (dx, dy) search over +-16 px of the build's picture against the original on the differing pixels (maximum matches, ties broken to the smaller shift), residual = differing pixels left after the best shift.
- "First visible": loads = first non-black frame; area changes = the first frame after the 4-5 frame transition dark run. "Full bright" = the first frame reaching 99 percent of the brightest sum in the window; loads fade in from black, area changes do not (the picture is full brightness at the first visible frame). For loads the first visible frame is already at level 1 (see `load-exact`); frames before it are black on both ROMs and equal.

## Commands

```sh
export LD_LIBRARY_PATH=/workspace/build/toolchain/sdl3/lib
cd research/longplay/startalign
python3 capture.py "/workspace/DO_NOT_COMMIT_ROMS/Ninja Ryukenden (J).pce" unmod-en /workspace/build/start-align/cap-unmod
python3 capture.py "/workspace/roms/Ninja Ryukenden - Enhanced v1.11-dev (apocalypse, reset 2, palette timing 3, original load timing).pce" original /workspace/build/start-align/cap-new
ONLY=1 python3 capture.py ... (event 1 only, same two commands, after widening EVENTS)
python3 compare.py cap-unmod cap-new report.json mismatch/   # per-frame equality, first/bright mismatch PNGs
python3 rows.py                                              # per-event rows and the first-differing-frame PNGs
python3 table.py                                             # the table below
```

Each run is one fresh power-on and one pass over 126,001 frames (about 3-4 minutes); one emulator at a time.

## Events

Build offset = where the build's backdrop sits relative to the original (x right, y down), from the best shift. "Start window" as defined above.

| # | Event | Stage/area | Event frame | Camera at entry | First visible / full bright | Whole frame identical (start window) | Backdrop verdict (start window) | Notes (outside the start window) |
|---|---|---|---|---|---|---|---|---|
| 1 | load | 1-1 start | 1 | 0 | 1 / 83 | no (24 of 91 frames differ) | shifted: build offset vs original (x,y) (2, 0), (8, 0), (9, 0); residual 2%-15% of differing px; 24/91 frames differ, rows 53-145, cols 126-197 | 19 later frames differ (92..111, from 91 frames after the first visible one; the moving backdrop) |
| 2 | load | 1-2 a0 | 2846 | 0 | 2857 / 2905 | yes (57 frames) | identical | - |
| 3 | load | 2-1 a0 | 10151 | 0 | 10162 / 10210 | yes (57 frames) | identical | - |
| 4 | area change | 2-1 a1 | 11343 | 0 | 11345 / 11345 | yes (9 frames) | identical | - |
| 5 | area change | 2-1 a2 | 12421 | 0 | 12424 / 12424 | yes (9 frames) | identical | - |
| 6 | area change | 2-1 a3 | 12546 | 768 | 12548 / 12616 | yes (9 frames) | identical | - |
| 7 | load | 2-2 a0 | 13256 | 768 | 13268 / 13316 | yes (57 frames) | identical | - |
| 8 | area change | 2-2 a1 | 14030 | 768 | 14033 / 14076 | no (8 of 9 frames differ) | shifted: build offset vs original (x,y) (2, 0), (7, 0), (8, 0); residual 2%-7% of differing px; 8/9 frames differ, rows 84-177, cols 0-119 | last 3 frames of the old area before the transition black differ (build offset (0, 2), residual 34%, 24846 px); 99 later frames differ (14042..14140, from 9 frames after the first visible one; the moving backdrop) |
| 9 | area change | 2-2 a2 | 14671 | 1792 | 14673 / 14673 | no (8 of 9 frames differ) | shifted: build offset vs original (x,y) (3, 0), (8, 0); residual 3%-6% of differing px; 8/9 frames differ, rows 114-176, cols 32-119 | last 3 frames of the old area before the transition black differ (build offset (0, 2), residual 0%, 144 px); 100 later frames differ (14682..14781, from 9 frames after the first visible one; the moving backdrop) |
| 10 | load | 2-3 a0 | 16547 | 0 | 16558 / 16626 | yes (77 frames) | identical | - |
| 11 | load | 3-1 a0 | 27793 | 0 | 27805 / 27853 | yes (57 frames) | identical | - |
| 12 | load | 3-2 a0 | 31416 | 0 | 31428 / 31476 | yes (57 frames) | identical | - |
| 13 | load | 3-3 a0 | 34867 | 0 | 34878 / 34974 | yes (100 frames) | identical | - |
| 14 | load | 4-1 a0 | 53302 | 0 | 53313 / 53361 | yes (57 frames) | identical | - |
| 15 | area change | 4-1 a1 | 55309 | 0 | 55312 / 55312 | yes (9 frames) | identical | last 3 frames of the old area before the transition black differ (build offset (-6, 0), residual 44%, 1685 px) |
| 16 | area change | 4-1 a2 | 55429 | 0 | 55431 / 55431 | yes (9 frames) | identical | - |
| 17 | load | 4-2 a0 | 57134 | 0 | 57146 / 57205 | yes (68 frames) | identical | - |
| 18 | load | 4-3 a0 | 60369 | 0 | 60380 / 60437 | yes (66 frames) | identical | - |
| 19 | area change | 4-3 a1 | 60708 | 0 | 60711 / 60711 | yes (9 frames) | identical | - |
| 20 | area change | 4-3 a2 | 61795 | 0 | 61798 / 61798 | yes (9 frames) | identical | - |
| 21 | area change | 4-3 a3 | 63544 | 0 | 63547 / 63547 | yes (9 frames) | identical | - |
| 22 | load | 4-4 a0 | 64436 | 0 | 64447 / 64535 | yes (97 frames) | identical | - |
| 23 | load | 5-1 a0 | 70025 | 0 | 70036 / 70132 | yes (100 frames) | identical | - |
| 24 | load | 5-2 a0 | 73278 | 512 | 73290 / 73338 | yes (57 frames) | identical | - |
| 25 | area change | 5-2 a1 | 74531 | 0 | 74534 / 74534 | yes (9 frames) | identical | - |
| 26 | area change | 5-2 a2 | 75459 | 512 | 75462 / 75558 | yes (9 frames) | identical | last 2 frames of the old area before the transition black differ (build offset (8, 0), residual 1%, 4668 px); 49 later frames differ (75512..75560, from 50 frames after the first visible one; the moving backdrop) |
| 27 | area change | 5-2 a3 | 76157 | 0 | 76161 / 76161 | yes (9 frames) | identical | - |
| 28 | load | 5-3 a0 | 77219 | 512 | 77231 / 77279 | yes (57 frames) | identical | - |
| 29 | area change | 5-3 a1 | 77972 | 0 | 77976 / 77976 | yes (9 frames) | identical | last 3 frames of the old area before the transition black differ (build offset (16, 0), residual 83%, 796 px); 13 later frames differ (78070..78082, from 94 frames after the first visible one; the moving backdrop) |
| 30 | area change | 5-3 a2 | 78669 | 512 | 78672 / 78672 | yes (9 frames) | identical | last 2 frames of the old area before the transition black differ (build offset (11, 14), residual 78%, 590 px); 6 later frames differ (78774..78779, from 102 frames after the first visible one; the moving backdrop) |
| 31 | area change | 5-3 a3 | 79287 | 0 | 79291 / 79291 | yes (9 frames) | identical | last 3 frames of the old area before the transition black differ (build offset (0, 5), residual 83%, 337 px) |
| 32 | area change | 5-3 a4 | 80296 | 256 | 80300 / 80400 | yes (9 frames) | identical | last 3 frames of the old area before the transition black differ (build offset (-8, 0), residual 77%, 3926 px); 52 later frames differ (80355..80406, from 55 frames after the first visible one; the moving backdrop) |
| 33 | area change | 5-3 a5 | 80630 | 0 | 80632 / 80632 | yes (9 frames) | identical | last 1 frames of the old area before the transition black differ (build offset (0, 1), residual 1%, 23993 px) |
| 34 | area change | 5-3 a6 | 80887 | 0 | 80890 / 80955 | yes (9 frames) | identical | last 1 frames of the old area before the transition black differ (build offset (0, -5), residual 4%, 30735 px); 58 later frames differ (80940..80997, from 50 frames after the first visible one; the moving backdrop) |
| 35 | load | 5-4 a0 | 82897 | 0 | 82909 / 82957 | yes (57 frames) | identical | - |
| 36 | load | 6-1 a0 | 86521 | 2048 | 86533 / 86581 | no (1 of 57 frames differ) | tiny (not backdrop): build offset vs original (x,y) (14, 10); residual 20%-20% of differing px; 1/57 frames differ, rows 168-170, cols 210-212 | 42 later frames differ (86590..86631, from 57 frames after the first visible one; the moving backdrop) |
| 37 | load | 6-2 a0 | 88458 | 1280 | 88469 / 88517 | yes (57 frames) | identical | - |
| 38 | area change | 6-2 a1 | 90754 | 768 | 90756 / 90756 | yes (9 frames) | identical | - |
| 39 | area change | 6-2 a2 | 91716 | 0 | 91719 / 91730 | yes (9 frames) | identical | - |
| 40 | area change | 6-2 a3 | 91820 | 0 | 91822 / 91835 | yes (9 frames) | identical | - |
| 41 | area change | 6-2 a4 | 92931 | 0 | 92933 / 93040 | yes (9 frames) | identical | - |
| 42 | load | 6-3 a0 | 93822 | 0 | 93834 / 93891 | yes (66 frames) | identical | - |
| 43 | area change | 6-3 a1 | 94460 | 0 | 94463 / 94463 | yes (9 frames) | identical | last 3 frames of the old area before the transition black differ (build offset (0, -4), residual 14%, 33893 px) |
| 44 | area change | 6-3 a2 | 94579 | 1792 | 94582 / 94653 | yes (9 frames) | identical | 89 later frames differ (94601..94689, from 19 frames after the first visible one; the moving backdrop) |
| 45 | area change | 6-3 a3 | 96625 | 0 | 96629 / 96629 | yes (9 frames) | identical | last 1 frames of the old area before the transition black differ (build offset (0, -4), residual 2%, 22701 px) |
| 46 | load | 6-4A a0 | 102317 | 0 | 102328 / 102406 | yes (87 frames) | identical | - |
| 47 | load | 6-4B a0 | 106481 | 0 | 106492 / 106550 | yes (67 frames) | identical | - |
| 48 | load | 6-4C a0 | 111242 | 0 | 111254 / 111341 | yes (96 frames) | identical | - |

## Events that do not match, and what the difference looks like

PNGs are side by side: unmodified | build | difference (magenta = differing pixel), in `/workspace/build/start-align/mismatch/` (not committed).

- 2-2 a1 (14,030): first visible frame 14,033, first differing frame 14,034: the mountain range and the cloud band (rows 84-177, cols 0-119 growing to 0-255) are drawn 8 px right in the build, then 7, 5, ... px; the dithering pattern also differs, so this is the Enhanced 2-2 backdrop (different texture/parallax) at an offset, not the native one. `ev14030-post-first-f14034.png`, `ev14030-s3a1-first-f14026.png`, `ev14030-s3a1-bright-f14028.png`.
- 2-2 a2 (14,671): same: 8 px at 14,674 (rows 114-176 first, then 84-177), 3-8 px afterwards. `ev14671-post-first-f14674.png`, `ev14671-s3a2-first-f14667.png`.
- 1-1 start (event 1): from frame 68: skyline between the buildings displaced 2-9 px. `ev1-post-first-f68.png`.
- 6-1 load (86,521): 5 pixels at one object, not backdrop. `ev86521-s16a0-first-f86589.png`.
- Old-area last frames before the transition black (listed in the table notes): `ev55309-*`, `ev75459-*`, `ev77972-*`, `ev78669-*`, `ev79287-*`, `ev80296-*`, `ev80630-*`, `ev80887-*`, `ev94460-*`, `ev96625-*` (all named `*-first-*` or `*-bright-*`).
- Later in the window, outside the start: `ev*-post-first-*` / `ev*-post-vis8-*` files for 5-2 a2 (`ev75459-post-first-f75512.png`, differs at the right edge, cols 193-255, build 8 px right then ~5), 5-3 a1/a2/a4/a6, 6-3 a2 (`ev94579-post-first-f94601.png`, rows 53-161, 8 px), 6-1.

## Interpretation (inferred, not measured)

- Stage loads: the Enhanced draw lands the backdrop at the original's position at the camera the stage is entered at (camera 0, 512, 768, 1280, 2048 in these loads), including 2-2, 5-2, 5-3, 5-4 whose Enhanced backdrop is drawn later in the load (`load-exact`). Verified identical here frame for frame, not just at one frame.
- 2-2 a1 and a2 are entered at camera 768 and 1792 (a multiple of 16, C > 0): the original's native backdrop starts at column 1 of the left edge (`docs/ARCHITECTURE.md`, native backdrop with the 8 px jitter); the Enhanced offset formula puts it 8 px from there. That matches the measured 8 px at the first frame, but I did not test the formula.
- Other area changes entered at camera 0 or 512 (5-3, 5-2, 6-3, 4-1) are identical at the start; their later differences are the Enhanced backdrop's own parallax (offset varying frame to frame).

## Not covered

- Death respawns, Continue/Game Over, Level Select entries, the cutscenes and the ending.
- Other routes: the native 8 px jitter depends on travel history, so another route, other speed or a different arrival camera can land on a different offset (this run measures this one recording only).
- Other palette modes (NES-A/B, SMS, GB DMG, APOCALYPSE), other languages, smooth parallax OFF (the unmodified-like path), the published 1.10 build.
- Real hardware, a real-time (non-fast) core, VDC scroll registers read directly.
- The pictures during the 4-5 black transition frames of an area change were compared (they are within the windows and equal in all events not listed), but "black" was not checked to be the same black level beyond pixel equality.
- The best-shift search is a heuristic on the differing pixels: for small or flat regions several shifts tie (reported ambiguity was 1 for the rows quoted in the verdicts except where noted in the JSON).
