# Combined alignment build (align-combined): adversarial review

Reviewed: `3379c90..48beea8` (source: `src/dispatch`, `src/stage22`,
`src/stage52`, `src/castle`, `src/palette/main.asm`; records `load-exact.md`,
`start-pos.md`, `cinema-lock.md`, `align-combined.md`), build
`2f134a80...8880` ("apocalypse, reset 2, palette timing 3, original load
timing, 2-2 start, cinema lock"; the file in `/workspace/roms/` has that
SHA-256), against the unmodified HuCard and, where a regression had to be
told from an older property, palette timing 3 (`a0019797...2621`, the build
of the previous review). **Emulator evidence only** (Geargrafx `78fc3d7`: a
private copy of the in-process core, and the headless emulator for the
gates); no real-hardware data. **Verified** = measured or reproduced in this
review; **inferred** = read in the source or reasoned, not measured.
Nothing under `src/` was changed.

## Verdict

**Ready for the owner's hardware test as is.** No probe found a stage load,
area change, respawn, Continue or Level Select entry where the three changes
skip, double or misplace a draw, show it on a lit frame, or add a frame:

- Timing (verified): `full-load.json` from power-on, 126,001 frames. In
  ORIGINAL, NES-A and NES-B every one of the 124,958 main-loop updates
  starts on the unmodified ROM's frame and takes its number of vblanks, and
  the update counter, master flags, stage, area, camera, lives, health,
  Ryu's state and `$2E63` are equal in every frame. SMS, GB DMG and
  APOCALYPSE: the same, except that one update is sampled a frame later at
  97,646 (it still ends 322,809 clocks before its vblank; question 5).
- Picture (verified): in ORIGINAL every frame from each of the 15 changed
  loads and area changes through the frame before the camera first moves is
  pixel-identical to the unmodified ROM, the black frames included; the same
  from the respawn or reload on after 15 deaths and 4 Game Over -> Continue.
  The first lit frames of 7 Level Select entries equal the natural loads'
  below the HUD. Japanese and Chinese give the same results.

What the owner should know before he looks at a screen (both are older
than this build and the same in palette timing 3):

- **F1**: in APOCALYPSE, SMS and GB DMG the first visible frame after some
  5-3 area changes shows the foreground black for one frame (the backdrop is
  complete). He will see it in APOCALYPSE at every 5-3 area change.
- **F5**: in the same three modes 2-2's area changes still write two
  palettes to the video chip in the middle of the last black frame.

Two menu gates each fail one opening on this ROM: one next to 2-2's first
area change, the same on palette timing 3 (F3), and one in 4-1 with SMOOTH
PARALLAX OFF, new, a single note written a frame late after the menu (F2).
Neither touches game timing or the picture in play. The record corrections
(F4) and the small undocumented cost (F2) should go into the records before
a merge; nothing has to be fixed before the test.

## Findings, most severe first

### F1 (medium for the three mapped modes, verified; not caused by these changes): the first visible frame after some area changes lacks the foreground's colours

- What: after an area change the game uploads all 512 colours in one
  vblank. In GB DMG, SMS and APOCALYPSE the idle-time worker must convert
  them first; where the update with the Enhanced draw leaves too little
  idle time, the vblank falls back to a partial mapped upload and the rest
  comes a frame later. The picture then shows the backdrop (palettes 0-1)
  and whatever else fitted, and the foreground tiles of the later palettes
  black, for one frame.
