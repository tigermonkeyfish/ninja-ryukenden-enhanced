# Reusable PC Engine knowledge

This is the portable part of the project. It preserves methods and evidence
that another game investigation can reuse without adopting Ninja's addresses.

| Start with | What it preserves |
| --- | --- |
| [Investigation workflow](WORKFLOW.md) | Baselines, tracing, hypotheses, evidence, bounded experiments |
| [Smooth parallax recipe](PARALLAX.md) | Native-motion check, original-only loops, phase tiles, round offsets, upload formats, palette/foreground constraints, timing |
| [Failure case studies](LESSONS.md) | Symptoms, root causes, fixes, and what must be re-checked elsewhere |
| [Headless emulator harness](EMULATOR.md) | Building the patched Geargrafx, driving it, the rules that keep replays exact, debugger reference and trace profiling |
| [Hardware and toolchain facts](HARDWARE.md) | Frame timing, banking and ROM expansion, VDC/VCE behaviour, block transfers and interrupts, pceas syntax; each fact with its basis and confidence |
| [Experiment template](EXPERIMENT-TEMPLATE.md) | A reusable record format for the next game |

Tools, from most to least portable:

| Tool | Scope |
| --- | --- |
| [`scripts/pce_tiles.py`](../../scripts/pce_tiles.py) | Game-independent background tile encoding/decoding and horizontal phases |
| [`scripts/bps.py`](../../scripts/bps.py) | BPS creation/application with CRC verification (headered or headerless sources) |
| [`scripts/emulator_session.py`](../../scripts/emulator_session.py) | Game-independent client for headless Geargrafx |
| [`research/tools/vdc.py`](../../research/tools/vdc.py) | Game-independent: decode HuC6270 background layers from VRAM/VCE dumps |
| [`scripts/comparison_video.py`](../../scripts/comparison_video.py), [`comparison_route.py`](../../scripts/comparison_route.py), [`comparison_smooth.py`](../../scripts/comparison_smooth.py) | Frame-exact replays of two ROMs, route search with real input, stacked videos; Ninja addresses in one place each |
| [`scripts/audit_cutscenes.py`](../../scripts/audit_cutscenes.py), [`compare_cutscenes.py`](../../scripts/compare_cutscenes.py) | Capture every cinema frame of two ROMs and compare; Ninja's scene variables |
| [`scripts/native_gfx.py`](../../scripts/native_gfx.py) and the backdrop builders | Decoding a game's packed original art and generating patch data from it at build time; Ninja's formats, the pattern is general |
| [`research/tools/`](../../research/tools/README.md) | The probes behind the timing, slowdown and fidelity work (reference implementations) |

The Ninja implementation is a reference case, not a universal patch engine.
Background composition, spare ROM/VRAM, IRQ structure, RAM ownership and game
state differ between games. Start each port with a new audit.

## How to keep this knowledge useful

Separate four kinds of material:

1. **General method:** the technique and its required conditions.
2. **Game-specific evidence:** addresses, hashes, traces and observations.
3. **Reusable implementation:** small tools with synthetic tests and no ROM data.
4. **Open questions:** hypotheses or untested behavior, explicitly labeled.

For a new game, copy the experiment template into its own repository and link
back to the applicable technique. Record deviations rather than weakening the
original evidence. Promote a game-specific helper into shared tooling only
after removing its addresses, assumptions and copyrighted asset inputs.

These documents can later move into a dedicated PC Engine research repository.
Keeping them together here initially makes every lesson traceable to a working
reference implementation. A separate shared library becomes useful once a
second game establishes which interfaces are actually common.
