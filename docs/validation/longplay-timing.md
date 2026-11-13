# Full-playthrough timing recording (in progress)

Emulator evidence only (headless Geargrafx). Goal: one power-on-to-ending input
recording, replayed in the six palette modes, each with its mode already stored
in backup RAM (status SETTINGS LOADED, menu never opened, no Level Select).
Owner rule (2026-11-13): no re-syncing of the six replays except the start; the
headline is the plain replay with identical per-frame input. A re-aligned replay
is only a labelled secondary diagnostic, and only if a divergence occurs.

## State of the recording

`research/longplay/full.json` (ROM under test: v1.11-dev apocalypse, reset 2,
palette timing 2, ORIGINAL stored in backup RAM) reaches **the first update of
2-1** (stage byte 2, area 0), at frame **10,136** from 1-1's first update
(plus 480 boot frames before it). That is act 1 complete: 1-1, 1-2 (boss), and
the 1-2 cinema. Per-stage markers are in `stages` (name, start_frame,
end_frame, idle_after). No deaths, no Continue so far (1-2 is finished with
health 1).

- 1-1: the stored smoothed run `research/comparison-runs/1-1.json`, replayed
  unchanged from the real start; it runs straight into 1-2 (no cinema).
  Verified: from a real start (no Level Select) 1-1's state after 2,843 frames
  is stage byte 1, area 0, health 9, lives 2.
- 1-2: a one-room boss fight (a bar). Bot search with boss scoring: 1,960
  frames, boss health reaches 0, Ryu at health 1. Then the game plays the boss
  death sequence and the 1-2 cinema with **no input**: idle 5,333 frames until
  stage byte 2, area 0, master 0 (the cinema (master 1,3) ends by itself at
  about frame 10,135; no button is needed).
- **Verification: partial.** The 1-1 to 1-2 transition and the idle tail were
  replayed in fresh sessions from power-on (scripts/longplay_lib boot, the probe
  `research/longplay/hand/idle_probe.py` reproduced the cinema ending at
  frame 10,135 to 10,136). A whole-file cold replay with a pass/fail check was
  NOT yet written. 2-1 area 1 was replayed from the file in fresh sessions
  (each search/probe session replays full.json first, the same way).

## What exists, how to run it

Environment for every command: `LD_LIBRARY_PATH=/workspace/build/toolchain/sdl3/lib`,
run from the worktree, long runs with run_in_background.

- `scripts/longplay_lib.py`: `boot_to_first_update(game, rom, mode, entered)`:
  power-on with the backup-RAM image `bram_image.settings_entry(options=MODE_BITS[mode])`,
  title left with Run (the palette_lag e2e loop), stops at 1-1's first update
  (`$8457`), saves and reloads that state (`entered`). Returns status (opt byte
  `$2100`, save status `$2105` = 9 for ORIGINAL here, boot frames = 480).
  `play_segments(game, segments)` replays `[frames,[buttons]]` segments in
  chunks of 500 (the emulator caps a step at 1000 frames), each checked.
  It does not use breakpoints (so no `step_recording`); a six-mode replay should
  use `palette_lag.step_recording` for the sound commands (`$38:$4006`).