- Measured (pictures, pixels below the HUD that change between the first
  visible frame and the next, `full-load.json`):

  | Area change | First visible frame | ORIGINAL, NES-A, NES-B | SMS | GB DMG | APOCALYPSE |
  | --- | --- | --- | --- | --- | --- |
  | 2-2 area 1 | 14,033 | 0 | 0 | 0 | 0 |
  | 2-2 area 2 | 14,673 | 0 | 56 (one sprite) | 56 | 56 |
  | 5-2 areas 1-3 | 74,534, 75,462, 76,161 | 0 | 0 | 0 | 0 |
  | 5-3 area 1 | 77,976 | 0 | 0 | 0 | **17,126** |
  | 5-3 area 2 | 78,672 | 0 | 0 | 0 | **18,429** |
  | 5-3 area 3 | 79,291 | 0 | 0 | 0 | **13,812** |
  | 5-3 area 4 | 80,300 | 0 | **17,562** | **16,955** | **18,662** |
  | 5-3 area 5 | 80,632 | 0 | 0 | 0 | **18,131** |
  | 5-3 area 6 | 80,890 | 0 | **3,079** | **1,950** | **3,183** |

  (47,104 pixels lie below the HUD.) The same at respawns into those areas
  (timer deaths, APOCALYPSE: 5-3 areas 0, 1, 2 and 4 17,149-19,025, area 6
  3,367; SMS and GB DMG, area 4: 17,474 / 16,864). The four stage loads are
  complete in every mode (the fade's steps change the picture on the
  original's frames and on no other frame).
- Not a regression: palette timing 3 gives the same numbers frame for frame
  (APOCALYPSE and SMS re-run here: all six 5-3 values and 2-2 area 2 equal).
  Game timing is not involved (the counters are equal).
- The update that carries the Enhanced draw leaves 95,000-139,000 clocks
  before the vblank in 5-3 (2-2: 41,000-53,000; 5-2: 111,000-120,000). The
  worker needs more than 139,000 for 512 colours in APOCALYPSE and between
  103,000 and 112,000 in SMS and GB DMG (inferred from which 5-3 areas
  fail). Where the partial upload happens to cover every palette on screen
  (2-2, 5-2) nothing shows.
- Other stages' area changes were not checked by picture in the mapped
  modes (no windows captured there).
- Options (owner's decision; nothing here was built): record it as a known
  deviation of the mapped modes; or upload nothing until every colour is
  converted (the picture then appears one frame later than the original's
  in those modes, complete; game timing unchanged); or let the worker
  convert ahead while the transition holds the lock (needs a design: the
  game restores the RAM palette under the lock without queuing it).
- Blocks the hardware test: no.

### F2 (low, verified; new with load-exact): `deferred_draw` costs 6 CPU cycles more per update whenever `$2258` is `$FF` or `$FE`

- The record says a camera high byte costs what it did (`cmp #$fc` / `bcc`
  taken = the old `cmp #$fe` / `bne` taken: 11 cycles). `$FF` and `$FE`
  now fall through two more branches: 17 cycles against 11 (`$FE`: 15
  against 9). `$2258` stays `$FF` for a whole stage wherever no Enhanced
  renderer runs: 1-2, 2-1, 2-3, 3-3, 4-3, 4-4, 5-1, 6-2 and 6-4 A-C (29,335
  of the playthrough's gameplay frames, about 45 percent), and with SMOOTH
  PARALLAX OFF until the native renderer first redraws.
- Effect measured: none on any frame count (every update of those stages
  keeps the unmodified ROM's vblank count in all six modes; the tightest
  gameplay update there, 6-4 C at 112,475, keeps 5,919 clocks against the
  unmodified ROM's 7,635; palette timing 3 had 18 more, inferred).
- One gate shows it: `check_menu.py --only runs --parallax-off` fails one
  of its 140 openings on this ROM and none on palette timing 3 (4-1, stored
  frame 1,664, `$2258` = `$FF`): after the menu is cancelled one music
  channel's next note is written a frame later than in the run without the
  menu (PSG channel 5 frequency 1,164 where the reference has 1,196, at the
  end of the second frame only; its envelope and every other register agree
  from the next frame, so the driver itself is in step). The eight
  neighbouring frames 1,660-1,668 pass on both builds; with SMOOTH PARALLAX
  ON the same frames pass. Inferred: the 18 clocks move the main loop's
  wait against the timer interrupt, which the menu cannot hold.
- Fix: none needed for the test. For the record: state the cost. A
  cycle-neutral dispatch would have to keep the first compare `cmp #$fe` /
  `bne` and tell a pending load draw from an area change behind it (for
  example by `$2257`); only 3 bytes are free in the range (`$FF6D-$FF6F`).
- Blocks the hardware test: no.

### F3 (low, verified; the same in palette timing 3): `check_menu.py --only sweep` at every frame fails one opening next to 2-2's first area change

- Stored 2-2 run, Select at frame 788 (the last gameplay frame before the
  area 0 -> 1 exit; the sweep's default step 1; the previous review ran step
  3 and did not meet it). After the menu is cancelled the first frame of
  the transition differs from the run without the menu: another picture and
  one VCE entry (`$AE`), equal from the next frame on. At the first vblank
  after the return the menu's run stands in the sprite routine (`$F93C`),
  the reference in the transition's palette fill (`$220C`): the update that
  starts the transition has about 2 percent of a frame to spare (7,635
  clocks here, 8,085 in the unmodified ROM) and the two runs end it on
  different sides of the vblank.
- Palette timing 3: the same failure at the same frame with the same two
  addresses and the same VCE entry. Frames 785-787 pass, 789-791 are refused
  or see no Select, on both builds.
- Effect: opening and cancelling the menu on that one frame shows the old
  picture one frame longer (or shorter) before the black. No game state
  differs. Blocks the hardware test: no.

### F4 (record corrections, verified)

- load-exact's fixed-bank bytes are **six, `$FF67-$FF6C`** (`cmp #$fc`,
  `bcc`, `bcc`), not the four `$FF67-$FF6A` its record names twice
  (`$FF42-$FF6A` should read `$FF42-$FF6C`); `draw_done`'s `rts` is at
  `$FF6C`. `$FE00-$FFF5`
  is `$FF` in the original, the range is inside dispatch's `$FF2C-$FF6F`,
  the guard is `init_hook_end > $ff70`; three bytes are left.
- The author's edge case (an area change with `$224A` = 0 and a cached
  camera low byte `$FF`) cannot happen in 2-2, 5-2, 5-3 or 5-4 (question 1).
  The real condition for that path would be a stage whose first area has no
  backdrop and a later one has: then `$2257` is still the load's `$FF`
  (no cache ever ran), not a camera byte. No such stage uses these three
  renderers.
- The records' "first visible" frame for a load is the fade's second lit
  step (their dark run counts frames under 10 percent lit). The first lit
  frames are 13,268 (2-2), 73,290 (5-2; table: 73,298), 77,231 (5-3; table:
  77,239) and 82,909 (5-4; table: 82,917). No consequence: every frame of
  those windows is identical to the unmodified ROM's.
- A frame-end VCE sample is taken while the vblank's upload is under way
  (the emulator's frame ends inside the handler; the block transfer is not
  atomic there). So "VCE at the frame end" comparisons in the records
  (start-pos: 14,032 and 14,672 "palettes 13/14 black until the vblank")
  describe the sample, not the picture: the picture of 14,033 / 14,673 has
  the merged palettes (identical to the unmodified ROM's frame).
- The mapped modes' stripe in 2-2 area 2's last black frame is one line, 24
  (APOCALYPSE) or 32 (SMS, GB DMG) pixels, picture row 153, columns 32-63;
  the records call it two lines (that was the ORIGINAL-mode stripe before
  start-pos). Area 1's black frame has none in any mode.

### F5 (note, verified in the emulator; the hardware part inferred): the mapped modes still write the VCE in the middle of a frame at 2-2's area changes

- start-pos took `palette_now` out of the area-change draw for ORIGINAL and
  NES only. GB DMG, SMS and APOCALYPSE still write 32 colours at once about
  42 lines into the transition's last black frame (and at 1-1's first
  update, unchanged). The emulator shows the dash of F4. A console may also
  show the write itself as a few stray dots on the lines it lands on (a
  known effect of VCE access during the picture; this emulator does not
  draw it). 1.10 did this in every mode, so the build is no worse than what
  the owner has seen.
- A cheap fix for the dash exists (verified in a scratch build only, not
  gated, `src/` untouched): in `draw_all`, for the mapped modes, draw first
  and write the two palettes afterwards (`jsr cache` / `ldx #208` / `ldy
  #32` / `jmp $febe`; 3 bytes more in bank `$56`). On the playthrough to
  14,700 in SMS, GB DMG and APOCALYPSE: the dash is gone (0 pixels at
  14,672), the first visible frames 14,033 and 14,673 and every other window
  frame are the build's pixel for pixel, the game fields and every update's
  vblank count are unchanged, the draw updates keep 41,500-47,500 clocks
  (87-126 fewer than the build). The write still lands inside the picture
  (after the draw, below the rows that use those palettes), so what a
  console shows of the write itself is not settled by it; taking the write
  out altogether needs F1's fix. Not tried there: respawns, Level Select.

### F6 (note, verified): Level Select loads show the old picture's colours for the load's 13-17 frames

- As start-pos recorded: Run in the menu loads the new stage with the VCE
  still lit; the screen goes to one colour two frames after the load ends
  and the two load pieces are drawn in single-colour frames (`$38` and `$37`
  in all seven entries tried, ORIGINAL, SMS, GB DMG and APOCALYPSE). Not
  changed by these branches; no counterpart in the original.

## The eight questions

### 1. load-exact: can the deferred draws be skipped, doubled, misplaced or seen?

No, in every path found (verified where marked).

- Structure (read in the original ROM and the source): every stage load is
  `$8244`, which calls `$82CD` (`init_background`) and then sets `$2E63` =
  `$3A` at `$82D0`; only `$83FF` decrements `$2E63`, once per update, after
  the Select hook has called `deferred_draw`. So the hook sees `$3A`, `$39`,
  `$38`, `$37` in four successive updates whatever the load's length; the
  entry's script (`$F49A`, the fade) does not touch `$2E63`; pause and the
  menu are refused while it counts (`$2201` = 0, `$2E63` non-zero). Run in
  the menu calls `$8244` from inside the hook and the same update runs the
  first entry step; the next three updates are as above.
- Deaths respawn through the area change (`$8627` -> `$8503` -> `$840A`,
  `$2E63` = `$0A`), except a boss-stage death and Continue, which go
  through the master script to `$8244`. Game Over (`$865A`) and the death
  sequence count `$2E63` down from `$40` through `$38` / `$37`, but with a
  camera byte in `$2258` (the markers are consumed before gameplay can run).
- Verified: on the playthrough `$2258` = `$FD` only with `$2E63` `$3A`-`$38`
  and `$FC` only with `$37`, at the four changed loads, in all six modes;
  no marker on any of the 60,096 frames per run where the menu could open;
  in gameplay of the four stages the cache always holds the render camera.
  Branches from saved states, same inputs on both ROMs: timer deaths in
  every area of 2-2 and 5-2, in 5-3 areas 0-4 and 6 and in 5-4 (which
  reloads 5-3), Game Over -> Continue from 2-2, 5-2, 5-3 and 5-4, Level
  Select into 2-2, 5-2, 5-3 and 5-4 (from 2-2) and restarts of each: the
  pieces at `$38` / `$37` at every reload, no fallback draw, the game fields
  equal to the unmodified ROM's in every frame (760 each; one frame-end
  sample of the lives byte and of `$2E63` apart in some, with the counter
  equal), and from the respawn or reload on every picture identical to the
  unmodified ROM's (ORIGINAL). SMS, GB DMG and APOCALYPSE: the same fields
  as ORIGINAL, VRAM equal, the pieces in single-colour frames.
- Stage clear -> next stage: the playthrough's 2-1 -> 2-2, 5-1 -> 5-2,
  5-2 -> 5-3 and 5-3 -> scene -> 5-4.
- Reset during a load: the game has no soft reset; its only jumps to the
  reset are the script's end and END on the Game Over screen. A console
  reset meets the RAM clear (`tii` over `$2000-$3FFF` at `$E025`), which
  zeroes `$2257/$2258/$2E63` (read, not run).
- The fallbacks (verified by writing the bytes during gameplay in 2-2, 5-2,
  5-3 and 5-4, 40 frames each against the same state left alone): `$FD` or
  `$FC` left pending with `$2E63` = 0 is drawn at once in that update; the
  picture, VRAM and the update counter are those of the untouched run in
  every frame. `$FF` with `$2257` = `$FF` becomes `$FD` and is drawn one
  update later; `$FF` alone and `$FE` draw at once. Those three re-anchor
  the backdrop at the camera (as any `$FF` did before), which moves 2-2's
  picture when the camera is away from the area's entry; no update is lost
  and nothing hangs. None of them is reached in play.
- `$2258` / `$2257` collisions: the native code touches them only in
  `$80C2` / `$80D4` (MPR5 and MPR6 saved and restored inside one `$8097` or
  `$80AB` call; byte search of the original for absolute operands). The
  hooks write after the native call returns. With SMOOTH PARALLAX OFF, or in
  a stage without a renderer, `$2258` can hold the saved MPR6 bank (3 in
  gameplay) or `$FF`: neither is a marker, and a marker reaching the lookup
  with the renderer gated off does nothing. `$2257` = `$FF` as "load" cannot
  be met at an area change in these stages: `$224A` is 1 from the load's
  area-0 setup to the next load (verified: 1 on every frame of the four
  stages outside the load itself; `$8090`, the only clear, is called at the
  load only), so `$80AB` always stores the MPR5 bank there first.
- `$FF67-$FF6C`: free in the original (all of `$FE00-$FFF5` is `$FF`); the
  one `20 6A FF` byte pattern in the ROM is inside packed data (bank 7).
  No language path executes there: the unmodified ROM would run `$FF`
  bytes.

### 2. First visible frame

- ORIGINAL (verified): identical to the unmodified ROM at all 15 events,
  the black frames before it included, and after every death and Continue
  tried. NES-A and NES-B (verified): VRAM equal to ORIGINAL's on all 312
  window frames; single-colour frames to the original's last black frame;
  the first lit frame does not change on the next frame (0 pixels) at any
  of the 15 events; no stripe in 2-2's black frames.
- GB DMG, SMS, APOCALYPSE (verified): VRAM equal to ORIGINAL's (two
  mid-update samples apart, before the events); the four loads complete on
  the original's frames; the area changes as in F1's table: the backdrop
  complete everywhere, the foreground a frame late at some 5-3 area
  changes, one sprite a frame late at 2-2 area 2.
