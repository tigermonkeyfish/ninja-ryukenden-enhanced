# Start position (start-pos): 2-2's area starts against the unmodified ROM

The owner: "The goal is for all of the background position starts to match
the unmodified rom." The `start-align` survey reported the Enhanced 2-2
backdrop 8 px right of the original at the two 2-2 area starts. Emulator
evidence only (Geargrafx `78fc3d7`: the in-process tracer core of
`research/longplay/drift` / `load`, the headless emulator for the gates), no
real-hardware data. **Verified** = measured here; **inferred** = read in code
or reasoned, not measured.

Builds: unmodified HuCard (`Ninja Ryukenden (J).pce`, English by the title
switch), published 1.10, the `load-exact` build (`27d1eaa0…dcf0`, "old") and
this build (`888a8730…d1f9`, "new").

## Answer

- **The 8 px is not a start position.** On both 2-2 area starts the first
  visible frame (14,033 and 14,673) is pixel-identical to the original in the
  old build already, and so is every earlier frame of the transition except
  one (below). The camera first moves on the very next frame (768 -> 766 at
  14,034; 1,792 -> 1,790 at 14,674): the recorded play scrolls left from the first frame.
  On that frame the **original's** backdrop jumps a whole tile (8 px) left
  while the foreground has not scrolled yet; the Enhanced backdrop stays.
  That jump is the native sawtooth (mechanism below), and from then on the
  two differ by design: the native backdrop follows the screen in an 8 px
  sawtooth, the Enhanced one moves at 1/8 of the camera (smooth parallax).
  `start-align` called 14,034 "the first frame" because its PNGs were named
  after the first *differing* frame after the first visible one.
- **One real start difference was found and fixed:** in 2-2 area 2's last
  black transition frame (14,672) the old build showed two lines of the
  backdrop's lower rows (picture rows 152-153, columns 32-175, 144 pixels)
  where the original is black. Cause: the area-change draw wrote 2-2's merged
  palettes 13/14 to the VCE at once (`palette_now`) in the frame in which the
  native transition still keeps every colour black; the rows the draw had
  already written when the raster passed them lit up. Fix (Original and NES
  modes): the merged palettes go into the RAM palette only; the native
  transition queues all 512 colours (`$F394`) in that same frame and the
  vblank uploads them, merged palettes included, for the original's first
  visible frame. Published 1.10 has the same stripes (14,032: 184 px; 14,672:
  424 px).
- **Now:** all 48 events (the `start-align` list) have every frame from the
  start of the black/transition through the frame before the camera first
  moves pixel-identical to the unmodified ROM, except 6-1's 5-pixel
  horizon-star difference (from 86,589; unchanged, not backdrop position;
  see the survey). 2-2 area 1: 4 black frames + 1 visible frame before the camera
  moves, identical. 2-2 area 2: 3 + 1, identical (was: the black frame
  14,672 differed).
