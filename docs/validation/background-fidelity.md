# Background fidelity review of v1.01 (2026-10-11)

> This record follows the development from 1.01 to the 1.09 release, build by
> build. Versions 1.00 and 1.01 were internal releases that were never
> published; their hashes appear here only as the baseline each development
> build was measured against. The release itself is described in
> [VALIDATION.md](../VALIDATION.md).

Emulator comparison of the raw original (headered, SHA-256 `1b3f411d…`) and
Enhanced v1.01 (`0ad5e8a5…`) across all 11 parallax stage entries. This is
emulated evidence (headless Geargrafx `78fc3d7` with the headless-fast patch),
not a hardware report. Captures, per-sample VRAM/RAM/palette/SAT dumps, the
HTML report and the tools are in the ignored `captures/bg-fidelity/` folder.

## Result

| Stage | Result |
| --- | --- |
| 1-1, 3-1, 3-2, 4-1, 5-4 | Native art; no visible joins (1-1: 56 edited pixels) |
| 2-2 | Native art on a 200-px loop: 56 native columns dropped, left mountain narrowed (documented contour/cloud edits) |
| 4-2, 6-1 | Native art plus the documented cloud-join edits; 6-1 sky/moon stationary as requested |
| **5-2** | **Defect:** areas 2 and 4 show flat blue in the right-hand vista where the original shows clouds, mountain and forest |
| **5-3** | **Seam:** castle-window horizon wrap cuts a cloud into a block (areas 4 and 6); the same art is repaired in 6-1 |
| **6-3** | **Seam:** arcade wrap cuts one arch short with an extra pillar (areas 1 and 3), usually beside the foreground column |

Area numbers are 1-based in the order the native forward transition reaches them.
Foreground tile words, HUD and the palette entries used by native cells were
unchanged in every sample; the remaining screenshot differences were timer,
animation-tile and palette-flash phase. Patched palettes (1-1 palette 1, 2-2
palettes 13–14) are referenced only by patched background cells.

## Findings

- The native backdrop in these scenes is **screen-locked**. It follows the map
  for up to 8 px and then snaps back, so its position jitters by 8 px depending
  on travel history. It therefore only ever shows one screen of art.
- Every patched row matches `floor(camera/8) + anchor` with 100% agreement (the
  6-1 upper sky is stationary).
- Openings: areas entered at camera 0 are pixel-identical to the original.
  Areas entered elsewhere open shifted (2-2: 32–56 px, 5-3 area 5: 128 px,
  6-3 area 3: 80 px), because the anchor reproduces `floor(C_entry/2)` (the
  earlier half-speed composition), not the original's fixed backdrop.
- **5-2 cause:** native art exists only inside the narrow opening. Areas 2 and 4
  are entered at camera 0 (anchor 0). By the time the opening is visible at
  camera 508, the texture has moved 63 px past the art. Confirmed in a fresh
  session with an unmodified ROM buffer, no breakpoints and no writes, after
  240 untouched frames.

## Method

- Both ROMs boot to the first gameplay update. Stages are entered with debugger
  writes mirroring Level Select at `$83F3`; areas advance through native `$8490`.
- At every update (`$8457`), native `$E341` is called with `$220E = ±4`. Ryu is
  held at camera+128 at height `$60` with full health. Both ROMs get the same
  emulator-ROM-buffer NOP of `jsr $E341` at `$925E`.
- Samples are taken every 32 camera px in both directions plus each area entry:
  1,734 matched pairs, with equal camera and render camera in every pair.
- The background layer is decoded from VRAM and the VCE (screen y = row×8+50,
  x = map x − render camera). Patched cells are those whose tile number differs
  at the same camera.
- Checks: every 8-px Enhanced texture window must occur in the same native row
  (provenance); adjacent column pairs never seen in native art in two or more
  rows count as joins; colour-histogram distance flags missing scenery. All
  flagged joins and scores were reviewed by eye.
- Decisions API (6 calls, background focus): identical control, a clean pair
  and the 2-2 recomposition came back "same", and the 5-2 vista "different"
  (missing scenery 1.0). It missed both small wrap seams.

## Not covered

Respawn or checkpoint entry cameras (they change the anchor and can reveal
other texture regions), vertical sections, crowded real-input play,
timing/performance, and ORIGINAL mode. Sprite pose differences reflect the two
runs' frame counters being offset by the splash screen.

## Development fixes (1.02-dev, 2026-10-11)

Build `a832e00a06d0e2442d0744537417b6f95f1c697273f6543803408fa9950cec14`
(branch `bg-fidelity-fixes`). Rerunning the same 11-stage sweep against the
original gave:

| Stage | Change | Evidence |
| --- | --- | --- |
| 5-2 | Fixed anchor 192 | Vista present in all four areas; colour-content distance max 0.058 (was 0.64) |
| 6-3 | 30-tile loop, 5-tile map | 100% of windows native (was 94.6%), no joins or tears |
| 5-3 | 6-1 repaired horizon | Rectangular cloud block gone; screenshots identical to the 6-1-style horizon build |
| 5-4 | Original horizon kept | 4/4 screenshots identical to v1.01 |
| 2-2 | Ridge rows on the native 25-tile loop | Row 5/6 tear (124-152 columns per area) gone |
| 1-1, 3-1, 3-2, 4-1, 4-2, 6-1 | None | Every screenshot identical to v1.01 (194/114/178/168/194/131) |

