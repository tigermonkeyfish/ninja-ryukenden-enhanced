# Failures worth preserving

These are Ninja Ryukenden case studies. Symptoms and fixes are tied to the
development record and current source; the portability statements describe
what to investigate in another game, not guarantees that the same cause
will explain a similar-looking bug. Versions named here before 1.09 (the
REV builds, 1.00, 1.01 and the 1.0x-dev builds) were internal development
builds; 1.09 is the first public release.

## Colored bars after death

**Observed:** a revision looked correct during initial play, but after death
Ryu was followed by colored horizontal bars, easier to see while jumping.

**Finding/fix:** renderer cache storage had reused `$2251–$2256`, native
background geometry needed by the respawn rebuild. Preserving that geometry,
moving the cache and invalidating it on initialization fixed the reported
corruption (stage-one work, 2026-09; addresses in the architecture map).

**Reusable lesson:** RAM ownership includes future lifecycle paths. Cold-boot
success is insufficient evidence that scratch storage is free. Add death,
respawn and jump to rendering regressions, and compare the rebuilt map as
well as the visible player sprite.

## Foreground building became transparent

**Observed:** the last building partly revealed the parallax behind it.

**Finding/fix:** foreground classification and palette ownership needed to
match the native game. The skyline was fitted into palette 1 while palette 2
and the foreground cutoff were preserved.

**Reusable lesson:** correct RGB output in one background capture does not
prove correct transparency or foreground ownership. Check map attributes,
palette indices and overlapping objects where background exposure is largest.

## Late-stage slowdown and glitching

**Observed:** late exposed scenery and the crowded encounter were worse than
the opening area.

**Finding/fix:** skip rendering when the camera is unchanged, upload on phase
changes, use sequential map writes and compact tables, and verify completion
against raster deadlines. Later split-sky work also required bounded transfer
chunks rather than an unrestricted bulk copy.

**Reusable lesson:** benchmark the busiest visible geometry and real enemy
load. Keep emulated update clocks separate from host performance. Increasing
ROM capacity can buy precomputation; it cannot by itself buy runtime time.

## Mountain cut and cloud seam in 2-2

**Observed:** a mountain was vertically cut near the entrance; later, cloud
edges aligned with the left ledge, and a repaired slope looked unnaturally
stepped or straight.

**Finding/fix (v1.00):** a 200-pixel mountain repeat with coherent
absolute-camera positioning, then cloud/contour joins repaired by editing
art from neighboring columns.

