# Headless emulator harness

Every emulator measurement in this project came from Geargrafx driven as a
headless debugger server. This page is enough to rebuild that setup for
another PC Engine game.

## Build

Geargrafx commit `78fc3d7a1b9f55d78d8fe64c13368131a269e204` with one local
change, [geargrafx-headless-fast.patch](emulator/geargrafx-headless-fast.patch)
(GPL-3.0 like Geargrafx itself; licence text beside it). With
`NG_DEBUGGER_FAST=1` the headless loop skips host audio pacing and polls the
debugger every 1 ms instead of every frame. Emulation (CPU and video cycles,
the frames a step runs) is unchanged; only wall-clock speed is. Never use
wall-clock speed as evidence of game performance.

```sh
git clone https://github.com/drhelius/Geargrafx.git
cd Geargrafx
git checkout --detach 78fc3d7a1b9f55d78d8fe64c13368131a269e204
git apply /path/to/docs/pc-engine/emulator/geargrafx-headless-fast.patch
make -j4 -C platforms/linux        # needs pkg-config, SDL3 and OpenGL dev files
```

Run it as a JSON-RPC/MCP server over standard input and output:

```sh
SDL_AUDIODRIVER=dummy NG_DEBUGGER_FAST=1 ./geargrafx --headless --mcp-stdio --portable
```

[`scripts/emulator_session.py`](../../scripts/emulator_session.py) starts it
and handles requests, timeouts and cleanup; `Game` in
[`scripts/comparison_video.py`](../../scripts/comparison_video.py) adds frame
stepping, memory and register access, breakpoints, screenshots and saved
states. The debugger offers execution, memory and VDC-register breakpoints,
a CPU trace log with clock counts, VRAM/VCE/SAT reads and PNG screenshots.
After an emulator update, save the server's `tools/list` reply and re-check
the reference below against it.

## Rules that made the evidence reliable

Each is a case study in [LESSONS.md](LESSONS.md).

- **Start every comparison from one saved state.** Boot paths leave counters
  that stage entry does not reset; load the same state into both ROMs
  (retarget the cartridge CRC in the state for the second ROM, below).
- **One fresh session per replay.** A session that cold-booted the game, or
  already entered a stage, can run two game updates in its first frame step.
  Make the start state in a session of its own.
- **Normalize after a breakpoint stop:** save and reload the state, so the
  next frame step has a defined length.
- **Check every step:** require the reported executed frames, and add a
  tripwire on a counter whose first step is known.
- **Find a real frame clock before timing anything.** A game's frame counter
  may stop during loads; the save state's master-clock counter does not.
  One frame is 358,995 master clocks when the VCE runs 263 lines (Ninja), not
  21.477 MHz / 60 ([HARDWARE.md](HARDWARE.md)).
- **Release the pad on every state load.** A state does not carry the
  debugger's held buttons. Store the held set with each state, release
  everything after loading and press the stored set again. End every scripted
  move with all buttons released: most games act on new presses, so a button
  held across moves never presses again.
- **Make every test intervention opt-in per tool** and name it in the tool's
  output. A camera NOP that a background sweep needed stopped real input from
  scrolling when the same harness drove a route bot.
- **Declare what equality excludes.** Whole-RAM comparisons need a reviewed
  list of excluded bytes with a reason each (the patch's own bytes, boot-path
  counters, sound-driver workspace that differs for single frames); report
  their differences separately. The interface has no audio capture, so state
  "audio not compared".
- **When a result depends on an emulator timing edge, read that edge in the
  emulator's source, then bisect it with a delay stub**, and record the margin
  as emulator evidence. See LESSONS, "Block transfers held the playfield split
  a line late".
- **Repeat a mismatch before believing it**, and keep emulator evidence
  separate from hardware reports.

## Debugger reference (Geargrafx `78fc3d7`)

