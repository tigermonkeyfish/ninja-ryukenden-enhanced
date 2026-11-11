# Palette modes: SMS (1.11-dev)

Emulator evidence (headless Geargrafx `78fc3d7` with the headless-fast patch,
binary SHA-256 `2de50e51…`, [EMULATOR.md](../pc-engine/EMULATOR.md)), not a
hardware report; audio not compared. Design:
[architecture, palette modes](../ARCHITECTURE.md#palette-modes).

| Build | SHA-256 | Source |
| --- | --- | --- |
| Before (`hell-palette`) | `42328ceefc1e85f661d4b03d2ec78036fdef1e1ffa213490aded7bea8cc8d7fe` | commit `ad42e5a` (rebuilt here: the same bytes as its record) |
| SMS | `444ff70bee588d24253e16f9b06a38bc472cafc55b2c0246ff8afd1867f987ef` | branch `sms-palette`, commit `5193462` and later documentation and probe commits (the same bytes from the headered and the headerless original) |

Method: one start state, a cold boot of the original saved at the 1-1
main-loop hook; every replay is a fresh session that loads it, writes
`$2100`/`$2101` (0 Original, `$10` GB DMG, `$18` HELL, `$B8` SMS: mode
`$38` with bit 7), enters the stage as Level Select does and steps one frame
at a time. Probes: [`research/tools/sms-palette/`](../../research/tools/sms-palette)
(`record.py`, `analyse.py`, `unittest_upload.py`, `stagestarts.py`,
`upload_cost.py`, `guard.py`, `ramwatch.py`, `freewatch.py`, `shots.py`,
`runmany.py`: the HELL probes for the new layout, plus SMS colour checks)
and, unchanged, `timing_trace.py`, `split.py`, `updates.py` and
`entry_timing.py` in [`research/tools/gb-palette/`](../../research/tools/gb-palette)
(with `GB_WORK` set to the work folder). Lines are counted after the VDC
vblank interrupt, 1365 master clocks each.

## The mode and its encoding

`src/palette/sms.json` holds the owner's chosen mock-up, candidate A: each
3-bit channel goes to the nearest of the Master System's levels 0, 85, 170,
255 in linear terms (channel c stands for c x 255 / 7) and is shown as PC
Engine 0, 2, 5, 7; so 0-1 → 0, 2-3 → 2, 4-5 → 5, 6-7 → 7.
`scripts/palette_tables.py` generates the table; the ROM-free tests pin it to
the mock-up's `table-A.json` (SHA-256 of the 512 words `bb0779db…d927`),
check it channel by channel against that rule, and check that every output
is one of the 64 SMS colours, that all 64 occur and that each maps to
itself. It applies to every VCE entry and the border, as GB DMG.

`$2100` (all settings now):

| Bits | Meaning |
| --- | --- |
| 0-2 | Original background, No Damage, NES Firewheel (unchanged) |
| 3-5 | Palette mode: `$00` Original, `$08` NES-A, `$28` NES-B, `$10` GB DMG, `$18` HELL, `$38` SMS; `$20` (uploads as Original) and `$30` (as GB DMG) unassigned |
| 6 | unassigned (zero) |
| 7 | set exactly when bits 3-5 are SMS (`$B8`) |

The palette module's state (left-over entry, busy history, mapped colours
in the VCE) moved from `$2100` bits 5-7 to `$2104` bits 5-7. Why this
scheme:

- Eight mode values with room to spare: six are spoken for (Original, NES-A,
  NES-B, GB DMG, HELL, SMS). Bits 3-4 keep their meaning as the upload
  family, so every existing test of them stays valid: the NES loader hooks'
  `and #$18 / cmp #$08` accept NES-A and NES-B alike, and "which NES" is
  bit 5.
