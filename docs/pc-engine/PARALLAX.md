# Smooth parallax using phase tiles

This recipe was implemented in Ninja Ryukenden. It applies when a background
layer shares the BAT with foreground (one VDC, no second scroll register for
the backdrop) and enough ROM, VRAM and update time can be made available.
Those conditions must be measured in each game. Ninja's implementation is
described in [ARCHITECTURE.md](../ARCHITECTURE.md); the case studies behind
each rule are in [LESSONS.md](LESSONS.md).

## Measure the native backdrop first

Find out how the original backdrop moves before designing anything: sample it
at several camera positions and compare with the native map. Ninja's
backdrops are screen-locked (no parallax; an 8 px jitter that depends on
travel history). A screen-locked backdrop has no designed continuation and no
guaranteed art outside its window, so scrolling it means building a
continuation, and areas entered at different cameras show different parts of
it.

## Generate everything from the original ROM

Decode the original's tiles, maps and palettes with your own decoder (find it
from a VRAM or palette-buffer write breakpoint) and generate the patch's data
at build time. Validate the decoder against every use in emulated VRAM/VCE,
and pin its output with hashes. Owning the decoder separates original from
edited art by construction.

## Reconstruct the background as pixels

A PC Engine background tile is 8×8 pixels stored in four bitplanes (32 bytes).
Keep palette indices and palette ownership, not only final RGB colors. Index
zero's transparency behavior matters where sprites or other tile artwork
overlap. A numerically identical index in two palettes need not mean the same
color.

`pce_tiles.py` implements this encoding with a synthetic bitplane test. Its
phase helper assumes both adjacent tiles share a palette. Palette conversion,
if needed, is the caller's explicit responsibility.

## Precompute eight horizontal phases

For each adjacent pair of tiles A and B, concatenate their eight-pixel rows.
For phase p in 0..7, keep columns p..p+7 and encode them as one tile:

```text
phase(A, B, p)[row] = (A[row] + B[row])[p : p+8]
```

Deduplicate pairs and repeated phase tiles to reduce storage. At runtime,
combine a coarse tile-map position with the selected fine phase. Both must
come from the same coordinate; mismatched rounding creates seams or jumps.
Upload cost scales with distinct tile pairs, so prefer the loop with fewer
pairs when seams are equal.

If the game animates any backdrop tile (Ninja's castle stars), find every
such tile with a VRAM write watch over the tile range. Either leave those
pairs out or precompute one image per (phase, animation frame) and pick it
from the game's own animation counters; never run a second animation clock.

## Build the loop from original columns

The visible map is not the artwork's repeat. Choose a loop of original
columns that keeps the native picture in order as far as round starts show
it, then repeats original columns:

- A screen-locked backdrop shows 33-34 native columns at once. A loop that
  short puts the wrap, and any repair, on the opening screen; a longer loop
  (Ninja: 25-50 tiles) holds the untouched opening plus bridge columns that
  scroll into view later.
- Search loops with exactly the acceptance test as objective (Ninja: 16×8
  windows compared by colour against the same row of the original;
  `scripts/native_seams.py`). Treat overscan/filler columns as ordinary
  columns, not as a designed continuation.
- List the remaining seams for review by eye before considering any new art.

## Keep the coordinate stable

Derive the background position from an absolute camera coordinate where
available. Screen coordinates modulo a map width can lose the information
needed for a non-power-of-two texture repeat.

For a requested background divisor q:

```text
D = floor(C / q) + anchor
```

The anchor fixes which texture column a round opens on. An anchor computed
from the entry camera (Ninja's first versions:
`anchor = floor(C_entry/2) - floor(C_entry/8)`, kept from a divisor-2
composition) makes rounds entered at camera > 0 open shifted and can move
art out of a small window. Instead, measure the original's first frame of
each round and derive per-round offsets; in Ninja every measured offset fit
0 for camera 0 and (1 - C/16) mod L otherwise, and one area with a narrow
window (5-2) uses a fixed anchor. Verify every round start against the
original's first frame.

At one-eighth camera speed, one background pixel advances per eight camera
pixels. Very low speeds still have visible pixel-sized steps. The user's
rejection of an earlier 10%-of-SMOOTH setting was an aesthetic observation,
not evidence of a broken divider.

## Separate texture boundaries from screen boundaries

A copy loop over a loop of length L meets three boundaries: the texture wrap
(L), the stored map row's wrap (Ninja stores 64 entries a row, so a run that
reaches entry 64 resumes at 64 mod L), and the BAT row end. When L does not
divide 64 all three move independently. Plan the splits once per update, not
per row, and test camera positions that cross each one.

