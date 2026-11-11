# Dark lift: SMS, HELL and the NES modes' 4-1 (1.11-dev)

Emulator evidence (headless Geargrafx `78fc3d7` with the headless-fast patch,
binary SHA-256 `2de50e51…`, [EMULATOR.md](../pc-engine/EMULATOR.md)); no real
hardware, audio not listened to. Design:
[architecture, palette modes](../ARCHITECTURE.md#palette-modes).

**This record is incomplete.** The session that made it was wound down
before the brightness measurements, the screenshots, the Level Select
entries and the NES on-screen counts were started; they are listed under
[Not done](#not-done-next-steps) with their commands. What is below was run
to the end.

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

None of these was started; the probes are written, and only `measure.py`
and `nescheck.py` were tried (on the survey's `hell-1-1` captures, where
`nescheck.py` fails as it should: 10 entries hold `$040`).

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

- **Brightness as the survey measured it** (mean L*, % of the playfield
  below L* 10 and 20, 4-1 trunk/fill separation; 4-1's five frames, 5-1
  area 0, 6-2 areas 0-4, the 6-4 rooms; six modes) and the comparison with
  the study's predicted numbers (`build/dark-lift/numbers/`).
- **Screenshots** `hell-1-1` against the candidate (4-1 three points, 5-1
  area 0, 6-2 two areas, 1-1, 2-2, 5-3; SMS, HELL, NES-A, NES-B). Nobody has
  looked at the candidate's stages yet, only at the fade strips.
- **The 22 Level Select entries** in SMS, HELL, NES-A and NES-B beyond what
  `check_menu.py` covers (it enters all 22 and checks the modes' colours in
  1-1).
- **NES on-screen counts** against `hell-1-1` (fade frames, leftover rows),
  and 4-1's RAM palette in the NES modes.
- The SMS flash: how many transitions show it (every stage and area change,
  deaths, Continue), and whether to close it in the upload (finish the
  left-over entry before a load locks the palette, a code change) or by
  leaving `$049` / `$041` black.
- HELL's grey order (`$049` lighter than `$092`): look at the stages that
  use both, and decide whether `$092` should rise with it.
- Timing, stack and free-ROM probes were not rerun: no code changed, and
  Original and GB DMG are identical frame for frame.

## Not covered

Real hardware; listening to the sound; cinemas, the title, the ending,
Continue and Game Over in the changed modes; the owner's review of the
colours.
