# A repeatable ROM investigation workflow

Case studies for each step are in [LESSONS.md](LESSONS.md); hardware and
toolchain facts in [HARDWARE.md](HARDWARE.md); the emulator harness in
[EMULATOR.md](EMULATOR.md).

## 1. Establish identity and a baseline

Record the supplied ROM's size, header convention and SHA-256. Keep it
immutable. Record emulator/tool versions and hardware separately. Start with
an unmodified game run and a minimal input sequence that reproduces the issue.

Use a new output name, hash and version for every candidate given to a
tester, and show the version on screen (Ninja's notice splash prints it), so
a report always names the bytes it is about. Never overwrite a differing copy
under the same name, and never infer the running revision from an emulator
window title or a renamed file.

Agree the fidelity policy before building. This project's is: original art
only; unavoidable seams are listed with images for the maintainer's review;
new art only after per-item approval, documented with its reason. That policy
is what forced the decoder, the original-only loops and the exact round
starts below.

## 2. Observe before choosing the patch

Capture the visible frame and the corresponding tile map, referenced graphics,
palettes, sprites, camera state and update timing. Track which routines write
the scrolling registers, map words or tile patterns. Determine whether the
effect is implemented by raster scrolling, map rewrites, pattern animation,
sprites or a combination.

Measure how the native effect actually moves before improving it. Ninja's
backdrops turned out to be screen-locked (only an 8 px jitter that depends on
travel history), so the original has no designed continuation and no art
outside one screen; adding parallax means building a continuation from the
original's own columns. Compare overscan columns with earlier ones: they can
reveal the artist's repeat.

Generate patch data from the original ROM. When bytes cannot be found
verbatim, start from where they land (VRAM, the RAM palette buffer), set a
write breakpoint and follow the call stack to the decompressor; model it and
validate it against every use. Data copied from a capture or an earlier patch
cannot be told apart from edited data.

## 3. Map ownership and lifetimes

Before calling a RAM byte "free," inspect its behavior at cold boot, normal
play, death, respawn, Continue, stage/subarea transition and menus. Distinguish
temporary scratch from geometry or state retained for a later rebuild.
Evidence for a free range is a sentinel fill plus a read/write watchpoint that
stays silent over all of those paths; see HARDWARE.md, "RAM and option
design" (also: make zero mean the default).

Record CPU-visible addresses together with bank mappings and ROM offsets.
The same CPU address can refer to different physical banks. Audit original
code/data before treating an apparently blank ROM region as unreferenced.
For VRAM, prefer borrowing from a layer you replace whose next owner always
reloads it, and audit BAT references, sprite pattern ranges, mid-area
rewrites and every later consumer (restarts, transitions, cinemas).

## 4. State a falsifiable hypothesis

Write the symptom, candidate cause, predicted observation, smallest experiment
and pass/fail condition. Keep hypotheses separate from results. Examples:

- If a seam comes from a bad texture repeat, it should recur at a predictable
  texture coordinate even when the camera crosses a different screen edge.
- If corruption is caused by retained geometry being overwritten, a clean
  cold boot can pass while a death/reload fails with changed geometry bytes.
- If slowdown is due to renderer load, an equivalent input replay should show
  increased emulated update cost, not just different host FPS.

State a limit as what the current pipeline lacks and what would remove it
("not in our inputs yet", not "cannot be recovered"), and measure a
documented claim before repeating it.

## 5. Implement within a measured budget

Preserve registers, flags, bank mappings, the game's VDC register-select
shadow and borrowed scratch across hooks. Keep native initialization paths
intact where possible, and insert added screens in front of native sequences
rather than editing them. Add one feature or fix at a time and isolate its
changed ROM ranges. Expand the ROM before scavenging free space inside the
original (HARDWARE.md, "CPU and memory map"); guard every hand-placed region
with an assembler `.fail` check; make the build refuse a base ROM other than
the one the hooks were written against.

A routine's total cost is only one constraint. Interrupt latency, transfer
chunk size and the scanline where work completes also matter: a scanline
interrupt's register write is delayed by the longest uninterruptible stretch
running when it fires (two adjacent block transfers count as one). Measure
the actual build in every area, at a speed above the player's, against the
original; then profile the late updates themselves. Do not turn a favorable
early-stage measurement into a universal claim about later scenes.

## 6. Compare equivalent states

Use a frame-exact replay harness: both games start from one saved state, each
recording runs in a fresh emulator session, every frame step is checked, and
a mismatch is recorded again before it counts (EMULATOR.md). Align
comparisons to gameplay update boundaries, not arbitrary wall time. Capture
the camera value consumed by rendering; a later camera sample can be one
update ahead. Compare both what should change and what should not:

- Intended background pixels, including palette index zero/transparency.
- Foreground map words, referenced tiles and palette ownership.
- Sprite patterns, attributes and palettes.
- Movement, health, progression and other relevant game RAM, against a
  declared list of excluded bytes.
- Frame/update cost, scanline deadlines and reserved-memory guards.
- Load length in frames (stage entry, respawn, every area change) and the
  time of any raster-split register write, against the original.

Decide equality on VRAM, palette and sprite-table state. Screenshot
differences can be pure timing; when screenshots are needed, mask sprites
from the current and previous frame and accept a difference only if one
offset explains all of it. A vision-model judge is a sanity check on composed
images, never acceptance evidence. Make the search objective of any
generator identical to the acceptance test.

Document test interventions such as forced camera movement, health writes or
temporary ROM hooks, keep each one opt-in per tool and named in its output,
and finish with ordinary controller input wherever practical.

## 7. Exercise lifecycle and extremes

Test the entrance while standing still, maximum exposed background, crowded
encounters, reversals, wrap boundaries, deaths, respawn plus jumping, Continue,
stage selection and native exits. A bug can require a particular history of
stage jumps rather than the destination stage alone. Treat every background
rebuild as a load: stage entry, respawn, area change and menu return.

Reach deaths through a native path (here a stage timer set to its last
ticks), and compare each path with the original on the same path, not with a
fresh entry. A test trick that fails on the build must be tried on the
unmodified game. If the patch adds a boot screen, measure power-on to first
control and title Start to control against the original.

Use emulator evidence to narrow causes and real-hardware feedback to confirm
behavior on the target. Label each separately. An emulator input/UI problem
can be independent of a ROM problem; test those hypotheses independently.

## 8. Package the evidence with the result

Publish the patch, original/target hashes, source/build boundary, controls,
tested scope and open questions. Build the final release bytes before the
hardware test and produce every piece of evidence (videos, cinema check,
hardware test) from those exact bytes; any change after review, however
small, gets a new version. If both header conventions are in circulation,
publish a patch for each with identical output.

Tell testers to start each candidate from reset: emulator save states from an
earlier build mix old RAM and VRAM with new code. Record each hardware report
with console, cartridge or flash cart, build hash and the scope tested.

Prove what a build reads: a Python audit hook on `open` events
(`sys.addaudithook`) lists every input file a build actually used. Keep a
publication audit that rejects game-derived binaries by default, with a short
allowlist (here a few script-made guide screenshots, each generated from the
emulator with the game state it claims asserted first).

Preserve the experiment that failed as a short case study; preserve large raw
traces locally with an indexed location. Do not require future contributors
to rediscover the project's invariants from a conversation transcript.

## Long experiments and agent shells

- Keep checkpoints of multi-hour searches on persistent disk, written after
  every accepted step, with each pass's output beside the run. `/tmp` is
  often RAM-backed: a power cut here lost hours of smoothing work and the
  slowdown probes. Delete superseded states as you go, and move a probe into
  the repository as soon as it works.
- Never kill processes by a pattern that also matches your own command line
  (`pkill -f`, `ps | grep | xargs kill` killed the agent's own shell twice).
  List the PIDs in one command and kill them by number in the next.
- Keep one project per session. Reference shared toolchains (emulator,
  assembler) by environment variable rather than by mixing projects' context.
