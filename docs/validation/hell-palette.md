# Palette modes: HELL (1.11-dev)

Emulator evidence (headless Geargrafx `78fc3d7` with the headless-fast patch,
[EMULATOR.md](../pc-engine/EMULATOR.md)), not a hardware report; audio not
compared. Design: [architecture, palette modes](../ARCHITECTURE.md#palette-modes).

| Build | SHA-256 | Source |
| --- | --- | --- |
| Before (`popup-menu`) | `43db8b4c9c3f662c6edd4d22dd03d62385b0e84748ff8d898cb936a12aa6ecb5` | commit `46bbbe3` |
| HELL | `42328ceefc1e85f661d4b03d2ec78036fdef1e1ffa213490aded7bea8cc8d7fe` | branch `hell-palette` (the same bytes from the headered and the headerless original) |

Method: one start state, a cold boot of the original saved at the 1-1
main-loop hook; every replay is a fresh session that loads it, writes
`$2100`/`$2101` (0 Original, `$10` GB DMG, `$18` HELL), enters the stage as
Level Select does and steps one frame at a time. Probes:
[`research/tools/hell-palette/`](../../research/tools/hell-palette)
(`record.py`, `analyse.py`, `unittest_upload.py`, `upload_cost.py`,
`stagestarts.py`, `shots.py`) and, unchanged, the GB DMG probes
`timing_trace.py`, `split.py`, `updates.py`, `entry_timing.py`,
`freewatch.py` and `guard.py` in
[`research/tools/gb-palette/`](../../research/tools/gb-palette) (with
`GB_WORK` set to the work folder). Lines are counted after the VDC vblank
interrupt, 1365 master clocks each.

## The mode

`src/palette/hell.json` holds the owner's chosen mock-up, candidate C
("Lava"), as parameters; `scripts/palette_tables.py` ports its mapping
operation for operation and the ROM-free tests pin the generated table to
the mock-up's 512 colours (SHA-256 of the words
`1388df9d…afc7`). It applies to VCE entries 0-239 (background palettes
0-14); the HUD palette, the sprite palettes and the border keep their
colours.

## What changed in the ROM

Against the `popup-menu` build only these bytes differ: bank `$43`
`$7800-$7B4F` (HELL code, 848 bytes) and `$7C00-$7FFF` (HELL table), both
`$FF` before; bank `$46` `$4429-$4A0A` (the menu: the PALETTE values and the
full re-queue on a mode change, 1,547 bytes in all, 17 more) and
`$5000-$53EF` (the palette code reorganised, 1,023 bytes; the Original and
GB DMG paths keep their cycle counts). No RAM and no fixed-bank bytes are
added.

## a. Original and GB DMG unchanged