- `scripts/longplay_search.py`: replays full.json, then the comparison_route
  depth-first search from that state, appends the stage to full.json when it
  finishes (then idles until the next stage's first gameplay frame).
  Flags: `--stage LABEL` (marker name), `--boss-hp ADDR` (e.g. `0x1035`) and
  `--forward left|right` (boss room: fixed fighting direction, scores damage once
  boss hp is above 0, finishes when it returns to 0), `--extra FILE` (hand-made
  or partial segments played before the search, run-file format `{"segments":...}`),
  `--extra-frames N`, `--budget NODES`, `--frames LIMIT`, `--seconds N` (wall-clock
  limit, default 600), `--out FILE` (do not touch full.json), `--commit-partial`.
  Unfinished searches write `/workspace/build/longplay/LABEL.partial.json`
  (whole route including --extra) and exit 1. Resume by passing it as `--extra`.
  A search costs about 4 s per node (about 450 frames per 90 s of search).
- `scripts/comparison_route.py`: one change: boss scoring only applies once the
  boss hp is above 0 (`cur['boss'] > 0`) because 1-2's boss hp is 0 until it spawns.
- Helpers in `research/longplay/hand/` (not maintained tools, paths inside them
  are scratch paths): `look.py PARTIAL` replays full + partial and saves a
  screenshot and a state; `grid.py STATE right|left` button-timing grid for a
  jump; `climb.py STATE left|right` wall-hop timing grid; `idle_probe.py` prints
  state changes while idling after full.json.
- **The six-mode replay and the per-act comparison do NOT exist yet.** The recording
  stops at 2-1, and nothing in this branch replays full.json in modes other than
  ORIGINAL. A replay entry point is still to be written (power-on with
  `MODE_BITS[mode]`, then `play_segments`, with the e2e per-frame trace).

## RAM and transition detection used

- Game-update counter `$2000`; master flags `$2240/$2241` (gameplay = `$2240` 0;
  title (1,1); cinema after 1-2 (1,3)); stage byte `$2E5F` (index in the Level
  Select list: 1-1 = 0, 1-2 = 1, 2-1 = 2); area `$2E60`; Ryu x (u16) `$2E9E`,
  y `$2EA0`; health `$2EAD`; lives `$2EAF`; camera x (u16) `$220F`; pages `$2237`;
  score `$2ED0` (6 digits). (Addresses are RAM offsets +`$2000` in CPU terms as
  comparison_route uses them: `HEALTH=0xead` etc. are offsets into the 8 KiB RAM.)
- Boss health: offset `$1035` (CPU `$3035`), 16 full, **0 until the boss
  spawns**; confirmed in 1-2 (it was 14 after a stray hit, 0 at death). The same
  address is used by comparison_route for 5-4. 2-1 is not a boss room.
- Stage end = stage byte changes, or master flag nonzero, or boss hp back to 0
  after having been above 0. After a boss death the stage byte stays the same
  for about 865 frames (area becomes 1), then the cinema (master 1,3); the next
  stage is detected by stage byte changed, area 0, master 0.
- Health is NOT reset between stages by the game apart from what the cinema/stage
  entry does: 1-2 ended with 1 and 2-1 began with 16.

## 2-1 (stage byte 2): what was learned (not finished)

Stage runs the bot found without hand help: area 0 to area 1. Area 1 is 5 pages
wide and **opens scrolled to its right end** (camera 388 at x about 516), so the
bot plays it leftward; further, the way on is up.

- First trap: area 1, x 504 to 520, y 58 (health 15): a gap between a central
  pillar (hazard-stripe column) and the right wall; below it a pit (y 205, death).
  Hand grid (`grid.py`, state at that spot): the combination "right 3 frames, I+right
  24, right 28" reaches x 603, y 56 safely (on a girder to the right). Other
  grids ending in the pit all died. This hop is the start of the tail of
  `research/longplay/hand/2-1.extra.json`.
- After it the bot walked left along the area to the left wall: second trap area 1,
  x 28 to 41, y 73 to 152 (it hangs on the left wall; the scene is a vertical
  shaft with girders). `climb.py` showed wall hops (2 frames I+right, then 10 to 16
  frames left) climb about 20 px per hop with no damage, y wrapping above the
  screen top (so the climb continues up beyond one screen).
- `research/longplay/hand/2-1.extra.json` = the bot's route to the second trap
  (`2-1.bot-partial.json`) + the first hop above + 8 wall hops (2 frames I+right,
  10 frames left) + 1 idle frame. Played after full.json it ends at area 1, x 15,
  y 127, health 15, lives 2, game frame 10,136 + 2,783. It is NOT known whether it
  is above the trap yet or where the exit zone of area 1 is: map it as the
  EMULATOR doc says (debugger x/y writes, 45 frame steps) before continuing the
  search from this extra file (`--extra research/longplay/hand/2-1.extra.json`).
  The last search (600 s limit) was started from it and killed at handover before
  any result.

## Map decoder and fast search (2026-11-13, continuing)

Emulator evidence only.

- **Collision map in ROM (one decoder for every stage):** a CPU trace of one
  2-1 frame (headless Geargrafx `set_trace_log`) shows bank 1 `$9299` mapping
  bank 7 at `$6000` and calling `$6000`, which tests Ryu's box (copied to
  `$2E91-$2E97`) against rectangles: bank 7 `$62F2 + 2*stage` -> stage table
  (`+2*area`) -> page table (`+2*page`, page = high byte of x) -> 5-byte
  records `[type, x0, y0, x1, y1]` until `$FF`. Types: `00` floor/platform,
  `01` girder, `02` wall Ryu clings to, `03` solid block, `13` door-like
  (some are the area exits, e.g. 2-1 area 1 top right x 1218-1248 y 0-64; a
  poke scan confirms which). No map buffer in RAM.
  `research/longplay/fast/stagemap.py STAGE` draws every area as ASCII
  (coordinates only; nothing of the ROM is stored).