- No stale tiles of the previous stage and no missing backdrop tiles were
  seen in any mode.

### 3. start-pos

- Safe (inferred from the native sequence, verified on the playthrough and
  the 2-2 branches): `draw_all` is reached only from `deferred_draw` in the
  transition's second update, and that update's script step (`$8445`)
  queues all 512 colours (`$F394`) and unlocks after the draw; the vblank
  that follows uploads them from the RAM palette. Area changes forward or
  back and every respawn take this path; Continue and the menu's Run take
  the load path (RAM palette only, then the fade). The update keeps 47,000
  (area 1) and 53,000 (area 2) clocks before that vblank in ORIGINAL (the
  unmodified ROM: 327,000).
- ORIGINAL and NES cannot show stale palettes 13/14 on a visible frame on
  any path found: the RAM palette and its backup hold the merged palettes
  from the load on (the load's `$F614` and the transition's `$F718` copy
  them), and nothing loads a colour set at an area change.
- `$2100` bit 4 is the right test there: the menu cannot be open (the hook
  refuses while `$2E63` counts), a cancelled preview puts the old bits back
  before it returns, and Run restarts the stage.
- The mapped modes' black-frame dash: one line of 24-32 pixels (F4), equal
  to palette timing 3's. A three-byte change removes it in a scratch build
  (F5); until that is gated, record it as a known deviation.

