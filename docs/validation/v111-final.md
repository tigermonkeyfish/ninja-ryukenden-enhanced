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

PENDING

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