Other checks:

- The original-ROM rerun was 100% identical, so the harness is deterministic.
- Foreground, HUD and sprites are unchanged (the only differences are HUD
  timer, animation and palette-flash phase).
- `scripts/check_notice.py` passed. ROM-free tests and the public audit passed.
- Real pit deaths in 5-2 and 6-3, and mid-area restarts in 2-2, 5-2, 5-3 and
  6-3, rebuilt backgrounds identical to a fresh entry. A real death in 2-2 was
  not achieved in the harness.

**2-2 composition.** The original's rows 6-15 repeat every 25 tiles: columns
0-1 equal 25-26 in rows 6-11 and 13, and columns 32-33 equal 7-8. The 200px
loop is therefore the original artists' period. The frozen data only contains
native columns 7-31 for those rows, so that window was forced. The creative
choices were:

- the separate 256px ridge loop (the tear, now fixed);
- reshaping mountain A's left slope (`stage22-mountain-contour`);
- bridging a cloud tile join that exists at x=128 in the original
  (`stage22-cloud-join` pixels);
- one native-tile swap at row 8, column 31 that the loop join needs.

`NINJA_STAGE22_ART=native` restores the original pixels under the contour and
cloud-bridge edits: 98.7% of windows are native and no non-native joins remain. The
maintainer chose the native pixels (2026-10-12); in 1.02-dev they were the
default and `NINJA_STAGE22_ART=kept` rebuilt the v1.00 edits. 1.03-dev removed
that option: 2-2 is generated from the original ROM (see "Native rebuild").

### Round starts (2026-10-12, build `a832e00a…`, before bridge columns)

Every round (area) of the 11 modified stages was entered as the game does
(Level Select writes, then the native round transition). The first frame was
compared with the raw ROM's; the page is `captures/bg-fidelity/report/round-starts.html`.

**Exact:** 1-1, 3-1, 3-2, 4-1, 5-4, 6-3c/d; the rounds with no backdrop on
screen at the start are identical as well.

**Aligned, but not pixel-exact:**

- 2-2a/b/c: aligned after per-round offsets (they were +32, +32 and -56px). The
  left 56px shows loop art where the original shows its non-repeating left edge.
- 5-3e: aligned (it was +120px).

**Not exact, by trade-off or limitation:**

- 5-2a/c: an 8px offset, kept deliberately.
- 5-3a-e: the repaired 6-1 horizon shows in the small windows.
- 6-1: the repaired horizon and moon placement (v1.01 design), 8px from the
  original.
- 4-2a: the cave mouth shows the cloud-join extension.

With a 256px loop of non-tiling art, a round cannot both open exactly like the
original and scroll without a seam. Doing both needs bridge columns outside
the opening view (a longer loop).

### Bridge columns (2026-10-12)

The maintainer chose exact round starts with no seams for 4-2, 5-3 and 6-1.
Build `8ad10b0a1fc260b1b9b92f70260af49dc72e04ac98ae5e41dbaa5a1800286d2e`
(`build/dev/Ninja Ryukenden - Enhanced v1.02-dev.pce`, cumulative BPS
`c6007d1f36161c0b687dad94d062e5f50f13c78793f7d0420ef1f05319e4a44b`) loops the native
picture plus bridge columns. See [the architecture map](../ARCHITECTURE.md) for the
construction. Alternate `v1.02-dev (2-2 v1.00 edits)` is `3a7a8990…8890`.

Round starts, rerun on every round of the 11 stages:

| Stage | Rounds | First frame vs original |
| --- | --- | --- |
| 1-1, 3-1, 3-2, 4-1 | all | exact (unchanged) |
| 4-2 | a | exact, 280/280 columns (was 89/280) |
| 5-3 | a-e | exact, sky and horizon (were 76-97%) |
| 5-3 | g | columns aligned; 3% differ only in animated star frames |
| 5-4 | a | exact; the arena special case is gone |
| 6-1 | a | 3,340/3,344: one star of horizon rows 14-15 is omitted |
| 6-3 | c, d | exact (unchanged) |
| 2-2 | a-c | aligned, 90/90/95% (native default); left 56px not recoverable |
| 5-2 | a, c | 8px offset (needs a 34+ tile loop and a TIA-format generator) |

6-1 omits that star because its sky is stationary while the horizon scrolls. The
castle map shows the native stars through the sky's animated star slots.

Offsets were chosen from native column identity at each first frame. Pixel-shift
scores were ambiguous when only small windows of backdrop show (5-3 rounds a
and c).

Other checks:

- Every screenshot of 1-1, 3-1, 3-2, 4-1, 5-2 and 6-3 is identical to the
  previous build (194/114/178/168/138/203 samples).
- Motion: horizon rows move as one texture at the expected speed (0.99
  agreement); the 6-1 sky stays stationary.
- Seams: the only new joins are at the bridges, and none is a visible cut. The
  4-2 splice (picture column 33 → native column 16) carries a continuous
  cloud. The castle bridge's joins are mirror axes or native adjacencies, except
  the v1.00 flank.
- Mid-area restarts in 4-2, 5-3, 5-4 and 6-1 rebuilt backgrounds identical to
  a fresh entry.
- Upload volume: 4-2 uploads 12.9 KB per scroll phase, below 2-2's existing
  14.3 KB. The castle lists add one run per phase.
