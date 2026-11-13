# Full-playthrough timing recording

Emulator evidence only (headless Geargrafx). Goal: one power-on-to-ending input
recording, replayed in the six palette modes, each with its mode already stored
in backup RAM (status SETTINGS LOADED, menu never opened, no Level Select).
Owner rule (2026-11-13): no re-syncing of the six replays except the start; the
headline is the plain replay with identical per-frame input. A re-aligned replay
is only a labelled secondary diagnostic, and only if a divergence occurs.

## State of the recording

**Complete (2026-11-13):** `research/longplay/full.json` runs from 1-1's first
update to the finished THE END screen: 126,003 frames (+480 boot frames =
126,483 from power-on, 35 min 08 s at 60 Hz), 22 stage markers, no death, no
Continue (lives 2 throughout). Cold-start check `scripts/longplay_check.py
--mode original`: PASS for every stage start and the end (headless, one
session, 186 s). Table and per-stage method: section "Complete recording" at
the end. The paragraphs below are the history of how it was built.

### Earlier state (act 1, before the map work)

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

### Stages that have a Level Select comparison run

- The stored runs do **not** replay from the played-in start: 2-2's run dies in
  area 0 at every start offset 0-12 frames (`research/longplay/fast/tryrun.py`).
- Instead `research/longplay/fast/runpath.py STAGE` replays the run on the
  original through Level Select (headless, about 12 s) and records Ryu's
  path (frame, area, x, y, health, stage, `$2EAA`), committed in
  `research/longplay/paths/`. `plan_from_path.py STAGE` writes a plan with one
  beam leg per area whose waypoints are the path's grounded/clinging points
  about every 40 frames plus the area's last point (the way out). Points in the
  8 frames after an area change are skipped (stale coordinates).
- Ryu's y byte wraps above the top of the screen (a climb reads 250s); the
  beam treats y >= 224 as negative.
- Wall climbs need dense waypoints (every 12 frames, air points kept, r 12):
  2-2's area 2 climb up the right-hand door wall (x 1982, y 102 -> 18) is its
  own leg ("a2-climb", 296 frames).

### Beam lessons (2-3, 3-1)

- Motion state `$2EAA`: 0 stand, 1 walk, 2 crouch, 3 air, 5 clinging, 6 slash
  (ground or air), 8 crouch slash, 9 hurt (knock-back). Airborne = 3, 9, or 6
  with vertical speed `$2EA7` non-zero.
- A jump over a pit was lost because falling nodes (closer to the next
  waypoint) crowded the beam until they died. Now an airborne node keeps its
  takeoff score (health/boss terms still count) and a third of the beam is
  kept for grounded nodes. 3-1's gap at x 976-1040 needs a running start
  (standing jump 0.5 px/frame, running 1.5 px/frame).
- Path waypoints use standing/walking/clinging points only: the Level Select
  bot's slash and jump points include detours to fight enemies.
- Bosses: 2-3's boss health is `$1035` again (16 at frame 79 of the stage);
  the beam needs a pull toward the boss (its x at `$2F1C`, first enemy slot),
  otherwise ties keep Ryu standing; 708 frames, Ryu 14 -> 9 health. The idle
  after it (boss death + act 2 cinema) is 10,535 frames.
- `plan_from_path.py` cuts long areas into ~500-frame chunks ending on a
  grounded path point (goal `near`), so a solved chunk is cached.

### 4-1 and 4-2 (in progress at this note)

- 4-1: four plan chunks plus three area legs, solved without hand points;
  ends in the cinema; committed (`a50ecb9`), cold check PASS.
