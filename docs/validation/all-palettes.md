# All palettes in one build (1.11-dev): validation record

Emulator evidence only (headless Geargrafx `78fc3d7` with the headless-fast
patch, binary SHA-256 `2de50e51…`, [EMULATOR.md](../pc-engine/EMULATOR.md));
no real hardware, audio registers compared (PSG state), audio itself not
listened to. Design: [architecture, palette modes](../ARCHITECTURE.md#palette-modes),
[NES palette mode](../ARCHITECTURE.md#nes-palette-mode),
[menu display](../ARCHITECTURE.md#menu-display).

The PALETTE row offers every mode: ORIGINAL, NES-A, NES-B, GB DMG, HELL,
SMS (`$2100` bits 3-5 `$00`, `$08`, `$28`, `$10`, `$18`, `$38` with bit 7:
`$B8`).

| Build | SHA-256 | Source |
| --- | --- | --- |
| `sms-palette` (reference for Original, GB DMG, HELL, SMS) | `444ff70bee588d24253e16f9b06a38bc472cafc55b2c0246ff8afd1867f987ef` | `f9fdacb`, rebuilt here: the bytes of its record |
| `nes-palette-2` (reference for NES-A) | `052419169bfc43adf62d69ff649f8db583cbec023412c1351b9fa37fba923aa2` | `c3e0d53`, rebuilt: the bytes of its record |
| `popup-menu` (their common base) | `43db8b4c9c3f662c6edd4d22dd03d62385b0e84748ff8d898cb936a12aa6ecb5` | `46bbbe3` |
| Early delivery (merge and NES-B, before the menu's sound hold) | `355628676d05a9bceffdb935c0c48bae8588deb7297927875b0bbba59f7240f0` | `169f0c5` |
| Candidate | `8682d4401c92c00df5c4c1027a733e3aa6541785aeaca7c3df9a46f51665b723` | branch `all-palettes` (the same bytes from the headered and the headerless original) |

Work folder (private): `build/all-palettes/` with `seed.state` (the
`sms-palette` record's start state, a cold boot of the original saved at the
1-1 main-loop hook) and `original.pce`. Every replay is a fresh session from
it ($2100/$2101 written to the mode). Probes:
[`research/tools/all-palettes/`](../../research/tools/all-palettes) and,
unchanged, the SMS, NES and GB palette probes named below.

## 1. The merge

`nes-palette-2` merged into `sms-palette` (`9760ce2`). Conflicts and how
they were resolved:

- `src/palette/main.asm`: `sms-palette`'s code (the NES branch changed only
  comments); families 00 and 01 upload natively whatever bit 5 says.
- `src/options/menu.txt`: `@ $38 $00=ORIGINAL $08=NES-A $28=NES-B $10=GB_DMG $18=HELL $38=SMS`
  with `sms-palette`'s comment block.
- `src/options/main.asm`: `PALETTE_BITS = $38`, `OPTION_BITS = $3F`; the
  NES preview test compares the family (`and #$18 / cmp #$08`), so NES-A and
  NES-B both keep the mode the menu opened in (`OPENED_OPTIONS`, `$2100` as
  pushed at open, still at `$2103,X`: `menu_open`'s pushes did not change),
  masked with `$38`, and falls into `set_palette` (bit 7 with SMS, full
  re-queue on a change). Run now also sets the draft's palette bits through
  `set_palette` first: an NES value was never previewed, so without it Run
  from SMS to NES-A would have left bit 7 set (`$88`).
- `scripts/check_menu.py`: both options parts merged into one with all six
  values (below); `tests/test_tools.py`: the PALETTE line and the six texts.
- Docs: both sides kept and rewritten (this record, architecture, handoff,
  options guide, lessons).
- `src/modules.json`, `scripts/asset_transforms.py`, stage11, stage22,
  `stage61-upload`: merged without conflict.

ROM: the two branches change no byte in common outside the menu (bank `$46`
`$4400-$4AFF`): against `popup-menu`, `sms-palette` changes 6,416 bytes,
`nes-palette-2` 7,740, 1,043 of them both, all in `$8C429-$8CA10`; outside
the menu the merged build equals their union byte for byte. The build's
range check also rejects overlapping claims.

## 2. NES-B

`scripts/nes_palette.py` takes the re-light generator change as designed in
`build/nes-relight/` (`relight_targets`, `role_spans`, `relit`; the
`lift` / `lift_black` role keys accepted; no data file changed: the scratch
`lift_black` on 4-1's sky is not applied). The build writes NES-B's
`nes-b-tables.inc`, `nes-b-sets.inc`, `nes-b-anim.inc` and the `_b` merged
palettes of 1-1 and 2-2 from `relit(data)`; NES-A's generated files are
unchanged (compared with `nes-palette-2`'s generator: identical text).

| | NES-A | NES-B |
| --- | --- | --- |
| Sets differing from NES-A | | 18 of 18, and the 3-2 variant |
| Animation lists differing | | 38 of 55 (records of its own; 17 lists point at NES-A's) |
| Sprites, Ryu, HUD | | NES-A's (the build fails otherwise) |
| Merged colours in the set rows | 596 | 636 |
| Animation lists with fewer distinct colours | | 8 of 55; 3-1's three lists (entries 28, 30, 31) become one colour each: **3-1's animated lights do not animate in NES-B** |
| Colours outside the 47 NES colours | 0 | 0 |

Space, 4,529 bytes: bank `$3B` `$4200-$4F7D` (3,454: sets and variant, the
bank's `$FF` tail), bank 3 `$D7FE-$DB03` (774: NES-B's table; nes-palette's
claim grows from `$D400-$D9FF` to `$D400-$DBFF`), bank `$45` `$42D3-$4369`
(151: NES-B set addresses, the lookup), stage11 56 and stage22 94 (palettes
and out-of-line copy loops). Left free: bank 3 `$DB04-$DBFF` (252), bank
`$45` `$436A-$43FF` (150), bank `$3B` `$4F7E-$4FFF` (130). Not used:
bank `$46` `$4100-$42FF`, `$4B00-$4FFF` (save code), `$5B00-$5FFF`.
Guards: bank 3 before `$DC00`, bank `$3B` before `$5000`, bank `$45`
before `$4400`, stage11 / stage22 as before.

Why the new ROM is free: bank `$3B`'s data end at `$761CE` in the original;
bank 3 `$DA00-$DBFF` was `$FF` and unclaimed. Read/execute watches over
`$761CF-$76FFF` and `$7A00-$7BFF` on the `sms-palette` build
(`sms-palette/freewatch.py`, `nes-palette/freestages.py`): 0 stops over a
cold boot to 600 updates of 1-1 (683 frames), the 11 stored runs (35,084
frames) and all 22 Level Select entries (600 frames each holding right,
area exit moved every 150: 13,200 frames). Positive control: the same
watch on the NES-B build in NES-B stops in 1-1's load at `$CEAE` (the
animation records' copy, bank 3 `$DAxx`).

## 3. HELL parameters

`scripts/palette_tables.py` takes the retuning's optional "steel" family
(`build/hell-tune/gen/palette_tables.diff`, `b9d25a0`). `src/palette/hell.json`
is unchanged: the HELL table is the shipped one (SHA-256 prefix of the 512
words `1388df9d…`, the same as `sms-palette`'s generator; the unit test pins
it), GB DMG's and SMS's too. With `hell-D-ship.json` / `hell-D2-ship.json`
the merged generator gives exactly the tuning generator's tables (each 16
words differ from the shipped table, 240 mapped entries), so the owner's
choice is a swap of `src/palette/hell.json`.

## 4. The popup-menu sweep failures

`check_menu.py`'s sweep failed 8 of 727 openings on `popup-menu`,
`hell-palette` and `sms-palette` (2-2 at 784-788 and 3943, 5-3 at 5290 and
6189): video state differing at one or two frame ends after the menu.

Diagnosis (`sweepdiag.py`, `committed.py`, on the `sms-palette` build):

- What differs: at the end of the frames of an area change (2-2's at 789:
  frames 3 and 4 after an opening at 786), 2 BAT words (`$035E-$035F`, then
  `$05FE-$05FF`); the picture is the same in those frames, the game's RAM is
  the same at every update boundary. The main loop stands at another
  instruction at the frame end (`$4430` against `$505D`): the area change
  redraws the BAT from the main loop across several frames, so a frame end
  catches the redraw one cell further or not.
- Why: the sound driver runs in the VDC interrupt (`$FD16` → `$EA5B`, bank
  `$38`; the timer interrupt `$FCD3` only acknowledges) and played on while
  the menu was open. Afterwards its state was some 50 bytes different
  (notes further on), its work in each vblank took other time, and the main
  loop was a few cycles elsewhere at every frame end. That is invisible
  while the game writes VRAM only in vblank, and shows while a redraw spans
  frames. With the run without the menu given the driver's state as the
  menu left it (`--same-music`), the 786 opening is exact.
- Why "just before an area change": only because the sweep compares 10
  frames after each opening. Openings 6, 11, 16, 19 and 29 frames before
  the 2-2 change compared for 24-40 frames show the same 2-word difference
  at the change (770, 775, 778, 781, 783; 760 by chance not). And the
  change is not decided at 784-787: from those frames, holding Left avoids
  it (`committed.py`: with Left held no change; without input or with the
  run's input at 789); from 788 it happens whatever the input. Refusing
  the menu in the last frames before a change would only have moved the
  difference out of the check's window, so it was not done.

Fix (`14726b7`): **the sound holds while the popup is open.** The menu
saves the driver's play flags `$387E` and clears bits 6-7 (music and effect
channels); the driver's tick then advances nothing and only writes volume 0
to each channel; after the menu's last vblank the flags go back. The driver
resumes from exactly its state at the Select hook (only zero page `$8B`,
the tick's own scratch, which every tick clears before use). This is a
**behaviour change from 1.10 and the earlier popup builds**: music and
effects pause while the window is open and continue where they stopped, as
in the game's own pause. Two alternatives were tried and dropped: the
driver's own pause commands (`$83`/`$86` through `$EA84`, the native pause's)
change its state (53 bytes at the return), and the differences stayed.

`check_menu.py` follows the fix: the menu now returns before the emulator's
frame boundary (its last vblank is shorter), so both runs are compared from
the next VDC interrupt; the PSG registers (enable, amplitude, frequency,
balance, noise; main amplitude, LFO; not the emulator's waveform position)
are compared at every frame end from the second (the held channels come
back with the driver's second tick, so frame 0 differs: about one frame,
17 ms, of sound later than without the menu); the state at that first
interrupt is diagnostic only (the run without the menu may still be in the
hook's update there).

One difference remains and is not a menu fault: **the timer interrupt's
phase.** The timer (reload `$74`, a period 143 CPU cycles longer than a
frame) runs on through the menu, and its interrupt only acknowledges; after
the menu it lands at another point of the frame, which the menu cannot
restore (its prescaler is not readable). It moves the main loop by its own
length. In the full sweep this showed once: 1-1, opening at 2829, one VRAM
word (`$0340`) at the end of frame 1 of the 1-1 → 1-2 load (main loop at
`$E5FD` against `$E601`), the picture the same, the next frame end the
same; the interrupt trace shows the VDC interrupts at the same times (within
a fraction of a line) and the timer's 9 lines apart (`sweepdiag.py`). The
check lists such frames apart ('timer_phase_frames'; the sweep's
'opened, timer phase only'; the report's 'timer_phase_only') when the VDC
interrupts agree in every frame, the timer's moved, the sound driver's RAM
was the same at the return, the picture is the same and the next frame end
agrees; `--strict` fails them. Negative control: the `sms-palette` build's
2-2 786 opening still fails the new check (video state frames 3-4, PSG
registers frames 2-5, sound RAM different).

## 5. Evidence

### Menu (`scripts/check_menu.py`, all parts, music as played)

| Part | Result |
| --- | --- |
| runs | 140 openings in the 11 runs, all exact, no raster-timing frame, no timer-phase frame; stack low-water `$21D7` |
| sweep | 1,393 Select presses: 726 opened and exact, 1 opened and differing only by the timer phase (1-1 2829, above), 572 refused, 94 not seen by any update. All 8 former failures exact. `--strict`: the one timer-phase opening fails, nothing else |
| select | cold boot LANGUAGE reads ENGLISH; all 22 Level Select entries and Run on the next: passed |
| options | 36 cases, all passed: each option row; PALETTE NES-A, NES-B (Right once, twice; NES-A also by Left five times), GB DMG, HELL, SMS (Right 3-5 times, SMS also by Left); 12 Run paths through the modes (each mode then ORIGINAL; all six in Right and in Left order; GB DMG and SMS straight after each other; NES-A then GB DMG; SMS, NES-B, HELL, NES-A; NES-B, SMS, NES-A), every mode on the way exact (mapped: the VCE is its table over the RAM palette, `$2104` bit 7 set; NES-A / NES-B: the RAM palette holds that variant's 1-1 colours, the VCE equals it; after an NES mode the original colours are back; `$2100` bit 7 exactly with SMS) and the end equal to never leaving Original; 12 cancels after changing everything (from Original with each of NES-A, NES-B, GB DMG, HELL, SMS highlighted; from GB DMG to HELL and to NES-B; from HELL to SMS; from SMS to ORIGINAL and to GB DMG; from NES-A via NES-B to HELL; from NES-B via NES-A to SMS), each compared for 900 frames with the run without the menu: exact; stack low-water `$21C5` |

`scripts/check_boot.py` (early build and candidate): passed (idle frames
1-899 identical to the original, 136 distinct screens, first 1-1 update at
frame 163 when mashing Run, defaults English, Enhanced, damage on).

### Stored runs against the single-mode builds

`sms-palette/record.py` on the candidate in each mode, all 11 runs (35,084
frames each), compared per frame (`sms-palette/analyse.py identity`:
screenshot, VCE, sprite table, game RAM outside `comparison_video.OWNED`,
gameplay fields) with the reference build's recording in the same mode:

| Mode | Against | Picture, VCE, SAT, gameplay | RAM |
| --- | --- | --- | --- |
| Original | `sms-palette` | VCE, SAT, gameplay identical; picture 2 frames (2-2 789, 1660) | 2-2 every frame, 5-3 one frame (712) |
| GB DMG | `sms-palette` | VCE, SAT, gameplay identical; picture 1 frame (5-3 6494, the frame the NES record found for GB DMG) | 5 frames (2-2 3958, 4-2 2646, 5-2 1823 and 2937, 6-1 1749) |
| HELL | `sms-palette` | identical | 6 frames (2-2 3958, 3-2 3145, 4-2 2646, 5-2 1823 and 2937, 6-1 1743) |
| SMS | `sms-palette` | VCE, SAT, gameplay identical; picture 1 frame (6-3 1540, 1 pixel) | 6 frames (2-2 3958, 3-2 3145, 5-2 1823 and 2937, 6-1 1743) |
| NES-A | `nes-palette-2` | identical | every frame of 1-1, 3-1, 4-2, 5-2, 6-3 and from the next stage's load in 2-2, 3-2, 6-1 |

Explained (`nes-palette/framediff.py`, both builds, same frames):

- NES-A: only the animation records' list addresses in RAM (`$31A5-$31A7`,
  the copy in `$204A`): NES-A's table in bank 3 sits 12 bytes later (the
  NES-B test and its exit in `nes_anim_table` before it). Every stage with
  an animation set has them from its load on.
- Original, GB DMG, HELL, SMS against `sms-palette`: the NES branch's loader
  hooks (15 cycles per palette load outside NES mode, the HUD trampoline,
  the bank 3 call: about 25 cycles a stage load), exactly the differences
  the NES record found against its base: in 2-2 the stage load's extra
  cycles move the sound driver a tick (its RAM differs in every frame), and
  2-2 789 redraws the backdrop a moment apart (28,950 pixels on rows 51-56
  of that frame); single frames in loads near a run's end catch the load at
  another instruction (zero page `$2022-$2023`, RAM palette entries
  mid-unpack `$22A2-$22A5`, `$25E5`, the live stack); 6-3 1540 is one pixel
  of raster timing. Control: the candidate's Original recording equals
  `nes-palette-2`'s Original recording in every field of every frame of all
  11 runs, so in Original these differences are entirely the NES branch's
  (already in its record), none the merge's, NES-B's or the menu's.
- Gameplay (Ryu, timer, camera, area, stage, lives, health, master state,
  boss, SAT) is identical in every frame of every run in every mode.

NES-A and NES-B against Original on the candidate (`analyse.py due`): the
same gameplay fields and sprite table in every frame of all 11 runs; no
frame added or dropped.

### NES colours (NES-A and NES-B)

- Loaded data: every colour of both variants is one of the 47 NES colours
  (the build fails otherwise; unit tests).
- Stage loads (`all-palettes/stagecheck.py`, all 22 entries, 150 frames,
  Original against the mode): every load takes the same frames (78-83);
  gameplay fields and SAT identical; every managed entry holds its
  variant's colour (NES-A 0 mismatches, NES-B 0 mismatches).
- On screen (`nes-palette/onscreen.py`, an index picture every 30 frames):
  the 11 runs plus 900 frames, 1,481 samples per variant: no entry on
  screen outside the NES colours in gameplay (fade steps: NES-A 53,
  NES-B 76, each a channel-wise step at or below an NES colour). Boss
  fights (8 entries, 900 frames, No Damage) and every area of all 22
  entries (`warp`), 660 samples per variant: outside fades and cinemas
  only the known leftover rows: NES-A 4 entry-samples (row 10 entry 4 in
  4-3, 5-2, 6-3; 5-2 row 6 entry 2: the `nes-palette-2` record's), NES-B
  the same 4 and one more in a leftover row (2-1 row 14 entry 2, a fade
  step of an original colour left there by the start state; 2-1's set has
  14 rows).
- Animated colours (`animcheck.py`, 14 entries with animation sets, 240
  frames after the fade-in): in each variant every animated entry takes
  only its own variant's list colours, and NES-B's differ from NES-A's
  where the lists do. 3-1 in NES-B: entries 28, 30 and 31 hold `1AF`
  (their lists are one colour, above). 3-2 has no animated entry in any
  mode.

### Stack

`all-palettes/stackguard.py` (fill from `$2105`; `$2104` is the palette
module's state), the 11 runs with their stage loads: lowest `$21C2`
(Original, SMS), `$21C4` (NES-A, NES-B). The menu checks: `$21C5` at the
deepest (options), `$21D7` in the runs and the sweep. The watched margin
`$2105-$213F` is never reached (130 bytes above it at the deepest).

### Screenshots

Private, `build/all-palettes/shots/` (`all-palettes/shots.py`): 1-1 frame
600, 2-2 frame 400 and 5-3 frame 3000 of the stored runs in all six modes,
and the popup opened there in each mode; in all 18 popups the PALETTE row
reads the mode's name (ORIGINAL, NES-A, NES-B, GB DMG, HELL, SMS) and
`$2100` is the mode's value. Contact sheets `build/all-palettes/sheet-*.png`.

### ROM-free

`python3 -m unittest discover -s tests` and `scripts/audit_public.py`:
pass.

## Rerunning

From the repository root, `W=build/all-palettes` holding `original.pce`,
`seed.state`, `m2.pce` (the candidate), `ref-sms.pce`, `ref-nes2.pce`, the
emulator environment of `run-check.sh` and `NG_DEBUGGER_FAST=1`:

```sh
python3 scripts/check_boot.py --emulator $E --original $W/original.pce --candidate $W/m2.pce --output $W/boot
python3 scripts/check_menu.py --emulator $E --original $W/original.pce --candidate $W/m2.pce --output $W/menu   # --strict: timer phase fails
S=research/tools/sms-palette; A=research/tools/all-palettes; N=research/tools/nes-palette
GB_WORK=$W python3 $S/runmany.py $W/rec/log ap-orig 1 all record.py $W/m2.pce {run} $W/rec/ap-orig-{run}.json 0
#   and ap-gb 0x10, ap-hell 0x18, ap-sms 0xb8, ap-nesa 0x08, ap-nesb 0x28; n2-nesa / n2-orig from ref-nes2.pce
GB_WORK=$W python3 $S/analyse.py $W/rec identity smsb-orig ap-orig      # smsb-*: the sms-palette build's recordings
GB_WORK=$W python3 $S/analyse.py $W/rec due ap-nesb ap-orig
NES_WORK=$W python3 $N/framediff.py $W/ref-sms.pce $W/m2.pce 0 2-2 789 789
python3 $A/stagecheck.py $W/m2.pce 150 $W/sc-b.json 0x28        # and 0x08
NES_WORK=$W python3 $N/onscreen.py $W/m2.pce 0x28 30 OUT run:1-1:900 ... run:6-3:900
NES_WORK=$W python3 $N/onscreen.py $W/m2.pce 42 30 OUT ls:1:900 ... warp:0:180 ... warp:21:180
python3 $A/animcheck.py $W/m2.pce 0x28 240 0,1,2,4,5,9,10,11,12,13,17,18,19,21
python3 $A/stackguard.py $W/m2.pce 0x28
python3 $A/sweepdiag.py $W/ref-sms.pce 2-2 786 0 8 OUT.json      # SAME_MUSIC=1, ALIGN=hook|vblank
python3 $A/committed.py $W/ref-sms.pce 2-2 780,784,788 10
python3 $A/shots.py $W/m2.pce $W/shots 1-1:600:menu 2-2:400:menu 5-3:3000:menu
GB_WORK=$W python3 $S/runmany.py $W/fw fw 3 boot,1-1,... freewatch.py $W/ref-sms.pce {run} 761cf 76fff 7a00 7bff
```

## Not covered

Real hardware; listening to the sound around the menu (PSG registers
compared only); whole cinemas, the title, the ending, Continue and Game
Over in the new modes; NES-B's colours are the designed re-light, not
reviewed by the maintainer (and 3-1's animation is lost in NES-B); the
HELL retuning choice (D or D2) is pending.