All 11 stored runs (35,084 frames) recorded on both builds in Original and
in GB DMG mode (`record.py`, `analyse.py identity`): every frame's
screenshot, VCE, sprite table, game RAM (outside `comparison_video.OWNED`,
the music driver's workspace included) and gameplay field identical, in
both modes, in every run. `scripts/check_boot.py` and
`scripts/check_menu.py`: see [below](#checks).

## b. HELL colours

- In-place unit test of the upload against an independent Python model
  (`unittest_upload.py`, every mode, HELL's split and raw-chunk costs, the
  left-over, busy and full-queue rules, cinema state, palette_now across
  entry 240): 254 cases (seed 22) and 494 (seed 31), 0 failures; MPR2, MPR3,
  S, X, Y, the lock and zero page `$20-$26` as before. Negative control:
  with the model's raw set-up cost one lower, 42 of 254 fail.
- All 11 runs in HELL (`record.py`, `analyse.py due`): every VCE entry 0-239
  equals the HELL table value of its RAM colour and every entry 240-511 the
  RAM colour itself (entry 256 the border colour), except while uploads are
  still queued. The longest a single entry lags is 37 frames (3-1, the
  end-of-stage fade; 33-37 in the fades of 1-1, 2-2, 3-1, 3-2, 4-2, 5-2,
  6-1; 21 in 5-3 and 6-3; 11 in 4-1; 4 in 5-4), against 44-46 in GB DMG; the
  original's own lag in the same runs is up to 13.
- All 22 Level Select entries (`stagestarts.py`, 120 frames): every entry is
  due from frame 4-6 after the first update to frame 119 (the full re-upload
  of the mode's first vblank and the fade-in before that).

## c. Timing in HELL

- Updates: stage timer, Ryu, camera, area and sprite table identical to
  Original mode in every frame of all 11 runs (`record.py`, `updates.py`).
  `$2240` turns to 1 one frame later at the cinema after 4-1, 5-3 and 6-3
  (frames 2487, 6768, 5122), the same frames as in GB DMG mode (the full
  re-upload when a cinema begins).
- Vblank upload end (`timing_trace.py`): worst 18.99 lines over the 11 runs
  (GB DMG 18.19, Original 16.57); over the 22 stage loads 19.73
  (`entry_timing.py`); none after line 22 (the display starts about 22.8
  lines after the interrupt). 2-2's write at line 59.2 is the renderer's
  palette_now in the main loop (52.9 in Original, 59.1 in GB DMG).
- HUD split (scanline-interrupt CPU entry, `split.py`): past the cut-off
  (70.84) in the same frames as Original mode (1-1, 5-3 and 6-3 one each);
  2-2 none (Original one). In normal frames the largest shift against
  Original is +0.57 line, the maximum 70.40. 1-1 frame 2844 (a load frame
  already past the cut-off in Original, 73.94) enters at 78.03 in HELL and
  in GB DMG alike.
- Stage loads from Level Select after the mode has settled
  (`entry_timing.py`, 60 frames after): the same number of vblanks as
  Original in all 22 entries; 4-3's split entry is past the cut-off in both
  (74.89 / 74.54).
- Cost (`upload_cost.py`, synthetic queues at the 1-1 hook): unmapped
  colours go at 42 master clocks each (the native TIA rate; mapped ones
  150-156); a raw chunk's own work is about 1,220 clocks against the mapped
  chunk's 1,110, so the n/4 + n/32 + 3 colours it is charged cover it. A
  full 512-colour queue ends at 18.23 lines in HELL, 18.15 in GB DMG.

## d. Switching

Through the popup with controller input (`scripts/check_menu.py --only
options`, from 1-1, every case a fresh session):

- HELL chosen with Right twice or with Left (ORIGINAL wraps to HELL) and
  Run: `$2100` = `$98` after the restart and the VCE is exactly the HELL
  table applied to entries 0-239 of the RAM palette with entries 240-511 and
  the border unchanged; GB DMG with Right likewise the GB table (`$90`).
- Paths accepted with Run, each step checked: GB DMG then ORIGINAL; HELL
  then ORIGINAL; HELL, GB DMG, ORIGINAL; GB DMG, HELL, ORIGINAL. Every
  mapped mode on the way shows exactly its table (HELL after GB DMG and GB
  DMG after HELL included, which needs the menu's full re-queue), and each
  path ends with the same VCE as a run that never left Original.
- Cancel after changing every row (Select), compared frame by frame for 900
  frames with the same state run without the menu (every picture, VRAM,
  sprite table and palette at each frame's end, RAM at the update
  boundary): from Original with GB DMG previewed, from Original with HELL
  previewed, from GB DMG with HELL previewed, from HELL with ORIGINAL
  previewed. All exact, no frame with a different picture. Only upload
  scratch differs (`$2205-$220B`, `$2261-$2271`, `$2284-$2285`, and after
  the GB DMG preview `$2100` bit 5), as in the popup-menu record.
- The live preview: Left on the PALETTE row from Original gives `$2100` =
  `$98` while the window is open and HELL colours behind it (screenshot
  `1-1-f600-preview-hell.png`).

## e. Space, stack and free-ROM audit

| Region | Use | Free |
| --- | --- | --- |
| Bank `$43` `$7800-$7B4F` (file `$87800`) | HELL code, 848 bytes | `$7B50-$7BFF` (176) |
| Bank `$43` `$7C00-$7FFF` | HELL table, 1 KiB | |
| Bank `$46` `$5000-$53FE` | palette code, 1,023 bytes | `$53FF` (1) |
| Bank `$46` `$4400-$4A0A` | the menu, 1,547 bytes | `$4A0B-$4AFF` (245) |
| Fixed bank | nothing added | `$FECF-$FEDF` (17), `$FFEE-$FFF5` (8) |
| Bank `$46` | untouched, unowned or reserved | `$4100-$42FF`, `$4B00-$4FFF` |
| Bank `$45` | untouched | `$4000-$43FF` |

`src/modules.json`: stage11's range is `$80000-$877FF` (was to `$87FFF`), the
palette module claims `$87800-$87FFF` in addition. Why that space is free:
stage11's generator (`scripts/native_backdrops.py`, `PHASE_ATLAS`) puts 1-1's
phases 6 and 7 in bank `$43` at `$6000 + phase x size`, size = pairs x 32
with at most 83 pairs (enforced), so its data ends by `$74BF`; the current
build reaches exactly that. The build rejects any module byte outside its
ranges, so a larger stage11 would fail loudly. Read/execute watch over file
offsets `$87800-$87FFF` on the old build (`freewatch.py`): 0 stops over a
cold boot to 600 updates of 1-1 (683 frames) and all 11 runs (35,084
frames); positive control, the same watch over stage11's bank `$43` data
(`$86000-$860FF`): 20 stops in the first 68 frames of 1-1 (its TIA at
`$4C0E` with MPR3 = `$43`). `.if/.fail` guards: the HELL code ends before
the table, the table before `$8000`, `HELL_MAPPED` at most 256; the palette
code before `$5400`.

The HELL code runs with bank `$43` in MPR3 (saved on the stack and restored
by exits in bank `$46`); the upload unit test checks MPR2 and MPR3 after
every case. RAM: none added; zero page `$20-$26` as the GB DMG path (saved
and restored).

Stack (`guard.py`, 2-2 with the menu opened four times and a full palette
re-queue forced while it was open): low-water mark `$21C6` in HELL (the TIA
built on the stack and MPR3's byte: 12 bytes deeper than GB DMG), 134 bytes
above the watched margin's top `$2140`; GB DMG `$21D2` on both builds,
Original `$21D3`.

## f. Screenshots

Private (`build/hell-palette/shots/`, `shots.py`; replays of the stored
runs, HELL and Original at the same frame): 1-1 frame 600, 2-2 frames 400,
1200, 2400 (areas 0-2), 3-1 600, 4-1 600 and 2100 (areas 0 and 2), 5-2 900
(area 1), 5-3 3000 (area 3); the popup open in HELL (1-1, 2-2, 5-3; the
PALETTE row reads HELL, sprites hidden as always); the live preview from
Original after Left on the PALETTE row (`$2100` = `$98` during it). Also the
first frames of 1-1, 2-2, 3-1, 4-1, 5-2 and 5-3 from Level Select
(`build/hell-palette/shots-start/`). Compared by eye with the mock-up
sheets (`sheet-C.png`, `compare-2-2.png`, `contact-C.png`): the same lava
skies and water, red and orange mountains, scorched columns, red rock in
4-1, tan walls in 5-2 and the dark red castle in 5-3, with Ryu, the enemies,
items and the HUD in their own colours. The mock-ups were made from captured
frames at other camera positions, so the pictures are compared area by area,
not pixel by pixel.

## Checks

- `scripts/check_boot.py`: passed (idle frames 1-899 identical to the
  original, first 1-1 update at frame 163 when mashing Run, defaults
  English, Enhanced, damage on).
- `scripts/check_menu.py` (all parts, music as played): `runs` 140 openings
  in the 11 runs, all exact; `select` all 22 Level Select entries and Run on
  the next, passed; `options` 16 cases (above), passed. `sweep` reports 8
  of 727 openings with video state differing for 1-3 frames before an area
  change (2-2 Select at 784-788 and 3943, 5-3 at 5290 and 6189), so the
  script's overall verdict is FAILED. They are not HELL's: the `popup-menu`
  build gives the same outcome case for case (2-2 swept twice on each
  build; 5-3 once: the same two cases). With the music driver's state
  copied (`--same-music`) 5-3 is exact on the HELL build, and 2-2 leaves the
  same two cases on both builds (788: one picture in frame 0; 3943: video
  state at the end of frame 1). The popup-menu record reported only the two
  5-3 cases; the 2-2 ones need a look in that work, not here. One sweep of
  the old build saw 3943 exact and the repeat did not, so single sweep
  cases can vary between sessions.
- ROM-free: `python3 -m unittest discover -s tests` (33 tests) and
  `scripts/audit_public.py` pass.

## Rerunning

From the repository root, with `GB_WORK` (default here
`/workspace/build/hell-palette`) holding `original.pce`, `base.pce` (the
`popup-menu` build) and `hell.pce`, and the emulator environment of
`run-check.sh` (Geargrafx and SDL paths):

```sh
R=research/tools/hell-palette; G=research/tools/gb-palette; W=$GB_WORK
python3 $R/runall.py record.py $W/hell.pce $W/rec hell 0x18        # and dev-orig 0, dev-gb 0x10;
python3 $R/runall.py record.py $W/base.pce $W/rec base-orig 0      # base-gb 0x10
python3 $R/analyse.py $W/rec identity base-orig dev-orig            # and base-gb dev-gb
python3 $R/analyse.py $W/rec due hell dev-orig
python3 $R/runall.py timing_trace.py $W/hell.pce $W/tt hell 0x18    # and dev-orig 0, dev-gb 0x10
python3 $G/split.py $W/tt dev-orig hell; python3 $G/updates.py $W/tt hell $W/tt dev-orig
python3 $G/entry_timing.py $W/hell.pce 0x18 60 0,1,...,21 $W/entry-hell.json 30   # and 0
python3 $R/stagestarts.py $W/hell.pce 0x18 120 all
python3 $R/unittest_upload.py $W/hell.pce 60 22                     # MODEL_RAW_SETUP=2: control
python3 $R/upload_cost.py $W/hell.pce 0x18
python3 $G/freewatch.py $W/base.pce 1-1 87800 87fff                 # each run and 'boot'
python3 $G/guard.py $W/hell.pce 2-2 0x18 300,900,1500,2100
python3 $R/shots.py $W/hell.pce $W/shots 1-1:600:menu:preview 2-2:400:menu ...
```

## Not covered

Real hardware; audio; whole cinemas in HELL (only the first 60 frames of
those after 4-1, 5-3 and 6-3 are in the runs: there the VCE equals the RAM
palette except in the first frame, mid re-upload, and in one frame the
original has too, exactly as in GB DMG mode); Continue and Game Over screens; boss rooms other than the 5-4 run's. The
mock-up comparison is by eye. The NES palette (value 01) is on a parallel
branch; merging must keep the Original and GB DMG paths' cycle counts (see
the architecture map) and repeat (a).