- 4-2: the y 71 ledges (type 00) only hold Ryu landing on them from above; a
  jump from the y 135 floor peaks at y 77 under them. Path waypoints now
  require Ryu standing (motion state 0/1/2, y within 8) and the bot's hop
  landings on platform tops (found from the ROM rectangles) are added as
  standing waypoints. Chunk 2 needed a hand point on the block x 1024-1097
  (top y 71); chunk 3 skips the bot's girder (x 1330-1359) and lands on the
  ledge x 1280-1535 directly from the floor (hand points). Chunk 4 (x 2041 ->
  2785, a bridge, the cliff at x ~2200 with a flying enemy at its top) is
  under search with a wider beam (120).
- New plan options: `add_points` [frame, x, y, r, ry(, standing)] and
  `skip_frames` [[a, b]] in a `follow` leg; wall hops are tried only while
  clinging.

### 4-3, 4-4, 5-1 (no Level Select runs for 4-3 and 5-1)

- 4-3 was made from the map alone: poke exit scans gave the exits (area 0:
  x 104, y < 24 on the left face of the hanging column; area 1: top right;
  area 2: x 1192, y < 24; area 3: right end x 744 -> area 4 = stage end).
  Hand waypoints per area; the gap x 624-720 in area 3 is crossed over the
  hanging wall x 544-592 and the platform x 645-672. Committed `cefe43c`.
- 4-4 boss: the 2-3 boss plan unchanged (484 frames). Committed `bcd18df`.
- Beam: a falling node is dropped as soon as no platform top or wall below it
  is within reach of the rest of its fall (ROM rectangles), so a walk off a
  ledge no longer outranks the running jump that clears the gap (5-1 x 1086).
- 5-1 (one area, 12 pages): legs to standing spots read off the map; the
  blocks that hang to 11-16 px above the floor (x 480-608, 1504-1600,
  2768-2896) are passed over, by the floating blocks before them.

### 5-1 and 5-2

- 5-1 (no run): 16 legs to standing spots off the map; blocks hanging to
  11-16 px above the floor are passed over; the ledge x 2210-2303 (top 72)
  is reached from the step x 2338-2366 (top 104), then the block top y 40.
  Goals now accept a slash pose only when Ryu's feet are on a map platform
  top (a slash at a jump's apex also reads vertical speed 0). Committed
  `26b9b10`.
- 5-2 area 2: the ledge x 194-255 (top y 40) is 64 px above the y 104 level,
  more than a jump (58 px). The Level Select bot got up by an enemy's
  knock-back; a timing grid from the step x 237, y 104 found the same (wait 4
  frames, jump left 20 frames: the hit lifts Ryu onto y 40, health -1). It is
  a fixed segment leg in the plan (`a2-knockback`), after the beam's route.

### 5-3 to 6-4B (and where 6-4C stands)

- 5-3: area 0's pipe exit needs up held on the pipe (motion state 4, about
  1 px/frame); area 2's first jump off the entry pipe works only from y 110
  (80 frames of up), grid-found and fixed; area 5's jump from the column top
  onto the girder grid-found and fixed. `be01f4b`.