- The upload must tell SMS from HELL without a cycle on the Original, GB DMG
  or HELL paths (a first build that tested bit 5 in HELL's path cost HELL 13
  cycles and changed HELL's stored runs; see (a)). Bit 7, a copy, lets the
  dispatch's own `and`/`cmp` do it: masked with `$98`, SMS gives `$98 - $10`
  (N set), HELL `$18 - $10` (N clear), so family 11 needs only a `bmi`, and
  its 2 cycles are paid inside HELL's own paths.
- The state had to leave `$2100` to free bit 5 (and bit 7); `$2104` is the
  byte above the options at the bottom of the stack page, where the native
  stack never reaches (below), and the module reads and writes it with the
  same absolute instructions, so no path changes length. `$2100` now holds
  only settings: the planned backup-RAM save stores `$2100` as it is (bit 7
  included; it must not store `$2104`, which is zero at reset and rebuilt by
  the module).
- The menu's draft keeps `$2100`'s bits 0-5 in its bits 0-5 (the language
  moves to draft bits 6-7), so Run is still a masked copy; `set_palette`
  writes bit 7 with the mode.

## What changed in the ROM

Against the `hell-palette` build only these bytes differ (bank and MPR2/MPR3
view; all were `$FF` before unless named):

| Region | Bytes used | What |
| --- | --- | --- |
| Bank `$46` `$5000-$53FF` (file `$8D000`) | 905 of 1,024 (was 1,023) | palette code: state in `$2104`, the `$98` dispatch, HELL's family-11 entry, SMS `bmi`s; `fold_queue` moved out |
| Bank `$46` `$5A00-$5AFF` (file `$8DA00`) | 163 | `fold_queue`, `vblank_sms`, `now_sms`, HELL's palette_now cinema exit |
| Bank `$3B` `$5000-$53FF` (file `$77000`) | 905 | the SMS copy of bank `$46` `$5000-$53FF`, byte for byte |
| Bank `$3B` `$5400-$57FF` | 1,024 | the SMS table |
| Bank `$3B` `$5A00-$5AFF` (file `$77A00`) | 163 | the copy of bank `$46` `$5A00-$5AFF` |
| Bank `$43` `$7800-$7BFF` (file `$87800`) | 842 (was 848) | HELL code: state in `$2104`, the `$2240` test moved to bank `$46`, one `sec` fewer, the cinema exit |
| Bank `$46` `$4400-$4AFF` | 1,567 (was 1,547) | the menu: PALETTE mask `$38`, value SMS, bit 7, language in draft bits 6-7 |

No fixed-bank bytes (`$FECF-$FEDF` and `$FFEE-$FFF5` still free), nothing in
bank `$45`, bank `$37`, bank 3, or bank `$46` `$4100-$42FF`/`$4B00-$4FFF`.
RAM: `$2104` (below).

## a. Original, GB DMG and HELL unchanged

All 11 stored runs (35,084 frames) recorded on the SMS build in Original,
GB DMG and HELL mode (`record.py`) and compared with the `hell-palette`
build's recordings from its own record (`analyse.py identity`): every
frame's screenshot, VCE, sprite table, game RAM (outside
`comparison_video.OWNED`, the music driver's workspace included) and
gameplay fields identical, in all three modes, in every run. `analyse.py
state`: in every frame the old build's `$2100` equals the new build's
`$2100 | $2104` (the module's state moved, nothing else), and the new
`$2100` never has bits 5-7 set in these modes.

A first build (`720b57e`, not delivered) tested the SMS/HELL variant inside
HELL's path, 13 cycles more per HELL vblank and palette_now: Original and GB
DMG were identical as above, but HELL differed from the old build in every
run (RAM in 146-583 frames, the music driver's state; the VCE in 1-2 fade
frames per run; the picture in one frame of 2-2 and of 5-3; gameplay fields
identical). That is why `$2100` bit 7 exists and HELL's paths were brought
back to their exact cycle counts (`5193462`); the identity above is that
build's.

`scripts/check_boot.py`: passed (idle frames 1-899 identical to the
original, 136 distinct screens, first 1-1 update at frame 163 when mashing
Run, defaults English, Enhanced, damage on).

## b. SMS colours

- In-place unit test of the upload against an independent Python model
  (`unittest_upload.py`: every mode, `$2100` values `$00 $08 $10 $18 $20
  $28 $30 $38 $98 $B8` and others with random low bits, `$2104` states,
  cinema state, palette_now, HELL's split and raw-chunk costs, the
  left-over, busy and full-queue rules): 458 cases (seed 22) and 518 (seed
  31), 0 failures; MPR2 (SMS switches it), MPR3, S, X, Y, the lock, zero
  page `$20-$26` and `$2100` as before. Negative controls: the model
  expecting GB DMG's colours in SMS, 99 of 458 fail; HELL's raw set-up cost
  one lower, 38 of 458 fail.
- All 11 runs in SMS (`record.py`, `analyse.py sms` and `due`): in every
  gameplay frame (`$2240` = 0; 34,904 frames) every VCE word is one of the
  64 SMS colours and every pixel of the screenshot has only the channel
  values the emulator shows for PC Engine levels 0, 2, 5 and 7 (0, 72, 182,
  255 of 0, 36, 72, 109, 145, 182, 218, 255), fade frames included. The
  first 60 frames of the cinemas after 4-1, 5-3 and 6-3 (180 frames) are in
  the original colours, as in GB DMG and HELL (cinemas, the title and the
  ending keep the native upload). Every VCE entry equals the SMS table
  value of its RAM colour (entry 256 the border colour's) except while
  uploads are still queued; the longest a single entry lags is 46 frames
  (3-1, the end-of-stage fade); 44-45 in the fades of 1-1, 2-2, 3-2, 5-2,
  6-1, 42 in 4-2, 28-30 in 5-3 and 6-3, 19 in 4-1, 14 in 5-4: GB DMG's
  figures (its longest is also 46 frames, 3-1). The original's own lag in
  the same runs is up to 13.
- All 22 Level Select entries (`stagestarts.py`, 120 frames): every entry is
  due from frame 14-16 after the first update to frame 119, and no VCE word
  outside the 64 appears in any of those frames (the mode's first full
  re-upload is still running in frames 0-13, 16 colours a vblank once left
  over; the entries not yet re-uploaded hold black).

## c. Timing in SMS

- Updates: stage timer, Ryu, camera, area and sprite table identical to
  Original mode in every frame of all 11 runs (`analyse.py due`, and
  `updates.py` on the timing traces). `$2240` turns to 1 one frame later at
  the cinema after 4-1, 5-3 and 6-3 (frames 2487, 6768, 5122), the same
  frames as in GB DMG and HELL mode (the full re-upload when a cinema
  begins). No frame is added or dropped.
- Vblank upload end (`timing_trace.py`): worst 18.24 lines over the 11 runs
  (GB DMG 18.19, Original 16.57); over the 22 stage loads 19.72
  (`entry_timing.py`; Original 16.58); none after line 22 (the display
  starts about 22.8 lines after the interrupt). So the upload does not end
  on the same line as Original's (a mapped colour costs about 156 master
  clocks against the native 42); it stays within the budget GB DMG
  established. 2-2's write at line 59.1 is the renderer's palette_now in
  the main loop (52.9 in Original, 59.1 in GB DMG).
- HUD split (scanline-interrupt CPU entry, `split.py`): past the cut-off
  (70.84) in the same frames as Original mode (1-1, 5-3 and 6-3 one each);
  2-2 none (Original one), as in GB DMG and HELL. In normal frames the
  largest shift against Original is +0.58 line, the maximum 70.40. 1-1 frame
  2844 (a load frame already past the cut-off in Original, 73.94) enters at
  78.03 in SMS and in GB DMG alike.
- Stage loads from Level Select after the mode has settled
  (`entry_timing.py`, 60 frames after): the same number of vblanks as
  Original in all 22 entries; 4-3's split entry is past the cut-off in both
  (74.73 / 74.54).
- Cost (`upload_cost.py`, synthetic queues at the 1-1 hook): every case ends
  0.055 line (75 master clocks, 25 CPU cycles) after GB DMG's, with the same
  writes and the same left-overs: GB DMG's code plus the family-11 dispatch
  (`bne` and `bcs` taken, `bmi` taken, `jmp`, `lda #`, `tam`, `jmp`). A full
  512-colour queue ends at 18.20 lines in SMS, 18.15 in GB DMG.

## d. Switching

Through the popup with controller input (`scripts/check_menu.py --only
options` part of the full run, from 1-1, every case a fresh session; the
PALETTE values in Left/Right order are ORIGINAL, GB_DMG, HELL, SMS):

- SMS chosen with Right three times or with Left (ORIGINAL wraps to SMS) and
  Run: `$2100` = `$B8` after the restart, `$2104` bit 7 set, and the VCE is
  exactly the SMS table applied to the whole RAM palette with the border at
  entry `$100`; GB DMG with Right (`$10`) and HELL with Right twice (`$18`)
  likewise their tables.
- Paths accepted with Run, each step checked: GB DMG then ORIGINAL; HELL
  then ORIGINAL; SMS then ORIGINAL; SMS, HELL, GB DMG, ORIGINAL; GB DMG,
  HELL, SMS, ORIGINAL; SMS straight to GB DMG and back to ORIGINAL; GB DMG
  straight to SMS and back to ORIGINAL. Every mapped mode on the way shows
  exactly its table (GB DMG after SMS and SMS after GB DMG included: the
  same code, another table, which needs the menu's full re-queue), and each
  path ends with the same VCE as a run that never left Original, with
  `$2100` = 0 and `$2104` bit 7 clear.
- Cancel after changing every row (Select), compared frame by frame for 900
  frames with the same state run without the menu (every picture, VRAM,
  sprite table and palette at each frame's end, RAM at the update
  boundary): from Original with GB DMG, HELL and SMS previewed; from GB DMG
  with HELL previewed; from HELL with SMS previewed; from SMS with ORIGINAL
  previewed; from SMS with GB DMG previewed. All exact, no frame with a
  different picture. Only upload scratch differs (`$2205-$220B`,
  `$2261-$2271`, `$2284-$2285`), as in the HELL and popup-menu records.
- The live preview: Left on the PALETTE row from Original gives `$2100` =
  `$B8` while the window is open and SMS colours behind it (screenshot
  `1-1-f600-preview-sms.png`).

## e. Space, stack, free-ROM and free-RAM audit

| Region | Use | Free |
| --- | --- | --- |
| Bank `$46` `$5000-$53FF` (file `$8D000`) | palette code, 905 bytes | `$5389-$53FF` (119) |
| Bank `$46` `$5400-$57FF` | GB DMG table | |
| Bank `$46` `$5900-$59FF` | speed, 143 bytes (claim shrunk from `$5900-$5FFF`) | `$598F-$59FF` (113) |
| Bank `$46` `$5A00-$5AFF` (file `$8DA00`) | `fold_queue`, SMS stubs, HELL cinema exit, 163 bytes | `$5AA3-$5AFF` (93) |
| Bank `$46` `$5B00-$5FFF` | unowned | 1,280 |
| Bank `$3B` `$5000-$57FF`, `$5A00-$5AFF` (file `$77000-$777FF`, `$77A00-$77AFF`) | the SMS copy (905 + 163 bytes) and the SMS table (1 KiB) | bank `$3B` `$41CF-$4FFF`, `$5800-$59FF` and `$5B00-$5FFF` stay `$FF` and unowned |
| Bank `$43` `$7800-$7BFF` | HELL code, 842 bytes | `$7B4A-$7BFF` (182) |
| Bank `$46` `$4400-$4AFF` | the menu, 1,567 bytes | `$4A1F-$4AFF` (225) |
| Fixed bank | nothing added | `$FECF-$FEDF` (17), `$FFEE-$FFF5` (8) |
| Bank `$46` | untouched, reserved | `$4100-$42FF`, `$4B00-$4FFF` |
| Bank `$45`, bank `$37`, bank 3 | untouched | |

`src/modules.json`: speed claims `$8D900-$8D9FF` (was to `$8DFFF`); the
palette module claims `$8DA00-$8DAFF`, `$77000-$777FF` and `$77A00-$77AFF`
in addition. `.if/.fail` guards: speed's code before `$5A00`; the palette
code before `$5400`; the `$5A00` code within 256 bytes; the HELL code before
its table; the SMS table before `$5800` and at the GB DMG table's
addresses; one guard per mirrored label that the copy's address equals the
original's (68 labels; a copy with one byte inserted fails to assemble,
tried), and the built ROM's copy compared byte for byte with bank `$46`.

Why that ROM is free: bank `$3B`'s data ends at `$761CE` in the original;
the rest is `$FF` and no module claims it. Speed's module is fixed code that
ends at `$598E`. Read/execute watches over file offsets `$77000-$777FF`,
`$77A00-$77AFF` and `$8DA00-$8DAFF` on the old build (`freewatch.py`): 0
stops over a cold boot to 600 updates of 1-1 (683 frames) and all 11 runs
(35,084 frames). Positive control: the same watch over bank `$3B` on the
SMS build in SMS mode stops in the first frame of 1-1 at `$5A99` with MPR2 =
`$3B` (the copy running). (A watch stops the replay at its first hit; only
the first stops are meaningful.)

Why `$2104` is free: the reset's RAM clear (`$E023`, a TII over
`$2000-$3FFF`) zeroes it; a read/write watch on CPU `$2104` on the old build
(`ramwatch.py`) saw only that clear over a cold boot to 600 updates of 1-1
(the byte 0 at the end) and nothing over all 11 runs; positive control: on
the SMS build the same watch stops at once in the palette code (`$5046`).
Every stack guard since 1.10 filled from `$2104` upward with a sentinel and
found the deepest use far above it (below). The watched stack margin is now
`$2105-$213F`; `guard.py` and `check_menu.py` fill from `$2105` on this
build (a first `check_menu.py` run filled `$2104` too and so changed the
upload's state under the menu: 7 false failures in the 1-1 time-out death
window, gone with the fill from `$2105`).

Stack (`guard.py`, 2-2 with the menu opened four times and a full palette
re-queue forced while it was open): low-water mark `$21D2` in SMS and in GB
DMG, `$21C6` in HELL, `$21D3` in Original, as in the HELL record; 134 bytes
above the margin's top `$2140` at the deepest.

## f. Screenshots

Private (`build/sms-palette/shots/`, `shots.py`; replays of the stored runs,
SMS and Original at the same frame): 1-1 frame 600, 2-2 frames 400, 1200,
2400 (areas 0-2), 3-1 600, 4-1 600 and 2100 (areas 0 and 2), 5-2 900, 5-3
3000, 5-4 300 and 700 (the boss fight with Malth), the popup open in SMS
(1-1, 2-2, 5-3; the PALETTE row reads `SMS`, within its 8-cell field), the
live preview from Original after Left on the PALETTE row (`$2100` = `$B8`
during it). Also the 120th frame of 1-1, 2-2, 3-1, 4-1, 5-2 and 5-3 from
Level Select (`build/sms-palette/shots-start/`).

Compared with the mock-up: candidate A's sheets (`contact-A.png`,
`compare-2-2.png`) were made by applying the per-channel quantisation to
captured frames. `mockcompare.py` does exactly that to each Original
screenshot above and compares the result with the SMS screenshot of the
same frame: 0 differing pixels in all 11 pairs (61,952 pixels each). By eye
the pictures match the sheets area by area: the 2-2 sky in cyan, white and
pink bands, white clouds, purple mountains; 4-1's blue rock; 5-2's tan
walls; the 5-3/5-4 castle in navy.

