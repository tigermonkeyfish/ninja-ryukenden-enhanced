# Load timing exact (load-exact): every stage start and area change on the original's frame

The owner: "stage start should appear like the original. all stages and all
substage/middle phases should have the backgrounds be perfectly aligned. to
the original". Emulator evidence only (Geargrafx `78fc3d7`: the in-process
tracer core of `research/longplay/drift` and the headless emulator for the
gates), no real-hardware data. **Verified** = measured here; **inferred** =
read in code or reasoned, not measured.

Builds: unmodified HuCard (`Ninja Ryukenden (J).pce`, English through the
game's own title switch, hold I + II and tap Select, as `longplay_six.py
--shortcut`), published 1.10, 1.11-dev palette timing 3 (`a0019797…2621`,
branch `palette-exact`, "pt3" below) and this build (`27d1eaa0…dcf0`,
"new").

## The defect

`init_background` (`src/dispatch`) drew the Enhanced backdrop inside the
stage load for 2-2, 5-2 and the castle stages 5-3 / 5-4. A load is one
main-loop update of 12-18 frames of pure CPU; the original's 2-2 load ends
210,045 clocks before its 17th vblank and the draw needs about 288,000, so
2-2 took 17 vblanks instead of 16; 5-4 took 18 instead of 17 (the boss one
frame late, the recorded inputs no longer fitting the original). 5-2 and
5-3 still fitted, 5-3 by 9,009 clocks. The same build also wrote 2-2's
palettes 13 and 14 to the VCE inside the load (`palette_now`), while the
original shows black: a band of the backdrop's lower rows at full colour on
a black screen for three frames (13,258-13,260 on the playthrough) before
the fade-in. Published 1.10 has the same two extra frames.

## What the original does after a load (verified)

`$82D0` sets `$2E63 = $3A`: the next 58 updates run the stage entry
(`$83F3`: `$2E63` non-zero -> `jsr $E0FE`, `dec $2E63`, `jmp [$2033]` =
`$F49A`, the fade). `$82E7 jsr $F436` sets the fade to level 0, step 1 of 8
every 7 updates, and `$F614` copies the RAM palette to its backup `$2686`
(the fade computes `$2286` from the backup). The level table `$F6D8` gives 0
for every component at level 0, so:

| Entry update | `$2E63` at the hook | Work | Clocks left before the vblank (original, the four stages) |
| --- | --- | --- | --- |
| U1 | `$3A` | fade step 1, level 0: all 512 colours black, queued (471k, one vblank inside) | 231,855-235,239 |
| U2 | `$39` | short | 312,546-314,520 |
| U3 | `$38` | short | 335,010-336,708 |
| U4 | `$37` | short | 329,646-336,708 |
| U5-U7 | `$36`-`$34` | short | 332,616-337,716 |
| U8 | `$33` | fade step 2, level 1 (components 7 -> 1): the first non-black colours | 229,539-236,355 |

Rendered frames (fast core, frame buffer): every pixel is black from the
load until the vblank after U8 in the original (VCE: 0 non-zero colours).
So U2-U7, about 2 million clocks, are invisible work time the load does
not have.

## Design

The load draws nothing; the draw runs in U3 and U4.

- `init_background` (unchanged bytes): native `$80AB`, `$2257 = $2258 =
  $FF`, the renderer. The renderers (2-2 `src/stage22`, 5-2 `src/stage52`,
  castle `src/castle`) treat `$2258 >= $FC` like `$FF` in their phase and
  initialize tests (`cmp #$fc` / `bcs`: the same cycles as `cmp #$ff` /
  `beq` for a camera byte) and then decide:
  - `$FF` with `$2257 = $FF`: the stage load. The speed bridge has set the
    entrance anchor (it does so on `$FF`, as before). 2-2 copies its merged
    palettes 13/14 into the RAM palette (the same code and cycles per mode
    as before) but does not write the VCE; the fade's `$F614` copies them to
    the backup and fades them in with everything else. `$2258 = $FD`, return.
  - `$FF` with any other `$2257`: an area change (the native `$80AB` leaves
    the MPR5 bank it saved in `$2257`) or the gameplay fallback: everything
    at once, as before.
  - `$FD` at `$2E63 = $38` (U3), piece 1: the fixed tile upload (2-2's
    `$6000` routine, the castle's `upload_fixed`) and every row's phase
    tiles (`<$30 = 0`: no tile-map entries), the cache written, then
    `$2258 = $FC`.
  - `$FC` at `$2E63 = $37` (U4), piece 2: the tile map (`<$2d = 0`: no tile
    uploads) and the real cache.
  - `$FD`/`$FC` at other `$2E63` values: return; at `$2E63 = 0` (outside an
    entry; not expected) everything at once.
- `deferred_draw` (`$FF42`, every main-loop frame from the Select hook):
  `cmp #$fc` / `bcc` first (a camera byte costs what `cmp #$fe` / `bne` cost
  before), `$FC`/`$FD` -> the renderer (`jmp $FE46`), `$FE` -> `$FF` and the
  area change's draw as before, `$FF` nothing. The renderer runs in U1-U4
  (U1 and U2 return early).
- Piece costs (verified, ORIGINAL; clocks taken from the update's free
  time): 2-2 208k + 81k, 5-2 111k + 113k, 5-3 139k + 89k, 5-4 139k + 111k;
  the castle's `animate_stars` (top of its renderer) also costs about 22k in
  the load and in U1/U2. Smallest margin left in any of these updates:
  126,759 clocks (2-2 U3).

Nothing changes after U4: the tile map, tiles, cache, anchor, palettes and
the RAM are what the draw-at-load build had at the first visible frame
(below). Bytes: bank 0 `$FF42-$FF6A` (dispatch's range; `$FF67-$FF6A` were
free, `$FF` in the original), bank `$56` (main and helpers, guarded), `$73`
and `$7C` (main code, guarded). The 2-2 fixed-upload call keeps the
`initialize:` / `lda` / `tam` / `jsr` form that `scripts/rev5_texture.py`
rewrites with the generated bank and address (now a subroutine).

## RAM and ROM audit

- No new RAM. `$2257-$225A` are the Enhanced renderer cache (the replaced
  native renderer's MPR saves and cursor, reserved since 1.0x; ARCHITECTURE
  RAM contracts); `$2258` gains two marker values, `$FD` and `$FC`
  (impossible camera high bytes like `$FE`), set and consumed only by the
  three renderers and `deferred_draw` between a load and its U4. `$2257 =
  $FF` was already written by `init_background`. `$2E63` (native) is only
  read.
- Lifecycle: `$FD` is written at the load, `$FC` in U3, the camera byte in
  U4; a death reload and a Level Select entry go through the same `$8244`
  load and `$82D0` (verified for a death reload below; Level Select entries
  by `palette_lag.py loadtime`). A renderer reached with `$FD`/`$FC` outside
  an entry draws at once.
- Load or area change: the renderers tell them apart by `$2257` (`$FF` from
  `init_background`; at an area change the native `$80AB` stores the MPR5
  bank there, since it runs only with `$224A` non-zero). `$224A` sampled
  every 50 frames of 2-2, 5-2, 5-3 and 5-4 on the playthrough: 1 throughout,
  0 only inside the 2-2 load before `$80AB` (verified). Inferred limit: an
  area change in these stages with `$224A = 0` and a cached camera low byte
  of `$FF` would be taken for a load and drawn at the next gameplay update
  (the `$2E63 = 0` path), one draw late; not seen.
- ROM: bank 0 `$FF67-$FF6A` (4 bytes, previously free, inside dispatch's
  reserved range `$FF2C-$FF6F`); nothing outside the modules' ranges
  (`project.py` refuses that). The 1-2 phantom-object bytes `$F234-$F236`
  are untouched (queued separately); `$FECF-$FEDF` stays free for that fix.

## Survey (verified)

Recording: `research/longplay/full-load.json` = `research/longplay/full.json` with two idle
hand-over shifts (`scripts/longplay_realign.py build`): -1 at 53,288 (3-3 ->
4-1, as `full-exact.json`) and -1 at 82,966 (5-3 -> 5-4: the idle stretch
after the 5-4 load, now that the load takes the original's 17 vblanks).
Up to frame 82,963 it is `full-exact.json` byte for byte; gameplay inputs
unchanged. The unmodified ROM now replays it from power-on to the ending.

Every stage load and area change of the playthrough (47 events: 22 loads,
25 area changes; `research/longplay/load/survey.py`, `survey_cmp.py`):
vblanks inside the event's update, clocks from its wait call to the next
vblank ("left"), and the smallest "left" over the window of 4 updates
before to 8 after (the fade's first step and the six short updates; for an
area change its transition and the deferred draw). "pattern" compares the
vblank count of every update in the window with the original's. `*` = a
window minimum under 20,000 clocks. pt3 replays `full-exact.json` (its
frames after 5-4 are one later: "+1 fr").

| Event | Frame | Stage | Original: vblanks / left / window min | 1.10: vblanks / left / window min / pattern | pt3: vblanks / left / window min / pattern | new: vblanks / left / window min / pattern |
| --- | --- | --- | --- | --- | --- | --- |
| load | 2846 | 1-2 a0 | 14 / 250,605 / 211,539 | 14 / 250,245 / 211,389 / equal | 14 / 249,507 / 211,389 / equal | 14 / 249,507 / 211,389 / equal |
| load | 10151 | 2-1 a0 | 15 / 256,065 / 212,169 | 15 / 255,825 / 212,025 / equal | 15 / 255,069 / 212,025 / equal | 15 / 255,069 / 212,025 / equal |
| area | 11343 | 2-1 a1 | 2 / 285,858 / 261,255 | 2 / 285,618 / 259,449 / equal | 2 / 285,378 / 259,155 / equal | 2 / 285,276 / 259,155 / equal |
| area | 12421 | 2-1 a2 | 2 / 284,400 / 270,510 | 2 / 284,250 / 268,716 / equal | 2 / 283,908 / 268,500 / equal | 2 / 283,908 / 268,470 / equal |
| area | 12546 | 2-1 a3 | 2 / 289,350 / 276,060 | 2 / 289,068 / 274,176 / equal | 2 / 288,828 / 273,960 / equal | 2 / 288,828 / 273,930 / equal |
| load | 13256 | 2-2 a0 | 16 / 210,045 / 210,045 | 17 / 273,210 / 234,489 / DIFFERENT 00001710000001 | 17 / 269,598 / 234,585 / DIFFERENT 00001710000001 | 16 / 203,199 / 126,759 / equal |
| area | 14030 | 2-2 a1 | 2 / 8,085 / 8,085 | 2 / 7,875 / 7,875* / equal | 2 / 7,635 / 7,635* / equal | 2 / 7,635 / 7,635* / equal |
| area | 14671 | 2-2 a2 | 2 / 23,505 / 23,505 | 2 / 23,295 / 23,295 / equal | 2 / 22,917 / 22,917 / equal | 2 / 22,917 / 22,917 / equal |
| load | 16547 | 2-3 a0 | 14 / 292,920 / 209,895 | 14 / 291,318 / 209,775 / equal | 14 / 290,838 / 209,775 / equal | 14 / 290,838 / 209,775 / equal |
| load | 27793 | 3-1 a0 | 16 / 254,109 / 228,285 | 16 / 253,857 / 228,165 / equal | 16 / 252,975 / 228,165 / equal | 16 / 252,975 / 228,165 / equal |
| load | 31416 | 3-2 a0 | 16 / 112,965 / 112,965 | 16 / 112,599 / 112,599 / equal | 16 / 111,609 / 111,609 / equal | 16 / 111,609 / 111,609 / equal |
| load | 34867 | 3-3 a0 | 14 / 196,125 / 196,125 | 14 / 195,789 / 195,789 / equal | 14 / 195,405 / 195,405 / equal | 14 / 195,405 / 195,405 / equal |
| load | 53302 | 4-1 a0 | 15 / 10,485 / 10,485 | 15 / 10,245 / 10,245* / equal | 15 / 9,369 / 9,369* / equal | 15 / 9,369 / 9,369* / equal |
| area | 55309 | 4-1 a1 | 2 / 122,817 / 122,817 | 2 / 122,655 / 122,655 / equal | 2 / 122,175 / 122,175 / equal | 2 / 122,175 / 122,175 / equal |
| area | 55429 | 4-1 a2 | 2 / 110,655 / 110,655 | 2 / 110,379 / 110,379 / equal | 2 / 110,019 / 110,019 / equal | 2 / 110,019 / 110,019 / equal |
| load | 57134 | 4-2 a0 | 15 / 9,519 / 9,519 | 15 / 9,129 / 9,129* / equal | 15 / 8,529 / 8,529* / equal | 15 / 8,529 / 8,529* / equal |
| load | 60369 | 4-3 a0 | 12 / 44,259 / 44,259 | 12 / 44,037 / 44,037 / equal | 12 / 43,389 / 43,389 / equal | 12 / 43,389 / 43,389 / equal |
| area | 60708 | 4-3 a1 | 2 / 289,590 / 277,428 | 2 / 289,368 / 275,688 / equal | 2 / 289,068 / 275,418 / equal | 2 / 289,068 / 275,418 / equal |
| area | 61795 | 4-3 a2 | 2 / 292,680 / 277,788 | 2 / 292,440 / 275,940 / equal | 2 / 292,200 / 275,820 / equal | 2 / 292,200 / 275,820 / equal |
| area | 63544 | 4-3 a3 | 2 / 297,900 / 266,700 | 2 / 297,660 / 264,900 / equal | 2 / 297,378 / 264,780 / equal | 2 / 297,378 / 264,636 / equal |
| load | 64436 | 4-4 a0 | 14 / 299,628 / 209,895 | 14 / 299,388 / 209,775 / equal | 14 / 298,926 / 209,799 / equal | 14 / 298,926 / 209,775 / equal |
| load | 70025 | 5-1 a0 | 12 / 66,699 / 66,699 | 12 / 66,357 / 66,357 / equal | 12 / 65,739 / 65,739 / equal | 12 / 65,739 / 65,739 / equal |
| load | 73278 | 5-2 a0 | 16 / 246,279 / 229,539 | 16 / 32,859 / 32,859 / equal | 16 / 32,205 / 32,205 / equal | 16 / 241,935 / 216,999 / equal |
| area | 74531 | 5-2 a1 | 3 / 322,110 / 266,268 | 3 / 321,828 / 120,219 / equal | 3 / 321,468 / 120,087 / equal | 3 / 321,468 / 120,087 / equal |
| area | 75459 | 5-2 a2 | 3 / 265,290 / 265,290 | 3 / 265,140 / 111,735 / equal | 3 / 264,768 / 111,735 / equal | 3 / 264,768 / 111,615 / equal |
| area | 76157 | 5-2 a3 | 3 / 316,146 / 275,178 | 3 / 315,906 / 120,339 / equal | 3 / 315,648 / 120,339 / equal | 3 / 315,648 / 120,219 / equal |
| load | 77219 | 5-3 a0 | 15 / 214,635 / 214,635 | 15 / 9,645 / 9,645* / equal | 15 / 9,009 / 9,009* / equal | 15 / 191,697 / 191,697 / equal |
| area | 77972 | 5-3 a1 | 3 / 340,326 / 271,446 | 3 / 340,086 / 128,115 / equal | 3 / 339,966 / 128,115 / equal | 3 / 339,966 / 128,115 / equal |
| area | 78669 | 5-3 a2 | 3 / 288,588 / 273,210 | 3 / 288,468 / 114,345 / equal | 3 / 288,228 / 114,345 / equal | 3 / 288,228 / 114,105 / equal |
| area | 79287 | 5-3 a3 | 3 / 290,190 / 270,600 | 3 / 289,950 / 112,629 / equal | 3 / 289,860 / 112,629 / equal | 3 / 289,860 / 112,509 / equal |
| area | 80296 | 5-3 a4 | 3 / 256,839 / 256,839 | 3 / 256,605 / 95,115 / equal | 3 / 256,425 / 95,115 / equal | 3 / 256,425 / 95,115 / equal |
| area | 80630 | 5-3 a5 | 2 / 18,195 / 18,195 | 2 / 17,955 / 17,955* / equal | 2 / 17,835 / 17,835* / equal | 2 / 17,835 / 17,835* / equal |
| area | 80887 | 5-3 a6 | 3 / 275,538 / 118,989 | 3 / 275,316 / 88,767 / equal | 3 / 275,298 / 88,767 / equal | 3 / 275,298 / 88,767 / equal |
| load | 82897 | 5-4 a0 | 17 / 210,909 / 210,909 | 18 / 330,156 / 227,649 / DIFFERENT 00001810000001 | 18 / 329,580 / 227,649 / DIFFERENT 00001810000001 | 17 / 188,175 / 188,175 / equal |
| load | 86521 | 6-1 a0 | 15 / 126,537 / 126,537 | 15 / 126,417 / 126,417 / equal (+1 fr) | 15 / 125,919 / 125,919 / equal (+1 fr) | 15 / 125,919 / 125,919 / equal |
| load | 88458 | 6-2 a0 | 14 / 187,479 / 187,479 | 14 / 186,099 / 186,099 / equal (+1 fr) | 14 / 185,325 / 185,325 / equal (+1 fr) | 14 / 185,325 / 185,325 / equal |
| area | 90754 | 6-2 a1 | 2 / 280,878 / 267,630 | 2 / 280,638 / 265,770 / equal (+1 fr) | 2 / 280,416 / 265,620 / equal (+1 fr) | 2 / 280,398 / 265,620 / equal |
| area | 91716 | 6-2 a2 | 2 / 306,330 / 252,099 | 2 / 306,090 / 250,245 / equal (+1 fr) | 2 / 306,090 / 250,125 / equal (+1 fr) | 2 / 306,090 / 250,125 / equal |
| area | 91820 | 6-2 a3 | 2 / 294,048 / 284,490 | 2 / 293,928 / 282,768 / equal (+1 fr) | 2 / 293,706 / 282,546 / equal (+1 fr) | 2 / 293,688 / 282,546 / equal |
| area | 92931 | 6-2 a4 | 2 / 285,978 / 275,700 | 2 / 285,756 / 273,810 / equal (+1 fr) | 2 / 285,618 / 273,690 / equal (+1 fr) | 2 / 285,516 / 273,690 / equal |
| load | 93822 | 6-3 a0 | 15 / 236,235 / 229,539 | 15 / 236,049 / 229,419 / equal (+1 fr) | 15 / 235,359 / 229,419 / equal (+1 fr) | 15 / 235,359 / 229,419 / equal |
| area | 94460 | 6-3 a1 | 2 / 15,825 / 15,825 | 2 / 15,705 / 15,705* / equal (+1 fr) | 2 / 15,705 / 15,705* / equal (+1 fr) | 2 / 15,705 / 15,705* / equal |
| area | 94579 | 6-3 a2 | 3 / 278,790 / 275,058 | 3 / 278,550 / 142,539 / equal (+1 fr) | 3 / 278,148 / 142,419 / equal (+1 fr) | 3 / 278,148 / 142,419 / equal |
| area | 96625 | 6-3 a3 | 3 / 322,590 / 239,379 | 3 / 322,350 / 166,869 / equal (+1 fr) | 3 / 322,110 / 166,869 / equal (+1 fr) | 3 / 322,110 / 166,869 / equal |
| load | 102317 | 6-4A a0 | 16 / 56,535 / 56,535 | 16 / 56,319 / 56,319 / equal (+1 fr) | 16 / 55,677 / 55,677 / equal (+1 fr) | 16 / 55,677 / 55,677 / equal |
| load | 106481 | 6-4B a0 | 14 / 226,809 / 210,309 | 14 / 226,689 / 210,045 / equal (+1 fr) | 14 / 225,915 / 210,045 / equal (+1 fr) | 14 / 225,915 / 210,045 / equal |
| load | 111242 | 6-4C a0 | 16 / 295,800 / 201,729 | 16 / 295,650 / 201,555 / equal (+1 fr) | 16 / 294,930 / 201,555 / equal (+1 fr) | 16 / 294,930 / 201,555 / equal |

Results:

- Before (1.10 and pt3 alike): 2-2 load 17 vblanks (original 16),
  5-4 load 18 (original 17); every other event already equal, 5-3's load
  by 9,009 clocks (1.10 9,645) and 5-2's by 32,205 (1.10 32,859).
- New: all 47 events equal to the original in every update of their
  windows, in all six modes (proof A). The four changed loads keep
  188,175-241,935 clocks before their last vblank (original 210,045-246,279)
  and their entry windows at least 126,759.
- Within 20,000 clocks in the original itself (native work, unchanged here,
  1.10-era hooks cost 360-1,120 clocks of it): 4-1 load (original 10,485,
  new 9,369), 4-2 load (9,519 / 8,529), 2-2 area 1 (8,085 / 7,635), 5-3 area 5
  (18,195 / 17,835), 6-3 area 1 (15,825 / 15,705). No load or area change
  is within 20,000 clocks because of this change.

## Proof A: one recording, seven runs, cold power-on to the ending (verified)

In-process (`lx.py`): cold power-on (the six modes with their settings
entry in backup RAM; the unmodified ROM without backup RAM, English by the
title switch), the title left as `longplay_lib` does, then `full-load.json`
as one input list (126,001 frames), no re-syncing. Compared every frame:
the update counter `$2000`, master flags `$2240/$2241`, stage `$2E5F` and
area `$2E60`.

Starts (first gameplay frame of each stage), identical in all seven runs:
1-1 1, 1-2 2,832, 2-1 10,136, 2-2 13,241, 2-3 16,533, 3-1 27,777, 3-2 31,401,
3-3 34,853, 4-1 53,287, 4-2 57,120, 4-3 60,357, 4-4 64,422, 5-1 70,012, 5-2
73,263, 5-3 77,205, 5-4 82,881, 6-1 86,506, 6-2 88,444, 6-3 93,808, 6-4A
102,300, 6-4B 106,466, 6-4C 111,227; the ending cinema (master 1, scene 14)
at 124,184.

| Run | Counter / master / stage / area against the unmodified ROM, 126,001 frames | 63 area changes | 22 starts, ending |
| --- | --- | --- | --- |
| ORIGINAL | identical in every frame | same frames | same frames |
| NES-A | identical in every frame | same frames | same frames |
| NES-B | identical in every frame | same frames | same frames |
| SMS | counter differs in one frame (97,646), the rest identical | same frames | same frames |
| GB DMG | counter differs in one frame (97,646), the rest identical | same frames | same frames |
| APOCALYPSE | counter differs in one frame (97,646), the rest identical | same frames | same frames |

97,646 (palette-exact's 97,647 on `full-exact.json`): the 6-3 -> 6-4
cinema's entry re-uploads all 512 colours in the mapped modes (palette-exact
residual); that update ends after the frame step's sample (counter 56
against 57 at that frame's end, 57 = 57 the next frame). No update is lost,
no event moves. Not part of this change.

Also on `full-exact.json` (without the 5-4 shift), ORIGINAL: this build and
the unmodified ROM are identical in all 126,002 frames; both leave the
recording the same way in 5-4 (Ryu dies, the 5-3 reload at 84,153 is a load
at the original's 15 vblanks; picture below). pt3 and 1.10 follow
`full-exact.json` instead (their 5-4 frame later).

Headless confirmation (`scripts/longplay_six.py run`, one emulator at a
time, the `longplay_check.py` criteria): this build in ORIGINAL and the
unmodified ROM (`--mode unmodified --shortcut`, language byte 1) on
`full-load.json`: **RESULT PASS** for both (22 of 22 stage starts at the
frames above and the ending at frame 126,001, master 1, scene 14). Their
per-frame update counter, master flags, stage and area arrays are identical
to each other in all 126,001 frames, and to the in-process ORIGINAL run.
The other five modes were run in-process only.

Before this change the unmodified ROM could not follow any one recording
past 5-4 with the patched build: the 2-2 frame was absorbed by 2-3, the 5-4
frame was not.

## Proof C: pictures (verified, frame buffer of the fast core)

`research/longplay/load/pic.py`: both builds rendered from their own state
over the load and 60-90 frames after; the first visible frame = the first
of five non-black frames in a row. Screenshots (not committed) in
`/workspace/build/load-exact/shots/`.

Draw-at-load build (pt3) against this build, same mode, each from its own
state before the load; "first visible" in frames of the playthrough:

| Load | Mode | First visible pt3 / new | Before it (non-black frames) pt3 / new | Frames equal from the first visible on | VRAM, VCE at the first visible frame |
| --- | --- | --- | --- | --- | --- |
| 2-2 | ORIGINAL | 13,269 / 13,268 | 13,258-13,260 / none | 58 of 58 (the fade-in and the entry; then pt3 plays one update behind) | equal, equal |
| 5-2 | ORIGINAL | 73,290 / 73,290 | none / none | 61 of 61 | equal, equal |
| 5-3 | ORIGINAL | 77,231 / 77,231 | none / none | 60 of 60 | equal, equal |
| 5-4 | ORIGINAL | 82,910 / 82,909 | none / none | 56 of 56 | equal, equal |
| 5-3 after the 5-4 death | ORIGINAL | 84,181 / 84,180 | the death fade's last frames / the same | 80 of 80 | equal, equal |
| 2-2 | SMS | 13,269 / 13,268 | 13,258-13,260 / none | 58 of 58 | equal, equal |
| 5-2 | SMS | 73,290 / 73,290 | none / none | 61 of 61 | equal, equal |
| 5-3 | SMS | 77,231 / 77,231 | none / none | 60 of 60 | equal, equal |
| 5-4 | SMS | 82,910 / 82,909 | none / none | 53 of 53 | equal, equal |
| 5-2 area 1, 5-3 areas 1 and 5 | ORIGINAL | (visible throughout) | - | 41 of 41 each | equal, equal |

What they show: in both builds the screen is black from the load until the
fade's second step; the first visible frame is the same dim (level 1)
picture with the complete Enhanced backdrop (2-2: mountains, cloud bands and
the lower rows in palettes 13/14; 5-4: the castle sky with the moon and
stars), and every later frame of the fade-in is the same pixel for pixel.
2-2 and 5-4 start one frame earlier, on the original's frame (the
unmodified ROM's first visible 2-2 frame is 13,268, measured with
`visible.py`). The one picture difference: pt3's three frames 13,258-13,260
at the end of the 2-2 load show a band of the backdrop's lower rows (the
palette 13/14 rows) in full colour on an otherwise black screen (4,255
pixels; 18 non-zero VCE colours) before the fade's black step clears it;
the original and this build are black there. The death reload (pt3 made to
die the same way with one more idle frame at the 5-4 hand-over, because a
state of one build does not load into the other) shows the same picture.

## Proof D: gates (verified, emulator)

Headless emulator, one at a time (`/workspace/build/load-exact/gates.sh`,
the palette-exact gate script pointed at this branch; bram baseline =
palette timing 3):

| Gate | Result |
| --- | --- |
| `python3 -m unittest discover -s tests` | 54 OK |
| `scripts/audit_public.py` | pass (469 files) |
| `check_boot.py` | pass: idle frames 1-899 identical to the original |
| `check_menu.py --only options --only reset` | 68 of 68, pass |
| `check_menu.py --only select` | 21 Level Select entries and the language row, pass |
| `check_bram.py --only cycle` | 17 of 17, PASS |
| `palette_lag.py pairs` (36) | all 36: first update +0 clk, sound RAM, counter, Ryu and stage equal, no lag frame, interrupt clocks equal |
| `palette_lag.py loadtime` (22 x 6) | 132 of 132 equal to ORIGINAL (+0) |
| `palette_lag.py e2e` (saved mode at power-on) | all six: first update +0, gameplay fields equal in all 2,903 frames, 96 sound commands; NES-A/B at ORIGINAL's clocks; GB DMG 6, APOCALYPSE 8, SMS 5 commands within -12..+60 clocks (palette-exact's numbers); min margin 146,208 |
| `palette_lag.py fastok` (195-215 colours) | holds (`FASTOK` `$80`/`$81` after a late vblank, never 1) |