### 4. cinema-lock

- The claim holds (read): bit 7 of `$2104` is cleared only by
  `plain_requeue`, `cinema_requeue`, `worker_requeue` (each calls `$F394`)
  and by configure (the menu's `set_palette` queues first); every other
  write keeps it. While bit 7 is set `RENT` is never MN (`rent_install`
  writes MN only with bit 7 clear and `LIVE` 0; the worker's cinema branch
  reaches `rent_mn` only after the re-queue or with bit 7 clear). An armed
  `FASTOK` cannot survive into a locked vblank: the worker does not arm
  while the lock is held and clears it at every entry.
- After the unlock the re-queue comes from the worker's next run or from
  the first vblank with colours queued, also when the worker has not run
  since gameplay (`LIVE` still `$10`: the fallback reaches `vblank_cinema`
  -> `cinema_requeue`).
- A scene that queues nothing after the unlock keeps the mapped colours
  until it first queues a colour (as in palette timing 3 for any scene
  start with an empty queue; palette timing 2 re-queued at the first
  unlocked vblank). Visible only in GB DMG, where black is `$040`, and only
  as that shade of black. Not on the route.
- Verified on the playthrough, the three mapped modes: at 65,923-65,925
  queue 1-2, lock 1, `$2104` `$C0`, MS, `LIVE` 0; at 65,926 lock 0, `$40`,
  MN; from 65,927 the VCE is the RAM palette. Over each of the 11 scenes the
  number of frames with entries not yet uploaded equals ORIGINAL's in SMS
  and APOCALYPSE; GB DMG has 13-22 more at each scene's start (black as
  `$040` until the scene's first upload).
- Forced vblanks: TO BE FILLED.
- Reset in a scene: the RAM clear. The menu cannot open in a scene.

### 5. Timing

- Confirmed with an own probe (hits on `$E06C`, `$E061`, `$FCEC`, `$82CD`,
  `$85B4`, `$8244`): the verdict's numbers. The 21 stage loads and 47
  `$85B4` calls (21 inside loads, 26 area changes) fall in the same update
  in all six modes as in the unmodified ROM. The survey's margins
  reproduce: 2-2 load 203,000 clocks left (original 210,000), its two
  pieces 126,000 and 256,000 (original 335,000, 336,000); 5-2 223,000 /
  216,000; 5-3 197,000 / 247,000; 5-4 196,000 / 222,000; 2-2 area 1's event
  update 7,635 (8,085), 4-1's load 9,369 (10,485), 4-2's 8,529 (9,519).
- 97,646 (SMS, GB DMG, APOCALYPSE): at each of the 11 scene starts the
  vblank after the worker's re-queue uploads all 512 colours (22,000 clocks
  in the handler), so the next update starts 6,500-22,000 clocks later than
  in the unmodified ROM. At ten of them the emulator's frame boundary is
  not between the two start times; at 97,646 it is (the unmodified ROM
  starts that update 3,681 clocks after the vblank, the mapped modes
  25,209), so the counter is sampled one frame later, once. The update
  ends 322,809 clocks before its vblank. Over the 11 starts the delayed
  update keeps at least 194,307 clocks (103,965). It cannot cost a frame on
  this route; a scene start is the scene's own script on any route.