- **What happens once the camera moves** (verified frame by frame on 2-2):
  the original's map column 0 sits at x = 8 floor((C - 8)/8) - BXR, with BXR
  one frame behind the camera: -8, -16, -14, -12, -11, -9, -16, -14, -13 at
  14,033-14,041 (camera 768, 766, 764, 763, 761, 760, 758, 757, 755). The
  Enhanced backdrop: -8, -8, -7, -7, -7, -7, -7, -6, -6. Differences 0, 8,
  7, 5, 4, 2, 9, 8, 7 px (the survey's "8, 7, 5 ... 2"). Matching those
  frames would mean reproducing the native sawtooth, i.e. no smooth
  parallax; not done.
- Mapped palette modes (GB DMG, HELL/APOCALYPSE, SMS) are unchanged: there
  the worker cannot convert all 512 queued colours before that vblank after
  the draw, and without the immediate write the palette 13/14 rows were black
  on the first visible frame (measured with a first version of this change),
  so they keep `palette_now` and with it the two-line stripe in 2-2 area 2's
  last black frame (old build and 1.10 alike). There is no unmodified
  reference picture for these modes.

## Mechanism (verified: code, RAM trace and pictures)

- Native: any camera move sets `$224B` (bank 0 `$E341`); the native render
  `$8097` -> `$80DF` computes the BAT address of map column 0 from the
  current camera C: column floor((C - 8)/8) (0 for C < 8), stored in
  `$2259/$225A`, and redraws when it changes. The playfield's BXR comes from
  `$2E4B/$2E4C` (render-time camera), one frame behind C. Traced on the
  unmodified ROM at 14,029-14,041 and 14,669-14,681: the model gives the
  measured screen position of map column 0 on every frame (e.g. 14,034: BAT
  column 30, BXR 256 -> x = -16; the foreground does not move on that frame,
  the backdrop moves 8 px left). Nothing depends on travel history beyond
  the camera and that one-frame lag.
- Enhanced 2-2: texture position at the left edge = D + 8 x opening, D =
  floor(C/8) + anchor, anchor = floor(Ce/2) - floor(Ce/8) at the entry camera
  Ce, opening = (1 - Ce/16) mod 50: native column 1 (x = -8) at any entry
  camera that is a multiple of 16, the original's position at rest. The
  renderer updates when `$2E4B` changes, so it does not move on the frame on
  which the native one jumps.
- The stripe: area change `$85B4` at 14,671 (`$80AB`, `$2258 = $FE`); the
  deferred draw in the next main-loop frame 14,672 runs from line 2.6 to
  205.6 after the frame start, `palette_now` at line 42.3; the native
  queues the full 512-colour upload (`$2260` count 1, 1,024 bytes from colour
  0, `$F39D-$F3AD`) in that same frame (watched RAM writes). VCE at the end
  of 14,671: 6 non-black BG colours in both ROMs; the old build's palette 13/14
  entries non-black from line 42 of 14,672. The split's BYR write is at line
  64.05 in every frame of both ROMs (not a split delay).

## The change

`src/stage22/main.asm`, `draw_all` (the area-change draw; also the
respawn's, which re-enters through the area change):

```
 jsr initialize
 jsr palette_ram
 lda $2100
 and #$10             ; bit 4: GB DMG, HELL, SMS (and the unassigned $30)
 beq drawn
 ldx #208
 ldy #32
 jsr $febe            ; palette_now: mapped modes only
drawn:
 jmp cache
```

Before: `palette_now` in every mode. Stage loads were not affected (since
`load-exact` they write the RAM palette only). No RAM, no new ROM: 7 bytes
more inside the module's existing claim (bank `$56` `$4C00-$4FFF`,
`helpers_end` guard), code after `draw_all` moves by 7 bytes (no
page-crossing penalties on the HuC6280).

## Cost (verified, tracer core)

`drawcost.py`: the deferred-draw frame, cycles outside the vblank wait.

| Frame | Mode | Old | New | `palette_now` |
| --- | --- | --- | --- | --- |
| 14,032 (2-2 a1) | ORIGINAL | 315,576 | 311,460 | 4,212 -> 0 |
| 14,672 (2-2 a2) | ORIGINAL | 309,795 | 305,721 | 4,212 -> 0 |
| 14,032 / 14,672 | SMS | 358,830 / 358,803 | 358,830 / 358,803 | 5,850 (kept) |

ORIGINAL: about 4,100 cycles less in the two area-change frames (the main
loop reaches its wait 3 lines earlier); SMS: the same totals (the frame is
saturated by the worker either way; the added test is 9 cycles before the
call; 11 in ORIGINAL/NES, taken). The unmodified ROM waits from line 17 in these frames. No other
path changed: gameplay updates in 2-2 do not run `draw_all`, and the
picture/VCE/RAM digests below are identical outside the two draw frames.

## Pictures (verified)

`pichash.py`, frames 13,230-16,540 (all of 2-2: the load, the three areas
scrolled through to the end, the boss transition), old and new, each mode:
RAM sample equal to the unmodified ROM in every frame (all six modes).

| Mode | Picture old != new | VCE (frame end) old != new |
| --- | --- | --- |
| ORIGINAL, NES-A, NES-B | 14,672 only | 14,032, 14,672 (palettes 13/14 black until the vblank, as in the original) |
| SMS, GB DMG, APOCALYPSE | none | none |

So the scroll through each 2-2 area (seams, tiles, tearing) is unchanged
frame for frame from the old build. ORIGINAL against the unmodified ROM:
3,127 differing frames of 3,311 (old 3,128): the moving backdrop by design.

## Survey: all 48 events, start window defined by the camera (verified)

`capture.py` (both ROMs, frames EV-4..EV+110) and `startwin.py`. Dark run =
from EV-1 the frames whose playfield (rows 60-229) has under 10 percent
non-black pixels (a load's black and fade start, an area change's transition;
HUD and sprites may show). First visible = the frame after it. Start window =
first visible .. the frame before the camera (`$220F`) first changes (to the
end of the capture if it does not). Game RAM equal on every captured frame.
Old against new: every captured frame identical except 14,672 (5,516 frames).

| # | Event | Frame | Camera | Dark run (frames) identical | First visible | Camera first moves | Start window frames | Start window identical | First differing frame from first visible | Previous build |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1-1 start | 1 | 0 | 0: yes | 1 | 67 | 66 | yes | 68 | same |
| 2 | 1-2 a0 | 2846 | 0 | 28: yes | 2873 | not in window | 84 | yes | - | same |
| 3 | 2-1 a0 | 10151 | 0 | 28: yes | 10178 | not in window | 84 | yes | - | same |
| 4 | 2-1 a1 | 11343 | 0 | 3: yes | 11345 | 11366 | 21 | yes | - | same |
| 5 | 2-1 a2 | 12421 | 0 | 4: yes | 12424 | not in window | 108 | yes | - | same |
| 6 | 2-1 a3 | 12546 | 768 | 3: yes | 12548 | 12579 | 31 | yes | - | same |
| 7 | 2-2 a0 | 13256 | 768 | 13: yes | 13268 | not in window | 99 | yes | - | same |
| 8 | 2-2 a1 | 14030 | 768 | 4: yes | 14033 | 14034 | 1 | yes | 14034 | same |
| 9 | 2-2 a2 | 14671 | 1792 | 3: yes | 14673 | 14674 | 1 | yes | 14674 | dark NO, window yes |
| 10 | 2-3 a0 | 16547 | 0 | 36: yes | 16582 | not in window | 76 | yes | - | same |
| 11 | 3-1 a0 | 27793 | 0 | 13: yes | 27805 | not in window | 99 | yes | - | same |
| 12 | 3-2 a0 | 31416 | 0 | 13: yes | 31428 | not in window | 99 | yes | - | same |
| 13 | 3-3 a0 | 34867 | 0 | 28: yes | 34894 | not in window | 84 | yes | - | same |
| 14 | 4-1 a0 | 53302 | 0 | 36: yes | 53337 | not in window | 76 | yes | - | same |
| 15 | 4-1 a1 | 55309 | 0 | 4: yes | 55312 | not in window | 108 | yes | - | same |
| 16 | 4-1 a2 | 55429 | 0 | 3: yes | 55431 | not in window | 109 | yes | - | same |
| 17 | 4-2 a0 | 57134 | 0 | 29: yes | 57162 | not in window | 83 | yes | - | same |
| 18 | 4-3 a0 | 60369 | 0 | 36: yes | 60404 | not in window | 76 | yes | - | same |
| 19 | 4-3 a1 | 60708 | 0 | 4: yes | 60711 | 60792 | 81 | yes | - | same |
| 20 | 4-3 a2 | 61795 | 0 | 4: yes | 61798 | 61804 | 6 | yes | - | same |
| 21 | 4-3 a3 | 63544 | 0 | 4: yes | 63547 | 63554 | 7 | yes | - | same |
| 22 | 4-4 a0 | 64436 | 0 | 36: yes | 64471 | not in window | 76 | yes | - | same |
| 23 | 5-1 a0 | 70025 | 0 | 28: yes | 70052 | not in window | 84 | yes | - | same |
| 24 | 5-2 a0 | 73278 | 512 | 21: yes | 73298 | not in window | 91 | yes | - | same |
| 25 | 5-2 a1 | 74531 | 0 | 4: yes | 74534 | not in window | 108 | yes | - | same |
| 26 | 5-2 a2 | 75459 | 512 | 4: yes | 75462 | 75511 | 49 | yes | 75512 | same |
| 27 | 5-2 a3 | 76157 | 0 | 5: yes | 76161 | not in window | 107 | yes | - | same |
| 28 | 5-3 a0 | 77219 | 512 | 21: yes | 77239 | not in window | 91 | yes | - | same |
| 29 | 5-3 a1 | 77972 | 0 | 5: yes | 77976 | 78069 | 93 | yes | 78070 | same |
| 30 | 5-3 a2 | 78669 | 512 | 4: yes | 78672 | 78773 | 101 | yes | 78774 | same |
| 31 | 5-3 a3 | 79287 | 0 | 5: yes | 79291 | not in window | 107 | yes | - | same |
| 32 | 5-3 a4 | 80296 | 256 | 5: yes | 80300 | 80355 | 55 | yes | 80355 | same |
| 33 | 5-3 a5 | 80630 | 0 | 3: yes | 80632 | not in window | 109 | yes | - | same |
| 34 | 5-3 a6 | 80887 | 0 | 4: yes | 80890 | 80939 | 49 | yes | 80940 | same |
| 35 | 5-4 a0 | 82897 | 0 | 21: yes | 82917 | not in window | 91 | yes | - | same |
| 36 | 6-1 a0 | 86521 | 2048 | 21: yes | 86541 | 86628 | 87 | NO | 86589 | same |
| 37 | 6-2 a0 | 88458 | 1280 | 36: yes | 88493 | not in window | 76 | yes | - | same |
| 38 | 6-2 a1 | 90754 | 768 | 3: yes | 90756 | 90757 | 1 | yes | - | same |
| 39 | 6-2 a2 | 91716 | 0 | 4: yes | 91719 | 91818 | 99 | yes | - | same |
| 40 | 6-2 a3 | 91820 | 0 | 3: yes | 91822 | 91924 | 102 | yes | - | same |
| 41 | 6-2 a4 | 92931 | 0 | 3: yes | 92933 | 92940 | 7 | yes | - | same |
| 42 | 6-3 a0 | 93822 | 0 | 21: yes | 93842 | not in window | 91 | yes | - | same |
| 43 | 6-3 a1 | 94460 | 0 | 4: yes | 94463 | not in window | 108 | yes | - | same |
| 44 | 6-3 a2 | 94579 | 1792 | 4: yes | 94582 | 94601 | 19 | yes | 94601 | same |
| 45 | 6-3 a3 | 96625 | 0 | 5: yes | 96629 | not in window | 107 | yes | - | same |
| 46 | 6-4A a0 | 102317 | 0 | 36: yes | 102352 | not in window | 76 | yes | - | same |
| 47 | 6-4B a0 | 106481 | 0 | 36: yes | 106516 | not in window | 76 | yes | - | same |
| 48 | 6-4C a0 | 111242 | 0 | 21: yes | 111262 | not in window | 91 | yes | - | same |

The 6-1 difference (5 pixels at rows 168-170, columns 210-212, from 86,589,
horizon rows 14-15) is consistent with the documented omitted horizon star
(HANDOFF: "6-1 omits one star of horizon rows 14-15"); not backdrop
position, unchanged. Frames before the dark run (the old area's last frames)
still differ at 12 area changes, as in `start-align`: the moving backdrop and
one-frame vertical offsets at the old area's end; not a start, unchanged.

## Other entries (verified unless marked)

`respawn.py` / `respawn_cmp.py`: branches from the recording, the same
inputs on both ROMs; no input after the respawn, so the camera does not move
in these windows.

| Entry | Camera | Dark run | First visible .. end of capture |
| --- | --- | --- | --- |
| Timer death in 2-2 area 0 (from 13,600) | 768 | identical | 289 frames identical |
| Timer death in area 1 (from 14,300) | 768 | identical | 554 frames identical |
| Timer death in area 2 (from 15,000) | 1,792 | identical | 541 frames identical |
| Game over, CONTINUE (from 14,300) | 768 (area 0) | identical | 221 frames identical |
| Level Select 2-2 from area 1 and from area 2 (build only) | 768 | - | first visible and the next 58 frames identical below the HUD to the original's natural 2-2 load; then only Ryu's sprite differs (the recording moves him) |

- Respawns re-enter through the area change (`$2E63` = 10) at the area's
  entry camera, so they take the same path as the recorded area starts. The
  timer-death branch at 13,600 shows the lives byte one frame-end sample
  later in both builds (counter equal, next frame equal): pre-existing,
  not a lost frame.
- Level Select (no counterpart in the original): old and new pictures equal
  in every captured frame; its load shows the new stage's foreground with a
  black backdrop band at full brightness for 14 frames before the fade-out
  in old, new and palette timing 3 alike (not changed here).
- Inferred, not run: other entry cameras. The opening offsets assume the
  entry cameras of `ROUND_CAMERAS` (768, 768, 1,792 for 2-2's rounds 0-2);
  an entry at another camera that is a multiple of 16 lands on native column
  1 as well (the formula), one that is not would not (none is known). Not
  tested: respawns with the camera moving, Japanese/Chinese, smooth parallax
  OFF (the native path, untouched).

## Timing gates (verified)

Gate list of `load-exact`, this build, one emulator at a time
(`/workspace/build/start-pos/gates.sh`, the load-exact script pointed at this
branch; bram baseline = palette timing 3).

| Gate | Result |
| --- | --- |
| Pristine build | unchanged source rebuilt to `27d1eaa0…dcf0` (the load-exact build) before the change |
| `python3 -m unittest discover -s tests` | 54 OK |
| `scripts/audit_public.py` | pass |
| `check_boot.py` | pass: idle frames 1-899 identical to the original |
| `check_menu.py --only options --only reset` | 68 of 68 ok, menu check passed |
| `check_menu.py --only select` | 21 Level Select entries ok, language row ENGLISH, passed |
| `check_bram.py --only cycle` | 17 of 17, PASS |
| `palette_lag.py pairs` (36) | all 36: first update +0 clk, sound RAM, counter, Ryu and stage equal, no lag frame, interrupt clocks equal |
| `palette_lag.py loadtime` (22 x 6) | 132 of 132 equal to ORIGINAL (+0) |
| `palette_lag.py e2e` | all six: first update +0, no differing frame in 2,903, 96 sound commands; NES-A/B at ORIGINAL's clocks; GB DMG 6, APOCALYPSE 8, SMS 5 commands within -202..+60 clocks (as load-exact) |
| `palette_lag.py fastok` (195-215 colours) | holds (`FASTOK` never 1 after a late vblank) |
| `full-load.json`, in-process, six modes against the unmodified ROM (`lx.py`, `cmp7.py`) | ORIGINAL, NES-A, NES-B: counter, master flags, stage and area identical in all 126,001 frames; SMS, GB DMG, APOCALYPSE: counter differs in one frame (97,646, load-exact's residual), the rest identical. All six: the 22 stage starts, the 63 area changes and the ending (124,184) on the unmodified ROM's frames |
| `full-load.json`, headless ORIGINAL (`longplay_six.py run`) | RESULT PASS (22 starts, ending at 126,001); its counter/master/stage/area arrays identical to load-exact's headless unmodified run |

The two area-change frames are the only frames whose work changed; no load
or area change takes another vblank (loadtime, the replays).

## Not covered

- Real hardware; a real-time core.
- The mapped modes' stripe in 2-2 area 2's black frame (kept, see above).
- The frames after the camera moves (by design, see Answer).
- Respawns or Level Select entries with the camera moving; other recordings.

## Deliverables

In `/workspace/roms/` (not in the repository), from branch `start-pos`:

| File | SHA-256 |
| --- | --- |
| `Ninja Ryukenden - Enhanced v1.11-dev (apocalypse, reset 2, palette timing 3, original load timing, 2-2 start).pce` | `888a87309656def55ca2770adf585b98954bf392106115a50a956c1d29b1d9f1` |
| `ninja-ryukenden-enhanced-v1.11-dev-apocalypse-reset-2-palette-timing-3-original-load-timing-2-2-start.bps` (headered original) | `78f7e3c79e243da35d023d96571d53de74b0ce9cbc378b1612449a3f8837ef4e` |
| `ninja-ryukenden-enhanced-v1.11-dev-apocalypse-reset-2-palette-timing-3-original-load-timing-2-2-start-headerless.bps` | `1460990befb72812b1ceb834f77fe6de470de018c5337b419b9d6bb290892767` |

The build from either original is that ROM; both patches applied with
`scripts/bps.py apply` give it (checksums verified). `patches/`, `release/`
and `VERSION` (`1.11-dev`, shown in the menu) unchanged.

## Rerunning

```sh
export LD_LIBRARY_PATH=/workspace/build/toolchain/sdl3/lib
cd research/longplay/startalign
python3 capture.py UNMOD unmod-en cap-unmod ; python3 capture.py BUILD original cap-new
python3 startwin.py cap-unmod cap-old startwin-old.json ; python3 startwin.py cap-unmod cap-new startwin-new.json
python3 wintable.py startwin-old.json startwin-new.json
python3 pichash.py ROM MODE 13230 16540 OUT.npz          # per mode, old and new
python3 respawn.py ROM MODE OUT 13600:death 14300:death 15000:death 14300:over [14300:select]
python3 respawn_cmp.py OUT_UNMOD OUT_BUILD
python3 splittrace.py ROM MODE 14666 14674 ; python3 drawcost.py ROM MODE 14032 14672
```