- VRAM: the 25 borrowed castle tiles (`$238`, `$240–$257`) are unreferenced by
  any Enhanced 5-3/5-4/6-1 BAT cell and by every sprite in the captures.
  Nothing rewrites them mid-area. 4-2's atlas now reaches tile `$719`; tiles
  `$6C0–$77F` are blank and unused in original 4-2.
- Cinemas: `scripts/audit_cutscenes.py` reran against a fresh original-ROM
  reference with the same emulator binary. All 15 cinema IDs reached THE END.
  IDs 1-5 and 7-14 match frame for frame (including ID 8 after 5-3, which the
  1.01 audit flagged). ID 0 has identical ordered images with a different
  initial hold. ID 6 (after 4-1, before any bridged stage) shows the known 1.01
  exception: one load frame, 8 pixels at x=40-47, y=240. Comparison:
  `build/dev/cinema-comparison-dev-l.json` (local).
- The six assembler `.fail` guards check every hand-placed castle/6-1 code
  and data boundary. ROM-free tests cover the extra-region packing, sky
  rows, castle star slots and the native-map hash check.

## Native rebuild (1.03-dev, 2026-10-20)

The maintainer asked for the original art as exactly as possible, no
invented art, and every round to open where the original does, then to
review each stage before deciding whether any new art is needed. 1.03-dev
regenerates every Enhanced backdrop from the original ROM. Build
`01c033271ad5d56786295c6db849630849e6e6847ce60ca9f12bcb3f130993b1`
(`build/dev/Ninja Ryukenden - Enhanced v1.03-dev.pce`, cumulative BPS
`97f40ff0bed0209bd61ee5107ebbfb9d4963f479f0e888c13333ab9a54567d85`).
Emulator evidence only (same headless Geargrafx); no hardware test yet.

**Decoder.** `scripts/native_gfx.py` models the native graphics loader. In
each of the 11 stage entries, every tile-set request it decodes (the common
set and both backdrop sets) equalled the original's VRAM word for word after
initialization. Decoded palette sets equalled the captured VCE palettes 0-2
of every stage, except 3-1 palette 1, which the game animates and the
backdrop does not use. No art comes from the frozen patch, so the v1.00 1-1,
2-2, 4-2 and 6-1 art edits and the 1.02-dev castle bridge art are gone.

**Loops** (`native_gfx.LOOPS`, chosen by `scripts/native_seams.py`, which
minimises 16x8 windows the original never shows in that row). "Seam joins"
count tile joins the original never draws side by side. The original never
scrolls these backdrops, so no designed loop exists; where these joins look
wrong is the maintainer's review list.

| Stage | Loop | Seam joins | Notes |
| --- | --- | --- | --- |
| 1-1 | 35: native 0-31, 18-20 | 3 | cloud rows 1-2 |
| 2-2 | 50: native 0-33, 9-24 | 13 | the original's non-repeating left edge (cols 0-6) meets the 25-tile repeat |
| 3-1 | 40: native 0-31, 2-9 | 0 | seamless (10-tile rows) |
| 3-2 | 32: native 0-31 | 6 | same loop as v1.01 |
| 4-1 | 46: native 0-31, 17-23, 3, 4, 26-30 | 0 | seamless |
| 4-2 | 34: native 0-33 | 12 | clouds and ground at the wrap (v1.00 repaired this with new art) |
| 5-2 | 33: native 0-32 | 22 | vista edge; the backdrop shows only through the cliff opening |
| 5-3, 5-4, 6-1 | 33: native 0-32 | 8 | horizon: the low cloud is cut where the tall cloud begins (v1.00/1.02-dev used new art) |
| 6-3 | 35: native 0-32, 3, 4 | 1 | row 16 |

**Round starts.** Every round with backdrop on screen in all 11 stage
entries, reached as before. All are identical in place (first-frame tile
columns), including 2-2 rounds a-c (90-95% in 1.02-dev) and 5-2 rounds a
and c (8px off in 1.02-dev). The exception is 6-1 at 3,340/3,344: the
stationary-sky design leaves one star out of the scrolling horizon rows 14-15.

**Provenance** (share of Enhanced 16x8 windows found in the same row of the
original; screen samples every 32px both ways in every area):

| | 1-1 | 2-2 | 3-1 | 3-2 | 4-1 | 4-2 | 5-2 | 5-3 | 5-4 | 6-1 | 6-3 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v1.01 | 94.1 | 95.1 | 97.1 | 99.85 | 98.0 | 92.5 | 74.4 | 87.0 | 98.8 | 96.3 | 94.6 |
| 1.03-dev | 97.5 | 98.6 | 100 | 99.85 | 99.4 | 96.4 | 100 | 87.5 | 98.8 | 98.5 | 100 |

The 5-3/5-4 windows include animated stars caught on different frames.

**Timing.** Emulated clocks per gameplay update while force-scrolling 80
updates from each stage entry. No update of any stage, in either build, took
longer than a frame at 2 or 8 px per update. Highest share of a frame spent
in the hooked update (v1.01 → 1.03-dev, 2px): 1-1 0.46→0.48, 2-2 0.65→0.71,
3-1 0.46→0.47, 3-2 0.63→0.67, 4-1 0.51→0.52, 4-2 0.60→0.59, 5-2 0.67→0.66,
5-3 0.70→0.74, 6-1 0.70→0.71, 6-3 0.53→0.45. While building this, 1.02-dev
was found dropping frames in 5-3 area 4 (5 of 60 updates) and spending 0.70
of a frame on average in 6-1. Both causes are fixed (see
[the lessons](../pc-engine/LESSONS.md)). Forced scrolling with Ryu held in
place is not a crowded encounter.