- **Exit scan:** `research/longplay/fast/exitscan.py STATE` pokes Ryu's x/y
  over a 16-px grid of the current area, steps 12 frames and marks where the
  area or stage changes (diagnostic only; the recording never pokes).
- **Ryu state bytes:** `$2EA7` vertical speed (signed), `$2EAA` motion state
  (1 on ground walking, 3 airborne, 5 on arrival through a floor door), `$2EA5`
  x speed, `$2EA6` sub-pixel accumulator (do not key on it).
- **Fast core:** `research/longplay/fast/shim.cpp` + `Makefile` build
  `libgx.so` from the same Geargrafx 78fc3d7 core sources as the headless
  emulator (`-DGG_DISABLE_DISASSEMBLER`), driven in-process with ctypes
  (`fastemu.py`). It loads the headless emulator's state files. Check: from
  `entered.state` (1-1's first update, ORIGINAL), full.json's 10,136 frames end
  with all 8 KiB of RAM identical to the headless replay. About 1,330 frames/s
  per process; save/load of a state costs about 35 us.
- **Beam search:** `research/longplay/fast/beam.py`: real button input in
  4-frame chunks (none, left/right, with I and/or II), scored by waypoint
  progress, distance to the next waypoint (y weighted 0.3 by default so jump
  arcs survive), health; deduplicated by (waypoint, area, x/3, y/3, `$2EA7`,
  `$2EAA`); the beam is shared between the top waypoint levels; 4 worker
  processes own the states. 2-1 area 1 (the leg the old bot could not do)
  took 93 s.
- **Stage builder:** `research/longplay/fast/extend.py research/longplay/plans/STAGE.json`
  replays full.json in the fast core, runs the plan's legs (fixed segments, a
  prefix of a run file, or a beam leg with waypoints read off the map), caches
  solved legs in `build/longplay/legs/`, idles to the next stage and appends
  the stage to full.json.
- **Cold-start check:** `scripts/longplay_check.py --mode MODE` (headless, one
  fresh session from power-on, whole file, PASS/FAIL per stage start and at the
  end record).

### 2-1 with the map (in progress)

- Area 1 (5 pages): the exit is at the **top right** (door x 1218-1248,
  y 0-64; poke scan: x 1224, y 8-24 -> area 2), not up the left wall where the
  bot was trapped (that wall x 0-20 is the area's left edge). Route: the pit
  hop at x 516 (old bot), girder x 562-640 y 69, block x 657-800 y 104, drop to
  the floor x 872-1023 y 152, girders up (y 133, 101, 69), along y 69 to
  x 1152, jump into the door. Beam leg a1: 544 frames, no hits.
- Area 2 (one-page shaft): entered at the bottom (x 156, y 190); exit door at
  the top x 164-208 y 0-32 (poke: x 168, y 8-24 -> area 3), reached by
  standing on the lower pillar (top y 106) and jumping beside the upper pillar.
  Leg a2: 124 frames.
- Area 3 (4 pages, played leftward from x 924): exit at the left end (poke:
  x 8, y 136-152 -> area 4). The floor has a gap x 100-328; the girder
  x 128-257 (top y 101) cannot be reached from the floor (y 152); the way is
  the small platform x 320-368 (top y 85) first. Leg a3 under search.
- Beam waypoints are [x, y, r(, area, ry)]; a floor gate needs a loose ry
  (girders above a floor change y by 19 px).
