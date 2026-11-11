# v111-final: saved settings with dark lift 2 (1.11-dev)

Emulator evidence only (Geargrafx `78fc3d7`, headless; the lock-modelling
emulator is the private build of
[bram-save.md](bram-save.md#branch-v111-merge-with-dark-lift-results-so-far-2026-11-11)).
Nothing here was seen on a console. 2026-11-11.

## What was merged

Branch `v111-final` = `v111` (`77a153f`: saved settings, `src/bram`,
`src/options`, the harness; with the dark-lift tables) + `dark-lift-fix`
(`f367289`: the same tables and the fade-out upload fix in
`src/palette/main.asm`, commit `b045238`). Both descend from `dark-lift`
(`2ad5815`). The merge conflicted in two documents and in no source file:
`docs/ARCHITECTURE.md` (bank `$46` map: the saved settings' ranges from
`v111`, the palette code's 926 bytes from `dark-lift-fix`) and
`docs/pc-engine/LESSONS.md` (both sides' new sections kept).

Build: SHA-256
`f3114ade8b9b198db7baf6afa5253551a4eacf6458b9fdb0833957ac2738a0a0`
(1,048,576 bytes), the same bytes from the headered and the headerless
original (`build/v111-final/final.pce`). 54 unit tests
(`python3 -m unittest discover -s tests`) and `scripts/audit_public.py`
pass.

## The build is the union of its parents

`research/tools/v111-final/unionproof.py BASE A B MERGED` with the
`dark-lift` build (`build/dark-lift-rom/dl.pce`, `23871f8f…39d7`) as the
base, `build/v111/v111.pce` (`7fc60a09…a0ae`) and
`build/dark-lift-fix/fix2.pce` (`1678b2e1…e2ae`) as the parents
(`build/v111-final/unionproof.txt`). All six statements hold:

- the bytes `v111` changed (A, 2,340) and the bytes the fix changed
  (B, 1,885) do not overlap;
- the merged build differs from `v111.pce` in exactly the bytes of B and
  holds `fix2.pce`'s bytes there;
- it differs from `fix2.pce` in exactly the bytes of A and holds
  `v111.pce`'s bytes there;
- everywhere else it equals the base (and so both parents).

Ranges (file offsets of the headerless image; listed with gaps under 16
bytes joined; module by `src/modules.json`):

| Set | Offsets | Bank and address | Bytes differing | Module |
| --- | --- | --- | --- | --- |
| A: merged against `fix2.pce` (= base against `v111.pce`) | `001FE6-001FF5` | `$00` `$FFE6-$FFF5` (reset trampoline) | 16 | bram |
| | `08C432`, `08C45A-08C465`, `08C49E`, `08C4CD-08C4E0` | `$46` `$4432-$44E0` | 1, 3, 1, 4 | options |
| | `08C502-08C8C2`, `08C8D3-08C92A`, `08C93B-08C951`, `08C971-08CAD4` | `$46` `$4502-$4AD4` | 932, 52, 22, 352 | options |
| | `08CB00-08CEC1` | `$46` `$4B00-$4EC1` | 957 | bram |
| B: merged against `v111.pce` (= base against `fix2.pce`) | `0770F3`, `077177-07739D` | `$3B` `$50F3`, `$5177-$539D` | 1, 517 | palette |
| | `08787A-087BEC` | `$43` `$587A-$5BEC` | 849 | palette |
| | `08D0F3`, `08D177-08D39D` | `$46` `$50F3`, `$5177-$539D` | 1, 517 | palette |

A is 973 bytes of `bram` and 1,367 of `options`; B is 1,885 bytes of
`palette`: the mapped upload in bank `$46` (GB DMG), its SMS copy in bank
`$3B` and HELL's code in bank `$43`.

**What carries over.** Each parent's record was made on a build that
differs from this one only in the other parent's bytes, so:

- everything in [dark-lift.md](dark-lift.md) ("fix build") about the
  palette code and tables carries over as long as backup RAM is absent and
  the menu is not used: with backup RAM absent the `v111` code was shown to
  leave the stored runs identical to the `dark-lift` build in every field
  of every frame (Original, GB DMG, SMS, HELL; `bram-save.md`), and the two
  stored runs repeated below are identical to the fix build's;
- everything in [bram-save.md](bram-save.md) ("Branch `v111`") about the
  file format, the image matrix, cut saves, the lock, the System Card and
  the boot carries over as far as it does not depend on the frames after a
  stage-end fade-out, the only frames the fix changes.

**What does not carry over** (interactions; the checks below are for
these): a mapped mode that came from backup RAM at reset instead of a
debugger write or the menu, with the fix's fade-out path; the menu's Run
(a save, interrupts off) and its window with the changed upload code; the
boot's timing with both changes. Not run here and so inherited only by the
argument above: the full image matrix (210 images, three models), the cut
saves, the System Card run, the many-files boots, `check_menu.py`'s runs,
sweep and Level Select parts, the NES modes, GB DMG and Original stored
runs on this exact build.

## Interaction checks on the merged build

`W=build/v111-final` (`original.pce`, `seed.state` and `fix2.pce` copied
from the parents' folders), `E` the pinned emulator, `L` =
`build/v111/locktest/geargrafx/platforms/linux/geargrafx`
(`2c12a540…c134`), `R=build/toolchain/run-check.sh`; one emulator session
at a time.

- `check_boot.py`, backup RAM absent
  (`$R scripts/check_boot.py --emulator $E --original $W/original.pce --candidate $W/final.pce --output $W/boot-absent`):
  frames 1-899 identical to the original, 136 distinct screens, first 1-1
  update at frame 163, defaults. **Pass.**
- `check_bram.py --only cycle` on the pinned emulator (baseline
  `fix2.pce`; `$W/cycle`): 16 of 16 power-cycle steps pass; the log equals
  `v111`'s line for line. **Pass.**
- `check_bram.py --only lock --bram-model lock` on `L` (`$W/lock-neg-lock`):
  the emulator applies the model; 12 of 12 negative controls as predicted
  (no unlock, `$48 $75 $00`: no backup RAM seen, nothing lands; `$80` only:
  works; lock read removed: works and the probe reports the bank open);
  the log equals `v111`'s. **Pass.**
- `check_bram.py --only cycle --bram-model lock` on `L` (`$W/cycle-lock`):
  16 of 16, the bank locked after every boot and Run; the log equals
  `v111`'s. **Pass.**
- `check_menu.py --only options` (`$W/menu-options`): all 36 cases pass;
  the log equals `v111`'s line for line. **Pass.**

- Stored runs, backup RAM absent, mode by the probes' debugger write
  (`MODES="sms:0xb8 hell:0x18" JOBS=1 sh research/tools/dark-lift/recall.sh $W $W/final.pce vf`,
  then `analyse.py $W/rec identity fx-sms vf-sms` and `fx-hell vf-hell`
  against the fix build's recordings copied from
  `build/dark-lift-fix/rec`): all 11 runs in SMS and all 11 in HELL
  (35,084 frames a mode; more than the one run a mode asked for, since a
  run takes seconds) are identical to the fix build's in every field of
  every frame: picture, VCE, sprite table, RAM, gameplay
  (`$W/identity-sms.txt`, `identity-hell.txt`). The seven stage ends with a
  load and the three with a cinema are among them. **Pass.**
- **A mode that came from backup RAM**
  (`research/tools/v111-final/savedboot.py $W/final.pce $W/saved saved-MODE OPTIONS 6-1`,
  one session each for `original 0x00`, `sms 0xb8`, `hell 0x18`; then
  `transreport.py $W/saved saved --modes sms,hell --all`): the machine is
  powered on with backup RAM holding the game's own file with that mode;
  controller input alone takes it through the title into 1-1; `$2100` is
  the saved mode, the status `OK` and backup RAM unchanged (asserted; no
  debugger write to `$2100` anywhere in the session). The 6-1 run is then
  entered as the stored-run probes enter a stage (the Level Select's
  debugger writes) and replayed to its end, the load of 6-2
  (1,793 frames, stage 17 at the end, `$2100` and backup RAM still as
  booted). Original's playfield is black in frames 1725-1758:

  | Saved mode | Late (frames until the playfield is black) | Flash | VCE entries lit at the load's lock | Gameplay against the saved-Original boot |
  | --- | --- | --- | --- | --- |
  | SMS | 3 (0.15% and 0.12% of the playfield, the fade-out's last step; 1-3 a run on the fix build) | none | 0 | equal in every frame |
  | HELL | 0 (its HUD band two frames more, as on the fix build) | none | 0 | equal in every frame |

  From frame 1728 (SMS) and 1727 (HELL) to the end of the span no VCE
  entry that is behind its due colour holds anything but black, and the
  playfield and the HUD band are black: six and seven frames before the
  stage changes at 1734 and the load takes the lock at 1735. Against the fix build's seed-state recordings of
  the same run (`fx-sms-6-1`, `fx-hell-6-1`, `fx-orig-6-1`) the pictures are
  the same in every frame except the first 15 (SMS) and 5 (HELL) of the
  run, and in all of them for Original. Those first frames are the probes'
  stage entry, not the game: it jumps into the stage from inside 1-1
  without a fade, and the upload then catches up from whatever the VCE held,
  which is 1-1 in the saved mode here and 1-1 in Original's colours in the
  seed-state probes (they write `$2100` after the boot). **Pass.** Limits:
  one run (a stage end with a load), the stage entered by debugger writes,
  the pinned emulator (backup RAM always unlocked); the lock-modelling
  emulator was not used for a played run.

## The transition survey the fix record left open

[dark-lift.md](dark-lift.md#not-verified-on-the-fix-build) lists 14 job
lines of the per-frame transition survey (`trans.py`) that the host stopped
on the fix build. They were run here, on `fix2.pce` as listed (the palette
code and tables of this build: see the union proof), one session at a time,
with the recordings in `build/v111-final/trans` beside copies of the fix
worker's (`build/v111-final/jobs/trans-rest-ordered.txt`; all 14 finished).
The 18 recordings that the fix worker already had and that these lines
made again are byte-identical to his.

`transreport.py $W/trans old,new` (`old` = the dark-lift build, `new` = the
fix build; `$W/trans-report.txt`, `trans-report.json`), 22 walks and 11
runs a mode, 37 spans in which Original's playfield is black:

| Fix build | Spans with a flash | Stage-end spans (11 walks, 7 runs) with VCE entries lit at the load's lock | Longest late arrival (frames) |
| --- | --- | --- | --- |
| SMS | 0 (7 spans, 62 frames on the dark-lift build) | 0 of 18 (18 of 18 before, 42-91 entries) | 9 (26 before) |
| HELL | 0 (0 before) | 0 of 18 (18 of 18 before, 43-49 entries) | 8 (9 before) |
| GB DMG | 0 (7 spans, 62 frames before) | 0 of 18 (18 of 18 before, 9-24 entries) | 9 (26 before) |

The four stage changes the fix record names as not recorded:

| Stage change | Mode | Dark-lift build | Fix build |
| --- | --- | --- | --- |
| 2-1 to 2-2 | SMS | black 13 frames late, flash 2 frames (1.4% of the playfield), 50 entries lit at the lock | 9 frames late (Original's dark area is black before the last step), no flash, 0 lit |
| 4-3 to 4-4 | SMS | 5 late, flash 16 frames (10.8%), 80 lit | 1 late, no flash, 0 lit |
| 5-1 to 5-2 | SMS | 22 late, flash 3 frames (0.08%), 74 lit | 1 late, no flash, 0 lit |
| 6-2 to 6-3 | HELL | 7 late, no flash, 46 lit | 1 late, no flash, 0 lit |

Unchanged by the fix, in all three modes, as its record says: the four
spans that are not fade-outs still reach the lock with entries lit (the
cut after the boss in 3-3 and 4-4, 130-162 entries; the area change in 5-2
and 5-3, 183-209), without a flash. Gameplay against Original differs on
the fix build only in the three forced-scroll walks the record lists (2-1
frame 363, 6-2 frame 544, 5-2 seven single frames), as on the dark-lift
build; the one-frame difference before each cinema is gone in all three
modes. GB DMG's 5-3 run, the one run missing there, is among the
recordings now (no flash, nothing lit).

With this the fix build's transition survey is complete for SMS, HELL and
GB DMG. Still not run in any mode: deaths, Continue and Game Over.

## Rerunning

From the repository root, `W=build/v111-final` holding `original.pce`,
`seed.state`, `final.pce`, `fix2.pce`, `rec/fx-*` and `trans/*` (copies
from `build/dark-lift-fix`), in the emulator environment of `run-check.sh`
with `GB_WORK=$W NES_WORK=$W NG_DEBUGGER_FAST=1`; `B=build`:

```sh
D=research/tools/dark-lift; S=research/tools/sms-palette; V=research/tools/v111-final
python3 -m unittest discover -s tests; python3 scripts/audit_public.py
python3 scripts/project.py build --rom ORIGINAL --output $W/final.pce --assembler pceas --bps-output patch.bps
python3 scripts/bps.py apply ORIGINAL patch.bps check.pce      # check.pce is final.pce
python3 $V/unionproof.py $B/dark-lift-rom/dl.pce $B/v111/v111.pce $B/dark-lift-fix/fix2.pce $W/final.pce
python3 scripts/check_boot.py --emulator $E --original $W/original.pce --candidate $W/final.pce --output $W/boot-absent
python3 scripts/check_bram.py --emulator $E --candidate $W/final.pce --baseline $W/fix2.pce --output $W/cycle --only cycle
python3 scripts/check_bram.py --emulator $L --candidate $W/final.pce --baseline $W/fix2.pce --output $W/lock-neg-lock --only lock --bram-model lock
python3 scripts/check_bram.py --emulator $L --candidate $W/final.pce --baseline $W/fix2.pce --output $W/cycle-lock --only cycle --bram-model lock
python3 scripts/check_menu.py --emulator $E --original $W/original.pce --candidate $W/final.pce --output $W/menu-options --only options
MODES="sms:0xb8 hell:0x18" JOBS=1 sh $D/recall.sh $W $W/final.pce vf
python3 $S/analyse.py $W/rec identity fx-sms vf-sms            # and fx-hell vf-hell
python3 $V/savedboot.py $W/final.pce $W/saved saved-original 0x00 6-1   # and saved-sms 0xb8, saved-hell 0x18
python3 $D/transreport.py $W/saved saved --modes sms,hell --all
python3 $D/runjobs.py $W/jobs/trans-rest-ordered.txt 1 $W/jobs/log      # the 14 lines, on fix2.pce
python3 $D/transreport.py $W/trans old,new --json $W/trans-report.json
```

## Not covered

Real hardware (the saved settings have not been seen on any console; the
checklist is
[bram-save-hardware-checklist.md](bram-save-hardware-checklist.md)); the
checks named under "What does not carry over" that were not repeated on
this build; a played run on the lock-modelling emulator; a mode loaded
from backup RAM in any run but 6-1, and in GB DMG and the NES modes;
deaths, Continue and Game Over in the mapped modes; sound.

## Delivered

In `/workspace/roms/` (new names; nothing there was changed):

| File | SHA-256 |
| --- | --- |
| `Ninja Ryukenden - Enhanced v1.11-dev (all palettes, dark lift 2, settings save).pce` | `f3114ade8b9b198db7baf6afa5253551a4eacf6458b9fdb0833957ac2738a0a0` |
| `ninja-ryukenden-enhanced-v1.11-dev-all-palettes-dark-lift-2-settings-save.bps` (for the headered original) | `f50c5d5459972df8aeaae5e91f224b602eceeeed75299d15dda743c5a129f220` |
| `ninja-ryukenden-enhanced-v1.11-dev-all-palettes-dark-lift-2-settings-save-headerless.bps` | `d9bab345b80d08e0233df63d9a72a8996aafc6cbbaa94abcf05cf71ae2e81608` |

The patches are the build's own (`scripts/project.py build --bps-output`,
one build from each original); `scripts/bps.py apply` of each to its
original gives the ROM again.
