# Validation and limits

## 1.09 release validation

Release 1.09 is defined by `release/current.json`. A source build from either
original ROM format (`scripts/project.py build --verify-release`) and direct
application of either release patch reproduce its target SHA-256
(`f84a31a8…b912`).

**Emulator evidence** (headless Geargrafx; method and results in
[the background-fidelity review](validation/background-fidelity.md)):

| Check | Result |
| --- | --- |
| Backgrounds | Every Enhanced backdrop is generated from the original ROM's own art; every round of the 11 parallax entries opens exactly like the original |
| Gameplay | Stored button input for all 11 enhanced stages plays frame for frame identically on the original and on 1.09 (sprites, Ryu, timer, lives, health, camera, area) |
| Timing | Stage loads, respawns and area changes take the original's frame counts; force-scrolling every area at 2 px per update, no update takes longer than the original's |
| Cinemas | On 1.09, after a full play of each enhanced stage, the next cinema is identical frame for frame. The whole-game cinema audit ([CUTSCENE-AUDIT.md](CUTSCENE-AUDIT.md)) reached all 15 cinemas on 1.08-dev, which differs from 1.09 only in the menu code and the splash version |
| Start timing | Power-on to the first 1-1 update with Run pressed takes 163 frames in both games |
| Splash and boot | `scripts/check_notice.py` on the release bytes: splash pixels match the ROM data, it holds still for 300 frames, a press or held Run leaves it at once, the Hudson screen is unchanged, and the English title and the defaults (Enhanced, No Damage off, English) are reached |
| Level Select | Applying a stage refills health; **II** closes the menu with nothing changed (cases in the review) |

**Hardware reports** (from the maintainer; separate from the emulator
evidence above):

| Hardware | Build | Report |
| --- | --- | --- |
| NEC PC Engine Duo-RX with Krikzz Turbo EverDrive PRO | 1.09 release bytes (`f84a31a8…b912`) | Looks good; stages and settings not specified |
| NEC PC Engine Duo-RX with Krikzz Turbo EverDrive PRO | An earlier development build with the same cinema cleanup | Cinemas good; normal settings through 6-1, No Damage from 6-2 onward (completion of the ending not stated) |
| TurboGrafx-16 with Krikzz Turbo EverDrive and an EDFX RGB adapter | An earlier development build | Some play testing; build, stages and settings not specified |

CI does not emulate the game or establish hardware correctness. The checks
above need private ROMs and the headless emulator described in
[docs/pc-engine/EMULATOR.md](pc-engine/EMULATOR.md).

## Test a change

Choose checks that exercise the changed behavior, and record the exact ROM
hash, emulator/tool version and results. A renderer change should include:

- Opening view before movement, movement both ways, stops and map wrap.
- Foreground tile words/pixels, sprite data and palettes, not only background.
- Ordinary death, respawn then jumping, Continue, stage selection and native
  stage exits. Reproduce the user's exact sequence.
- Worst visible sky/background area and crowded encounters with real inputs.
- Emulated frame/scanline timing and IRQ-sensitive transfer lengths.
- Original mode compared with the original game at equivalent update points.
- A reserved-RAM guard and confirmation of restored registers/bank mappings.
- The comparison runs (`scripts/comparison_video.py make` and `cinema`): the
  stored input must still play identically on the original and the change.

Keep test modifications separate from the output ROM. For example, invulnerability,
camera forcing, temporary hooks, scripted health restoration or save-state
CRC edits must be declared in a report and absent from the released bytes.
Prefer real input replays for the final behavioral check.

The splash and boot handoff check compares a build with an earlier Enhanced
build that has the splash (here the 1.09-dev build):

```sh
python3 scripts/check_notice.py --emulator /path/to/geargrafx \
  --baseline "/path/to/earlier-enhanced.pce" \
  --candidate "dist/Ninja Ryukenden - Enhanced v1.09.pce" \
  --output captures/splash-1.09
```

## Outstanding

Complete hardware coverage of every damage/death/Continue path and every
room/transition is not claimed. Audio was not recorded or compared in the
emulator checks. The hardware reports have the scopes described above.
