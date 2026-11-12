# Saved settings: no memory, full memory, write error (fall-back tests)

Check: `scripts/check_bram_fallback.py`. Emulator evidence only (pinned
headless Geargrafx and the test-only BRAM-modelling build of
`research/tools/bram-save/locktest_patch.py`); nothing here was seen on
hardware. Build tested: SHA-256
`cec5f7b3d1fddc224ad8da921b20e6b0eec55295d59f001a714c209a33bb8059`
(`v111-reset` at `bd7ab94`, "reset 2"); script commit see the branch
`bram-fallback-tests`.

The claim tested: when the settings cannot be loaded or saved, the player's
settings chosen in the popup are still used in the game, and the game plays
exactly as it does when the save works.

## Method (every scenario)

1. Cold boot, mash Run to the first 1-1 update. Asserted: backup RAM present
   or not as the scenario says, status `$2105`, `$2100`/`$3227`, first update
   within 400 frames (the baseline's is 163), popup status line text.
2. Open the popup (Select) and set NON-default settings from wherever the
   draft stands: Smooth Parallax OFF, No Damage ON, NES Firewheel ON, palette
   SMS, language Japanese ($2100 = `$BF`, $3227 = 0), then Run.
3. Asserted after Run: the scenario's save status; `$2100`/`$3227` equal the
   choice; the same stage restarted at full health (16), camera 0, within 300
   frames; the VCE equals the SMS table (`check_menu.mode_expected`) and the
   control's VCE.
4. Replay the stored run `research/comparison-runs/1-1.json` (2,843 frames,
   47 s of game time, one fresh session per scenario) frame by frame. Per
   frame: work RAM, VCE, sprite table, VRAM and the screenshot are hashed and
   compared with the CONTROL with the same settings. Ryu must move and act
   (camera advance of at least 700, at least 4 distinct Ryu states). With No
   Damage on, health stays 16 and lives stay unchanged in every frame.
5. Backup RAM byte for byte after the scenario equals what the model says
   (unchanged for full, read-only and open bus).
6. Power cycle (new session, the memory left behind): the status and
   settings that load are asserted.

The stored run was recorded for a different start; in these sessions it
walks and jumps through 1-1's first screens (camera 0 to 1,116), takes
hits, and then stalls at one place, where Ryu is hit repeatedly and dies once
(default settings: health reaches 0, a life is lost). That is useful: it
exercises damage, death and restart; the No Damage assertion is meaningful
because the same input hurts Ryu with default settings.

Comparison tolerance (stated honestly): the save routine runs at a different
length per scenario, which moves the instant at which a frame ends by a few
cycles against the game's own scratch writes. VRAM, VCE, sprite table and
screenshot are identical in every frame. Work RAM is identical in every frame
except for isolated frames in which the stack page (below the stack pointer
the save's leftovers are dead bytes and ignored; live bytes and SP compared
apart) or a few scratch bytes are caught mid-update: at most 5% of the
frames, never more than 6 in a row, at most 8 offsets in all, and the final
frame must be equal. Measured in the final run: 0 frames (control-old,
write-error, write-error-old), 63 (no memory, open bus; stack page only) and
92 (full memory; offsets `$2084`, `$38BD`, `$3942`). The status byte `$2105`
is excluded by design.

## Scenarios

| Scenario | How it is produced | Why faithful | Limits |
| --- | --- | --- | --- |
| control | pinned emulator, blank formatted memory (`empty-8800`) | an unused Duo-style memory | none |
| no-memory | pinned emulator, `power_on(rom)` without BRAM; bank `$F7` reads `$FF` and ignores writes | a console/cart with no backup RAM | the real mapper behaviour of an EverDrive/MiSTer without a save file is not modelled |
| no-memory-bus | `NG_BRAM_MODEL=openbus`: the bank reads the address's high byte (no device) | an unconnected bank, which the writable test must reject | only one of several possible open-bus patterns |
| full-memory | formatted image filled with other games' entries (`full`) so ours (24+2 bytes) does not fit, ours absent | what the System Card's own saves produce | file layout from `bram_image`, validated against the System Card's reader in `bram-save.md` |
| write-error | `NG_BRAM_MODEL=readonly` on the blank formatted image: reads work, writes never land; the save does not read back, ERROR 4 | a RAM whose write line is stuck or locked | models ignored writes only; no partial or corrupted writes, no write that lands wrongly |
| write-error-old | as write-error on an image holding an earlier save (HELL, No Damage, Chinese) | the old settings load, new ones are chosen, the save fails | as above |
| control-old | pinned, the same earlier-save image; Run saves | control of write-error-old | |

Expected results (all asserted): control READY then OK, power cycle loads the
saved `$BF`/Japanese; no-memory and open bus NONE before and after, defaults
after a power cycle; full FULL before and after, defaults after a power
cycle; write-error READY then ERROR 4, memory unchanged, defaults after a
power cycle; write-error-old LOADED (`$1A`, Chinese) then ERROR 4, memory
unchanged, and after a power cycle the OLD settings load again (the new ones
are used only until power-off, which is the intended behaviour).

## Result (final run, `check_bram_fallback.py`, about 12 minutes)

| Scenario | Result | RAM-transient frames of 2,843 |
| --- | --- | --- |
| control | PASS | 0 |
| no-memory | PASS | 63 |
| no-memory-bus | PASS | 63 |
| full-memory | PASS | 92 |
| write-error | PASS | 0 |
| control-old | PASS | 0 |
| write-error-old | PASS | 0 |

In all: camera 0 to 1,116, health 16 throughout, lives 2, backup RAM bytes
changed 0 for full, open bus and both read-only runs.

## Negative controls (all 18 required to bite; all did)

- Each scenario's expectations against the control's observations, and the
  control's expectations against each scenario's observations (this includes
  the FULL checks against a non-full image and the reverse): the boot status,
  popup line, run status and boot settings assertions flag it.
- Default settings instead of the player's: `$2100`, `$3227`, the VCE, the
  SMS palette check, the saved memory and the frame comparison all flag it;
  in this run health falls to 0 (the hits happen).
- The No Damage assertion on a default-settings game: flagged (health 0).
- A frozen game (no input): "Ryu did not move" (camera 0, 1 state) and the
  frame comparison flag it.
- One wrong screenshot hash in an otherwise good trace: flagged. A run of
  seven consecutive RAM differences: flagged. One backup RAM byte changed:
  flagged.
- Information: Japanese versus English language alone does not change any
  hashed field in 1-1 (language only shows in the cutscene and menu text), so
  the language is asserted through `$3227` in every frame, not through
  pictures.

## Not proven

Real hardware (Duo, TG-16 with CD, Turbo EverDrive Pro, MiSTer): how the real
memory fails, lock behaviour with real cartridges, partial or corrupt
writes, and electrical timing. The open-bus and read-only models are the two
failure shapes the emulator build can be made to show. Only one stage (1-1)
and one input run are replayed. Emulator timing is cycle-approximate; the
RAM-transient tolerance above is an observed property, not a proof of cycle
equality.

## Rerun

```sh
W=/workspace/build/bram-fallback
python3 scripts/project.py build --rom ORIGINAL --output $W/cand.pce --assembler pceas
/workspace/build/toolchain/run-check.sh scripts/check_bram_fallback.py \
  --emulator /workspace/build/toolchain/geargrafx/platforms/linux/geargrafx \
  --model-emulator /workspace/build/v111/locktest/geargrafx/platforms/linux/geargrafx \
  --candidate $W/cand.pce --output $W/final
```
