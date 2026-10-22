# Cinema audit

Enhanced borrows video memory for its backdrops. The native cinemas (the
story scenes between stages) assume their own VRAM contents, so every patch
that borrows VRAM must prove that each cinema still looks exactly like the
original's.

## Why: borrowed VRAM leaked into a story scene

During development a playthrough showed repeated graphics above Ryu's
portrait in the story after the second boss (the statue and girl dialogue),
with Enhanced on and No Damage off; the original did not. It needs a visit
to 2-2 before the boss: 2-2's enhanced atlas leaves data in VRAM words
`$7200–$72FF`, which native cinema sprites use as a blank 32×32 pattern,
`$0390`, without reloading it. Starting directly at the boss from stage 1
can miss the bug.

The fix keeps the native sprite reset and clears the borrowed pattern
immediately afterward, before cinema graphics load. The hook runs for every
native cinema, so it also covers later transitions and Original mode after
earlier Enhanced play. See [architecture](ARCHITECTURE.md) and
[LESSONS](pc-engine/LESSONS.md), "A gameplay atlas leaked into story sprites".

## Verification method

The audit uses Geargrafx commit
`78fc3d7a1b9f55d78d8fe64c13368131a269e204`, with a local headless-only pacing
patch (`NG_DEBUGGER_FAST=1`) that bypasses host audio pacing. No keyboard
experiment is applied. The emulator is an external dependency, not bundled
here; the patch is [preserved](pc-engine/emulator/geargrafx-headless-fast.patch).
Captures, ROMs and states remain private ignored files.

The reference starts from the original ROM at its first native cinema
initialization (`$8022`), with native English selected. The candidate starts
from the same saved machine state, changing only the state's cartridge CRC
to allow loading it with the candidate. This aligns CPU, RAM and video state;
it is a declared test intervention, not a cold-boot hardware playthrough.

Every gameplay stage initializes and renders for 120 frames, then the
debugger redirects the PC from `$8457` to the native completion path `$8478`.
Native progression selects the next scene. No in-game stage selector or
No Damage option is used. This exercises the history of background uploads
without claiming that enemies and bosses were fought normally.

Every rendered cinematic frame is captured. A JSONL file records its scene
and PNG hash; each distinct PNG is stored once. Run is pressed only to leave
the introductory attract loop and start the title screen. Story scripts,
dialogue, animations and transitions receive no skip input.

The comparator checks both exact frame sequences and ordered image changes
after collapsing repeated identical frames. The latter permits different
holds/fades without accepting reordered or missing images. An incomplete
capture fails validation. Matching means matching the original reference;
it does not assert that the original game has no rendering quirks.

## Reproduce locally

Build the candidate using [BUILDING.md](BUILDING.md), choosing a separate
development output. Supply a Geargrafx build with the headless MCP debugger:

```sh
python3 scripts/audit_cutscenes.py --emulator /path/to/geargrafx \
  --rom /path/to/original.pce --output captures/cinema-reference
python3 scripts/audit_cutscenes.py --emulator /path/to/geargrafx \
  --rom /path/to/candidate.pce --output captures/cinema-candidate \
  --seed captures/cinema-reference/boot.state
python3 scripts/compare_cutscenes.py \
  captures/cinema-reference captures/cinema-candidate \
  --output build/cinema-comparison.json
python3 scripts/check_cinema_entry.py --emulator /path/to/geargrafx \
  --original /path/to/original.pce --candidate /path/to/candidate.pce \
  --seed captures/cinema-reference/boot.state --output build/cinema-entry-check
```

The state trailer check is specific to this emulator format. A changed
format requires revisiting that check, not disabling it. The native title
fingerprint is also specific to this English reference and renderer.

## Results and limits

**Entry contract.** A direct entry-contract test, deliberately
seeding the borrowed pattern with nonzero bytes, confirmed that only those
512 VRAM bytes differ after cleanup. A, X, Y, P, SP and all MPRs match the
native reset. RAM differences are confined to seven inactive stack bytes
(`$21F5–$21FB`); the reserved low-stack margin is unchanged. The VDC selector
is restored; the write address advances to `$7300` as expected.

**Whole-game audit.** On 1.08-dev (which differs from 1.09 only in the menu
code and the splash version), all **15 native cinema IDs (0–14)** were
reached through **THE END**. Scene 0 (intro) matches image for image with
different holds (Enhanced's boot path). Scene 6 differs in one frame: an
8-pixel run on the bottom display line shows the scene's own sky colour one
frame longer while the cinema draws its picture (frame 9; frame 10 matches).
No foreign graphics appear. The story scene after 2-2 (ID 4) matches the
original for all 9,593 frames.

**After full play.** The audit renders each stage for only 120 frames, so
`scripts/comparison_video.py cinema` also checks the cinema after a full play
of each enhanced stage. On 1.09 the cinemas after all 11 runs (ten scenes) are identical frame for
frame, including scene 6 after 4-1, so the audit's one-frame difference
depends on its shortened path, not on leftover Enhanced data. See
[the review](validation/background-fidelity.md), "Smoothed comparison runs".

**Hardware.** The maintainer played an earlier development build with the
same cinema cleanup on an NEC PC Engine Duo-RX with a Krikzz Turbo EverDrive
PRO and confirmed the cinemas ("The cut scene is good"): normal settings
through 6-1, then No Damage from 6-2 onward.

The audit and these reports do not establish every damage/death/Continue
path, Japanese/Chinese story behavior or audio correctness.