### 6. Interaction

- start-pos with load-exact: the load writes 2-2's palettes into the RAM
  palette before the fade's backup copy and nothing else; the pieces write
  no colour; the area-change draw writes the RAM palette (and, mapped, the
  VCE). No order found in which one undoes the other; the 2-2 load is a
  single colour to the original's last black frame in all six modes.
- cinema-lock with the `RENT` forms: `$3740-$37B4` holds one of two
  contents at every frame end of the mapped runs (MS 63,399 frames, MN
  62,602) and one in ORIGINAL and NES (126,001), besides the reset's stub;
  the changed branch leaves before any `RENT` write.

### 7. Gates run here on the combined ROM

| Gate | Result |
| --- | --- |
| `check_menu.py --only sweep` (step 1) | 1 of 727 openings FAILED: F3 (the same on palette timing 3) |
| `check_menu.py --only runs --preview` | pass, 140 menus |
| `check_menu.py --only runs --parallax-off` | 1 of 140 FAILED: F2 |
| `check_menu.py --only runs` | pass, 140 menus |
| `check_bram.py --only matrix` | PASS, 211 images |
| `check_bram.py --only cut` | PASS |
| `check_bram.py --only timing` | PASS |
| Japanese (saved language 0; the unmodified ROM as it powers on), `full-load.json` to 84,500, ORIGINAL | game fields equal in every frame; every picture of 13,200-13,386 (the 2-2 load, fade and start window), 14,029-14,033 and 14,669-14,673 identical to the unmodified ROM's; the recording leaves the route at 65,933 in both |
| Chinese (saved language 2; the unmodified ROM with `$3227` = 2 written at 1-1's first update), to 84,500, ORIGINAL | the same result as Japanese, frame for frame |
| SMOOTH PARALLAX OFF (saved options `$01`), ORIGINAL, to 84,500, every picture of 2-2 and 5-2 to 5-4 hashed | game fields and all 83,807 updates equal to the unmodified ROM's; the four loads and the frames from each area change to 8 frames past the first visible one identical, except the exit frames 14,028 and 80,884 (the `exit-frames` record's playfield drop) and three frames after 2-2's camera moves; 833 of 14,702 pictures differ in all (2-2 724, 5-2 17, 5-3 92, 5-4 0): single frames where the native backdrop is redrawn a tile over, 19-42 pixels in the three looked at. Palette timing 3 with OFF gives the same picture as this build in every frame of 2-2 (0 of 3,401 differ), so this is the older cost of the wrapper before the native redraw, not these changes |
| Japanese and Chinese through the 5-2 and 5-3 loads and 5-2's area changes (from 73,200, 4,200 frames) and through 5-3's end, the story scene and the 5-4 load (from 81,000, 3,500 frames): the language byte written in a saved state of both ROMs, the recording replayed | game fields equal to the unmodified ROM's in every frame, the loads and area changes on the same frames (5-4's at 82,897 in both languages); APOCALYPSE's fields equal ORIGINAL's |
| Deaths, Continue, Level Select | question 1 |
| cinema-lock forced vblanks | TO BE FILLED |