- 5-4 boss (the 2-3 boss plan): 480 frames. 6-1: the path plan as generated.
- 6-2 (no run): map + poke exits per area (4 areas leftward/up the hanging
  columns' left faces, area 4 rightward to the end). `9db8c37`.
- 6-3: area 0's door column is climbed with up (fixed leg); area 2's post
  x 965-991 holds an enemy, Ryu gets onto it by a hit in the air as the bot
  did (grid); a drop from a cling and the exit by hand points. `1ef00b0`.
- 6-4A (676 frames) and 6-4B (1,105 frames) bosses: the boss plan. `b6d188a`,
  `6de7ed4`.
- `research/longplay/fast/rescue.py` turns a stalled leg plus a grid-found
  move into a fixed leg and a continuing beam leg.
- 6-4C (final boss, stage byte 21): boss health `$1035` = 16 from the 15th
  frame; the boss plan stalls with no damage at all; single attack patterns
  (slash, jump-slash at x 60-210) did no damage either. Ryu has no ninpo
  (HUD -00). Under investigation.


## Complete recording (2026-11-13)

Emulator evidence only (headless Geargrafx for the check, the in-process core
for the searches; both give identical RAM after the same input).

Command (one fresh session, power-on with the mode's backup-RAM image, the whole
file as one input list, no re-syncing):

    LD_LIBRARY_PATH=/workspace/build/toolchain/sdl3/lib \
      python3 scripts/longplay_check.py --mode original

Result in ORIGINAL: RESULT PASS; first gameplay frame of each stage (frames
from 1-1's first update; + 480 boot frames from power-on):

| Stage | Starts | Made by | Health at end |
|---|---|---|---|
| 1-1 | 0 | stored comparison run (verbatim) | 9 |
| 1-2 | 2,832 | old bot, boss scoring | 1 |
| 2-1 | 10,136 | old bot prefix + map waypoints (beam) | 15 |
| 2-2 | 13,241 | Level Select run's path as waypoints (beam), climb leg | 14 |
| 2-3 | 16,533 | boss beam (health `$1035`, pull to `$2F1C`) | 9 |
| 3-1 | 27,777 | path waypoints | 16 |
| 3-2 | 31,401 | path waypoints, wall hops | 16 |
| 3-3 | 34,853 | boss beam | 15 |
| 4-1 | 53,288 | path waypoints | 13 |
| 4-2 | 57,121 | path waypoints + hand points (ledge tops) | 11 |
| 4-3 | 60,358 | map + poke exits, hand waypoints (no run) | 10 |
| 4-4 | 64,423 | boss beam | 9 |
| 5-1 | 70,013 | map, hand waypoints (no run) | 14 |
| 5-2 | 73,264 | path waypoints + grid-found knock-back leg | 13 |
| 5-3 | 77,206 | path waypoints + grid-found pipe/girder legs | 13 |
| 5-4 | 82,882 | boss beam | 11 |
| 6-1 | 86,508 | path waypoints | 15 |
| 6-2 | 88,446 | map + poke exits, hand waypoints (no run) | 12 |
| 6-3 | 93,810 | path waypoints + climb, post (hit) and drop legs | 15 |
| 6-4A | 102,302 | boss beam | 12 |
| 6-4B | 106,468 | boss beam | 12 |
| 6-4C | 111,229 | boss beam on the head counter, then the stump | 14 |
| end | 126,003 | THE END screen fully faded in (flags `$2240/$2241` = 1,14) | |

The markers in `full.json` (`start_frame`) are where each stage segment was
appended; the check reports both (they differ by 0-4 frames where a stage's
first gameplay frame came inside the previous stage's last input segment).

- **6-4C (final boss):** owner's hint confirmed: the health bar (`$3035`)
  does not move at first; the head must be hit until it falls off. Its hit
  counter is `$303C` (RAM offset `$103C`, 16 down to 0; found by watching
  `$1030-$104F` while jump-slashing at x 130); only then do stump hits lower
  `$3035`. The beam scores the head counter, then the boss health (1,108
  frames). Static ROM scan: bank 2 `$A228` `DEC $3035`, bank 2 `$B321`
  `DEC $303C,X`.
- **Ending:** the boss death and cinema start at idle frame 877 (flags 1,13),
  the THE END screen's flags (1,14) at 11,849, its picture stops changing at
  13,665 (rendered-frame hashes); the file ends with 13,666 idle frames. About
  430 frames later the game moves on by itself (a black-and-white screen with
  staff names); the recording stops before that.
- **Six-mode replays:** not run by this work (the coordinator reports the
  six-palette checks through act 4 matched); the same command takes
  `--mode apocalypse|nes-a|nes-b|sms|"gb dmg"`.

### What the stages needed (reusable)

- Collision rectangles from ROM (bank 7 `$62F2` tables, `stagemap.py`); type
  00 tops hold Ryu only when he lands on them from above; 02 sides are
  clinging walls; door rectangles (13) are touched only from some sides (poke
  scans with `exitscan.py` find the exits).
- Motion state `$2EAA` (0 stand, 1 walk, 2 crouch, 3 air, 4 climbing a pipe
  with up held, 5 clinging, 6 slash, 8 crouch slash, 9 hurt), vertical speed
  `$2EA7`; jump height 58 px, running jump about 80 px across; wall hop
  (I + away 2 frames, toward 10) climbs about 20 px.
- Several places can only be passed the way the Level Select bot did, by an
  enemy's knock-back (5-2 area 2, 6-3 area 2): grid searches over
  wait/jump timings found them (`rescue.py` turns such a move into a fixed leg).
- Beam settings that mattered: airborne nodes keep their takeoff score,
  falling nodes are dropped when no platform is within reach (map), a third of
  the beam stays on the ground, standing waypoints require Ryu to stand.

## Six-mode plain replay of the whole recording (2026-11-13; emulator only)

Input: `research/longplay/full.json` as committed at `4bba5f4` (126,003 frames after
the 480 boot frames; 22 stage markers; ending record), replayed unchanged by
`scripts/longplay_six.py run` in a fresh headless Geargrafx session per mode:
power-on with the mode's backup-RAM image (menu never opened), title left with Run,
stop at 1-1's first update (frame 0), then the whole input list with **no
re-syncing and no RAM writes**. A seventh row, "unmodified ROM", is the original
HuCard (`Ninja Ryukenden (J).pce`, read-only) with no backup RAM and no settings,
same input, same start event. Raw logs and per-frame arrays: scratch
`/workspace/build/longplay-six/full/` (`raw/`, `run-*.log`, `compare.txt`); not committed.

| Mode | Result | Stage 1-1 .. 6-4C start frames | Ending (1,14) reached | Recording end | Game updates / lag frames | Gameplay state vs ORIGINAL |
| --- | --- | --- | --- | --- | --- | --- |
| ORIGINAL | PASS | all 22 as in `full.json` | 124,186 | 126,003 | 124,957 / 1,889 | reference |
| HELL (apocalypse) | PASS | identical | 124,186 | 126,003 | 124,957 / 1,889 | identical every frame except 2 single-frame shifts (below) |
| NES-A | PASS | identical | 124,186 | 126,003 | 124,957 / 1,889 | identical every frame |
| NES-B | PASS | identical | 124,186 | 126,003 | 124,957 / 1,889 | identical every frame |
| SMS | PASS | identical | 124,186 | 126,003 | 124,957 / 1,889 | identical except 1 single-frame shift |
| GB DMG | PASS | identical | 124,186 | 126,003 | 124,957 / 1,889 | identical except 1 single-frame shift |
| unmodified ROM | **FAIL** | 1-1 to 3-3 as ORIGINAL; 4-1 one frame early (53,287 vs 53,288); 4-2 onward missed | not reached (stuck in 4-1, stage byte 8) | 126,003 (stage 4-1) | 125,621 / 1,043 | diverges (below) |

Stage starts (gameplay from frame, identical in the six modes): 1-1 0, 1-2 2,832,
2-1 10,136, 2-2 13,241, 2-3 16,533, 3-1 27,777, 3-2 31,401, 3-3 34,853, 4-1 53,288,
4-2 57,121, 4-3 60,358, 4-4 64,423, 5-1 70,013, 5-2 73,264, 5-3 77,206, 5-4 82,882,
6-1 86,508, 6-2 88,446, 6-3 93,810, 6-4A 102,302, 6-4B 106,468, 6-4C 111,229.
Frames count from 1-1's first update; all seven runs boot in 480 frames to it.

### Difference between the six modes at the end

Frames are a fixed 358,995 master clocks (21,477,270 Hz, 16.715 ms). Differences vs ORIGINAL:

| Point (ORIGINAL frame) | Frames | Master-clock ticks | Milliseconds |
| --- | --- | --- | --- |
| Final boss defeated (boss health 0, 112,335), first main-loop update in that frame | 0 in all five | 0 in all five | 0 |
| Boss death sequence over (area 1, 113,147), first main-loop update | 0 | HELL +9, SMS +9, GB DMG +6, NES-A 0, NES-B 0 | at most +0.0004 |
| Last gameplay frame (master flag leaves 0 at 113,214), sound command | 0 | 0 | 0 |
| Ending (1,14) reached (124,186), sound command | 0 | 0 | 0 |
| End of the recording (126,003), frame-end clock | 0 | 0 | 0 |

The frame at which every event happens is the same in all six modes. Every stage-start
sound command (1-2 .. 6-4C) lands in the same frame at the same master clock in all
six modes (0 ticks). The six runs also start from the same clock (1-1's first update at
201,402,480 from power-on in each).

### What was compared between the modes

Every frame the harness reads the 8 KiB of RAM and stores the game-update counter
($2000; a frame whose counter did not move is a lag frame), master flags ($2240/1),
stage ($2E5F), area ($2E60), boss health ($3035) and two CRC32 fingerprints:

- CORE: counter; master flags; camera/pages ($220F-10, $2237); stage/area; Ryu
  block $2E9E-$2EB7 (position, health, lives); score and timer $2ED0-$2EDD; entity
  slots $2F00-$30FF (enemies, boss).
- WIDE: all RAM except $2100-$21FF (options byte, palette state, save status, stack),
  $2260-$2283 (palette upload queue), $2286-$2A85 (RAM palette and backup),
  $37C0-$37FD (WAITR, palette timing, worker scratch), $3C00-$3FFF (SHADOW). Those
  hold mode-dependent colour data, mode bytes or stack contents, which differ by design.
  No RNG address is identified in the docs; WIDE would include one.

Result: stage, area, master flags and boss health are identical in every frame in all
six modes. CORE: NES-A and NES-B identical in all 126,003 frames; HELL differs in 2
frames, SMS and GB DMG in 1 frame each. The single-frame differences: frame 97,648
(HELL, SMS, GB DMG): counter 55 vs 56 (one game update completed after that frame's
end, caught up in the next frame; totals of updates and lag frames are equal in all six),
with a few scratch bytes also differing; frame 60,709 (HELL only): Ryu's y byte $2EA0
is 190 vs 20 for that one frame. WIDE is not a useful pass/fail: it differs in 23,100 to
25,700 frames for HELL, SMS and GB DMG and in every frame for NES-A and NES-B, from
palette-related bytes ($2206/07 and similar) outside the excluded areas; I did not
find out what each byte is. Not measured: where inside the frame the update lands in
the frames where the counter shifted (97,648, 60,709): the clock windows (195 frames)
cover the stage starts and the end sequence only. So the sub-frame offsets are
measured at the marker frames only, not the whole run.

### Unmodified ROM (seventh row)

The plain replay does not hold on the original HuCard. First differences (frame,
what): 1: bytes $2050-$2051 differ (30,96 vs 182,181; a constantly changing value, role
not identified), $2257/8, and $3227 = 0 instead of 1 (the language byte, per
ARCHITECTURE: the patched default is English, the original Japanese); 5,668 first CORE
difference (1-2 boss/cinema area); 13,258 first game-update counter difference (74 vs 73,
17 frames into 2-2); 53,286 master flag and 53,287 stage/area: 3-3 hands over to 4-1 one
frame earlier than on the patched ROM; 64,504 boss health differs; 4-1's input then no
longer fits, and from 4-2 on every stage start FAILs. Stage-start sound commands up to
3-3 land in the same frame as ORIGINAL but 207 to 420 ticks (0.010 to 0.020 ms) earlier.
Not changed for the headline (no re-alignment). What is established: the
unmodified ROM is not frame-identical to the patched ORIGINAL for this input, it runs
2-2 onward with a different update count, and the language byte and the $2050 value differ
from the first frame. What is not established: which of these (the English text and
different screen lengths, or an unseeded random value) moves the 3-3 to 4-1 hand-over
by one frame; that needs a probe on the unmodified ROM's 3-3 boss/cinema.

### Cause of the unmodified-ROM drift: language or patch code (cause runs)

Emulator evidence only (Geargrafx 78fc3d7), plain replays of the same pinned recording
(cold power-on, real input, no RAM writes, no re-sync; frames count from 1-1's first
update). Raw outputs: `/workspace/build/longplay-six/cause/` (`raw/` per-frame arrays,
`probe/` RAM dumps, `run-*.log`). Tool options added to `scripts/longplay_six.py`:
`--tag`, `--shortcut` (native title language switch: hold I + II, tap Select, as in
`guide_screenshots.py`; the language byte read $3227 = 1 at the start of 1-1),
`--language` (saved language in the backup-RAM image for the patched modes; 0 = Japanese).
"ORIGINAL" below is 1.11-dev ORIGINAL palette, English (the earlier headline run).

| Run | Language ($3227) | Code | Result | 4-1 starts | First divergence from 1.11-dev ORIGINAL (English) |
| --- | --- | --- | --- | --- | --- |
| earlier | Japanese (0) | unmodified | FAIL from 4-2 | 53,287 | CORE 5,668; update counter 13,258; master/stage 53,286/53,287 |
| A | English (1, native shortcut) | unmodified | FAIL from 4-2 | 53,287 | identical to the Japanese unmodified run |
| B | Japanese (0, saved) | 1.11-dev ORIGINAL | FAIL from 5-1 (4-2 57,121, 4-3 60,358, 4-4 64,423 PASS) | 53,288 | update counter and CORE 65,934; master/stage/area 70,013 |
| C | English (1, default) | published 1.10 | FAIL from 4-2 | 53,287 | CORE 5,668; update counter 51,763; master/stage 53,286/53,287 |

Updates / lag frames / frames with more than one update: ORIGINAL 124,957 / 1,889 / 844;
unmodified (JP) and A (EN) 125,621 / 1,043 / 662 each; B 125,448 / 1,239 / 685; C 125,620 / 1,044 / 662.
Stage starts 1-2 .. 3-3 are the same frame in all runs (2,832; 10,136; 13,241; 16,533;
27,777; 31,401; 34,853). 1-1 is the common start.

Pairwise (first differing frame; None = identical over all 126,003 frames):
- unmodified JP vs A unmodified EN: None in counter, master, stage, area, boss health and CORE.
  The language byte alone changes nothing the arrays see in the unmodified code, story scenes included.
- unmodified JP vs C (1.10 EN): master, stage, area, boss: None; update counter 13,258 (C one update behind, 73 vs 74); CORE 13,258. 1.10 ends with 125,620 updates against 125,621.
- 1.11-dev ORIGINAL EN vs B 1.11-dev JP: nothing before 65,934; there B is one update behind (158 vs 159, nothing else in CORE differs).
- B vs unmodified (either language): same divergence as ORIGINAL vs unmodified (13,258; 53,286/53,287).

Where, and what the game is doing:
- 5,668 (CORE only, 1.11-dev vs unmodified and 1.10; counter equal): stage 1 area 0 to 1 (the boss/cinema area opens, counter 7 to 8). Five bytes in entity slots differ ($3099, $30B5, $30BC, $30D4, $30E4: 192/8/32/242/190 unmodified, 128/7/255/127/224 in 1.11-dev); they stay different afterwards. Not identified what those slot bytes are. Present in 1.11-dev in both languages, absent in 1.10.
- 13,258: stage 2-2 (stage byte 3, scene 3, master 0), 17 frames into gameplay: the unmodified and A runs complete one more game update (74) than 1.10 and 1.11-dev (73) in the same frame; the update/lag pattern differs for 8 frames in a repeating pair (13,258-13,316) and the totals stay one apart. Shared by 1.10 and 1.11-dev, independent of language. Cause not identified (RAM differs in about 530 bytes there, mostly the stack page and RAM-palette areas).
- 51,763: inside the act 3 story scene (master 1, scene 5, stage 7; the scene runs 36,490 to 53,287 in ORIGINAL). Unmodified is two updates ahead from here (it had one from 13,258; the shift at 51,763-51,765 adds one), 1.10 equals unmodified in master flow. 1.10 vs 1.11-dev: counter 210 vs 209 and a handful of bytes ($2011-$2029 scene variables, $2088) differ, i.e. the story scene's own text/timing variables run out of step. The story text engine is the code that reads $3227, but the Japanese/English runs of the unmodified code match exactly, so the difference is in the patched code's text/scene handling, not the choice of language.
- 53,286-53,287: the hand-over to 4-1 happens one frame earlier (53,287) in unmodified, A and C, and at 53,288 in every 1.11-dev run (the recording's own marker is 53,288).
- 65,934 (B only): stage 4-4's end (stage byte 11, master 1, scene 7, area 1): the Japanese run is one update behind the English run, then 70,013 (5-1) fails. Here language does matter, in 1.11-dev code only; what the text-scene code is waiting on is not identified.

What the evidence establishes:
- Language is not what separates the unmodified ROM from the patch: English-selected unmodified (A) is frame-for-frame identical to Japanese unmodified over the whole run, and 1.10 (English) matches the unmodified master flow, 4-1 at 53,287, at every frame. The same stage-start drift appears with unmodified code in either language.
- The earlier drift (4-1 one frame early, then fail) therefore follows the code: 1.11-dev's 4-1 start (53,288) differs from unmodified and 1.10 (53,287); 1.10 and 1.11-dev differ from each other from 51,763 in the act 3 story scene, and from the unmodified at 13,258 (both patched), i.e. the patches add timing (one update at 2-2) and 1.11-dev adds more.
- Within 1.11-dev language has a small effect of its own, from 65,934 (4-4 end scene), in this recording.
- Not proven: what in the code makes the 13,258 update, the 51,763 scene shift and the 5,668 entity bytes (no disassembly or breakpoints on those frames); that the 1.10 EN and 1.11-dev defaults differ only in code (they also differ in start clock: 201,402,243 vs 201,402,480 vs unmodified 201,402,039); other languages (Chinese); real hardware.

### Method notes

- Memory: one emulator at a time, 4 GB free required; each run holds the geargrafx
  process at about 1.6-1.7 GB RSS from boot with no growth (1,688 to 1,704 MB over a run;
  python 23-27 MB). The first attempt ran three at once and was killed by the system
  for low memory near frame 120,000 (nothing wrong in the runs).
- Breakpoints (sound command $38:$4006, main-loop update $8457) are armed only in
  the 195 window frames (`step_with_stops`, state normalised after each window).
  A 3,000-frame test gave fingerprints identical to the plain run.
- Boot: the unmodified ROM boots in the same 480 frames; its start clock is 441
  ticks earlier than the modes' (201,402,039 vs 201,402,480).
- Everything here is emulator evidence (Geargrafx 78fc3d7); no real-hardware claim.

### Re-aligned replay on the unmodified ROM (secondary diagnostic)

RE-ALIGNED, not a plain replay: the plain-replay headline above stands unchanged. Emulator
evidence only (Geargrafx 78fc3d7). Tool: `scripts/longplay_realign.py` (`build`, `starts`);
runs by `scripts/longplay_six.py run --mode unmodified --shortcut` (cold power-on, real
input). Raw outputs: `/workspace/build/longplay-six/realign/` (`raw/`, `run-*.log`, `probe/`).
Recording: `research/longplay/full-unmodified.json` (`adjustments` list; flagged
`complete: false`).

Method: only the number of idle (no button) frames in a hand-over stretch was changed,
at the end of the stretch; gameplay inputs and their order are untouched. One adjustment
was needed: frame 53,288 (3-3 to 4-1, act 3 story scene), -1 idle frame, because the
unmodified ROM reaches 4-1 one frame earlier (53,287). With it the unmodified ROM
reproduces every stage start 4-1 .. 5-4 exactly one frame earlier than the patched ROM
(each start keeps the same offset to the recording's marker; PASS in the checker with
shifted markers). A cold run of the 4-1 .. 4-3 prefix and a cold full run gave the same
starts.

Stage start = first frame with stage byte set and master flag 0 (the recording's
marker can be a few frames later). Patched = 1.11-dev ORIGINAL, English, untouched
recording (still PASS in the earlier full run). Unmodified = adjusted recording.

| Stage | Patched frame | Unmodified frame (re-aligned) | Cumulative difference (unmod - patched) |
| --- | --- | --- | --- |
| 1-1 | 1 | 1 | 0 |
| 1-2 | 2,832 | 2,832 | 0 |
| 2-1 | 10,136 | 10,136 | 0 |
| 2-2 | 13,241 | 13,241 | 0 |
| 2-3 | 16,533 | 16,533 | 0 |
| 3-1 | 27,777 | 27,777 | 0 |
| 3-2 | 31,401 | 31,401 | 0 |
| 3-3 | 34,853 | 34,853 | 0 |
| 4-1 | 53,288 | 53,287 | -1 |
| 4-2 | 57,121 | 57,120 | -1 |
| 4-3 | 60,358 | 60,357 | -1 |
| 4-4 | 64,423 | 64,422 | -1 |
| 5-1 | 70,013 | 70,012 | -1 |
| 5-2 | 73,264 | 73,263 | -1 |
| 5-3 | 77,206 | 77,205 | -1 |
| 5-4 | 82,882 | 82,881 | -1 |
| 6-1 .. 6-4C | 86,508 .. 111,229 | not reproduced | n/a |
| Ending (1,14) | 124,186 | not reproduced | n/a |

Result: the patched ROM is 1 frame (16.715 ms) SLOWER than the original game from the
act 3 story scene (between 51,763 and 53,288) through the 5-4 start, 0 before. Last
gameplay frame and ending: not measured (the unmodified ROM does not get there).
Updates / lag frames over the same stretch (unmodified frames 1..82,880 vs patched
1..82,881): unmodified 82,227 / 1,329; patched 82,226 / 1,339. Whole-run totals of the
patched ROM 124,957 / 1,889; the unmodified whole-run totals are only available from the
plain replay (125,621 / 1,043), which is out of step and not comparable.

Where idle shifts were not enough: stage 5-4 (stage byte 15), inside the stage, not in a
hand-over. The update/lag pattern parts at unmodified frame 82,899 (18 frames in: the
unmodified ROM completes updates in different frames, 17 frames from 82,899 to 82,956),
the boss spawns (boss health $3035 = 16) at 82,965 against 82,967 in the patched ROM
(one frame earlier than the -1 shift explains), boss health then drops at 83,023 against
83,024, the area change to the boss area never happens in step, and the unmodified game
leaves 5-4 at 84,154 (stage byte 14) while the patched game enters the 5-4 boss area at
84,320. The input no longer fits and 6-1 on fails. No inputs were invented.
What differs is the in-stage lag/update timing (same family as the 2-2 difference at
13,258, which did not break the run there); why 5-4 breaks is not identified. An RAM probe
at 82,880-82,965 (`probe/`) showed the Ryu block unchanged in both runs over those frames,
so it did not locate the cause either. Not measured: stages 6-1 to the ending, the
difference at the last gameplay frame and at the ending, any real-hardware timing.