**Other checks.**

- Restart from live renderer state (Level Select path) in all 11 stage
  entries rebuilt backgrounds identical to the fresh entry. A real death was
  not achieved in the harness, as before.
- Cinemas: `scripts/audit_cutscenes.py` from the 1.02-dev reference state.
  All 15 reached THE END with results identical to the 1.02-dev audit: 13
  frame-exact, ID 0 same images with a different initial hold, ID 6 the known
  1.01 load-frame exception. The 2-2 atlas now also borrows native 2-2
  backdrop tiles; the audit plays 2-2 before the cinema that once showed the
  leak.
- Screenshots outside the backdrop matched v1.01's differences (sprite poses,
  HUD timer), plus three 2-2 HUD-timer samples and one new 5-2 frame (area 2,
  reverse sweep, camera 192): the whole playfield one line lower than the
  original. The same sample matched in an earlier 1.03 candidate. The scroll
  split's write time measured identical to the original in area 0. Cause
  found and fixed in 1.04-dev (see "Split timing" below).
- `python3 -m unittest tests/test_tools.py` (23 tests) and
  `scripts/audit_public.py` passed.

A local review page (gitignored) shows each loop, its joins and every round
start: `captures/bg-fidelity-1.03-dev/review/index.html`.

## Split timing and castle data (1.04-dev, 2026-10-20)

Build `6c849de81144c44b5334003f3d0a709a4618f4c9c691a8304247d57f48f2fd85`
(branch `bg-fidelity-fixes`). Emulator evidence only (Geargrafx).

**The 1.03-dev 5-2 frame.** The playfield one line low (area 2, reverse
sweep, camera 192) was reproduced deterministically by rerunning the capture
flow. The HUD/playfield split handler wrote BYR at 71.08 lines after vblank
instead of 69.9: the interrupt arrived during the first of two back-to-back
32-byte VRAM TIAs in the 5-2 renderer and was taken only after the second.
A delay stub in the original's handler put the cut-off at ~70.9 (no shift
at 70.84, a shift at 70.97).

**Split latency, every update of the 11-stage sweep** (latest BYR write in
lines after vblank; updates past 70.85 in brackets):

| | 1-1 | 2-2 | 3-1 | 3-2 | 4-1 | 4-2 | 5-2 | 5-3 | 5-4 | 6-1 | 6-3 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| original | 69.96 | 69.97 | 69.95 | 69.95 | 69.96 | 69.95 | 69.95 | 69.95 | 69.90 | 69.96 | 69.91 |
| v1.01 | 70.55 | 69.95 | 70.22 | 70.33 | 70.25 | 69.92 | 71.08 (1) | 70.51 | 69.90 | 70.51 | 70.97 (1) |
| 1.03-dev | 70.41 | 69.92 | 70.22 | 70.22 | 70.26 | 69.93 | 71.08 (2) | 70.51 | 69.90 | 70.50 | 71.01 (1) |
| 1.04-dev | 70.41 | 69.92 | 70.22 | 70.22 | 70.26 | 69.93 | 70.51 | 70.51 | 69.90 | 70.50 | 70.50 |

1.04-dev separates the 5-2/6-3 32-byte TIAs with a NOP and splits the 6-1 sky
upload's into 16-byte blocks. Rerunning the 5-2, 6-1 and 6-3 captures, the
only screenshot that changed from 1.03-dev is the 5-2 frame, which now
matches the original. Round starts are therefore unchanged. Highest share of a
frame spent in the update (2px): 5-2 0.655 (was 0.655), 6-1 0.712 (0.708),
6-3 0.447 (0.447). No update ran late at 2 or 8 px.

**Deaths.** The earlier pit-death method (holding Ryu at Y `$F0`) no longer
kills Ryu in the harness, in the original either. A timer death (timer
`$2EDB-$2EDD` set to 002) killed Ryu in every one of the 11 stage entries,
in both the original and 1.04-dev, and the game respawned him normally. The
respawned screenshot is pixel-identical to the original's in 10 of 11 entries,
including 5-4's checkpoint respawn at camera 512. 6-1 differs only in
twinkling stars caught on other frames and the star its stationary sky
omits. Against a fresh entry, the respawned background is identical in 1-1,
2-2, 3-2, 4-1, 5-2 and 6-3. 3-1, 4-2 and 5-3 differ by exactly the same pixel
columns in the original (native animation; tile maps identical).

**Castle data.** Re-running the v1.00 castle builder's derivation from the
ROM decoder reproduced all 788 frozen castle images (sky phases, star frames,
v1.00 horizon tiles), the star tables, frame maps, sky upload lists and fixed
uploads byte for byte. The build now regenerates them and checks the static
tables; dropping every frozen backdrop asset from `src/modules.json` left the
ROM byte-identical. Mid-stage restarts (5-2, 6-1, 6-3) rebuilt backgrounds
identical to a fresh entry. Cinemas (`scripts/audit_cutscenes.py` from the
1.02-dev reference state): all 15 reached THE END with results identical to
the 1.03-dev audit (13 frame-exact, ID 0 a different initial hold, ID 6 the
known 1.01 load-frame exception).