### 8. Hardware assumptions and residual risks

What these three changes take from the emulator (all inferred for the
console; none was measured on hardware):

- **The entry's black frames.** The two load pieces write tiles and the
  tile map while the picture is displayed, in frames where every colour is
  the same. That the colours are equal is the game's own fade (level 0),
  not a timing effect. In the mapped modes it also needs the worker to
  convert 512 colours in the first entry update's idle time (231,000 clocks
  there against a need of 103,000-139,000 or more, question F1); the
  emulator shows single-colour frames from the update before the first
  piece in every mode, also after a Level Select from a lit screen. VRAM
  writes during the picture are what the gameplay renderers do every
  frame; a late playfield split in those frames is invisible.
- **Vblank counts.** The changed loads end 188,000-242,000 clocks (52-67
  percent of a frame) before their last vblank and the pieces leave at
  least 126,000: the console would have to be a third of a frame slower
  than the emulator to change a count there. The places where "no added
  frame" rests on the emulator's cycle accuracy are older and elsewhere
  (measured here, ORIGINAL, clocks left before the vblank, build /
  unmodified): native updates the hooks make 360-1,116 clocks tighter:
  2-2 area 1's event update 7,635 / 8,085, 4-2's load 8,529 / 9,519, 4-1's
  load 9,369 / 10,485, 6-3 area 1 15,705 / 15,825, 5-3 area 5 17,835 /
  18,195; gameplay updates the Enhanced renderers fill: 3-2 at 32,770
  (7,515 / 59,385) and 32,903 (12,495 / 73,929), 2-2 at 13,929 (12,495 /
  231,885), 13,942 (13,749 / 60,519) and 13,936 (15,945 / 62,595), 5-2 at
  75,689 (19,809 / 93,537); and 2-2's two area-change draws (47,000 and
  53,000 / 327,000). A console 2-4 percent of a frame slower than the
  emulator in one of those updates would add a frame there. F2's 18 clocks
  per update belong to this list.