**Superseded:** since 1.03-dev no edited art is used. 2-2 loops 50 original
columns (native 0-33, then 9-24) chosen by a seam search, and the native map
turned out to contain its own 25-tile repeat (see "A small sky window went
blank" and "A loop seam test must measure what the review measures").

**Reusable lesson:** first separate motion/math errors from texture-repeat
errors, then from aesthetic art repairs. A camera offset is not a substitute
for fixing an incompatible texture boundary. Look for a loop of original
columns before editing art. Ask testers for a reproducible landmark and side
of the edge.

## Background jumps as a stage opens

**Observed:** the backdrop moved by itself immediately after load.

**Finding/fix:** preload the correct phase before revealing the scene, and
anchor new speed modes to the intended entrance composition. (The entrance
anchor later proved wrong for rounds entered at camera > 0; see "Round
offsets follow from entry cameras".)

**Reusable lesson:** distinguish the initial state from the first normal
update. Compare the untouched opening frame, the next update and the first
player movement. Ensure cache invalidation and initialization agree.

## Stage select returned to the old stage's boss

**Observed:** jumping from an earlier boss to 6-1 could lead back to the
earlier progression path on death/completion.

**Finding/fix:** visible stage selection was not the full native progression
state. Synchronize current stage, next master-script cursor and pending
progression flag (`$2241`, `$2247`, `$2248`).

The next-script cursor values were derived from the original's master
script, not typed in (architecture map, "Facts kept from retired build
scripts"). A later report found that a warp also kept the previous stage's
health: a native stage start refills it, a warp skipped that. 1.09 sets full
health (`$2EAD = 16`) on selection.

**Reusable lesson:** a debug warp must update the game's state machine, not
just map ID, and must apply the resets the native path performs (health,
timers, per-life state). Derive table values from the game's own data. Test
origin→destination→death, Continue and natural stage exit. History-sensitive
tests are necessary.

## No Damage could affect time-outs

**Finding/fix:** native contact damage and timer expiry share an entry point.
The timer's caller needs a bypass so optional contact immunity does not make
time-out immortal. Falling has its own native death path.

**Reusable lesson:** audit every caller before intercepting a shared routine.
Specify the option's behavior precisely and test each distinct death cause.

## A protective effect lost to the order of two checks

**Observed:** with the Fire Wheel spinning round him, Ryu was still hurt by
enemies he fell onto, by bullets, and by bosses.

**Finding/fix:** each enemy runs its contact check (hurts Ryu) before its
kill check (where the wheel kills it), and the wheel's hitbox reaches only a
few pixels below Ryu's feet. Anything entered faster than that per update,
and anything the kill check never kills, touches Ryu first. The "Use NES Firewheel logic"
option (1.11-dev) asks a separate rule from the existing damage
gate instead of reordering the native checks, so with the option off the
game runs the original code path.

**Reusable lesson:** when a power-up "should" protect but does not, read the
order of the per-object checks and the hitbox reach per update, not just
whether the protection flag exists. Put an optional behaviour change at an
existing choke point and keep the condition in its own routine so it can be
changed to match a reference without touching the hook.

**Confidence/limits:** game code read and emulator replays (1.11-dev,
[validation](../validation/nes-firewheel.md)); the per-object order is
Ninja's.

## One repeating moon became a fixed sky

**Observed:** a repeated moon made the stage look wrong; the requested result
was one stationary moon and twinkling stars with moving mountains.

**Finding/fix:** split sky and horizon responsibilities, retain native star
animation, match the preceding boss arena's moon placement, and check IRQ
timing for the added work. REV7 was reported working on real hardware.

**Reusable lesson:** identify which visual components should move before
optimizing a uniform scrolling effect. Preserve continuity across adjacent
scenes as an explicit requirement.

## Hidden English did not require a new translation

**Finding/fix:** the title shortcut changes native language byte `$3227`.
Set it to English at reset, then resume original initialization. The native
language switch and existing dialogue remain in use; chapter/logo artwork
is not automatically replaced.

**Reusable lesson:** look for latent game functionality before building a
replacement. Verify the option's complete lifecycle and distinguish text
selection from artwork localization.

## Experiments became hard to reproduce

**Observed:** successive builders relied on prior ROMs, generated files and
private emulator captures.

**Finding/fix:** freeze release identity, curate the actual runtime sources,
declare generated-data dependencies, and verify a clean source export.

**Reusable lesson:** preserve validated bytes and the path back to them while
refactoring tools. A patch bootstrap is an honest intermediate build model;
do not call it independent asset regeneration. Record the remaining migration
work instead of hiding fixture dependencies. (The bootstrap was later
retired: see "Retire a bootstrap patch by diffing outside the modules".)

## A gameplay atlas leaked into story sprites

**Observed:** v1.00 showed repeated garbage above a story portrait after the
second boss. The user reproduced it during ordinary Enhanced play, No Damage
OFF, and verified the original ROM was clean. A direct jump to the boss from
stage 1 missed it; running 2-2 first reproduced it in the emulator.

**Finding/fix:** a gameplay tile atlas occupied VRAM that the cinema engine
assumed was a permanently blank sprite. Native sprite-table reset did not
reset its pattern data. Clearing the borrowed 512 bytes at cinema entry
removed the corruption. See the architecture map for game-specific addresses
and the cutscene audit for verification scope.

**Reusable lesson:** VRAM allocation must account for every later consumer,
including invisible sprites, menus, endings and transitions. Blank patterns
are still assets with ownership contracts. Test the preceding gameplay
history, not just an isolated scene. A clean sprite table does not imply
clean sprite patterns. Compare complete ordered image sequences as well as
representative screenshots; separate image differences from timing shifts.

**Confidence/limits:** the overlap and cleanup were directly observed in RAM,
VRAM and rendered frames. The general lifetime rule transfers; the addresses,
blank-pattern convention and reset timing must be rediscovered per game.

## A small sky window went blank after scrolling was added

**Observed:** in a 2026-10 emulator review of v1.01, two of the four 5-2
climbing screens showed flat blue where the original's narrow cliff opening
shows clouds, a mountain and forest. Every pixel the patch drew was native
art, so a check of "is each pixel from the original?" passed.

**Finding:** the original backdrop is screen-locked, so it only needed art
inside the visible opening. The patch scrolls the backdrop from an anchor that
depends on the entry camera. Areas entered from the other end move the art out
of the opening before it comes on screen. Separately, 256-px wraps that the
native screen never displays left an unrepaired cut cloud (5-3) and a cut arch
(6-3). See [the review](../validation/background-fidelity.md).

**Reusable lesson:** before adding parallax, measure how the native backdrop
actually moves. A screen-locked backdrop has no designed continuation and no
guaranteed art outside its window. Verify three separate things: provenance
(every displayed window exists in native art), joins (adjacent columns that
never sit side by side natively), and content (scenery replaced by flat
colour). Test every entry direction and camera, because entry-dependent
anchors change which part of the texture each window shows.

**Fix (1.02-dev):** 5-2 uses a fixed anchor that aligns the art with the
opening wherever the climb starts. 6-3 loops at a multiple of its native
5-tile arch period. 4-2, the castle and 6-1 use bridge columns (next lesson).
The native 2-2 map turned out to contain its own 25-tile repeat. Before
inventing a loop length, compare a map's overscan columns (here 32-33) with
earlier columns: they can reveal the artist's repeat.

**Confidence/limits:** observed in emulation with VRAM-decoded backgrounds and
confirmed in an untouched session. The motion and anchor findings are
Ninja-specific; the three-check method and the overscan-repeat hint transfer.

## A round could open like the original or loop without a seam, not both

**Observed:** after the 1.02-dev fixes, rounds of 4-2, 5-3 and 6-1 still
opened on repaired art. The v1.00 seam repairs had edited the very columns the
original shows at a round start, because the patch's 32-tile loop equals the
screen width.

**Finding:** a screen-locked backdrop shows 33-34 native columns at once. Any
loop that short puts the wrap, and therefore any wrap repair, on the opening
screen. A longer loop (here 45 or 50 tiles) holds the untouched native picture
plus bridge columns that scroll into view only after the opening. The bridge
can be assembled almost entirely from existing material:

- native columns chosen by a boundary-pixel search;
- an earlier approved repair;
- a shape's own end, mirrored at a mirror-axis join (always continuous);
- periodic rows continued at their native period, so those joins are native
  adjacencies.

Choose the alignment from native column identity at each round's first frame.
Pixel-shift scores are ambiguous when only a small window of backdrop shows.

**Reusable lesson:** do not repair a wrap inside the region an exact opening
needs; move the wrap out of it. Reuse existing tile slots and upload lists
wherever the images are unchanged, then append the few new pairs as one
contiguous run: list space, not tile data, was the binding limit here. When
VRAM is full, a replaced native layer's tiles can be borrowed. Audit BAT
references (by palette), sprite pattern ranges, mid-area writes and the next
consumers (restarts, transitions, cinemas) before using them. Guard every
hand-placed code/data boundary with an assembler `.if … .fail` check, because
overlapping `.org` blocks assemble silently.

**Confidence/limits:** emulator-only. Every round start of the changed stages
was compared with the original's first frame. Mid-area restarts rebuilt
identically and the cinema audit was rerun (see the validation record).
Addresses, loop lengths and the borrowed tile range are Ninja-specific; the
bridge construction and the audit order transfer.

## The original art was packed, not lost

**Observed:** 1.02-dev could not show 2-2's left 56px or 5-2's exact opening
because the frozen patch data lacked those native tiles, and no 2-2 backdrop
tile occurred verbatim anywhere in the ROM. Every Enhanced profile depended on
art recovered from an earlier patch, so edits could not be told apart from
originals without the edit records.

**Finding/fix:** a VRAM write breakpoint on one backdrop tile during stage
initialization led to the graphics loader; its tables, header and packing
(`$F13F`: a control byte per 8 output bytes choosing literal or repeat per
byte lane) were transcribed into a static decoder. It reproduced every
backdrop and foreground tile request of all 11 stages word for word against
the original's VRAM. The palettes were not verbatim either: the live palette
was located in RAM, a write breakpoint on it led to the unpacker (9-bit
colours with their bit 8 grouped in a leading byte). The build now generates
every backdrop from the original ROM's tiles, maps and palettes.

Before the decoder existed, two missing 2-2 tiles were reported as "cannot
be recovered". The maintainer's reply ("why, we have the rom?") was right:
absent from the pipeline's inputs is not absent from the ROM.

**Reusable lesson:** when bytes cannot be found in the ROM, start from their
destination (VRAM, RAM palette buffer), break on the write and follow the call
stack to the decompressor. State a blocker as what the current pipeline lacks
and what would remove it. Model it offline and validate it against every
use, not a sample. Pin what the decoder produces with hashes so a different
ROM revision fails loudly. Owning the decoder separates "original" from
"edited" by construction.

**Confidence/limits:** decoder output equals emulated VRAM/VCE for every
parallax stage. Only the tile-set kind is modelled (sprite-pattern and row
kinds are not). The format is Ninja-specific; the method transfers.

## A loop seam test must measure what the review measures

**Observed:** a first search for loops of original columns minimised joins
whose tile pair never appears side by side in the original. In the emulator
review, two of its loops (3-2, 4-1) scored worse than the plain 32-tile loop.

**Finding/fix:** the review checks every 16x8-pixel window, by colour, against
the same row of the original. `scripts/native_seams.py` now minimises exactly
that count with an exact shortest-path search over the last two columns.
It found seamless original-only loops for 3-1, 4-1 and 6-3. It also showed
that the 34-column maps' last two columns are filler for the backdrop's jitter
(the castle's ground period breaks there), so they are not trusted as a
designed continuation. Each loop only keeps the columns that round starts
actually show: 0-31 when every round opens at camera 0, 0-32 otherwise.

**Reusable lesson:** make the search objective identical to the acceptance
test, including colour comparison across palettes. Separate the columns an
exact opening needs from overscan/filler columns, and let the search treat
the latter as ordinary columns.

**Confidence/limits:** window scores agree with the emulator provenance rates.
A low window count does not prove a join looks natural; the remaining seams
are listed for review by eye before any new art.

## Round offsets follow from entry cameras

**Finding:** every per-round loop offset measured against the original's
first frames (2-2, 6-3, castle, 6-1 at loop lengths 25, 30 and 45) equals
0 for a round entered at camera 0 and (1 - C/16) mod L otherwise (C a
multiple of 16, texture index 0 at native column 0). The build computes the
offsets from the entry cameras, and every round of the 11 stages opened
exactly at the new loop lengths.

**Reusable lesson:** once a few measured offsets fit a closed form, derive the
rest and verify them, instead of re-measuring each loop change.

## Two performance regressions hid in development builds

**Observed:** an emulated timing probe (clocks per gameplay update from the
save-state cycle counter, forced scrolling at 1-8 px per update) showed 5-3
dropping frames in area 4 on 1.02-dev, which v1.01 did not, and 6-1 using
far more time per update than v1.01.

**Finding/fix:** (1) the stationary 6-1 sky added 8 to its current offset but
rebuilt the cached previous offset without it, so every frame looked like a
coarse change and redrew all 14 sky rows. (2) The castle horizon reused 6-1's
upload lists and appended new runs, so 28 tiles per scroll phase were
uploaded but never referenced. Both are fixed: the cache check repeats the
same arithmetic, and the lists are regenerated from the slots the map uses.
5-2's longer loop added upload work; a shorter loop of equal seam quality and
unrolled column writes brought it below v1.01.

**Reusable lesson:** compare per-update work against the previous release at
several scroll speeds, not only "does it lag at walking speed". A cache test
must recompute the previous value exactly as the current one. When reusing
another module's upload lists, regenerate them from what the map actually
references. Upload cost scales with distinct tile pairs, so prefer the loop
with fewer pairs when seams are equal.

**Confidence/limits:** emulator timing only; forced scrolling with Ryu held in
place is not a crowded encounter. This probe covered 80 updates from each
stage's entry, and there no update ran late at 2 or 8 px per update. That did
not cover whole stages: the later sweep of every area found late updates in
5-3 and 2-2, including 21 in v1.01 itself (see "Sweep every area, then
profile the late update"). Hardware timing is not established.

## Borrow VRAM from the layer you replace

**Finding:** 2-2's longer loop needed 29 more tile slots than the VRAM range
earlier builds had proven. The original 2-2 backdrop's own tiles are free
while every backdrop cell is replaced: across all samples of all three areas
none was referenced by a foreground cell, none by a sprite pattern, and none
was rewritten mid-area. The next stage's initialization reloads that VRAM,
so no handoff cleanup is needed, unlike the earlier borrowed blank sprite
pattern that leaked into a cinema.

**Reusable lesson:** prefer borrowing memory whose next owner always reloads
it. Audit BAT references by word, sprite pattern ranges and mid-area rewrites
over the whole area, then rerun the transition audits (cinemas, deaths,
restarts).

## Block transfers held the playfield split a line late

**Observed:** one 1.03-dev sample of 5-2 (area 2, camera 192) showed the whole
playfield one line lower than the original for a single frame, sprites
unaffected. v1.01 had the same kind of frame.

**Finding/fix:** the HUD/playfield split is a scanline interrupt (RCR `$6F`)
whose handler writes BYR at raster ~69.9 lines after vblank in the original,
every frame (the original's main loop is idle by then). The Enhanced
renderers are still running at that line. A per-update probe of the BYR write
time over the full 11-stage sweep, with a delay stub added in the handler to
find the cut-off, showed:

- Geargrafx applies the write a line late from ~70.9 (one line after the
  original's time).
- In the shifted frame the interrupt waited for two back-to-back 32-byte VRAM
  TIAs (~0.62 lines each with VDC wait states) and the write landed at 71.08.
  It was not serviced between the two blocks.
- 5-2 and 6-3 (back-to-back 32-byte TIA chains) reached 71.08 and 71.01 in
  both v1.01 and 1.03-dev. A 32-byte TIA followed by another instruction
  (castle trampoline) or back-to-back 16-byte TIAs (phase-atlas stages)
  stayed at or below 70.55. Immediate `st1/st2` writes (2-2, 4-2) did not
  delay it.

1.04-dev puts a NOP between the 5-2/6-3 32-byte blocks (16-byte blocks did not
fit their code bank) and split the 6-1 sky upload's back-to-back blocks into
16-byte ones; since 1.06-dev the 6-1 sky also uses one 32-byte block per tile
with a NOP between blocks. The latest write over the sweep is now 70.51 in
every stage, and the shifted sample matches the original. The rule all
renderers follow: at most one 32-byte TIA, or two adjacent 16-byte TIAs,
without another instruction between.

How the cut-off was found: a first theory (the interrupt was pending during
the first block) was dropped when a breakpoint showed the handler running only
after the second. Reading Geargrafx's source located the rules involved
(`huc6270.cpp` latches BYR `k_huc6270_byr_latch_clocks` = 36 units before a
line's display start; `IsCpuVramSlotAvailable` blocks CPU VRAM slots during
background and sprite fetch, which is where the TIA wait states come from; an
interrupt is serviced only between instructions, never during a transfer).
A delay stub in the handler then measured the cut-off: no shift at 70.84
lines, a shift at 70.97.

**Reusable lesson:** if a game splits the screen with a scanline interrupt,
measure that handler's write time against the original while your code runs,
not just whether the frame finishes. Treat the longest stretch of
uninterruptible instructions as the interrupt's added latency, and in
Geargrafx count two adjacent block transfers as one. Keep block transfers
short or separate them. The worst case comes from a specific alignment, so
sample every update, not every 8th.

**Confidence/limits:** emulator measurement (Geargrafx), deterministic and
reproduced. Why the interrupt was not serviced between two adjacent blocks
was not traced in the source. Real-hardware interrupt latency and the BYR
latch point are not measured; the margin is ~0.4 lines in the emulator. When
a bug turns on an emulator timing edge, read the emulator's implementation,
bisect the edge with a delay stub, and record the result as the emulator's
model.

## Re-run the old generator before replacing frozen data

**Finding:** the castle sky and star images (788 tiles in banks `$7D-$7F` and
`$5D00`) were frozen from a v1.00 builder that read a VRAM and palette
capture. Re-running that builder's derivation from the ROM decoder (native
tiles, palette set 14, the game's star frame lists at bank 2 `$AD68`/`$AD6D`)
reproduced every image, star table, upload list and fixed upload byte for
byte. The build now regenerates them, checks the static castle tables
against the result, and no longer extracts any frozen backdrop asset; the ROM
did not change.

**Reusable lesson:** before redesigning frozen generated data, port its
historical generator onto decoded original inputs and compare. Identical
output proves the data was exact and lets the build take it over without a
visible change; a difference pinpoints what the old capture got wrong.

## Retire a bootstrap patch by diffing outside the modules

**Finding:** the source build applied the v1.00 patch and then overwrote it
with assembled modules. Comparing the built ROM with the original outside
the declared module ranges listed what the patch still supplied: three hook
bytes, 414 castle horizon images (223 of them unused since an earlier
rebuild) and an 800-byte notice font. Each became source or generated data,
and the build now starts from the padded original.

Moving the horizon images also changed timing. Uploading them from their
positions in the regenerated sky atlas split each phase's list into about 30
runs instead of 11-16. The screenshots of most areas were identical, but the
first frame of 5-3's area 4, which redraws everything with both upload
groups, took one frame longer, and every later enemy and star animation
shifted by a frame. Storing the images phase by phase in tile order (12-13
runs) restored the timeline exactly.

**Reusable lesson:** to retire a bootstrap patch, diff the built ROM against
the original outside the module ranges; what remains is the dependency
list, including dead data. After moving data, compare game-state RAM over a
deterministic flow, not just screenshots. A frame lost at an area transition
shows up later as animation offsets. State driven by the vblank interrupt
(here the sound driver) tells a dropped frame apart from a shifted timeline.

**Confidence/limits:** emulator measurement (Geargrafx), deterministic and
reproduced. The per-run and per-tile costs are specific to this renderer.

## Sweep every area, then profile the late update

**Observed:** frame-time probes of each stage's first area found no late
updates, yet a sweep of every scrolling area at 2 px per update (Ryu runs at
1.5) found 27 two-frame updates in 5-3 area 2 and 20 in 2-2. The original had
none.

**Finding:** an instruction trace attributed to code labels showed the late
updates were the ones that rewrite every visible map entry (the backdrop
crosses a tile) on top of the per-update tile uploads, in stretches with
heavy game logic. In 5-3's interior areas 96-98% of those entries are
foreground: the rewrite read each cell and wrote it back unchanged. Reading
only the BAT high byte and skipping foreground writes (re-seeking the write
address before the next backdrop cell) halved the rewrite; planning the
column split once per update instead of per row, and replacing a 16-step
divide-by-8 with shifts, did the rest. 2-2 is mostly backdrop, so there it
also skipped rows whose entries are all equal.

**Reusable lesson:** measure late updates in every area at a speed above the
player's, against the original, before trusting a frame-time average. Then
profile the late update itself. A shared-layer parallax that preserves
foreground pays for the foreground on every redraw unless it can skip it.

**Confidence/limits:** emulator measurement (Geargrafx), deterministic
sweeps. Margins are 5-10% of a frame in the worst stretches found.

## Check load times against the original, frame for frame

**Observed:** comparing screenshots taken a fixed number of frames after a
stage jump made some builds look a frame ahead or behind the original.

**Finding:** the harness's stage jump returns at slightly different times in
each build, so fixed-frame sampling shifts by an update. Counting frames
from the stage-select hook to the first gameplay update (and, for deaths,
setting the timer at the same update number) is exact. It showed that
Enhanced first draws during loading had made 2-2 (1.05-dev) and the 5-4
respawn (1.04-dev) one frame longer than the original, and 6-1 since v1.01.
Delay-loop ROMs (the renderer replaced by a loop of known length) located
the frame budget for the 6-1 first draw to within 300 cycles.

**Reusable lesson:** when an enhancement runs during a load, compare the
load's length in frames with the original, not screenshots after a fixed
delay. A delay-loop ROM turns "is it close?" into an exact cycle budget.

**Confidence/limits:** emulator measurement. Load-length differences of one
frame are invisible to play but measurable by timing.

## Treat every transition as a load, not just stage entries

**Observed:** stage entries and respawns matched the original frame for
frame, yet a scripted run of 2-2 with identical inputs showed the HUD timer
one frame behind the original from the second area onward.

**Finding:** area changes inside a stage are loads too. The native
transition initializes the background in its fourth frame and that work
fills about 0.8 of the frame; the Enhanced redraw added there (0.8 frame)
pushed the rest of the transition a frame later. The CPU position at each
frame end (idle loop or not) showed which frame overran, and a
frame-boundary-relative timeline of the native init and the redraw showed
why. Moving the redraw one frame later, into a frame the original spends in
its vblank wait, made every area change identical to the original.

**Reusable lesson:** list every path that rebuilds a background (stage
entry, respawn, area or room change, menu return) and measure each against
the original. A delay-loop ROM that skips real work can hide the cost
elsewhere (here the skipped draw moved to the first gameplay update), so
check where the work lands within frames, not only its length.

**Confidence/limits:** emulator measurement (Geargrafx), forced and natural
area changes. The deferral relies on the main-loop hook running in a native
wait frame before the first gameplay update, which was checked for these
stages only.

## Replays are frame-exact only from a loaded state

**Observed:** the same button input, replayed from the same cold boot,
sometimes finished a stage and sometimes died. Two games (original and
Enhanced) recorded in separate sessions occasionally diverged from their
first frame.

**Finding:** two things made the start ambiguous, both in the harness, not
the game. First, the two boot paths (Enhanced's splash, before 1.10) left counters
that stage entry does not reset, and one stage (1-1) was sensitive to them.
Second, after the debugger stops on a breakpoint mid-frame, the next
frame step (Geargrafx `debug_step_frame`) covered either the rest of that
frame or one frame more, varying between sessions; in a session that had
only loaded a saved state, it did not vary (a session that had cold-booted
the game still could: next lesson). Starting both games from one saved state of
the original (cartridge CRC retargeted for the other ROM), and saving and
reloading again right after the stage's first-update breakpoint, made six of
six repeated replays identical and every original/Enhanced pair identical
frame for frame.

Passive play did not prove this. Before the boot-path counters were found,
3,341 updates of idle and forced-scroll play matched between the builds and
looked like proof that no hidden state differed; real input then diverged
from frame 0. Idle and forced scrolling never ran the input-dependent code
that read those counters (boot-path bytes such as `$31EF` and `$3213` differ
between the two boot paths).

**Reusable lesson:** treat the emulator session as part of the experiment.
Start every replay from the same loaded state, normalize after breakpoint
stops, and verify determinism by repeating a replay before trusting
comparisons. Record both games separately and compare traces frame by frame
rather than assuming they agree. Test determinism with real input (combat,
jumps), not only idle or scripted scrolling, and list the bytes the two boot
paths leave different.

**Confidence/limits:** Geargrafx with the headless MCP debugger and
`NG_DEBUGGER_FAST=1`; other emulators and debuggers may differ.

## A session that cold-booted is not a clean replay session

**Observed:** recordings of the original sometimes started one game update
ahead of Enhanced (stage timer one tick further at frame 0), although every
step reported one executed frame. It first looked like a rare mis-step under
host load: one 5-2 recording differed and the next matched. Then 4-1
differed the same way twice in a row, and so did 5-2 again. In the harness,
the original was recorded in the session that had cold-booted it and saved
the shared start state; Enhanced only loaded that state.

**Finding:** in a session that has cold-booted the game, the first frame
step after stage entry sometimes covers two game updates, even after the
state is saved and reloaded. One probe entered each of the 11 parallax
stages once in such a session: 2-2, 4-1, 5-4 and 6-3 took two updates; in
sessions that had only loaded the saved state, every stage took one.
Reusing one session for several replays broke them in the same way: a
scoring tool that replayed runs one after another in one session saw hits
and deaths that a fresh session did not show. Confidence high for this
Geargrafx build; the emulator-side cause was not traced.

**Reusable lesson:** make the start state in a session of its own, and
start every recording (both games) in a fresh session that loads it and
does nothing else first. Within one session, loading saved states and
replaying from them is fine (the smoother relies on it); entering a stage
from the start state again is not. Add a tripwire on a counter whose
first-update step is known: Ninja Ryukenden's stage timer low byte (`$2EDA`)
counts down once per game update in every stage. Check what the emulator
reports for every step, and record both games again before calling a
mismatch real. Before using any game counter as a clock, confirm that it
advances in every frame: `$2000` stops while an area loads.

## Skipping foreground writes corrupted the map at a wrap

**Observed:** the faster redraw (read every BAT cell, write only backdrop
cells) overwrote foreground at column 0 of three castle rows (14, 16, 22).

**Finding/fix:** the copy keeps two write chains: one writes every cell in
sequence, the other skips foreground cells and re-seeks the VRAM write
address (MAWR) at the next backdrop cell. MAWR and the read address (MARR)
advance independently, so after a skip MAWR still points at the last cell
written. A chunk that ended in the skipping chain at a map-row end resumed
sequential writes from that stale address. Ending every such chunk with a
re-seek fixed it. The loops are 25-50 tiles long, so a texture wrap (at the
loop length), a stored-row wrap (map rows hold 64 entries; a run reaching
entry 64 resumes at 64 mod length) and the BAT row end all split the copy;
planning those splits once per update instead of per row also cut the cost.

**Reusable lesson:** in a read-modify-write pass over a shared BAT layer,
track explicitly whether the write pointer is in step and re-seek after any
skip at every boundary. Once a texture repeat is not a power of two, design
the copy around all three wraps and test a camera position that crosses each.

**Confidence/limits:** emulator, reproduced and fixed; the build with this
redraw ran on a Duo-RX without reported problems. VDC pointer behaviour is in
[HARDWARE.md](HARDWARE.md).

## A harness death trick failed on the original too

**Observed:** respawn stayed untested for days because the harness could not
kill Ryu. Holding his y position at `$F0` (a pit death in earlier builds)
no longer killed him, and Enhanced was suspected.

**Finding:** the unmodified game behaved the same: his y saturates at 247.
Setting the stage timer digits (`$2EDB-$2EDD`) to 002 gives a genuine
time-out death through the native path in all 11 parallax stage entries of
both games. Respawn screenshots then matched the original's in 10 of 11
entries (6-1 differed only in stars caught on other frames and the star its
stationary sky omits). Against a fresh stage entry,
three respawns differed (3-1, 4-2 and 5-3 by 864, 288 and 1,443 pixel
columns), but the original differed by exactly the same counts with an
identical BAT: native tile animation runs on, so a respawn screen is not a
fresh-entry screen even in the original.

**Reusable lesson:** force events through a native countdown (timer, health)
pushed to its last tick, not by poking positions the engine may clamp. When a
test trick fails on a build, run it on the unmodified game first. The
reference for any lifecycle path (respawn, Continue, area re-entry) is the
original on the same path and history; if you compare with a fresh entry,
measure the original's own delta too.

**Confidence/limits:** emulator. A time-out uses a different native path
from contact and pit deaths (see "No Damage could affect time-outs"), so it
does not cover every death cause.

## A harness intervention leaked into another tool

**Observed:** a route bot driven with real input walked Ryu to x = 856 while
the camera stayed at 768.

**Finding:** the background-sweep harness NOPs the game's player-driven
camera call (`jsr $E341` at bank 1 `$925E`, ROM offset `$325E`) so that only
its forced scroll moves the camera. The bot reused that harness code.

**Reusable lesson:** an intervention that is right for one experiment is
silently wrong for another. Keep each one opt-in per tool, off by default in
shared code and named in the tool's output, and start any real-input tool
with a smoke test of the behaviour an intervention would break (does the
camera follow?).

## Screenshots overstated a mismatch that VRAM disproved

**Observed:** asked whether the ORIGINAL setting really shows the original
background, a screenshot comparison found about 47% of samples differing, by
up to 98 pixels.

**Finding:** the VRAM background state of all 1,734 samples was identical to
the original's. The screenshot differences were timing: a sprite or
animation caught a frame apart.

**Reusable lesson:** decide equality on VRAM, palette (VCE) and sprite-table
(SAT) state, and use screenshots for what only the picture shows. When a
screenshot check is needed, mask sprite boxes from the current and previous
frame's SAT with a margin, and accept a mismatch only if one whole-frame
offset explains every pixel. Measure a documented claim before repeating it.

**Confidence/limits:** emulator, one measurement; the method is general.

## A vision-model judge missed small seams

**Observed:** in the v1.01 review, six calls to a general image-comparison
model judged screenshot pairs. It flagged the large 5-2 defect (the missing
vista) and accepted the clean and intentional pairs, but called both small
wrap seams "same" (5-3 at 0.79, 6-3 at 0.99).

**Finding:** the provenance-window and seam counts found everything the
model found and more, deterministically. Using the model to steer the route
bot was considered and rejected: slow, paid, non-deterministic, and the
emulator already gives exact positions in RAM.

**Reusable lesson:** a vision model is at most a coarse second opinion on
composed images. Acceptance rests on deterministic VRAM or pixel metrics,
route search on RAM state. Log every call and keep its authorisation narrow.

**Confidence/limits:** one batch of six calls, one model.

## An added boot screen must cost no frames when skipped

**Observed:** Enhanced adds a notice screen before the publisher logo.
Without input it reached the title at frame 801 against the original's 618,
and the opening scene started 115 frames later.

**Finding:** pressing Run from power-on in both games reaches the first 1-1
update on the same frame (163), because Run leaves the notice with no delay.
An earlier build shortened the native publisher screen instead; that was
reverted, and the notice ran in front of an untouched native sequence,
which stayed byte-identical to the original. (1.10-dev removed the notice at
a player's request; its version and credit moved into the in-game menu.) (Speedrun timers for the NES
Ninja Gaiden games start at control or at Start, not at power-on; no PC
Engine leaderboard was found.)

**Reusable lesson:** make an added boot screen skippable by the button the
original's first screen accepts, with zero added frames, and insert it before
native sequences rather than editing them. Measure power-on to first control
(mashing the button) and title Start to control against the original before
calling a patch speedrun-safe. `research/tools/starttiming.py` does this.

**Confidence/limits:** emulator measurement.

## A palette written only to the VCE came undone at the next re-queue

**Observed:** while adding palette modes, the stored 1-1 run showed the
Enhanced skyline in red and white instead of blue from the area-1 fade-in to
the end of the stage, in 1.10 and 1.11-dev alike.

**Finding/fix:** the 1-1 renderer wrote its merged backdrop palette straight
to the VCE; the game's RAM palette (`$2286`), the source of every upload,
kept the native colours, so the first full re-queue (a fade) put them back.
1-1 and 2-2 now write their palettes into the RAM palette and to the VCE at
once.

**Reusable lesson:** in a game that keeps a RAM palette and queues uploads,
every added colour belongs in the RAM palette; a VCE-only write lasts until
the next fade, pause effect or palette reload. Test the frames after a
re-queue, not just the frame the colour was written.

**Confidence/limits:** emulator, all 11 stored runs; the RAM-palette design is
Ninja's.

## Mapping colours in the vblank upload costs the main loop its slack

**Observed:** the GB DMG mode maps each queued colour through a table in the
vblank interrupt (about 156 master clocks a colour against the native TIA's
42). Kept before the display start (about 22.8 lines after vblank), it still
made area changes in 2-2, 5-3 and 6-3 a frame late: the frames around an area
change leave the native main loop under a line to spare.

**Finding/fix:** the upload may take no more time than the native one would
for the same entries; what is left waits for vblanks in which the main loop
was idle (the interrupted PC in the vblank wait) and goes a little at a time.
Every frame of the 11 stored runs then kept the Original mode's updates; the
price is palettes lagging up to about 45 frames in fades.

**Reusable lesson:** interrupt-time work competes with the main loop even
when it ends long before any raster deadline. Budget added interrupt work
against what the original does in the same frame, measure update counts over
whole runs (stage timer per frame), and use the hardware-event trace (VDC and
CPU interrupts, VCE writes, master clocks) rather than instruction traces to
time it.

**Confidence/limits:** emulator (Geargrafx), deterministic replays; the
slack figures are Ninja's. The cinema after 4-1, 5-3 and 6-3 still starts one
frame later in GB DMG mode, and so does the Level Select load of 4-4.

## A paused game's sprite-table buffer is free VRAM for a moment

**Observed:** the popup menu needed 260 words to keep the BAT cells its
window covers. RAM had no room and the stack no longer could hold them.
Ninja builds its sprite table in one of two VRAM buffers each update and only
then points the VDC's SATB register at it (no automatic SATB DMA).

**Finding/fix:** the menu runs inside the update (the Select hook), before
the sprite-table routine; it borrows the buffer being built, and the same
update rewrites all 256 words of it before it is shown. Exact-restore checks
compare the whole VRAM one update later with the same state run without the
menu.

**Reusable lesson:** a double-buffered table that the game fully rewrites
before every display is scratch VRAM between the start of an update and the
rewrite. Prove three things before borrowing it: the writer writes every word
every time, nothing else selects the buffer for display, and the borrower runs
in that window. Refuse the borrowing in states that reset the buffers
differently (here: death and continue).

**Confidence/limits:** emulator, all stored runs, every Level Select entry,
deaths and area changes; the buffer layout is Ninja's.

## Compare a paused run with an unpaused one at update boundaries

**Observed:** after a cancelled menu, RAM compared at a fixed number of frames
differed from the run without the menu in a stack byte and the CPU position,
and an occasional single screenshot taken at a breakpoint differed.

**Finding/fix:** the music driver keeps playing while the game waits in the
menu, so afterwards it spends different time in each interrupt and the update
in progress at a frame's end is a few cycles apart. Pictures are compared
after whole frame steps from a normalized state; machine state is compared at
the next update boundary (the main-loop hook). A frame step started at a
still-set execute breakpoint reports a whole frame although the CPU stopped
at the breakpoint again, so breakpoints are reached by continue-and-poll.

**Reusable lesson:** a pause shifts interrupt timing even when game state is
identical; compare state at a code point the game reaches once per update,
and take pictures only of completed frames.

**Confidence/limits:** Geargrafx `78fc3d7` behaviour of the debugger; the
interrupt-time differences are Ninja's sound driver.

## Adding a mode without moving the old modes by a cycle

**Observed:** the HELL palette mode needed a third branch in the vblank
palette upload and in palette_now, which the Original and GB DMG modes also
run every frame. Two added cycles in an interrupt can shift the next timer
interrupt's service, and with it the music driver's RAM at frame boundaries
(the GB DMG work saw exactly that), so whole-run identity checks (picture,
RAM, sprite table, VCE every frame) could fail for modes that did not change.

**Finding/fix:** the new test rides on branches the old paths already took.
The `bne` that sends Original away now lands on a `bcs` that Original falls
through (2 cycles), paid for by turning the following taken `bpl` into a
not-taken `bmi` (2 cycles less). palette_now's entry became one taken `bcs`
instead of a not-taken `bcc` and a `jmp` (2 cycles less); Original spends
them on its `bcs`, GB DMG on a `nop`. A `bra` that had to become a `jmp`
for range costs the same 4 cycles. The HuC6280 has no page-crossing
penalties, so moved code keeps its timing. The new mode's state needs went
to the writer instead: the old paths cannot test which mapped table the VCE
holds, so whoever changes the mode queues a full re-upload.

**Reusable lesson:** when old behaviour must stay frame-identical, count
cycles per path and per branch outcome, not just totals: rearrange so each
old path executes the same number of cycles in the same order up to its
first observable write, and push work the old paths cannot afford to the
rare event that needs it. Verify with the same whole-run identity check.

**Confidence/limits:** emulator (Geargrafx `78fc3d7`), all 11 stored runs in
Original and GB DMG ([validation](../validation/hell-palette.md)); cycle
counts from the HuC6280 tables and the trace log.

**Again with SMS (1.11-dev):** a first SMS build tested the SMS/HELL
variant inside HELL's path (13 cycles more): Original and GB DMG stayed
identical, but HELL's stored runs differed in the music driver's RAM in
hundreds of frames and in a few fade frames. The fix made the test free: a
copy of the variant in an option bit the dispatch already loads (`$2100`
bit 7, included in its `and` mask) makes the existing `cmp` leave N set
for SMS only, so family 11 needs just a `bmi`, and its 2 cycles were found
inside HELL's own paths (a `sec` the carry made redundant, a branch sense
flipped by testing earlier, a cinema path padded to its old length).
**Lesson:** before adding a test, look at the flags the existing compare
already produces; an extra copy bit in the byte being masked can carry a
mode split for free ([validation](../validation/sms-palette.md)).

## A per-stage colour exception without RAM

**Observed:** one input colour had to look different in one stage only
(HELL: 1-1's sidewalk fleck is also 2-2's far ridge). The obvious design
was a RAM key and value set by a stage-load hook and compared for every
colour in the upload, costing RAM (with its lifecycle audit), a hook in
code every mode runs, and a compare per colour in every stage.

**Finding/fix:** the upload already runs a loop per chunk; it reads the
visible stage there and, in the one stage with an exception, runs a copy of
the loop with the compare (`cpx #key / beq`, the value as immediates from
generated equates). Other stages pay one `lda/cmp/beq` per chunk; the other
modes nothing, so their whole-run identity held frame for frame. The colour
follows the stage variable from the first upload after it changes, so no
load hook is needed ([validation](../validation/hell-1-1.md)).

**Reusable lesson:** put a rare exception where the code already branches
per batch, keyed on state the game keeps anyway, and specialise the inner
loop for it rather than testing in the common loop. Separately: a per-frame
VCE check in Geargrafx can catch an upload in progress (the frame boundary
falls inside the vblank work), so a few cycles' shift can add a one-frame,
one-entry "not yet due" that is gone the next frame; look at the PC at the
boundary before calling it lag.

**Confidence/limits:** emulator (Geargrafx `78fc3d7`); one stage, one
colour.

## Code running in a mapped bank cannot unmap it

**Observed:** the first HELL build crashed at the end of its first upload:
the code in bank `$43`, mapped at MPR3 (`$6000-$7FFF`) by a stub in bank
`$46`, restored MPR3 with `pla / tam #3` and then executed its `rts` from
whatever bank the interrupted code had there.

**Finding/fix:** every exit that restores MPR3 is in bank `$46` (MPR2),
which stays mapped; the HELL code jumps there. A single-step trace from the
mapped code's entry showed the jump into the wrong bank at once.

**Reusable lesson:** a bank switch takes effect at the next instruction
fetch. Keep the switch-back, and anything after it, in a region the switch
does not touch (the fixed bank or another MPR), and unit-test new banked
code in place with the MPR it must restore checked afterwards.

**Confidence/limits:** HuC6280 behaviour, general to any banked 6502-family
code; seen in the emulator.

## Same code, other data: switch the bank under the running code

**Observed:** the SMS palette mode is the GB DMG mode with another colour
table. GB DMG's upload reads its table with absolute indexed loads
(`lda table,x`) from the same bank as its code; pointing it at another
table would have cost cycles (an indirect load, or a test and a second
copy of every lookup) in a path whose timing had to stay exact.

**Finding/fix:** a second bank holds a byte-for-byte copy of the code at the
same addresses, with the other table where the first bank has its own. The
SMS dispatch (reached only in SMS) does `lda #bank / tam #2` while running
in MPR2 and goes on at the next instruction, which the CPU now fetches from
the copy; every later table read hits the SMS table. The fixed-bank
trampoline that called the code restores MPR2 on return, so no exit path
changed. The copy is assembled from the same source lines (marked
`;@mirror` and copied by the build with each label renamed), with a guard
per label that the copy's address equals the original's, so the two can
never drift apart; a tampered copy fails to assemble.

**Reusable lesson:** when a routine must run unchanged with other data at
no cost to its existing callers, give the data its own bank and duplicate
the code into it at the same addresses; switch banks under the running code
at an instruction both copies share. Generate the copy from the same source
and guard it by address, never by hand. It costs the code's size again in
free ROM at the same bank offset.

**Confidence/limits:** HuC6280 MPR semantics (the switch takes effect at the
next fetch), emulator evidence in
[validation/sms-palette.md](../validation/sms-palette.md); needs free space
at the same offset in another bank, and the interrupted code must not depend
on the switched MPR (here the trampoline saves and restores it).

## Swap palette data where the loader maps its bank, not in the RAM palette

**Observed:** an alternative colour set had to reach every place the game
uses colours: the live RAM palette, its backup, every fade step, the area
changes' re-queues. All of it starts from two loaders that map one data
bank and unpack through one routine.

**Finding/fix:** the loaders' unpack calls go to a 26-byte hook in the data
bank's own free tail (mapped there at both call sites, so no fixed-bank
bytes); in the alternative mode it unpacks from another bank's copy, found
by the source address the loader set up. Everything downstream carries the
new colours by itself; tables that bypass the loaders (the HUD's) need their
own small hook. The colour data stay plain JSON, generated at build time.

**Reusable lesson:** find the narrowest point all palette data passes
(here the unpack call with its bank mapped) before patching consumers; a
bank's own unused tail is a place for a hook that its loaders reach.

**Confidence/limits:** emulator, every stage load and the stored runs
(validation/nes-palette.md); addresses are Ninja's. Even a 15-cycle test on
the unchanged path moved Ninja's music driver a timer tick in one stage,
with two single frames redrawn a moment apart: any hook on a load path
shifts sub-frame timing, so compare such builds per frame and explain each
difference.

## A pause that lets the sound driver run is not a pause for timing

**Observed:** after Ninja's popup menu (which waits for vblanks while it is
open), the game was compared with the same state run without the menu.
Everything matched at update boundaries, but in openings whose comparison
window reached an area change, one or two frame ends showed 2 BAT words
apart. The sound driver runs in the vblank interrupt and had played on
through the menu, so its work per vblank afterwards differed; the main loop
stood a few cycles elsewhere at frame ends, which shows only while the game
writes VRAM from the main loop across frames (an area change's redraw, a
stage load).

**Finding/fix:** clear the driver's own play flags while the menu is open
(its tick then advances nothing and only silences the channels) and put
them back after the menu's last vblank: the driver resumes from exactly its
state, and the PSG registers match the run without the menu from the
second frame on. The driver's pause/resume commands changed its state and
did not do it. The menu now returns before the emulator's frame boundary
(its last vblank is shorter), so comparisons start at the next vblank
interrupt in both runs, not at the return. What remains is the hardware
timer's phase: a timer whose period is not a whole number of frames runs on
through any pause, and a frame end inside multi-frame work can then see one
write more or less (once in 727 openings). The interrupt trace tells it
apart: VDC interrupts at the same times, the timer's moved.

**Reusable lesson:** when proving a pause "invisible", freeze every
interrupt-driven state machine that the pause does not own, compare from a
synchronisation point both runs share (an interrupt, not a return address),
and log interrupt entry times so that a residual timer phase is shown, not
assumed. Do not refuse the pause near the place a check happens to notice
the difference; measure whether the difference depends on the distance
first.

**Confidence/limits:** emulator (Geargrafx `78fc3d7`), Ninja's driver
(`$387E` bits 6-7) and timer (reload `$74`); validation/all-palettes.md.
Audio was compared as PSG register state, not listened to.

## The emulator never ran the unlock: backup RAM from a HuCard

**Observed:** Ninja's saved settings (1.11-dev) passed more than 200 backup
RAM images in headless Geargrafx without its unlock and lock code ever
being exercised: that build does not decode `$1807`/`$1803` for a HuCard,
so the memory is open whenever the machine has it. A wrong unlock would
have shown `SAVE: NONE` on the first console and nowhere else.

**Finding/fix:** a test-only copy of the emulator models the lock for
HuCards in four ways chosen by an environment variable: the MiSTer core's
rule (bit 7 of a `$1807` write opens, a `$1803` read closes), a stricter one
that opens only on the three bytes `$48 $75 $80`, a memory that ignores
writes, and no memory with an open bus. `scripts/check_bram.py --bram-model`
runs the whole image matrix on it. Three things made the result worth
believing: the check first proves that the emulator applies the model (a
copy of the ROM with the unlock removed must see no memory; the pinned
emulator is refused); negative controls must fail exactly as predicted
(unlock removed, cut down to `$80`, ending in `$00`, lock read removed); and
"locked again" is tested by a stub that maps bank `$F7` after every boot
and save and tries to read and write it, not by reading the emulator's
flag. The sequence itself was checked against two independent sources, the
System Card 3.0 ROM's own code and HuC's library
([HARDWARE.md](HARDWARE.md#backup-ram-bram-from-a-hucard)).

**Reusable lesson:** before trusting a pass, ask which lines of the new code
the emulator can make fail. For hardware an emulator does not model, build
the model (from a second implementation's source, not from the code under
test), make the test refuse an emulator without it, and add a mutant of the
code for every property claimed. Then say plainly what is left for the
console: here, whether the Duo's memory answers a card in the slot at all.

**Confidence/limits:** emulated on models read from the MiSTer core's RTL
and from HuC; the System Card bytes confirm the order of operations on the
Duo's own software. No hardware run yet
([validation/bram-save.md](../validation/bram-save.md)).

## A patched emulator linked from stale objects

**Observed:** the first test-only emulator was made by copying the pinned
emulator's tree with its object files, patching `memory.h` (new members in
the middle of a class) and `memory.cpp`, and running `make`. It built and
started. Its build log held link-time warnings that `Memory`'s declaration
differed between translation units: most objects had been compiled against
the old header and were reused. Separately, the emulator's CD unit calls
`Memory::UpdateBackupRam(true)` at every reset after the memory's own
reset, which would have re-opened the bank behind the lock model on any
reset of a machine with backup RAM.

**Finding/fix:** rebuilt from a copy with every object deleted (no
warnings), and the model now also governs `UpdateBackupRam`. The binary was
never used for evidence before the rebuild.

**Reusable lesson:** a test fixture needs the same review as the code it
tests. After patching a header in a copied build tree, delete the objects;
read the build log for type-mismatch warnings; and look for every caller of
the state the patch takes over, not only the paths the patch touched.

**Confidence/limits:** build logs (`build/bram-save/locktest/build.log`
against `build/v111/locktest/build.log`); whether the stale-object binary
misbehaved was not investigated.

## A reset-time loader has a budget, and a mashed button hides the overrun

**Observed:** the saved-settings loader walks the backup RAM directory at
low CPU speed during reset. The boot stayed the original's frame for frame
with ordinary directories, but with 112 tiny files the first stage update
came at frame 143 instead of 163 in the check that mashes Run: twenty
frames *earlier*.

**Finding/fix:** Ninja's reset code runs about 5.8 frames with interrupts
off, takes the pending vblank interrupt as soon as it enables them, and
then waits for the next one, 59,832 master clocks (43.8 lines) later. A
loader that ends inside that wait changes nothing; a longer one makes the
whole boot run one vblank interrupt behind. The check presses Run for 2
frames in every 20, so a boot one frame behind can meet an earlier press:
the number moved by a whole press period and in the "wrong" direction. The
real delay shows only in an idle boot compared picture by picture: the
same pictures, one frame later (`research/tools/bram-save/manyfiles.py`).
The walk costs about 950 clocks an entry and loading the entry about
10,600 more, so the boot is the original's up to 56 files with no saved
settings and up to 45 other files with them; `check_bram.py` asserts 48
and 42 entries and reports longer directories apart. The delay was left in
on purpose ([validation/bram-save.md](../validation/bram-save.md), "Many
files"): reading faster is not known to be safe, and refusing long
directories would trade a frame for a feature.

**Reusable lesson:** measure a boot hook's slack as "time until the next
interrupt the boot waits for", in master clocks, and compare idle boots
before input-driven ones. A check that feeds periodic input can turn a
one-frame shift into a multiple of its period.

**Confidence/limits:** emulator (Geargrafx `78fc3d7`); Ninja's reset path
only ([validation/bram-save.md](../validation/bram-save.md), "Many files").