Memory areas (`read_memory`/`write_memory` `area`; `list_memory_areas` gives
the current list):

| Area | Contents | Offsets |
| --- | --- | --- |
| 0 | System RAM, 8 KiB | Offset 0 is CPU `$2000`: zero page `$00` is 0, Ninja's `$2241` is `0x241`. Not `0x2000`. |
| 1 | Zero page | 256 bytes |
| 3 | ROM | Headerless file offset. Writes change only the emulator's loaded copy (useful for test stubs and harness NOPs; lost on reload). |
| 4 | VRAM | Offset in 16-bit words (32K words); `size` in bytes, so advance the offset by size/2 when paging |
| 6 | SAT | 256 words, same units as VRAM |
| 8 | VCE palette | 512 words, same units |
| 14, 15 | Logical (64 KiB as currently mapped), physical (2 MiB) | |

Breakpoints:

- `memory_area: 'rom'` takes a ROM file offset: bank × `$2000` + (address &
  `$1FFF`). Ninja's main-loop hook, CPU `$83F3` in bank 1, is `'23f3'`. This
  is unambiguous; a CPU address (`'cpu_addr'`, the default) matches whatever
  bank is mapped there.
- `cpu_addr` read/write ranges (`set_breakpoint_range`) serve as watchpoints.
  `vram` write breakpoints find the code that writes a tile (the way to a
  decompressor); `huc6270_reg` breaks on VDC register access.
- A breakpoint hit during `debug_step_frame` ends the step with an error
  containing "interrupted"; a completed step reports `frames_executed`.
- `debug_run_to_cursor` (and `debug_continue`) return before the CPU arrives.
  Poll `debug_get_status` until `paused` is true and `pc` is the address
  expected.

Limits found the hard way: `load_media` needs an absolute path; a step count
must be at least 1; trace memory sizes are `100K`, `500K`, `1M`, `2M` or `5M`
entries; `get_trace_log` returns at most 1000 lines per call.

Screens and timing:

- `get_screenshot` is 256×242 for a 256-pixel mode. The game decides which
  lines are visible: Ninja's 224 lines are rows 18-241 (the videos crop
  `crop=256:224:0:18`), and the capture analysis placed BAT row r at
  screenshot y = 8r + 50 (Ninja's HUD split and vertical scroll included). Derive these from the game's VDC
  display registers (VSR, VDW, BYR) and check them on a known tile; do not
  reuse Ninja's numbers.
- At a CPU breakpoint, a screenshot shows the last completed frame, not the
  state at the breakpoint. Screenshots taken at update boundaries can show
  the previous camera.
- Save-state layout: byte 0 is a CD-ROM flag; bytes 1-8 are a little-endian
  u64 of **master clocks** since power-on (`m_master_clock_cycles`, 21.477 MHz;
  three per CPU cycle at high speed). To read emulated time, save a state and
  read that field. The state ends with a 200-byte header whose little-endian
  u32 at `len(state) - 48` is the cartridge CRC32, computed over the ROM
  without a copier header. To load a state into a different ROM, write that
  ROM's headerless CRC32 there. The layout is build-specific: re-check it after
  any emulator update, and refuse an unrecognised state rather than guess.
- Trace lines read `@clock +delta BB:PPPP ...`: the absolute master clock, the
  master clocks since the previous retained entry (`RESET` if the clock went
  back; nothing for the oldest entry), then bank and PC. Sequence numbers are
  not in the line; they come from the call's `start`/`next_sequence` fields.

## Driving the game from the debugger

- **Call a native routine with a synthetic JSR.** At an idle point (Ninja's
  main-loop hook `$83F3`) save X, Y, P and S; write the routine's inputs; put
  the return address minus one on the stack page (low byte at `$2100 + S - 1`,
  high at `$2100 + S`), set S to S − 2, load A and set PC to the routine
  (Ninja's stage initialization `$8244` with A = stage). Run back to the hook,
  restore X, Y and P. The same debugger writes drive both ROMs identically,
  with no test code in either.
- **Redirect PC to a native path** instead of synthesising its result: Ninja's
  forward area transition (`$8490`) and stage completion (`$8478`, from the
  gameplay loop at `$8457`) reach every area and every cinema quickly. A
  shortcut can differ from full play on a transition frame; confirm a
  difference with a full play before reporting it.
- **Force scrolling through the game's own camera routine.** The background
  sweeps call the native scroll routine (`$E341`, with the delta in `$220E`)
  at each gameplay update and hold Ryu at camera + 128 with full health, so
  map streaming and wraps are real; the player-driven call at bank 1 `$925E`
  (ROM offset `$325E`) is NOPed in the ROM copy so knockback cannot add a
  second scroll. Both ROMs get identical interventions, samples are read at
  the update boundary, and real input finishes the job (the sweep misses
  crowded-encounter load).
- **Unit-test a small routine in place.** Write a stub (`jsr routine / nop`)
  into the emulator's ROM copy, set PC to it, run to the byte after it and
  compare A and RAM with an independent model over every edge case (the speed
  division was checked over 2,964 and 988 cases), with sentinel bytes around
  its scratch. Restore the ROM copy in a `finally`. Use a stub region that
  production code will never claim.
- **Check a hook's entry contract.** Seed the memory it may touch with
  non-zero bytes, run the original and the patched path from the same state,
  and require identical registers, MPRs, VDC register selection and RAM except
  the intended bytes. Bytes below the restored stack pointer can differ (dead
  pushes); declare that rather than ignore it silently.

## Trace-profiling recipe

To find where a late update spends its time:

1. Reach the update with a breakpoint at the gameplay loop, then enable the
   trace: `set_trace_log` with `output: 'memory'`, `memory_size: '5M'`,
   filter `cpu.instructions`.
2. Read `get_trace_log(count=1)['total_logged']` before and after stepping one
   update. The two sequence numbers bracket it (reading the tail blindly can
   return entries from before a reset).
3. Page through the bracket with `start` and `count ≤ 1000`, parse
   `@clock +delta BB:PPPP`, and add each entry's delta to the routine that owns
   its bank and PC.
4. Map routines from the assembler's symbol files (`research/tools/mkwork.py`
   builds every module with listings and `.sym`); fold RAM trampolines into
   their caller.
5. Convert units once: master clocks / 3 = CPU cycles; 358,995 clocks = one
   263-line frame.

`research/tools/tprof.py` is the reference implementation. Breakpoint-to-
breakpoint clocks per update jitter by a few per cent with the breakpoint's
position in the frame; they are not a frame budget by themselves.

## Desktop frontend input

A tester reported directions sticking in the desktop build. The frontend's
opposing-direction filter (`input_filter_opposing_directions`) keeps the
first of Left and Right held instead of the newest. The game's sampled pad
byte matched the injected input, so the ROM was not at fault. Before
suspecting a ROM, compare the game's sampled pad byte with the input; do not
change a user's emulator input settings silently. The frontend behaviour was
confirmed by compiling the function with tests; the effect on a physical
keyboard was not confirmed.

## Tools

- [`scripts/comparison_video.py`](../../scripts/comparison_video.py): replay
  button input on two ROMs, compare them frame by frame, render a stacked
  video, check the next cinema.
- [`scripts/comparison_route.py`](../../scripts/comparison_route.py) and
  [`scripts/comparison_smooth.py`](../../scripts/comparison_smooth.py): find a
  route through a stage with real input, then make it look like play. The
  smoother replays an edit only until game RAM matches the old run for a
  number of frames, then reuses the old trace: in a deterministic emulator the
  same state and input give the same game.
- [`research/tools/`](../../research/tools/README.md): the probes behind the
  timing, slowdown and background-fidelity work (Ninja addresses included;
  reference implementations).
