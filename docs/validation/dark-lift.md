# Dark lift: SMS, HELL and the NES modes' 4-1 (1.11-dev)

Emulator evidence (headless Geargrafx `78fc3d7` with the headless-fast patch,
binary SHA-256 `2de50e51…`, [EMULATOR.md](../pc-engine/EMULATOR.md)); no real
hardware, audio not listened to. Design:
[architecture, palette modes](../ARCHITECTURE.md#palette-modes).

**This record is incomplete.** The session that made it was wound down
before the brightness measurements, the screenshots, the Level Select
entries and the NES on-screen counts were started; they are listed under
[Not done](#not-done-next-steps) with their commands. What is below was run
to the end. The flash and the grey order it left open are taken up in
[Dark lift 2](#dark-lift-2-the-flash-and-the-shade-order-branch-dark-lift-fix),
which corrects two statements of this part: the flash's cause (the load
drops the queue; 91 entries, not ten) and "HELL did not show it" (HELL
leaves 43-49 entries behind, none on a playfield tile).

The owner found 5-1 and 6-2 too dark and 4-1's parallax background almost
invisible. A survey of the `hell-1-1` build (`build/dark-survey/`) showed
SMS and HELL sending dark colours to black and NES-A / NES-B showing 4-1's
trunks only faintly; a mock-up study (`build/dark-lift/`) recommended a
data-only change per mode. This branch applies that set.

| Build | SHA-256 | Source |
| --- | --- | --- |
| `hell-1-1` (reference) | `fa158540598587c3b47dad4344ad99040cf46d62dfc9ccf01184d7a6320ef4c9` | `fb1de01`, the bytes of its record |
| Candidate | `23871f8fe45ebdd8f2e8fda65a3a585b17248a4af17f27b1805b436b0bdf39d7` | branch `dark-lift`, `3a90757` (the same bytes from the headered and the headerless original) |

Work folder (private): `build/dark-lift-rom/` with `seed.state` and
`original.pce` (the `hell-1-1` record's), `h1.pce` (`hell-1-1`), `dl.pce`
(the candidate), `rec/` (recordings; `h1-*` are the `hell-1-1` record's).
Probes: [`research/tools/dark-lift/`](../../research/tools/dark-lift) and,
unchanged, the SMS, HELL, NES and GB palette probes.

## 1. What changed

Data and the table generator only: no assembly, no menu, no RAM, no new ROM
range.

- **SMS, the study's "Sa"** (`src/palette/sms.json` `"dark_rescue":
  {"min_luma": "0.5"}`; `scripts/palette_tables.py` `sms_table`): a colour
  that the channel rule sends to black although its luma (R × 0.299 + G ×
  0.587 + B × 0.114, channels 0-7) is at least 0.5 takes SMS level 2 in each
  channel that holds 1. That is four colours: `$040` → `$080`, `$041` →
  `$082`, `$048` → `$090`, `$049` → `$092`. Every output is still one of
  the 64 colours. `$001`, `$008` and `$009` (the darkest blue, red and
  purple; luma below 0.5) still show black: "a visible colour never becomes
  black" holds for the green and grey ones only. The generator also accepts
  `dark_rescue: true` (every colour) and `dark_map` (single colours); the
  shipped file uses neither.
- **HELL, "Hb"** (`src/palette/hell.json`): the dark ends of `green_ramp`,
  `grey_ramp` and `steel_ramp` raised, and a new optional "leaf" family
  (`leaf_ramp`, `leaf_windows` `[[100, 140, 0.9]]`, `leaf_mix`) for
  saturated pure greens. 21 colours change (as R G B, before > after):
  `$040` 000>110, `$041` 100>210, `$049` 100>310, `$080` 110>310, `$0C0`
  and `$0C1` 110>320, `$100` 210>420, `$101` and `$108` 220>420, `$140`,
  `$141`, `$148` 320>430, `$180`, `$181`, `$182` 320>530, `$188` 420>530,
  `$1C0`, `$1C1` 420>641, `$1C2`, `$1C8`, `$1D0` 430>641. No colour but
  black maps to black (candidate D sent `$040` there). The 1-1 override
  (`$094` → 210) and the 240 mapped entries are unchanged.
- **NES-A and NES-B, "Na"** (`src/nes-palette/stages/08-4-1.json`): a new
  role `backwood` (ramp `09`, `18`; strict; `08` excluded) on the bark
  entries of rows 0 and 3 (entries 6, 8-11), which resolve to `$080`,
  `$092`, `$080` (NES-B `$090`), `$0A0`, `$090` instead of `$040`.
  `scripts/nes_palette.py` is unchanged.
- GB DMG: untouched.

Against the study: the generated `gb-table.inc`, `hell-table.inc` and
`sms-table.inc` equal `build/dark-lift/gen/tables/recommended-Hb-Sa/` byte
for byte, and all eight NES includes equal `gen/tables/nes-Na-backwood/`
byte for byte (only `nes-sets.inc` and `nes-b-sets.inc` differ from the
`hell-1-1` generator's, in set 8).

In the ROM exactly 50 bytes differ from `hell-1-1`:

| Region | Bytes |
| --- | --- |
| Bank `$43` `$7C40-$7FD0` (file `$87C40-$87FD0`), HELL table | 26 (21 colours) |
| Bank `$3B` `$5440-$5449` (file `$77440-$77449`), SMS table | 4 |
| Bank `$45` (file `$8B7DD-$8B819`), NES-A set 8 | 10 |
| Bank `$3B` (file `$767DD-$76819`), NES-B set 8 | 10 |

The study's HELL and SMS tables are at file `$87C00` and `$77400` in the
candidate, its packed NES-A and NES-B sets at `$8B200` and `$76200`; the GB
DMG table at `$8D400` is the `hell-1-1` build's.

## 2. Evidence

### ROM-free

`python3 -m unittest tests.test_tools` (49 tests) and
`scripts/audit_public.py`: pass. The tests pin the new HELL table (SHA-256 of
the 512 words `7be5da49…272b`), that it differs from candidate D
(`1435b5a1…d641`, reproduced from D's ramps) in exactly the 21 colours
above, that no non-black colour maps to black, 240 mapped entries, the
override; the new SMS table (`9323ab4a…b314`), candidate A (`bb0779db…d927`)
without `dark_rescue`, the four rescued colours, every output among the 64,
the exact luma threshold, `dark_map`'s check; and 4-1's `backwood` records
in NES-A and NES-B (NES colours, lighter than `$040`).

### Boot and menu

- `scripts/check_boot.py`: passed (idle frames 1-899 identical to the
  original, 136 distinct screens, first 1-1 update at frame 163 when mashing
  Run, defaults English, Enhanced, damage on).
- `scripts/check_menu.py` (all parts, music as played): **passed**. runs:
  140 openings in the 11 runs, all exact, stack low-water `$21D7`; sweep:
  726 opened and exact, 1 opened and differing only by the timer phase (1-1
  2829, the one the `all-palettes` and `hell-1-1` records list), 572
  refused, 94 not seen; select: all 22 Level Select entries and Run on the
  next; options: all 36 cases (HELL and SMS from 1-1 show exactly the new
  tables over the RAM palette, HELL with the override; NES-A and NES-B hold
  their 1-1 colours).

### Stored runs (`hell-1-1/record11.py`, `dark-lift/summary.py`)

All 11 runs (35,084 frames) on the candidate in each mode, compared per
frame with the `hell-1-1` record's recordings of its build (screenshot,
VCE, sprite table, game RAM outside `comparison_video.OWNED`, gameplay
fields):

| Mode | Against `hell-1-1` | VCE and gameplay on the candidate |
| --- | --- | --- |
| Original | **identical**, every field, every frame | |
| GB DMG | **identical**, every field, every frame | |
| SMS | sprite table, RAM and gameplay identical in every frame; picture and VCE differ (the table) | every VCE entry equals the new SMS table of its RAM colour except while uploads are queued; gameplay and sprite table equal to Original in every frame (`$2240` one frame later at the cinema after 4-1, 5-3, 6-3, as before); no gameplay frame with a VCE entry or a pixel outside the 64 colours (`hell-1-1`: also none) |
| HELL | sprite table, RAM and gameplay identical; picture and VCE differ | every VCE entry 0-239 equals `hell_stage_table($2E5F)` of its RAM colour, 240-511 the RAM colour, except while uploads are queued; frames not yet due per run exactly `hell-1-1`'s (136, 134, 101, 122, 74, 124, 143, 170, 4, 122, 117; 2-2 one fewer than its 135), longest lag 37 as there; gameplay as SMS |
| NES-A | 10 runs identical in every field; 4-1 differs in picture (2,447 frames), VCE (2,462) and RAM (every frame: the palette); sprite table and gameplay identical | the VCE equals the RAM palette except while uploads are queued (20 frames in 4-1, as on `hell-1-1`); gameplay equal to Original |
| NES-B | the same: 10 runs identical, 4-1 picture 2,447, VCE 2,462, RAM every frame | as NES-A |

SMS frames not yet due: 145, 144, 111, 135, 84, 135, 154, 209, 14, 133, 141
(1-1 … 6-3) against `hell-1-1`'s 139, 138, 105, 129, 84, 129, 148, 209, 14,
127, 141: six more in the seven runs that end in the next stage's load. They
are frames of that stage's fade-in (1-1 2856-2861, 6-1 1759-1764) in which
entries still wait for their upload; with candidate A the waiting colour and
the colour due were both black, so the wait did not count. The upload is
the same code and the RAM is identical.

Not checked on the emulator: that the RAM palette of 4-1 holds exactly the
new set-8 colours in the NES modes (`dark-lift/nescheck.py` on captures; the
ROM bytes and the unit tests cover the data, `check_menu.py` covers 1-1).

### Fades (`dark-lift/fades.py`, `fadereport.py`)

The study warned that lifted dark colours pass through one brighter step
just before black. Every frame of four fades was recorded on both builds in
SMS and HELL: the Level Select entry of 4-1 and of 6-2 from the main-loop
hook through the load (the fade-in), the end of the stored 4-1 run (fade-out
to the cinema, frames 2400-2547) and 6-2's last area left by its exit
(fade-out, 6-3's load and fade-in). Per frame: mean L* of the playfield and
the share of it that got lighter or darker than the frame before by more
than 1 L*. A mapped fade step is held 8 or 16 frames.

| Fade | SMS | HELL |
| --- | --- | --- |
| 4-1 fade-in | no pixel darker at any step; the first steps are lighter than before (frame 58: mean L* 7.5, 29% not black; `hell-1-1` 1.7, 8%) | 0.8% of the playfield 5 L* darker at frame 43 after one step of 9 frames (shown 210, then 110); 0.8% by 3 L* at frame 66 on both builds |
| 4-1 fade-out | no pixel lighter at any step on either build | 0.7% of the playfield 5 L* lighter for 3 frames (2468-2470); `hell-1-1` none |
| 6-2 fade-in | no pixel darker; starts 16 frames earlier (first colours at frame 41, `hell-1-1` 57) | no step against the fade above 0.5% |
| 6-2 fade-out and 6-3's load | fade-out: no pixel lighter. **Then a flash: frames 79-85 (7 frames) show 6-3's floor strip, 7.0% of the playfield, in grey `$092` and `$082` (L* 31) on the black screen**, black again for 16 frames, then the fade-in. `hell-1-1` and Original are black there. **6-3's fade-in: 3.5% of the playfield is grey `$092` in the steps before the last (frames 120-139, 20 frames; `$092` covers 14.2% there, `hell-1-1` 10.8%) and turns 26 L* darker at the last step (frame 140)**; `hell-1-1` has no pixel darker | fade-out: no pixel lighter. 6-3's fade-in: 4.5% of the playfield 5 L* darker at frame 134 after a step of 15 frames, 0.7% by 7 L* at 119; one frame (118) differs on both builds while the upload lands (9.2% by 10 L*; `hell-1-1` 4.3% by 18) |

Read plainly: the fade-outs show no lighter step in either mode (HELL
0.7% of the picture by 5 L* for 3 frames). The fade-ins do show the step the
study warned of, small in HELL (under 5% of the picture, 5-7 L*) and
visible in SMS in 6-3 (3.5% of the picture grey for 20 frames before it
settles 26 L* darker; none in 4-1 or 6-2). **The SMS flash in 6-3's load is
real and new.** Its cause is not
the fade's arithmetic: when the load sets the palette lock (`$2283`), ten
background entries of the VCE still hold the fade-out's last step before
black (RAM colours `$049` / `$041`; the mapped upload's left-over entry had
not reached them), and the new stage's tiles appear on them for 7 frames
before the lock opens. The same stale entries exist on `hell-1-1`, where
candidate A showed those colours as black. It can be expected wherever a
mapped fade-out is cut by a load; only this one transition was looked at.
HELL did not show it here (its entries were black at the lock). Pictures:
`build/dark-lift-rom/shots/fades/fade-<mode>-<case>.png` (`hell-1-1` above,
candidate below; the steps near black); numbers:
`build/dark-lift-rom/fades-report.txt`.

A model of the fade (each channel one lower per step) over all 512 colours:
SMS has no colour whose next darker step shows lighter, before or after.
HELL has 73 such colours (54 with candidate D, most by 4-7 L*); the new
ones include **grey `$092` (R2 G2 B2, shown 100, L* 3) to `$049` (shown
310, L* 25)**: the darkest grey is now lighter than the next grey. In a
still picture a tile shaded with both greys has its two darkest shades
reversed; no capture here was checked for it.

### Brightness (partial)

Not measured as the survey did. The only real captures of both builds are
the steady frames of the fade traces (playfield rows 50-241):

| Scene | SMS `hell-1-1` | SMS candidate | HELL `hell-1-1` | HELL candidate |
| --- | --- | --- | --- | --- |
| 4-1 area 0, 60 frames after the first update | L* 9.2, 31% not black | 14.7, 51% | 8.2, 64% | 11.9, 73% |
| 4-1 run frame 2400 (area 2) | 35.8, 67% | 42.7, 90% | 29.1, 89% | 34.0, 90% |
| 6-2 area 0, 60 frames after the first update | 3.8, 27% | 9.0, 44% | 6.5, 57% | 10.2, 58% |
| 6-2 area 4 | 10.9, 47% | 12.8, 53% | 11.2, 71% | 14.1, 71% |

6-2 area 0 agrees with the study's prediction for its survey frames (SMS
3.8 → 9.1, HELL 6.5 → 10.2). `dark-lift/measure.py` on the survey's own
captures of `hell-1-1` reproduces the study's "current" column exactly (HELL
4-1 12.2/57/86/27, SMS 13.8/58/59/20, NES-A 18.9/36/56/21), so it is ready
for the candidate's captures.

## Dark lift 2: the flash and the shade order (branch `dark-lift-fix`)

Work on the three open points of the record above. **Also incomplete**:
the host stopped one survey run for low memory, and what had not finished
is listed under [Not verified](#not-verified-on-the-fix-build) and was not
rerun.

| Build | SHA-256 | Source |
| --- | --- | --- |
| Dark lift (before) | `23871f8fe45ebdd8f2e8fda65a3a585b17248a4af17f27b1805b436b0bdf39d7` | branch `dark-lift`, rebuilt here: the same bytes |
| Fix build | `1678b2e1b2eaabcb27ae8a23e51dd95d0f411c2e570a1bd3f2e224aa3541e2ae` | branch `dark-lift-fix`, `b045238` (the same bytes from the headered and the headerless original) |

Work folder (private): `build/dark-lift-fix/` (`dl.pce`, `fix2.pce`,
`trans/` the transition recordings, `capidx/` index captures of all 22
stages, `hell/` the grey candidates, `hellmock2/` their pictures). New
probes in [`research/tools/dark-lift/`](../../research/tools/dark-lift):
`trans.py`, `transreport.py`, `unittest_fade.py`, `leftover_cost.py`,
`hellorder.py`, `hellmock.py`.

### A. The SMS flash: cause

Read from the game's code (fixed bank and bank 1 of the original) and from
a per-frame recording of 6-2's exit (`trans.py walk:17`):

1. The stage-end fade-out (bank 1 `$8510`, the only fade-out in gameplay)
   sets a 58-tick timer (`$2E63`) and starts the native fade (`$F422`): 8
   steps, brightness `$2A8A` 7 down to 0, one every 7 ticks, each
   recomputing all 512 colours of the RAM palette under the lock (more than
   a frame, so the steps are 8 frames apart) and queuing them. The last step
   (all black) is at tick 50; after it `$2A8A` is `$FF`. The load starts when
   the timer ends, 8 ticks later.
2. The mapped upload gives a 512-colour step 130 colours in its first vblank
   (0.266 x 512 less 6 for the left-over entry before it) and then, as a
   left-over entry, 16 colours a vblank while the main loop idles: about 240
   colours per 8-frame step. Every mapped fade therefore runs behind, and
   of the last step's 512 colours only about 270 have been written when the
   load begins.
3. The load holds the lock for 14 frames and, when it starts the fade-in
   (`$F436`), empties the queue (`$F345` clears `$2260-$2282`). The
   left-over entry is dropped; the module then finds an empty queue and
   forgets it too.
4. The VCE entries the left-over entry had not reached keep the fade's step
   before black. In 6-2's exit in SMS that is 91 entries: background 2-8,
   15, 31, 47 and sprite entries 327-463 and 488-495, showing `$080`,
   `$082`, `$092` (RAM `$040`, `$041`, `$049`). The load draws 6-3's floor
   with entries 2-8 ten frames into the lock, and it shows until the
   fade-in's first step (level 0, black again) has uploaded its first 136
   colours: frames 983-989 of the walk (79-85 of the earlier trace).

So the entries were not "about ten" and the left-over entry had not merely
"not reached them": the game discards the queue. With candidate A those
colours (every channel 0 or 1) showed as black, which hid it. **GB DMG has
had the same flash since the mode exists**: the same entries hold its
second shade `$090` on its black `$040`. HELL leaves entries behind too
(43-49 per stage change: 223, 233, 239, the HUD palette's 241-255 and
sprite entries), but none of them is on a playfield tile during the loads
recorded.

The **grey step in 6-3's fade-in** (3.5% of the playfield grey for 20 frames,
then 26 L* darker) is a different thing and is not fixed here. No VCE entry
is late in those frames: the colour is due. The fade-in passes the floor's
blue-grey `$04A` (R1 G1 B2) through `$049` (R1 G1 B1), which the dark
rescue shows as grey `$092` (L* 31), and ends on `$04A`, which the channel
rule shows as `$002` (L* 4). It is the table, see [Shade order in SMS](#shade-order-in-sms).

### A. How widespread (the dark-lift build)

`trans.py` on the dark-lift build in Original, GB DMG, HELL and SMS: every
area exit of all 22 Level Select entries (the exit moved onto Ryu, as the
survey's warp) and the 11 stored runs, every frame; `transreport.py`. A
span is a run of gameplay frames in which Original's playfield (screenshot
rows 50-241) is entirely black; 37 spans, the same frames in every mode.

| Kind of span | Spans | SMS | GB DMG | HELL |
| --- | --- | --- | --- | --- |
| Stage-end fade-out into the next stage's load (11 stage changes: 1-1, 2-1, 2-2, 3-1, 3-2, 4-2, 4-3, 5-1, 5-2, 6-1, 6-2; 7 of them in a run and a walk) | 18 | 42-91 entries not black at the load's lock; black 0-26 frames late; a flash in 7 spans | 9-24 entries; 0-26 frames late; a flash in the same 7 spans, the same frames | 43-49 entries; 0-9 frames late; no flash |
| Stage-end fade-out into a cinema (8 frames) | 12 | black 5-8 frames late (8: never, in 8 spans) | 5-8 frames late | 0-8 frames late |
| Cut to black after a boss (3-3, 4-4; 16 frames; not a fade: `$F275`/`$F26F` fill the RAM palette) | 2 | 13 frames late | 13 | 8 |
| Area change that goes entirely black (5-2, 5-3; two spans of 4 frames, two of 2; a fill of colours 0-255 and the load at the next tick) | 4 | the 4-frame spans: not black in any frame; the 2-frame spans: black | not black in any frame | as SMS |
| 2-2's start (8 frames) | 1 | 6 frames late | 6 | 6 |

The flashes (SMS and GB DMG alike; the share is of the playfield):

| Stage change | Frames | Largest share | Seen in |
| --- | --- | --- | --- |
| 4-3 to 4-4 | 16 | 10.76% | walk |
| 6-2 to 6-3 | 8 | 7.14% | walk |
| 2-1 to 2-2 | 2 | 1.38% | walk |
| 3-2 to 3-3 | 12 | 0.29% | run and walk |
| 5-1 to 5-2 | 3 | 0.08% | walk |
| 4-2 to 4-3 | 9 | 0.04% | run (the walk: none) |

In SMS they are grey or green on black (`$092`, `$082`); in GB DMG the
second olive on the darkest (`$090` on `$040`). The HUD band (rows 18-49)
never flashes; over the 22 walks it stays lit after Original's is black for
110 frames in SMS, 114 in GB DMG and 469 in HELL (HELL's HUD palette is the
last the left-over entry reaches, and it often never did).

Area changes inside a stage are mostly not in the table: Ryu stays on
screen, so Original's playfield is not entirely black. They are a cut, not
a fade, and the mapped modes have never followed them: the native game
blacks out colours 0-255 in one vblank and loads at the next tick, the
mapped upload gets 28 colours of it. That is as it was in every mapped
mode since GB DMG and is not changed here.

Not looked at: deaths, Continue, Game Over (a `die:` case exists in
`trans.py` and was not run).

### A. The fix

`src/palette/main.asm`, the mapped uploads only (`mapped_upload` for GB DMG
and SMS, `hell_upload` for HELL). While the native fade's level `$2A8A` has
bit 7 set (`$FF`: a fade-out has ended on black and no fade has begun
since), a left-over entry gets `FADE_CAP` = 136 colours a vblank instead of
16, under the same condition as before (the main loop idle at this vblank
and at the last one with work). 136 is what a fade step's 512 colours get
in their first vblank, so these vblanks are no longer than every fade
step's first already was. With that first vblank three more complete the
black: four ticks before the load. The colours still come from the RAM
palette through the table; the game's state only sets the pace.

The paths without that state take the cycles they took: the idle left-over
path is the old one cycle for cycle (39 cycles from the branch to
`next_chunk`, 45 in HELL: a taken branch for a branch and a jump, the
shared tail inlined, three `nop`s in HELL), the busy path too (a `nop` for
the branch that is no longer taken). The Original and NES path, the
new-work path and `palette_now` are the bytes they were at the addresses
they had (the first changed byte in bank `$46` is at `$5177`, inside
`mapped_upload`; before it only the operand of `jmp now_hell` at `$50F3`).
No RAM, no fixed-bank bytes, no new claim: +21 bytes in bank `$46`
`$5000-$53FF` and its SMS copy in bank `$3B` (code now ends at `$539D`),
+24 in bank `$43` (ends at `$7BEC`; 19 bytes free before the table).

A first build used the whole cap (168 colours). Its fade vblanks ended up
to 22.45 lines after the interrupt in HELL (21.5 in SMS), too close to the
display (22.8), so it was not kept.

Cost: in the three or four vblanks after a stage-end fade-out the upload
runs to about line 18 instead of line 4, while the main loop only counts
ticks. Nothing else changes. Not fixed by it: the cut after a boss, area
changes, the fade steps before the last (they still run behind), the grey
step of 6-3's fade-in.

### A. Evidence on the fix build

- ROM-free: `python3 -m unittest tests.test_tools` (49 tests) and
  `scripts/audit_public.py` pass.
- Unit test in place (`unittest_fade.py`: the hell-1-1 harness and model,
  each case also writing `$2A8A`; levels 8, 0-7 and `$FF`): 1,892 cases with
  seed 22 (44 of them a left-over entry at the fade's pace) and 1,892 with
  seed 31 (38), 0 failures. Negative control (the model without the rule):
  39 failures of 1,892.
- Timing of one left-over entry (`leftover_cost.py`, five queues, the
  hardware-event trace): with level 8 the first and the last VCE write and
  the scanline interrupt's CPU entry are equal to the master clock on the
  dark-lift build and the fix build, in SMS, GB DMG and HELL. With level
  `$FF` 136 colours go; the last write is 17.80-17.99 lines after the
  vblank interrupt in SMS, 17.75-17.93 in GB DMG, at most 18.72 in HELL
  (1-1, the override loop). The display starts about 22.8 lines after it.
- 6-2's exit in SMS (`trans.py walk:17`): the VCE is black in every entry 5
  frames after the last step (4 ticks left on the timer), the queue empty
  from the next frame, no entry lit at the load's lock, no playfield pixel
  lit until the fade-in.
- GB DMG, all 22 walks and 10 of the 11 runs (5-3 was not recorded): no
  flash in any span (7 before); no entry lit at the load's lock in any of
  the 18 stage-end spans (9-24 before); the screen is black 0-3
  frames after Original's in them (0-26 before; 2-1 to 2-2 9 against 13,
  where Original's dark area is black before the last step). The cut after
  a boss and the area changes are as before (9 and 4 frames late; 130-195
  entries). HUD band lit after Original's: 26 frames over the 22 walks (114
  before).
- HELL, 12 of the 22 walks (1-1 to 3-2 and 4-1 to 5-1): no entry lit at the
  load's lock in the 8 stage-end spans (43-49 before); HUD band 24 frames
  over the 12 walks.
- **Gameplay against Original, a change to know about.** On the dark-lift
  build the cinema after a stage begins one frame later in the mapped modes
  than in Original (`$2240`; the earlier records list it: 4-1, 5-3, 6-3).
  On the fix build it begins on Original's frame: in the 4-1, 5-3 and 6-3
  runs in GB DMG, SMS and HELL (below), in the 11 walks that end in a
  cinema in GB DMG and the 4 such walks recorded in HELL. So against the
  dark-lift build one frame is gone before each cinema; against Original
  the mapped modes no longer differ there. Why the frame was there was not
  traced (the left-over upload was still running when the cinema began; it
  no longer is). The other gameplay differences from Original are the
  dark-lift build's own, in the same frames: single frames in three walks
  (2-1 frame 363, 6-2 frame 544, 5-2 every eighth frame from 293, seven of
  them), not in any stored run; they are forced-scroll walks, and the frame
  after each is equal again.

### A. Regression: the 11 stored runs

`recall.sh` (`hell-1-1/record11.py`; 35,084 frames a mode) on the fix build,
against the dark-lift build's recordings of its own record (`rec/dl-*`):
`sms-palette/analyse.py identity`, `summary.py`, `diffwhere.py`.

| Mode | Against the dark-lift build | On the fix build |
| --- | --- | --- |
| Original | **identical**: picture, VCE, sprite table, game RAM, gameplay fields, every frame of every run | |
| NES-A | **identical**, the same | |
| NES-B | **identical**, the same | |
| GB DMG | sprite table identical in every frame; gameplay fields identical except the one frame the cinema begins in 4-1, 5-3, 6-3; picture, VCE and RAM differ in one window per run (below); 5-4, which has no stage end: nothing differs | gameplay fields and sprite table equal to Original in **every** frame of every run (`$2240` included); frames not yet due 128, 127, 94, 118, 78, 118, 137, 203, 14, 116, 135 (1-1 … 6-3; 145, 144, 111, 135, 84, 135, 154, 209, 14, 133, 141 before); longest lag 18 frames (42-46 before in the runs that end in a stage change, 19 in 4-1), 14 in 5-4 and 28 and 30 in 5-3 and 6-3 as before |
| SMS | as GB DMG | as GB DMG, the same counts; no gameplay frame with a VCE entry or a pixel outside the 64 colours |
| HELL | as GB DMG | gameplay equal to Original in every frame; frames not yet due 118, 116, 83, 104, 67, 106, 125, 163, 4, 104, 110 (136, 134, 101, 122, 74, 124, 143, 170, 4, 122, 117 before); longest lag 10-13 frames (33-37 before; 4-1 11), 21 in 5-3 and 6-3 and 4 in 5-4 as before |

Every frame that differs from the dark-lift build lies in one run of
frames per recording, which starts where the fade-out's last step is first
uploaded (`diffwhere.py`: no difference outside it in any mode):

| Run (its end) | GB DMG and SMS: picture | VCE | RAM | HELL: picture |
| --- | --- | --- | --- | --- |
| 1-1 (load at 2831) | 2823-2826 | 2822-2855 (SMS to 2862) | 2822-2844 | 2823-2855 |
| 2-2 (load at 3945) | 3937-3961 | 3936-3972 (3976) | 3936-3958 | 3938-3969 |
| 3-1 (load at 1886) | 1878-1902 | 1877-1919 | 1877-1901 | 1878-1912 |
| 3-2 (load at 3136) | 3128-3131, 3136-3147 | 3127-3165 (3167) | 3127-3149 | 3128-3160 |
| 4-1 (cinema at 2487) | 2480-2483 | 2479-2488 | 2479-2488 | 2480-2488 |
| 4-2 (load at 2637) | 2629-2632, 2638-2646 | 2628-2659 (2666) | 2628-2648 | 2630-2659 |
| 5-2 (load at 2928) | 2920-2925 | 2919-2953 (2960) | 2919-2942 | 2921-2953 |
| 5-3 (cinema at 6768) | 6761-6769 | 6760-6769 | 6760-6769 | 6762-6769 |
| 5-4 (none) | none | none | none | none |
| 6-1 (load at 1734) | 1726-1750 | 1725-1758 (1765) | 1725-1747 | 1727-1758 |
| 6-3 (cinema at 5122) | 5115-5120 | 5114-5123 | 5114-5123 | 5116-5123 |

What they are: the first range of pictures is the end of the fade-out,
black sooner (4 frames where the dark-lift build was 5 frames late, 25
where it was 26); the second range in 3-2 and 4-2 is the flash, exactly its
frames, now black; HELL's pictures differ through the load because its HUD
band and sprite entries are black now where they stayed lit. The VCE and
the module's state in RAM (`$2104`, the queue) differ until the next
stage's fade-in has written every entry once. After a cinema's first frame
(the one-frame shift above) the runs' recorded 60 frames are the cinema's
own.

**For GB DMG** (the owner: the mode is fine as it is): the fix changes 4 to
25 pictures at each stage end and nothing else in the 11 runs. They are an
improvement on the same grounds as in SMS: the flash was there in GB DMG
too (its second olive `$090` on its darkest `$040`: 3-2 12 frames and 4-2
9 frames in the runs; 4-3 to 4-4 10.8% of the playfield for 16 frames and
6-2 to 6-3 7.1% for 8 in the walks), and the screen now reaches its
darkest shade 0-3 frames after Original's black instead of up to 26. To
leave GB DMG exactly as it was, the rule would need a test of the mode in
the shared code (SMS runs GB DMG's bytes), a few cycles in GB DMG's
left-over path; not done.

### A. Boot and menu

- `scripts/check_boot.py`: passed (idle frames 1-899 identical to the
  original, 136 distinct screens, first 1-1 update at frame 163 when mashing
  Run, defaults English, Enhanced, damage on).
- `scripts/check_menu.py` (all parts, music as played): **passed**. runs:
  140 openings in the 11 runs, all exact, stack low-water `$21D7`; sweep:
  1,393 Select presses, 726 opened and exact, 1 opened and differing only
  by the timer phase (1-1 2829, the one every record since `all-palettes`
  lists), 572 refused, 94 not seen: the dark-lift build's counts; select
  and options: every case passed (stack low-water `$21C5`, HELL).

### A. Black frames of the runs in SMS and HELL

`blackruns.py` on the regression's recordings: SMS and HELL show black as
`$000`, so wherever Original's whole picture (HUD included) is black, theirs
must be the same picture. 263 such frames in the 11 runs:

| | Not black, before the mode's first black frame (late) | Not black after it (flash) | VCE entries not due at the load (the 7 runs that end in one) |
| --- | --- | --- | --- |
| SMS, dark-lift build | 120 | 21 (3-2: 12, 4-2: 9) | 42, 68, 62, 65, 73, 82, 80 |
| SMS, fix build | 17 (1-3 a run) | 0 | 0 in all 7 |
| HELL, dark-lift build | 263: never black in any of them (the HUD band stayed lit through every load) | 0 | 46, 43, 46, 46, 46, 46, 46 |
| HELL, fix build | 20 (2 a run) | 0 | 0 in all 7 |

### Not verified on the fix build

The second survey run (`jobs/trans-round2.txt`) was stopped by the host for
low memory after 16 of its 30 jobs and was not started again. So the
per-frame transition survey (`trans.py`) of the fix build is missing for:

- SMS: the 22 walks except 6-2's, and the 11 runs. The runs are covered by
  the table above and the regression; of the 11 stage changes that end in a
  load, 2-1 to 2-2, 4-3 to 4-4 (the largest flash) and 5-1 to 5-2 are
  **not recorded in SMS on the fix build** by anything. GB DMG, whose code
  SMS runs byte for byte with another table, is clean in all three.
- HELL: the walks of 5-2 to 6-4C, and the 11 runs (covered as SMS's); the
  stage change not recorded in HELL is 6-2 to 6-3.
- GB DMG: the 5-3 run (in the regression).

Also not run: deaths, Continue and Game Over in any mode; the stack and
free-ROM probes (no call, push or new range was added).

```sh
W=build/dark-lift-fix; D=research/tools/dark-lift    # GB_WORK=$W NES_WORK=$W NG_DEBUGGER_FAST=1
python3 $D/mkjobs.py trans $W $W/fix2.pce $W/dl.pce > $W/jobs/trans.txt
python3 $D/runjobs.py $W/jobs/trans.txt 2 $W/jobs/log         # 48 jobs; `grep ^trans-new` for the fix build only
python3 $D/transreport.py $W/trans old,new
python3 $D/unittest_fade.py $W/fix2.pce 300 22                 # NO_FADE_MODEL=1: control
python3 $D/leftover_cost.py $W/fix2.pce 0xb8                   # and 0x10, 0x18; dl.pce
```

### B. HELL's grey order

`hellorder.py` (table) and index captures of every area of all 22 stages
(`cap.py` warp, 176 captures; `hellorder.py CAP`, `hellmock.py`).

The table: among the 11 greys, `$049` (R1 G1 B1) shows 310 (L* 25.3) and
the next grey `$092` (R2 G2 B2) shows 100 (L* 3.4). That is the only
inversion of 3 L* or more the dark lift added. Candidate D already had 7 in
the grey family (`$124` shows 521, L* 45.2, the seven lighter greys
`$125-$16D` show 410, L* 32.4) and many in the others (the lava ramp's hot
step 710 over 620; 2,461 pairs in the blue family, 487 green, 223 warm, 2
steel); the dark lift removed 224 of the green ones and added none
elsewhere. On screen, counting pairs of one background palette row: 32
inverted pairs under candidate D, 31 under the dark lift; `$049`/`$092` is
the only new one, two green pairs (`$122`, `$123` with `$180`) are gone.

Where `$049` and `$092` are on screen together: 31 of the 176 captures, and
they touch (4-neighbour pixels) in 26, never in more than 99 pixels (5-1
area 0: the rune strip of the pillar at the left edge, 0.2% of the
playfield; then 4-1 area 0 with 32 pixels, 6-2 area 2 with 12, 4-3 and 4-2
with 8). Elsewhere the two belong to different things (4-3: `$049` 17.9%
of the playfield, the pillars and floor; `$092` 1.9%, the centre column's
pattern). Looked at (`build/dark-lift-fix/hellmock2/`: Original, candidate
D, dark lift, `$092` as 310): in 5-1 the runes are dark marks on a lit
pillar where Original has light marks on a dark one. It is visible when
enlarged, on a strip a few pixels wide.

**`hell.json` is not changed**, because no table value keeps both things
asked for:

| Choice | Order | Cost |
| --- | --- | --- |
| `$092` up to 310 (as `$049`) or 220 | restored (310: the two darkest greys one shade, as in candidate D; 220: three steps) | `$092` is 1-1's sidewalk seams and 2-2's dark detail: 2.1-2.3% of 1-1's playfield in area 0 (0.4% in area 1), 1.2%, 0.4% and 1.0% of 2-2's areas 0-2, 5.0-6.1% of 5-3's areas 0-3 change from near-black to mid brown. In 1-1 the seams all but vanish (looked at). 5-1's runes merge into the pillar with 310. |
| `$049` back to 100 | restored (one shade) | undoes the lift for the darkest grey: 4-1's trunks (8-21% of its playfield), 6-2 (6-18%), 4-3 (8-18%) near-black again |
| a second override stage in the upload | 1-1 and 2-2 kept, `$092` raised elsewhere | code: the override loops compare one colour in one stage; each further compare is 4 cycles a colour in that stage and changes HELL's timing there |
| leave it | reversed in at most 99 pixels of a screen | none |

### Shade order in SMS

Not asked for, found while tracing the fade-in's grey step, and larger than
HELL's. The dark rescue lifts four colours (`$040`, `$041`, `$048`, `$049`)
to SMS level 2 in each channel that holds 1; their neighbours with a
channel above 1 keep the channel rule, which drops green 1 to 0. So 70
pairs are inverted by 3 L* or more in the fade's order (one colour at least
the other's in every channel, shown darker): `$049` shows grey 222 (L*
30.6), `$04A` (R1 G1 B2) shows 002 (L* 4.2), `$051` (R2 G1 B1) 200 (L*
11.8), `$08A` (R1 G2 B2) 022 (L* 27.0). Before the dark lift there was
none. On the survey's captures (`hellorder.py --sms`): 6-2 area 0 has
`$049` on 12.7% of the playfield and `$04A` on 8.2% in one palette row,
touching in 4,279 pixel pairs; 4-1 `$049` 18.8% with `$08A` 12.2% (6,590);
5-1 `$041` with `$042`. So where Original shades from a dark grey up to a
blue-grey, SMS now shows the darker one clearly lighter, in still pictures
as well as for the fade steps. Whether that reads as wrong is the owner's
call; a fix is a palette decision (lift the neighbours with them, or lift
less), not an upload change.

### C. The evidence that had not run (on the fix build)

The fix build's tables are the dark-lift build's byte for byte, so these
measure the dark lift itself.

**Brightness** (`cap.py` through `mkjobs.py caps`, the survey's 33 captures
in each of the six modes; `measure.py` against the survey's captures of
`hell-1-1`). Cells: mean L* / % of the playfield below L* 10 / below L* 20
(/ distinct colours), the index reading, mean over a scene's captures.

| Scene | SMS before | SMS after | HELL before | HELL after | NES-A before | NES-A after | NES-B before | NES-B after |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 4-1 (5 frames) | 13.8/58/59/20 | 20.0/37/38/20 | 12.2/57/86/27 | 16.6/36/70/28 | 18.9/36/56/21 | 19.8/36/51/21 | 20.3/36/56/22 | 21.2/36/51/22 |
| 5-1 area 0 | 4.9/67/96/16 | 7.5/58/87/16 | 6.7/62/97/23 | 8.2/52/96/23 | 11.1/47/74/22 | the same | 29.7/27/34/22 | the same |
| 6-2 areas 0-4 | 10.7/58/78/17 | 14.1/47/67/17 | 10.6/55/81/20 | 15.0/44/58/21 | 16.3/37/69/18 | the same | 19.4/37/61/20 | the same |
| 6-2 area 0 | 3.8/82/92 | 9.1/64/75 | 6.5/73/87 | 10.2/56/73 | 10.0/47/88 | the same | 11.3/47/82 | the same |
| 6-4A | 4.9/70/95/22 | 4.9/70/95/22 | 7.4/67/87/31 | 7.4/67/87/32 | 9.5/60/78/23 | the same | 13.8/46/67/23 | the same |
| 6-4B | 5.1/69/95/17 | 5.1/69/95/19 | 7.7/66/87/27 | 7.7/66/87/28 | 9.9/58/77/18 | the same | 14.3/44/67/20 | the same |
| 6-4C | 16.0/38/63/19 | 16.7/36/60/19 | 20.7/13/34/22 | 20.7/13/34/22 | 23.2/13/51/18 | the same | 34.8/6/16/18 | the same |

4-1's back trunks against the fill behind them (L* of the trunk entry
`$03B` minus the fill's; pixel-weighted over the trunk and bark entries;
dE76):

| Mode | Before | After | Original mode |
| --- | --- | --- | --- |
| SMS | 0.0 / 2.0 / 0.0 (trunk and fill both black) | 30.6 / 24.6 / 30.6 (trunk `$092` on black) | 13.0 / 13.1 / 25.4 |
| HELL | 0.0 / 4.2 / 0.0 (both 100) | 21.9 / 18.0 / 41.1 (310 on 100) | |
| NES-A | 11.0 / 11.0 / 29.0 (`$040` on black) | 29.4 / 29.4 / 48.8 (`$090` on black) | |
| NES-B | 11.0 / 11.0 / 29.0 | 29.4 / 29.6 / 48.8 | |

**Against the study's predictions** (`build/dark-lift/numbers/`: "Sa",
"Hb", "Na"): every cell above and every trunk figure equals the predicted
one to the printed digit, in all four modes. Original and GB DMG measure
exactly as on `hell-1-1` in every scene. The rooms the lift was not for
stay dark: 6-4A and 6-4B measure the same in every mode (SMS 4.9 and 5.1
mean L*, 70% of the playfield below L* 10; one or two more distinct colours
in SMS and HELL), 5-1 area 0 in SMS rises from 4.9 to 7.5 and still has 58%
below L* 10.

**4-1's RAM palette in the NES modes** (`nescheck.py` on the five 4-1
captures of each mode): passed. 120 of the 128 set entries checked (8 are
written by the game or colour 0), every one the new set-8 colour, the VCE
equal to the RAM palette; the back trunks' ten entries hold `$080`, `$092`,
`$080` (NES-B `$090`), `$0A0`, `$090` twice over, all lighter than `$040`.

**Before and after, looked at** (`sheets.py`; private,
`build/dark-lift-fix/sheets/sheet-<mode>-{4-1,5-1-6-2,regress}.png`: the
`hell-1-1` build left, the fix build right; 4-1 frames 250, 1150, 1750, 5-1
area 0, 6-2 areas 0 and 2, 1-1 frame 600, 2-2 frame 400, 5-3 frame 3000).
Share of the picture that differs:

| Mode | 4-1 (three frames) | 5-1 area 0 | 6-2 area 0, area 2 | 1-1 | 2-2 | 5-3 |
| --- | --- | --- | --- | --- | --- | --- |
| SMS | 16.1%, 13.9%, 24.3% | 6.5% | 15.3%, 15.1% | 3.3% | 8.1% | 0.1% |
| HELL | 17.9%, 16.0%, 28.1% | 6.4% | 16.0%, 37.3% | 0.0% | 0.7% | 2.5% |
| NES-A | 7.6%, 5.0%, 2.6% | 0.0% | 0.0%, 0.0% | 0.0% | 0.0% | 0.0% |
| NES-B | 7.6%, 5.0%, 2.6% | 0.0% | 0.0%, 0.0% | 0.0% | 0.0% | 0.0% |

By eye:

- SMS: 4-1's far trunks, vines and ferns are there now (grey trunks, dark
  green leaves) where the screen was black; 5-1's floor reads as teal
  cobbles; 6-2's floor is a grey cobble floor and the statues stand out;
  6-2 area 2's left pillars and floor are grey. The lift is mostly this
  one grey (`$049` shown as 222). In 4-1 area 1 the rock wall's shadows are
  that grey too, lighter than the blues beside them, and the wall reads as
  speckled grey stone rather than blue rock (the reversal under
  [Shade order in SMS](#shade-order-in-sms)). **1-1 and 2-2 changed too**:
  1-1's brick in the awning's shade has a green hatch where it was black
  (3.3% of the picture), and 2-2's shadowed bridge wall is a lighter, flat
  olive with its mortar lines lifted (8.1%). The study gave 3.4% for each
  as a mean over three frames of the stage; they are the dark lift's, not
  this branch's.
- HELL: 4-1's trunks and ferns show brown on the dark red, the rock wall of
  area 1 is orange-brown with dark seams; 5-1's and 6-2's floors and
  statues are lighter; 6-2 area 2's pillars are golden brown with their
  reliefs visible where they were dark olive (the largest change, 37%).
  1-1 is identical in the frame compared; 2-2 differs in a few details near
  the fire bowl; 5-3 in girder details.
- NES-A and NES-B: only 4-1 changes; the back trunks are a textured brown
  where they were a flat dark green. Nothing else differs in any picture
  compared.

**The 22 Level Select entries** (`mkjobs.py starts`: `hell-1-1/stagestarts11.py`
120 frames in SMS and HELL, `all-palettes/stagecheck.py` 150 frames in
NES-A and NES-B):

- SMS: every entry is due for the new table from frame 14-16 after the
  first update to frame 119 (the mode's first full re-upload runs before
  that), as on the SMS build.
- HELL: every entry due from frame 4-5, 2-3 from 9 and 6-2 from 10 (the one
  frame more each that the `hell-1-1` record lists: the frame boundary
  inside that vblank's upload), with 1-1's override.
- NES-A and NES-B: `stagecheck passed` for all 22: no entry of a stage's set
  other than its NES colour (4-1 the new set 8), the same load length and
  gameplay as Original.

**NES colours on screen** (`nes-palette/onscreen.py` every 30 frames over
the 11 runs and every area of all 22 entries, 1,901 samples a mode, on the
`hell-1-1` build and the fix build): the same on both builds except 4-1.
Gameplay samples with an entry on screen that is not an NES colour: 4 in
NES-A and 5 in NES-B on both builds, the same ones (the leftover rows the
NES record lists: 4-3, 5-2 and 6-3 at frame 750 of their walks, 2-1 in
NES-B). Fade-step entries (a dimmed NES colour is not an NES colour): 1,559
against 1,561 in NES-A, 1,695 against 1,697 in NES-B; the two more are
4-1's entries 56 and 59 in one fade frame (frame 570 of its walk), where the
lighter trunks pass through `$049` and `$048` and the old colour was already
black. Cinemas: 494 in both.

### Delivered

For the owner's review, in `roms/` (new names; nothing there was changed):

| File | SHA-256 |
| --- | --- |
| `Ninja Ryukenden - Enhanced v1.11-dev (all palettes, dark lift 2).pce` | `1678b2e1b2eaabcb27ae8a23e51dd95d0f411c2e570a1bd3f2e224aa3541e2ae` |
| `ninja-ryukenden-enhanced-v1.11-dev-all-palettes-dark-lift-2.bps` (for the headered original) | `1791e6a5a181d6781b42ec18092dce04466e8bad5e11d428fb0d6ddc4f3599a4` |
| `ninja-ryukenden-enhanced-v1.11-dev-all-palettes-dark-lift-2-headerless.bps` | `fa9fce57cc655ed36a404e9aa8794191634a3d77e4d5c8d46f014d0fbbe00504` |

The ROM is the fix build (`scripts/project.py build` from either original
gives these bytes); the patches are the build's own (`--bps-output`), and
`scripts/bps.py apply` of each to its original gives the ROM again.

## Rerunning

From the repository root, `W=build/dark-lift-rom` holding `original.pce`,
`seed.state`, `dl.pce`, `h1.pce` and `rec/h1-*` (the `hell-1-1`
recordings), in the emulator environment of `run-check.sh` with
`GB_WORK=$W NES_WORK=$W NG_DEBUGGER_FAST=1`:

```sh
D=research/tools/dark-lift
python3 scripts/check_boot.py --emulator $E --original $W/original.pce --candidate $W/dl.pce --output $W/boot-dl
python3 scripts/check_menu.py --emulator $E --original $W/original.pce --candidate $W/dl.pce --output $W/menu
sh $D/recall.sh $W $W/dl.pce dl                       # 11 runs x 6 modes, 2 sessions
python3 research/tools/sms-palette/analyse.py $W/rec identity h1-orig dl-orig     # and gb
python3 $D/summary.py $W/rec h1 dl sms,hell,nesa,nesb
python3 $D/mkjobs.py fades $W $W/dl.pce $W/h1.pce > $W/jobs/fades.txt
python3 $D/runjobs.py $W/jobs/fades.txt 1 $W/jobs/log
python3 $D/fadereport.py $W/fades $W/shots/fades --min 0.5
```

## Not done (next steps)

None of these was started on the dark-lift build; all of them have since
been run on the fix build (the same tables), see
[C](#c-the-evidence-that-had-not-run-on-the-fix-build), with `$W` =
`build/dark-lift-fix`, `fix2.pce` for `dl.pce` and one session at a time.
`nescheck.py` on the survey's `hell-1-1` captures fails as it should (10
entries hold `$040`).

```sh
mkdir -p $W/starts $W/onscreen
for k in starts caps shots onscreen; do python3 $D/mkjobs.py $k $W $W/dl.pce $W/h1.pce > $W/jobs/$k.txt; done
python3 $D/runjobs.py $W/jobs/starts.txt 2 $W/jobs/log       # 22 Level Select entries: SMS, HELL due; NES-A, NES-B data
python3 $D/runjobs.py $W/jobs/caps.txt 2 $W/jobs/log         # the survey's captures, six modes
python3 $D/measure.py $W/cap build/dark-survey/cap --json $W/measure.json   # mean L*, % below 10 and 20, 4-1 trunk/fill
python3 $D/nescheck.py $W/cap $W/original.pce                # 4-1's RAM palette in NES-A and NES-B
python3 $D/runjobs.py $W/jobs/shots.txt 2 $W/jobs/log        # 1-1, 2-2, 5-3 on both builds
python3 $D/sheets.py $W/shots build/dark-survey/cap $W/cap $W/shots/old $W/shots/new
python3 $D/runjobs.py $W/jobs/onscreen.txt 2 $W/jobs/log     # NES colours on screen, both builds
```

- Brightness as the survey measured it, the screenshots, the 22 Level
  Select entries, the NES on-screen counts and 4-1's RAM palette in the NES
  modes: done, see C.
- The SMS flash and HELL's grey order: see
  [Dark lift 2](#dark-lift-2-the-flash-and-the-shade-order-branch-dark-lift-fix)
  (deaths, Continue and Game Over were still not looked at).
- Timing, stack and free-ROM probes were not rerun on the dark-lift build:
  no code changed, and Original and GB DMG are identical frame for frame.
  The fix build changes code; its stack use is unchanged by construction
  (no call or push added), which was not measured.

## Not covered

Real hardware; listening to the sound; cinemas, the title, the ending,
Continue and Game Over in the changed modes; the owner's review of the
colours.