A stationary sky can use camera-compensated phase/map selection while a lower
horizon moves. Ninja 6-1 keeps the upper sky and moon fixed and follows the
game's star animation. It also removes conflicting low star tiles at the
boundary. That row split is game artwork knowledge, not a generic constant.

## Respect foreground and palette ownership

Classify background versus foreground using the game's actual map/palette
conventions. Verify large foreground structures where much of the background
is visible. Reassigning a palette because it looked unused in an opening
screen can make a later building transparent or recolor another object;
check palette references across the whole stage's maps.

Palettes you add must also go into the RAM palette buffer the game's fader
reads, not only into the VCE, or the next fade restores the old colours
(Ninja 2-2 writes its two added palettes to both).

Ninja's stage 1 skyline colors fit in palette 1; preserving palette 2 was
necessary for the foreground building. Other stages use different layouts.

## Upload formats

The backdrop moves relative to the BAT on almost every update, so each update
uploads the current phase's images into fixed VRAM slots that the map refers
to. The phase images live in ROM; Ninja moves them in two ways, and neither is
best for every stage:

- **Block transfers from data** (`TIA` to the VDC data port, 16 or 32 bytes a
  block). Compact in ROM. Block transfers take immediate operands only, so a
  table-driven upload writes the instruction into interrupt-free RAM and
  calls it (HARDWARE.md). Each block delays interrupts (below).
- **Generated `st1`/`st2` code:** each VRAM word as two immediate stores, with
  seeks only at address discontinuities, packed into code banks. It costs
  four bytes of ROM per word but adds no interrupt latency. Words identical in
  all eight phases are uploaded once at initialization instead of every
  update.

## Bound the update cost

Cache the last camera/phase, skip unnecessary uploads, and use sequential map
writes where possible. Invalidate the cache on every initialization path that
can rebuild maps or graphics, and recompute the cached value exactly as the
current one. Preload the correct phase before revealing a stage if the first
normal gameplay update would otherwise cause a jump.

- **Foreground on a shared layer costs time on every redraw.** Ninja's
  redraw reads only the BAT high byte (palette nibble) of each cell and writes
  only backdrop cells, re-seeking the write address after skipped cells.
  Interior castle areas are 96-98% foreground, so this halved the rewrite.
  Rows whose entries are all equal can be skipped.
- **Raster splits limit block transfers.** The renderer still runs when the
  HUD/playfield split interrupt fires, so the longest uninterruptible stretch
  delays its scroll write. Ninja's rule, from measurement: one 32-byte TIA, or
  two adjacent 16-byte TIAs, with another instruction (a NOP will do) before
  the next block.
- **Order the work.** Run native work that must finish before scanout (the
  game's tile-animation upload) before the parallax work, and upload the top
  rows before the bottom ones.
- **Loads are part of the budget.** Drawing during a load can make the load a
  frame longer than the original; compare load lengths in frames for every
  stage entry, respawn and area change, and move a draw into a frame the
  original spends waiting for vblank if needed.

Measure scenes with maximum background exposure and active enemies, in every
area, at a speed above the player's. Do not transplant Ninja's bank numbers,
tile slots, palettes, spare stack bytes or time budget into another game.
Reuse the algorithm and the measurements that establish those resources.

## Select renderers by the game's own descriptor

Ninja's dispatcher recognizes a backdrop by the native background descriptor
(height, foreground cutoff, map address), not by stage number. Every path that
loads that backdrop (stage entry, area change, respawn, Level Select) then
picks the right renderer.

## Distribution

Phase tiles are derived from the original art and cannot be made at runtime
on a HuCard (8 KiB RAM, read-only cartridge, frame-exact loads), so a patch
that ships them carries derived game graphics. Ninja's patch, measured in
the October 2026 development builds, contains
no verbatim original code, music, sprites or text beyond short coincidental
runs, but about 400 KB of backdrop data derived from the original (535 decoded
tiles, their phase shifts, rebuilt maps and palettes). Measure this before
publishing by diffing the patch's literal data against the original, document
it, and consider offering a build-from-your-own-ROM path (this repository's
source build is one). This is a technical description, not legal advice.