## Checks

- `scripts/check_boot.py`: passed (above).
- `scripts/check_menu.py` (all parts, music as played; the stack fill from
  `$2105`): `runs` 140 openings in the 11 runs, all exact, stack low-water
  `$21D3`; `select` all 22 Level Select entries and Run on the next, passed,
  the LANGUAGE row reads ENGLISH after a cold boot; `options` 23 cases
  (above), passed. `sweep` reports 8 of 727 openings with video state
  differing for 1-3 frames before an area change (2-2 Select at 784-788 and
  3943, 5-3 at 5290 and 6189), so the script's overall verdict is FAILED,
  as on the `hell-palette` build: all 19 sweep windows (1-1 time-out death,
  5-4 idle death, the 17 area changes of 1-1, 2-2, 5-3, 6-3) give exactly
  the `hell-palette` record's counts of exact, refused, unseen and failed
  openings, case for case (the same five at 2-2 789, one at 2-2 3945, one
  at 5-3 5294, one at 5-3 6193). Not investigated here (see the HELL
  record).

- ROM-free: `python3 -m unittest discover -s tests` (36 tests) and
  `scripts/audit_public.py` pass.

## Merging with nes-palette-2

The NES branch adds palette data loaded into the RAM palette by loader hooks
and uploads it as Original; nothing in it reads `$2100` bits 5-7. To merge:

