# Original-versus-Enhanced comparison videos

Each parallax stage has a stacked comparison video for publication: the
original game on top, Enhanced below, playing the same button input frame
for frame. The input is stored here, so the videos can be regenerated for
any later build.

## What is stored

- `research/comparison-runs/<stage>.json`: the stage (Level Select index),
  the button input as `[frames, [buttons]]` segments starting at the
  stage's first gameplay update, and notes on how the route was made.
- `scripts/comparison_video.py`: replays runs, compares the two games frame
  by frame, renders the videos, and checks the cinema after each stage.
- `scripts/comparison_route.py`: the route search that produced the runs.

Videos, recorded frames and emulator states are generated files; keep them
out of the repository (the maintainer's copies are in an ignored `videos/`).

## Regenerate

Requirements: the headless Geargrafx build described in
[CUTSCENE-AUDIT.md](CUTSCENE-AUDIT.md), `ffmpeg` with libx264, and the Noto
Sans fonts (any other font is found through `fc-match`).

```sh
python3 scripts/comparison_video.py --emulator /path/to/geargrafx make \
  --original /path/to/original.pce --enhanced /path/to/enhanced.pce \
  --version v1.09 --work /tmp/comparison --videos videos \
  research/comparison-runs/*.json
```

For each run this cold-boots the original, saves its machine state at the
main-loop hook in 1-1 and loads that one state into both games (for Enhanced
with the cartridge CRC retargeted and its options at their defaults, the
same declared intervention as the cinema audit's seed). It then enters the
stage exactly as the patch Level Select does (the same debugger writes in
both games), replays the input one frame at a time, records every frame, and
compares the two games. The shared state matters: the two boot paths
(Enhanced's splash) leave counters that stage entry does not reset, and the
emulator's frame-step phase depends on a session's history, so only replays
from one loaded state are frame-exact (1-1 diverged from its first frame
otherwise).
A video is written only if the sprite table, Ryu's object bytes, the stage
timer, lives, health, camera, area and stage match on every frame; game RAM
outside Enhanced's own bytes is reported as well. The two games are recorded
one after the other, each in a fresh emulator session that loads the start
state and does nothing else first; the start state is made in a session of
its own. (A session that has cold-booted the game sometimes runs two game
updates in its first step after stage entry: see
[LESSONS](pc-engine/LESSONS.md).) Every frame step must report exactly one
executed frame, and the first step after stage entry must count the stage
timer down by exactly one. If the games differ, both are recorded again,
and only a difference that repeats stops the video.

Output: 2560×1440, 60 fps, H.264 High, yuv420p, BT.709, `+faststart`, with a
silent AAC track (the emulator interface has no audio capture). Each game is
the 256×224 display scaled 3× with nearest-neighbour pixels; labels name the
stage, both versions and the frame number. A recording note names the
emulator and its build as the emulator reports it over the debugger
interface (Geargrafx `78fc3d7`; the local build adds only an opt-in change
to host polling speed in headless mode, not to emulation), the host OS, and
that it is an emulator recording without audio. The host's speed cannot
change the result: the emulator is stepped one frame at a time.

## Cinemas after full play

```sh
python3 scripts/comparison_video.py --emulator /path/to/geargrafx cinema \
  --original /path/to/original.pce --enhanced /path/to/enhanced.pce \
  --work /tmp/comparison research/comparison-runs/*.json
```

After replaying each run, the following stages render for 120 frames and
leave through the native completion path, as the cinema audit does, and the
next cinema is captured frame by frame in both games (native English in
both). Every frame must match. This complements the full cinema audit,
which reaches every cinema but only renders 120 frames of each stage: here
the Enhanced renderer has run through the whole stage (every area, scroll
phase and animation) before the cinema loads.

## Making a new run

```sh
python3 scripts/comparison_route.py --emulator /path/to/geargrafx \
  --rom /path/to/original.pce --stage 3-1 --out research/comparison-runs/3-1.json
```

The search starts from the same kind of loaded state and plays with real
button input only. Boss rooms (5-4) score damage to the boss instead of
distance. Where it cannot find a way
(2-2 area 2 needed a climb up the right-hand wall; 5-3 and 6-3 several
climbs), script the segments by hand, save them as a run file, and continue
the search from it with `--prefix`. Search with the original ROM; the run
must then replay identically on Enhanced, which `make` verifies.

Hand-scripting that worked:

- Map an area from a saved state by writing Ryu's x (`$2E9E`) and y
  (`$2EA0`) with the debugger, stepping 45 frames and reading where he
  lands. This shows the platforms, pits, and the exit zones (the area
  changes). It is a diagnostic only: the run itself must reach each spot
  with button input.
- Then search small grids of button timings between two landing spots and
  keep the first that arrives with health left and stands still.
- Wall hops: hanging on a wall, I plus away for 2-4 frames, then toward for
  10-14 frames, regrabs higher; repeat to climb. Long gaps need a running
  start.
- Public longplays and speedruns show the intended way through; use them
  only as a local reference.
- Replay every finished run from a cold start (as `make` does) before
  saving it: a route found from a mid-run state can depend on that
  session's history.

## Smoothing a run

```sh
python3 scripts/comparison_smooth.py --emulator /path/to/geargrafx \
  --rom /path/to/original.pce research/comparison-runs/5-2.json
```

The route bot reaches the end of a stage but hesitates: it turns back,
stops and makes small hops (50 to 110 on-screen turns a minute). The
smoother uses the finished run as a guide and plays the stage again on the
original, in three passes (`--passes`, default `reroute,unhit,unturn`):

- **reroute** (the main pass): from checkpoint to checkpoint of the old run
  (every 90 frames and at each area change), a small search over plain moves
  (run, running jump, slash, jump-slash, a short wait) finds the shortest
  way to the next checkpoint; the bot's own moves (back steps, wall hops)
  are used only where plain moves cannot pass, then a wider and deeper
  search. Where the first way found takes a hit, the search goes on for a
  few more moves for one without. Progress is measured along the old path
  and must be continuous, because positions repeat in shafts and the y byte
  wraps above the top of the screen. Where no search passes (the wall climbs
  of 5-2, 5-3 and 6-3), it returns to the latest checkpoint from which the
  old input, aligned within 12 frames, still finishes the stage; the old
  run's own start is always such a checkpoint.
- **unhit**: before each hit, the same input with slashes (in the air,
  which keeps Ryu's path, or anywhere) or an earlier jump, kept only if the
  stage then ends with more health.
- **unturn**: each short burst of backward input is replaced by forward
  input or by standing still, and each stall is cut out, if the run still
  finishes.
- **shortcut** and **calm** (optional): plain input that reaches a later
  point of the run sooner, or a back-and-forth stretch replaced by walking
  and waiting that arrives on the same frame.

Every edit is kept only if the run still finishes the stage without losing
a life. The result of each pass is also written next to the output
(`<name>.after-<pass>.json`), so a long smoothing can resume from it. Then
run `make` again: the smoothed run must still play identically on Enhanced.

Results for the stored runs (emulator replays of the original, each in a
fresh session; turns are changes of Ryu's direction on screen, including
wall jumps and knockback):

| stage | frames | turns a minute | hits |
| --- | --- | --- | --- |
| 1-1 | 2,860 → 2,843 | 55 → 18 | 0 → 7 |
| 2-2 | 4,282 → 3,946 | 79 → 60 | 9 → 9 |
| 3-1 | 2,638 → 1,863 | 41 → 31 | 4 → 4 |
| 3-2 | 3,368 → 3,137 | 94 → 60 | 5 → 9 |
| 4-1 | 2,961 → 2,488 | 90 → 32 | 5 → 3 |
| 4-2 | 2,765 → 2,638 | 31 → 16 | 2 → 3 |
| 5-2 | 3,665 → 2,929 | 103 → 77 | 10 → 8 |
| 5-3 | 8,258 → 6,769 | 91 → 80 | 9 → 10 |
| 5-4 | 955 (unchanged) | 68 | 8 |
| 6-1 | 2,004 → 1,733 | 50 → 4 | 3 → 4 |
| 6-3 | 6,681 → 5,123 | 109 → 70 | 6 → 13 |

The smooth routes run past enemies that the bot stopped to fight, so some
stages take more hits (1-1, 3-2, 6-3); no run loses a life. 5-4 (the boss)
is unchanged: no edit kept the boss defeat.

## Limits

These are emulator recordings (Geargrafx), not hardware captures. A run
depends on the game's timing: if a later build changed load or lag timing,
`make` would report the divergence instead of writing a video, and the run
would need a new search. The route bot plays like a bot (hesitations, a few
hits), and each video starts at the stage's first gameplay frame.
