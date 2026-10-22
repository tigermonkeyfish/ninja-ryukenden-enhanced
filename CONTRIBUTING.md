# Contributing

Start with [the handoff](docs/HANDOFF.md) and reproduce the existing release
using [the build instructions](docs/BUILDING.md).

For bug reports, include the ROM hash, emulator/version or hardware setup,
stage/subarea, selected options, and a short reproduction sequence. Mention
deaths, Continue and stage jumps. Do not attach ROMs or save states to public
issues; describe the inputs needed to reproduce the problem.

For changes, keep a focused scope and explain the visible before/after
behavior. Include relevant tests and limitations. Preserve native artwork,
foreground, movement, collision and progression unless the change explicitly
targets them. Do not overwrite a published patch to fix an issue; increment
the version and record a new hash.

Whenever an investigation teaches something reusable, add it to the
[PC Engine knowledge base](docs/pc-engine/README.md), including its evidence
and assumptions. Keep game addresses in the project architecture document.

Original code, tools and documentation use the [MIT License](LICENSE). Submit
original contributions under that license; identify any third-party material
and its provenance. See [licensing scope](docs/LICENSING.md) for exclusions
covering the underlying game and external tools.
