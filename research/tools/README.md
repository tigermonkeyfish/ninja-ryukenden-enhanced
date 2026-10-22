# Research probes

The tools behind the 1.02–1.09 investigations: background fidelity, timing,
slowdown and load-time parity. They drive the headless Geargrafx harness
([docs/pc-engine/EMULATOR.md](../../docs/pc-engine/EMULATOR.md)) and are kept as
**reference implementations**, not a maintained toolkit: they use Ninja
Ryukenden addresses (`$83F3` main-loop hook, `$8457` gameplay update, `$2E9E`
Ryu, `$2EDA` stage timer, Enhanced's `$FE46` renderer entry and others listed
in [ARCHITECTURE.md](../../docs/ARCHITECTURE.md)), and some were written for
one stage. For another game, copy the method and replace the addresses.

The supported tools are in `scripts/`; the case studies these probes produced
are in [LESSONS.md](../../docs/pc-engine/LESSONS.md).

## Setup

Paths come from the environment ([`local.py`](local.py)):

```sh
export GEARGRAFX=/path/to/geargrafx          # headless build, patched
export PCEAS=/path/to/pceas                  # for mkwork.py
export NINJA_ORIGINAL_ROM=/path/to/original.pce
export NINJA_ENHANCED_ROM=/path/to/enhanced.pce
python3 research/tools/loadall.py "$NINJA_ORIGINAL_ROM" orig
```

Results go to `captures/tools/` (ignored by Git; `NINJA_TOOLS_WORK` changes
it). Most probes take `ROM LABEL ...` and write `<probe>-<label>/`, so the
original and a build can be run side by side and compared.

Several probes date from before the fresh-session rule (LESSONS: "A session
that cold-booted is not a clean replay session"): they boot and enter stages
in one session. Their per-frame timing within a stage is sound, but compare
first-step results only between runs made the same way.

Units: the save-state clock (`FRAME = 358995` per frame, 1365 × 263 lines)
and the trace log's `+N` deltas are both master clocks (Geargrafx source);
divide by 3 for CPU cycles. `areadraw.py`'s "if units are master clocks"
hedge can be read as settled.

## Background fidelity (does Enhanced show the original's art?)

The capture pipeline: `capture.py` force-scrolls every area of both ROMs with
the same debugger interventions and saves VRAM, VCE palette, sprite table,
RAM and a screenshot per sample; the analysis tools decode the background
layer with `vdc.py` and compare.

| Tool | What it does |
| --- | --- |
| `core.py` | Session wrapper, stage jump, stdlib PNG I/O (shared) |
| `vdc.py` | Decode HuC6270 background layers from VRAM/VCE dumps (game-independent) |
| `capture.py` | Matched background sweeps for one ROM |
| `video_capture.py` | Screenshot every update of a forced sweep |
| `analyze.py` | Shift-tolerant comparison of matched samples |
| `model.py` | Test motion models (static backdrop vs scrolled texture) |
| `compose.py` | Model-based composition: native backdrop vs Enhanced texture |
| `stitch.py`, `pano.py` | Per-row speed and repeat period; stitched panoramas |
| `mapping.py` | Map each Enhanced panorama column to the native column it reproduces |
| `wrap_test.py` | Is each Enhanced row the native backdrop wrapped at a period? |
| `seams.py`, `find_seam.py`, `seam_shot.py` | Joins whose column pair never occurs natively; crops |
| `vshear.py` | Horizontal tears: row stacks that never occur natively |
| `relshift.py`, `shift2d.py`, `fine_probe.py` | Horizontal / 2-D shift between the two backgrounds |
| `entry_shift.py`, `entry_groups.py`, `horizon_index.py`, `round_page.py` | Round starts: opening composition and alignment |
| `content.py` | Missing or extra scenery by colour content |
| `palcheck.py` | Palette entries that differ and whether visible cells use them |
| `tileset.py`, `tilewatch.py` | Animated tiles: are Enhanced frames a subset of native ones? |
| `shotcheck.py` | Differences outside background cells (sprites, HUD, foreground) |
| `viz.py`, `viz_changed.py`, `make_pairs.py` | Diagnostic images |
| `report.py`, `build_report.py` | Per-area report and its HTML page |
| `death_test.py`, `death_hit.py`, `death_timer.py`, `reinit_test.py` | Background after a pit death, enemy death, time-out or Level Select re-entry. Compare it with the original's own respawn, not with a fresh entry: native animation makes some areas (3-1, 4-2, 5-3) differ from a fresh entry in the original too |

## Timing and slowdown (does Enhanced keep the original's frame budget?)

| Tool | What it does |
| --- | --- |
| `sweep.py` | Force-scroll every area both ways; count updates that take two frames |
| `tprof.py`, `prof.py` | Master clocks per update, by routine from the CPU trace (`tprof`) or by segment (`prof`) |
| `reach.py` | Reach a stage area at the gameplay hook (shared by the probes) |
| `loadall.py`, `load.py`, `samestart.py`, `entry.py`, `frames.py` | Stage load: frames from select to the first update |
| `loadmap.py`, `initdraw.py`, `inittrace.py` | Where a load's frames go: busy/idle map, clocks and traced cycles of the first draw |
| `areacost.py`, `areadraw.py`, `areaidle.py`, `areatrace.py`, `areawin.py` | Area changes inside a stage: frames, cycles, position within the frame |
| `respawn_u.py` | Time-out death to the first update after the respawn |
| `determ.py`, `cadence.py`, `stepcheck.py` | Update-aligned state traces, timer cadence, step checks |
| `runspeed.py` | Real input through an area: camera and frames per update |
| `starttiming.py` | Power-on and title press to the first 1-1 update |
| `verifyruns.py` | Replay comparison runs on the original; where each ends |

## Build helpers

| Tool | What it does |
| --- | --- |
| `mkwork.py` | Assemble all modules into a kept work directory with listings and symbols (for `tprof.py` labels) |
| `gencols.py`, `gencols22.py`, `gencols_sky.py` | Emit the column-copy code pasted into `src/castle`, `src/stage22` and `src/stage61-sky` (`*-generated.inc`) |