ROM-free tests (25) and `scripts/audit_public.py` passed.

## No v1.00 input (1.05-dev, 2026-10-20)

The maintainer asked to remove every dependency on v1.00. 1.05-dev builds
from the original ROM alone: `project.py build` pads the headerless original
with `$FF` to 1 MiB and writes the 20 modules over it; no patch is applied
and no data is extracted. Build
`9f3cd22feb13bfb48a7dcef6b9316e839c27af300bc9731702f0e194fb40737f`
(`build/dev/Ninja Ryukenden - Enhanced v1.05-dev.pce`, cumulative BPS
`75d522ee50fcf95960547279e69c46e387ba5b5262d810edc973fe4139dfe68c`).
Emulator evidence only (same headless Geargrafx); no hardware test yet. A
build run under a Python audit hook opened no patch and no
`release/manifest.json` (only `release/current.json`, for the original
ROM's size and SHA-256) and produced the same hash.

**What v1.00 still supplied to 1.04-dev.** Comparing 1.04-dev with the
original outside the module ranges left three items: three NOPs at bank 1
`$845A` (the gameplay hook), banks `$35-$36` (414 horizon images of v1.00's
cloud repair, 191 of them still used and checked, 223 unused), and the boot
notice font (800 bytes, drawn for v1.00; 1 of its 25 glyphs occurs in the
original). Now `native-hooks` assembles the NOPs, `scripts/notice_assets.py`
holds the font as glyph rows (checked byte-identical to the v1.00 font), and
the castle module generates the horizon images. Outside the module ranges
the 1.05-dev ROM equals the original byte for byte.

**Castle/6-1 horizon.** VRAM placement follows the regenerated atlas: a
horizon pair that is an atlas horizon pair or a fixed slot takes that tile
(81 of 85), the rest borrowed tiles (4, was 23). A first version uploaded
the images from their atlas positions, about 30 runs per phase instead of
1.04-dev's 11-16. Its screenshots matched 1.04-dev in 5-4 and 6-1 but not in
5-3 from area 4 on: enemy poses and star twinkles were a frame off. The
game state (timer, star counters) split at the area 3-4 transition, whose
first frame redraws the whole backdrop with both upload groups. The castle
now stores the 74 listed tiles x 8 phases, generated from the original art,
phase by phase in tile order in banks `$35-$36` and the `$4A` tail: 12-13
runs per phase, split only by the fixed slots.

Against 1.04-dev, captured with the same three-stage flow (5-3, 5-4, 6-1),
all 328 screenshots are identical. Outside the stack, the sound driver's
RAM (bank `$38` code, run from the vblank interrupt) and its zero page
(`$2083-$2086`), RAM is identical too. In 5-3 from area 2 on the sound
counters are one tick apart: 1.04-dev spent one more frame there. The
game timeline is the same.

| | 5-3 2px | 5-3 8px | 5-4 | 6-1 2px | 6-1 8px |
| --- | --- | --- | --- | --- | --- |
| 1.04-dev | 0.739 / 0.476 | 0.717 / 0.536 | 0.066 | 0.712 / 0.468 | 0.643 / 0.608 |
| 1.05-dev | 0.734 / 0.472 | 0.714 / 0.533 | 0.066 | 0.705 / 0.464 | 0.637 / 0.604 |

(Highest / mean share of a frame spent in the update, area 0 force-scroll,
80 updates; no late updates.) Split latency, every update: 5-3 70.51, 5-4
69.90, 6-1 70.51 lines, as in 1.04-dev. Mid-stage restarts rebuilt the
background identically to a fresh entry (5-3, 5-4, 6-1). Timer deaths
respawned with screenshots identical to 1.04-dev (5-3 and 5-4 identical to
the original; 6-1 differs from the original only as before). Cinemas
(`scripts/audit_cutscenes.py` from the 1.02-dev reference state): all 15
reached THE END, with a comparison identical to 1.04-dev's. ROM-free tests
(27) and `scripts/audit_public.py` passed.

**Existing slowdown, unchanged by 1.05-dev.** Force-scrolling 5-3 area 2 for
128 updates, the updates that took two frames were: original 0, v1.01 4,
1.04-dev 8, 1.05-dev 8 at 2 px per update (at 4 px: 0, 4, 9, 9). In areas 3
and 4 at 4 px there was 1 each in 1.04-dev and 1.05-dev. The Enhanced part of
an update stays below 0.75 of a frame; with the rest of the game's work in
this area, some updates miss vblank. This needs its own fix.

## Slowdown (1.06-dev, 2026-10-20)

The maintainer asked for the slowdown to be removed so that the game feels
like the original ("speed runners should not complain"). Build
`6fc4a1b7a09a0f8cbdb67ecfbee9ace4588d104ffd28f6cb8c359539bf23fb6a`
(`build/dev/Ninja Ryukenden - Enhanced v1.06-dev.pce`, cumulative BPS
`5ba2df4ad0b6997ecbf2007069ccd2ca8795e8354d2beafeefe78835ec3d3999`).
Emulator evidence only (same headless Geargrafx); no hardware test yet.

**Method.** Every scrolling area of every stage entry (24 areas) was
force-scrolled end to end and back, counting updates that took two frames.
Ryu runs at 1.5 px per frame (measured), so 2 px per update covers real play
with margin; 3-4 px is a stress test.

| updates taking two frames (2 px) | original | v1.01 | 1.05-dev | 1.06-dev |
| --- | --- | --- | --- | --- |
| 5-3 area 2 | 0 | 21 | 27 | 0 |
| 2-2 area 0 | 0 | 0 | 16 | 0 |
| 2-2 area 2 | 0 | 0 | 4 | 0 |
| other 21 areas | 0 | 0 | 0 | 0 |

**Cause.** An instruction trace attributed to code labels: the late updates
rewrite every visible map entry (the backdrop crosses a tile, every ~9
camera px) on top of the per-update phase uploads, in stretches with heavy
game logic. In 5-3's interior areas 96-98% of those entries are foreground,
read and written back unchanged. The fix (docs/ARCHITECTURE.md, "Redraw
cost"): read only the BAT high byte and leave foreground unwritten; plan the
column split once per update; skip 2-2 rows whose entries are all equal;
upload-only updates skip the row walk; the speed bridge divides by shifts.
Worst update, CPU cycles (one frame of 263 lines = 119,665; an earlier note used 119,318, from a wrong frame length):

| | uploads | entries | loop | bridge | total |
| --- | --- | --- | --- | --- | --- |
| 5-3 rewrite, 1.05-dev | 38.6k | 25.1k | 13k | 3.6k | 84.1k |
| 5-3 rewrite, 1.06-dev | 38.8k | 10.1k | 9.5k | 1.4k | 62.6k |
| 2-2 rewrite, 1.05-dev | 49k | 18.9k | 15.1k | | 83k |
| 2-2 rewrite, 1.06-dev | 48.8k | 16.6k | 7.5k | 0.6k | 73.5k |

In the busiest stretches found, 5-3's rewrite updates keep about 10% of the
frame spare and 2-2's about 5%. At 4 px per update only 3-2 area 0 slows (2
updates; 4 at 3 px), as in 1.05-dev; v1.01 and the original have none. That
speed is above Ryu's.

**Picture.** Against the 1.03-dev captures of all 11 stage entries, the
backdrop map rows are identical wherever the picture code did not change in
between: 1-1, 2-2, 3-1, 3-2, 4-1, 4-2, 5-2 and 6-3 (5-2 keeps the one frame
1.04-dev fixed). 5-3, 5-4 and 6-1 use 1.05-dev's tile slots and match its
captures exactly; their screenshots also equal 1.03-dev's. In 2-2 only the
HUD timer and sprite graphics differ, because the capture samples one update
later than before (below). Restarts in all 11 entries rebuilt the
background identically to a fresh entry. Split latency, every update: at
most 70.58 lines (4-1), none past 70.85.

**Load times.** Frames from the stage-select hook to the first gameplay
update, and for a timer death set at the same update, the first update after
the respawn reload:

| | entry: original | entry: 1.05-dev | entry: 1.06-dev | respawn: original | respawn: 1.06-dev |
| --- | --- | --- | --- | --- | --- |
| 2-2 | 83.24 | 84.24 | 83.24 | 533.54 | 533.54 |
| 5-4 | 84.24 | 84.25 | 84.25 | 608.75 | 608.75 |
| 6-1 | 82.23 | 83.24 | 83.24 | 533.54 | 534.55 |
| other 8 | equal | equal | equal | equal | equal |

1.06-dev matches the original everywhere except 6-1, which loads and
respawns one frame later, as v1.01 and 1.05-dev do (the 5-4 respawn was one
frame longer in 1.04-dev). The extra frame comes from the Enhanced first
draw while loading: with delay-loop ROMs replacing the 6-1 renderer, a first
draw of 71,749 cycles keeps the original's length and 72,053 adds a frame;
6-1's is now 72,603 (86,261 in 1.05-dev). Earlier screenshot comparisons
taken a fixed number of frames after the harness's stage jump were off by
one update between builds (the jump returns at slightly different times),
which is why 2-2 and 5-4 screenshots can differ while the game timeline
matches the original.

Timer deaths: all 11 entries died and respawned; respawn screenshots equal
the original in 9, 6-1 as before (star frames, omitted star) and 5-4 by the
fixed-frame offset above.
Cinemas (`scripts/audit_cutscenes.py` from the 1.02-dev reference state):
all 15 reached THE END, with a comparison identical to 1.04-dev's. ROM-free
tests (27) and `scripts/audit_public.py` passed.

## 6-1 load (1.07-dev, 2026-10-20)

Build `ed906b6aa5ff1c1856795341d61831ffe3e87a98ccf3205af3c0ae29af268279`
(`build/dev/Ninja Ryukenden - Enhanced v1.07-dev.pce`, cumulative BPS
`3fcc1aab6bb0a40a07fc2205eef1e5941b7ce8cacafeb95904c2cdca5249d128`).
Emulator evidence only; no hardware test yet.

**Change.** 6-1 skips the Enhanced load-time draw. The native load already
shows the round's opening picture, which the Enhanced one matches, and the
first gameplay update draws the Enhanced backdrop within one frame (its
update-to-update frame deltas equal the original's). The 4 borrowed horizon
tiles moved to `$238-$23B`, because the native picture on screen until that
update uses `$243` (and `$23D`, `$245-$247`, `$24C-$24F`, `$252`).

| | entry: original | entry: 1.06-dev | entry: 1.07-dev | respawn: original | respawn: 1.06-dev | respawn: 1.07-dev |
| --- | --- | --- | --- | --- | --- | --- |
| 6-1 | 82.23 | 83.24 | 82.23 | 533.54 | 534.55 | 533.54 |
| other 10 | equal | equal | equal | equal | equal | equal |

All 11 stage entries and respawns now take the original's frame count.
At 2 px per update, 5-3's seven areas and 6-1 had no update taking two
frames. 6-1 sprites matched the original in all 131 captures, and the castle
screenshots did not change with the tile move. ROM-free tests (27) and
`scripts/audit_public.py` passed.

## Area changes (1.08-dev, 2026-10-21)

Build `0dab997d07e44dd5623b9a6d484256f56d31bc5b9a98c3f719cc6d9e04a3b984`
(`build/dev/Ninja Ryukenden - Enhanced v1.08-dev.pce`, cumulative BPS
`8a68028e951bd2d321f27556a2b744b9bc8ec6eee01b84357f12dbd19955b8c5`).
Emulator evidence only; no hardware test yet.

**Found by a scripted run.** A bot-made input log for all of 2-2 (4,282
frames, real button input from the first gameplay update) was replayed on
the original and on 1.07-dev, recording every frame. Position, camera,
health and lives matched, but at each area change 1.07-dev placed Ryu one
frame later, and from the area 2 entry the stage timer ran one frame behind
the original for the rest of the stage. At that frame the original CPU was
already in its idle loop while 1.07-dev was still drawing.

**Cause.** The native transition initializes the background (`$80AB`) in its
fourth frame, using about 0.8 of it. 1.07-dev drew the Enhanced backdrop
right after (0.8 frame in 2-2), past the frame boundary, so the rest of the
transition ran a frame late. Forced area changes (`$8490`), frames from the
change to the first gameplay update:

| area change | original | 1.07-dev | 1.08-dev |
| --- | --- | --- | --- |
| 2-2 0→1, 1→2 | 6, 6 | 7, 7 | 6, 6 |
| 5-3 4→5 | 6 | 7 | 6 |
| other 5-3, 5-2, 4-1, 6-3 changes | — | equal | equal |

**Fix.** The area change only marks the draw pending; the next main-loop
frame draws it, a frame the original spends in its vblank wait
(docs/ARCHITECTURE.md, "Area changes"). Stage loads still draw while loading.

**Results.** Frame-by-frame traces of all 20 forced area changes (area, Ryu,
camera, timer, sprite table, 200 frames each) are identical to the original.
The scripted 2-2 run matches the original on all 4,342 recorded frames in
sprite table, Ryu's object bytes, timer, lives, health, camera, area and
stage. Game RAM differs only in renderer workspace (`$224B`, `$2250`,
`$2257-$225A`, `$2428-$2465`, `$2828-$2865`), the language byte (`$3227`,
English) and two bytes set on the boot path before gameplay (`$31EF`,
`$3213`), all constant during play. Stage entries (11) and respawns (11)
still match the original's frame counts, and force-scrolling the eight
busiest areas at 2 px per update gave no update taking two frames. ROM-free
tests (27) passed.

## Comparison runs and cinemas (1.08-dev, 2026-10-21)

Build `0dab997d…b984` (1.08-dev). Emulator evidence only (Geargrafx, headless
MCP debugger). Method and tools: [COMPARISON-VIDEOS.md](../COMPARISON-VIDEOS.md).

**Gameplay.** For each parallax stage entry a run of real button input
(`research/comparison-runs/`) was replayed on the original and on 1.08-dev
from one shared machine state and recorded frame by frame. Every run plays
its stage to the end (next stage, cinema, or the 5-4 boss defeated), and in
every frame the sprite table, Ryu's object bytes, the stage timer, lives,
health, camera, area and stage are identical in both games.

| stage | input frames | recorded frames | identical | video length |
| --- | --- | --- | --- | --- |
| 1-1 | 2,860 | 2,920 | all | 0:49 |
| 2-2 | 4,282 | 4,342 | all | 1:12 |
| 3-1 | 2,638 | 2,698 | all | 0:45 |
| 3-2 | 3,368 | 3,428 | all | 0:57 |
| 4-1 | 2,961 | 3,021 | all | 0:50 |
| 4-2 | 2,765 | 2,825 | all | 0:47 |
| 5-2 | 3,665 | 3,725 | all | 1:02 |
| 5-3 | 8,258 | 8,318 | all | 2:19 |
| 5-4 | 955 | 1,015 | all | 0:17 |
| 6-1 | 2,004 | 2,064 | all | 0:34 |
| 6-3 | 6,681 | 6,741 | all | 1:52 |

Game RAM outside Enhanced's own bytes (renderer workspace, the language
byte, two boot-path bytes) also matches, except on 10-98 frames per stage
(1-3%) where bytes in the sound driver's work area (`$3800-$39FF`, used by
bank `$38`) differ for a frame and then agree again (identified in 2-2, 3-2
and 6-3). This fits sound requests landing at a slightly different point
within a frame; no gameplay or screen difference follows. The audio itself
was not recorded or compared.