- `src/options/menu.txt`: the PALETTE line becomes
  `@ $38 $00=ORIGINAL $08=NES-A $28=NES-B $10=GB_DMG $18=HELL $38=SMS`
  (NES-B once its data exists; `NES-A` and `NES-B` fit the 8-cell field).
  Take this branch's comment block (bits 3-5, bit 7).
- `src/options/main.asm`: the NES branch's `preview_palette` keeps the live
  mode while NES is highlighted (`cmp #PALETTE_NES` after `and
  #PALETTE_BITS`). With `PALETTE_BITS = $38` that compare must test the
  family, `and #$18 / cmp #$08`, so NES-A and NES-B both keep the opening
  mode; the value it falls back to (`OPENED_OPTIONS,x`, `$2100` as pushed
  at open) must be masked with `$38` and go through `set_palette` (which
  writes bit 7 for SMS and queues the colours), as this branch's
  `preview_palette` already does.
- `src/nes-palette/main.asm`, `src/stage11`, `src/stage22`: their `lda $2100
  / and #$18 / cmp #$08` tests need no change; they hold for NES-A and NES-B.
  NES-B's own data choice tests bit 5 (`lda $2100 / and #$20`, or `bit #$20`
  with A holding `$2100`); NES-A is bit 5 clear.
- `src/palette/main.asm`: the NES branch changed only comments; take this
  branch's code (the dispatch masks `$98`; families 00 and 01 go to the
  native upload whatever bit 5 says).