palette-exact's own per-vblank and act 3 checks: the vblank handler, `RENT`,
`WAITR` and the worker are untouched (no file of `src/palette` or
`src/bram` changed); the act 3 scene keeps 4-1 at 53,287 in all six modes
(proof A); lost updates are the original's (proof A: every update counter
equal in ORIGINAL and NES, one sample in the mapped modes).

## Verified / inferred / not run

- Verified (emulator): the tables above.
- Inferred: that the entry's fade is black until U8 on real hardware as in
  the emulator (it is the game's own level-0/level-1 table, not a timing
  effect); that the death and Level Select loads not replayed here behave
  as the ones that were (same `$8244` path and `$82D0`).
- Not run: headless playthroughs of NES-A, NES-B, SMS, GB DMG and
  APOCALYPSE (in-process only); real hardware; deaths other than the one 5-4 death reload;
  Continue / Game Over; Japanese and Chinese over the playthrough; the
  `check_menu.py` runs/sweep parts and `--preview`; `check_bram.py`
  matrix/cut/timing/lock.

## Deliverables

In `/workspace/roms/` (not in the repository), from branch `load-exact`:

| File | SHA-256 |
| --- | --- |
| `Ninja Ryukenden - Enhanced v1.11-dev (apocalypse, reset 2, palette timing 3, original load timing).pce` | `27d1eaa0c51b57c9939c6c268f05d066968c90d5769b35ac44e7b52a2c8ddcf0` |
| `ninja-ryukenden-enhanced-v1.11-dev-apocalypse-reset-2-palette-timing-3-original-load-timing.bps` (headered original) | `86384b2a364234f56faff8bf59a838ac8d6f6422b6b5d43878155178678dcaf5` |
| `ninja-ryukenden-enhanced-v1.11-dev-apocalypse-reset-2-palette-timing-3-original-load-timing-headerless.bps` | `376271c2f7107bca3bf5d6f77ee905a543981310355cdbda46b3c41401f99142` |

The build from either original is that ROM; both patches applied with
`scripts/bps.py apply` give it (checksums verified). `project.py apply`
still gives 1.10 (`3d5c05df…bbf6`); `patches/`, `release/` and `VERSION`
(`1.11-dev`, shown in the menu) unchanged.

## Rerunning

```sh
make -C research/longplay/drift watch && make -C research/longplay/load    # libgxw.so, libgxl.so
python3 scripts/longplay_realign.py build research/longplay/full.json ADJ.json full-load.json   # ADJ below
cd research/longplay/load
python3 lx.py TAG ROM MODE full-load.json [--states F ...]      # MODE: original .. sms, none, unmod-en
python3 cmp7.py unmod.npz TAG.npz ; python3 survey_cmp.py unmod.npz new=TAG.npz
python3 pic.py NAME REC FIRST LAST ROM_A STATE_A F ROM_B STATE_B F [--png DIR]
```

`ADJ.json`: `[{"frame": 53288, "frames": -1}, {"frame": 82966, "frames": -1}]`.