- **VCE writes in the picture** (F5): mapped modes, 2-2's area changes.
- **Sprites, SATB transfer:** not touched by these changes.
- **Turbo EverDrive Pro:** the saved settings are unchanged (matrix, cut
  and timing gates pass). A save state made on an older build must not be
  loaded (previous review F4: the vblank routine lives in RAM).
- **What a screen cannot show:** one frame more or less. The frame counts
  need a 60 fps capture of the console against the original HuCard on the
  same console.

## Hardware checklist for the owner

Correct = what the emulator shows; anything else is worth a note with the
stage, area, palette mode and what was pressed.

1. **2-2's start** (finish 2-1; ORIGINAL, then APOCALYPSE): black, then
   the fade-in with the mountains, clouds and lower rows there from its
   first dim frame. No coloured band on the black screen before the fade
   (earlier builds showed one for three frames). Nothing appears late.
2. **5-2, 5-3 and 5-4 starts** (5-4 follows the story scene): black, then
   the complete fade-in (5-3 / 5-4: sky, moon and stars from the first dim
   frame).
3. **Level Select** into 2-2, 5-2, 5-3 and 5-4 (Select, STAGE, Run): about a
   quarter of a second of the new stage in the old colours while it loads
   (known, as before), then black, then the complete fade-in.