- `src/modules.json`: no overlap (NES: bank `$45` `$4000-$43FF` and
  `$5200-$5FFF`, bank `$37` `$7C30-$7FFF`, bank 3 `$CE98` and
  `$D400-$D9FF`, bank 0 and 1 hooks; SMS: bank `$3B`, bank `$46`
  `$5A00-$5AFF`, speed's claim shrunk). `stage61-upload`'s range is changed
  by the NES branch only.
- After merging: add NES-A and NES-B to `check_menu.py`'s options part (the
  values in menu order change the Left/Right presses of its cases), and
  repeat (a) for Original, GB DMG and HELL and (b) for SMS, since the NES
  hooks run in every mode.

## Rerunning

From the repository root, with `GB_WORK=/workspace/build/sms-palette`
holding `original.pce`, `seed.state` (the HELL record's), `base.pce` (the
`hell-palette` build) and `sms.pce`, and the emulator environment of
`run-check.sh` (Geargrafx and SDL paths):

```sh
S=research/tools/sms-palette; G=research/tools/gb-palette; W=$GB_WORK
python3 $S/runmany.py $W/rec/log new-sms 3 all record.py $W/sms.pce {run} $W/rec/new-sms-{run}.json 0xb8
#   and new-orig 0, new-gb 0x10, new-hell 0x18; old-* from base.pce (or the HELL record's rec/)
python3 $S/analyse.py $W/rec identity old-hell new-hell        # and orig, gb; 'state' likewise
python3 $S/analyse.py $W/rec sms new-sms new-orig
python3 $S/analyse.py $W/rec due new-sms new-orig
python3 $S/runmany.py $W/tt/log sms 2 all timing_trace.py $W/sms.pce {run} $W/tt/sms-{run}.json 0xb8   # and orig 0, gb 0x10
python3 $G/split.py $W/tt orig sms; python3 $G/updates.py $W/tt sms $W/tt orig
python3 $G/entry_timing.py $W/sms.pce 0xb8 60 0,1,...,21 $W/entry-sms.json 30   # and 0
python3 $S/stagestarts.py $W/sms.pce 0xb8 120 all
python3 $S/unittest_upload.py $W/sms.pce 60 22     # MODEL_SMS_TABLE=gb or MODEL_RAW_SETUP=2: controls
python3 $S/upload_cost.py $W/sms.pce 0xb8          # and 0x10
python3 $S/runmany.py $W/fw fw 3 boot,1-1,... freewatch.py $W/base.pce {run} 0x77000 0x777ff 0x77a00 0x77aff 0x8da00 0x8daff
python3 $S/runmany.py $W/rw rw 3 all ramwatch.py $W/base.pce {run} 2104 2104   # and ramwatch.py ... boot
python3 $S/guard.py $W/sms.pce 2-2 0xb8 300,900,1500,2100
python3 $S/shots.py $W/sms.pce $W/shots 1-1:600:menu:preview 2-2:400:menu ... 5-4:700
python3 $S/mockcompare.py $W/shots
python3 scripts/check_boot.py --emulator ... --original $W/original.pce --candidate $W/sms.pce --output ...
python3 scripts/check_menu.py --emulator ... --original $W/original.pce --candidate $W/sms.pce --output ...
```

## Not covered

Real hardware; audio; whole cinemas, the title and the ending in SMS mode
(they stay in the original colours by design; only the first 60 frames of
the cinemas after 4-1, 5-3 and 6-3 are in the runs); Continue and Game Over
screens; boss rooms other than the 5-4 run's. The NES-A/NES-B encoding is
prepared but untested with the NES data (that branch is not merged here).