**Cinemas after full play.** After each run, the following stages were
completed through the native path (120 frames each, as in the cinema audit)
and the next cinema was captured frame by frame in both games, native
English in both:

| after | cinema scene | frames | result |
| --- | --- | --- | --- |
| 1-1 | 3 | 4,400 | identical |
| 2-2 | 4 | 9,593 | identical |
| 3-1, 3-2 | 5 | 16,796 each | identical |
| 4-1 | 6 | 1,081 | identical |
| 4-2 | 7 | 4,108 | identical |
| 5-2, 5-3 | 8 | 1,721 / 1,689 | identical |
| 5-4 | 9 | 2,120 | identical |
| 6-1, 6-3 | 10 | 4,670 / 4,659 | identical |

Scene 4 is the story scene that showed repeated graphics after 2-2 in v1.00;
after a full Enhanced 2-2 it is identical to the original.

**Cinema audit (all 15 scenes).** `scripts/audit_cutscenes.py` on 1.08-dev
reached every scene with the same result as 1.03-dev to 1.06-dev: scene 0
(intro) matches image for image with different holds (Enhanced's boot path),
and scene 6 differs in one frame: an 8-pixel run on the bottom display line
shows the scene's own sky colour one frame longer while the cinema draws its
picture (frame 9; frame 10 matches). No foreign graphics appear. After a
full play of 4-1, scene 6 is identical frame for frame (table above), so this
depends on the audit's shortened path, not on leftover Enhanced data.

**Harness.** Replays are frame-exact only from a loaded state; see
docs/pc-engine/LESSONS.md, "Replays are frame-exact only from a loaded
state". ROM-free tests (28) and `scripts/audit_public.py` passed.

## Level Select health (1.09-dev, 2026-10-21)

Build `a6554ae3…cdd8` (1.09-dev). Emulator evidence only.

Before, a stage started from the in-game menu kept the health Ryu had when
the menu opened: 1.08-dev, hit to 12 of 16 in 1-1, restarted 1-1 and then
3-1 at 12. The native game refills health on a respawn (bank 1 `$8DFC`:
`$2EAD = 16`, then the bar redraw). The menu now stores 16 in `$2EAD` when
**I** applies a stage, before the stage starts, so the stage's own HUD draw
shows the full bar.

| case (1.09-dev) | health | result |
| --- | --- | --- |
| hit in 1-1 | 12 | |
| **II** (back) | 12 | play continues at x 335, unchanged |
| **I**, same stage | 16 | 1-1 restarts (x 32, timer full) |
| hit again, then **I** to 3-1 with Original and No Damage | 16 | 3-1 starts, options `$03` |

Score and lives carry over as before. Only bank `$45` (the menu, code after
the insertion moved 5 bytes) and the splash version text differ from
1.08-dev; the menu runs only after Select, so normal play is unchanged.

## Start timing (1.09 candidate, 2026-10-21)

Build `f84a31a8…b912` (1.09). Emulator evidence only. From power-on, with
Run pressed for 2 frames every 20 frames (real input only), the original
(Japanese, and English forced as in the cinema audit) and 1.09 reached the
same master-state changes on the same frames: intro at frame 6, title at
43, story at 63, gameplay at 82, and the first 1-1 gameplay update at
frame 163. Pressing Run at power-on leaves Enhanced's splash without a
frame of delay, so time from the title press (or from power-on) to control
is unchanged. Without input, the splash holds the opening scene back (115
frames in the cinema audit) before any speedrun timer starts.

**Cinemas after full play, 1.09 candidate.** The cinema check above, rerun on
`f84a31a8…b912`: the same 10 cinemas after all 11 runs, every frame
identical to the original's (same frame counts as on 1.08-dev).

## Smoothed comparison runs (1.09 candidate, 2026-10-21)

Build `f84a31a8…b912` (1.09). Emulator evidence only (Geargrafx, headless
MCP debugger). Method: [COMPARISON-VIDEOS.md](../COMPARISON-VIDEOS.md),
"Smoothing a run".

**Harness.** Both games are now recorded in fresh sessions from a start
state made in a session of its own. Before, the original was recorded in
the session that cold-booted it; there the first step after stage entry
sometimes covered two game updates (a probe of all 11 stages: 2-2, 4-1, 5-4
and 6-3), which showed up as the original running one update ahead from
frame 0. The first step after entry is now checked (stage timer `$2EDA`
down by exactly one). See docs/pc-engine/LESSONS.md, "A session that
cold-booted is not a clean replay session".

**Gameplay.** The 10 smoothed runs and the unchanged 5-4 run were replayed
on the original and on 1.09 and compared frame by frame as before: every run
finishes its stage, and the sprite table, Ryu's object bytes, the stage
timer, lives, health, camera, area and stage are identical on every frame.

| stage | input frames | recorded frames | identical |
| --- | --- | --- | --- |
| 1-1 | 2,843 | 2,903 | all |
| 2-2 | 3,946 | 4,006 | all |
| 3-1 | 1,863 | 1,923 | all |
| 3-2 | 3,137 | 3,197 | all |
| 4-1 | 2,488 | 2,548 | all |
| 4-2 | 2,638 | 2,698 | all |
| 5-2 | 2,929 | 2,989 | all |
| 5-3 | 6,769 | 6,829 | all |
| 5-4 | 955 | 1,015 | all |
| 6-1 | 1,733 | 1,793 | all |
| 6-3 | 5,123 | 5,183 | all |

**Cinemas after full play.** The cinema check on 1.09 with the smoothed
runs: after every run the next cinema is identical frame for frame to the
original's (scenes 3 to 10). Frame counts match the 1.08-dev table except
after 4-1: 1,106 frames instead of 1,081, the same in both games (the
cause of the longer capture was not examined).