4. **2-2's two area changes** (and back): the screen is black between the
   areas and the new area is complete on its first frame. ORIGINAL and NES:
   nothing at all in the black (earlier builds showed two lit lines). APOCALYPSE, SMS,
   GB DMG: a short dash at mid-height for one frame at the second change is
   known (F5); note anything more (dots, a line across the screen).
5. **5-3's area changes:** ORIGINAL and NES: complete on the first frame.
   APOCALYPSE (and SMS / GB DMG at two of them): the platforms are black for
   one frame (F1, known, as in the previous build).
6. **Deaths:** let the timer run out in each area of 2-2, in 5-2 and in 5-3,
   and lose to 5-4's boss (the game goes back to 5-3). After the black the
   backdrop is complete at once, in the right place, no stray tiles.
7. **Game Over -> Continue** in 2-2 and in 5-3: as a stage start.
8. **GB DMG, 4-4's boss beaten -> the story scene:** its colours are the
   original's from the first picture (cinema-lock).
9. **SMOOTH PARALLAX OFF**, 2-2 and 5-3: the original's picture.
10. **If a capture is possible:** frames from the last lit frame before 2-2
    and before 5-4 to their first lit frame, against the original HuCard:
    the same count (1.10: one more).
11. Power off or reset during a stage load, then boot: normal. Do not load
    EverDrive save states made with an older build.

## Not checked

- Real hardware; a real-time core; sound beyond the PSG registers the menu
  gates compare.
- Deaths, Continue and Level Select in NES-A and NES-B (ORIGINAL, SMS, GB
  DMG and APOCALYPSE were run); a respawn in 5-3 area 5; deaths with the
  camera moving; a death during a transition.
- Area changes of the other stages in the mapped modes by picture (F1 may
  apply to them; only the four changed stages have picture windows here).
- Japanese and Chinese past the act 5 scene on the recorded route (its text
  runs to another length, so the recording leaves the route at 65,933 in
  both ROMs alike); 5-2, 5-3 and 5-4 were reached with the language byte set
  in a saved state instead.
- `check_bram.py --only lock` and the `--bram-model` variants (they need the
  test-only emulator); `palette_lag.py` pairs / loadtime / e2e / fastok,
  `check_boot.py`, `check_menu.py` select / options / reset (the combined
  record's results taken as read).
- The scratch variant of F5 beyond frame 14,700 and with any gate.

## Probes

Scratch, not committed: `/workspace/build/align-combined-review/`.
`lib/libgxar.so`: load-exact's `shim_load.cpp` with a render flag for the
hit-recording run loop, linked against the same core objects (the other
branches' libraries were not rebuilt). `ar_run.py` (whole recording: fields,
`RENT` hash, hits, VCE against the mode's table, pictures in the changed
stages' windows, saved states), `ar_an.py` / `ar_marg.py` (updates, vblank
counts, margins, markers), `ar_fv.py` / `ar_fv2.py` / `ar_loads.py`
(first visible frames by picture), `ar_branch.py` / `ar_bran.py` /
`ar_bran2.py` (deaths, Continue, Level Select, language branches),
`ar_poke.py` (fallback paths), `sweep_one.py` (one menu opening of
`check_menu.py` with the differing video and PSG state printed), the
cinema-lock author's `cl_fuzz_worker.py` on a copy of the previous review's
core. The source at the branch tip rebuilds to the reviewed ROM
(`project.py build`, same SHA-256).
