# Credits and provenance

**TIGERMONKEYFISH** — project direction, visual review, gameplay feedback,
real-hardware testing and the community credit used in the patch.

The first development stage (the parallax renderers, Level Select, No
Damage, English by default, the splash and the cinema cleanup, up to the
internal builds 1.00 and 1.01) used **OpenAI Codex Astra** for code
generation, reverse-engineering assistance, debugging, tooling and
documentation, guided by that feedback.

The refinement that led to release 1.09 used **Anthropic Claude Opus 5.5**,
directed and reviewed by TIGERMONKEYFISH. That work rebuilt every Enhanced
backdrop from the original game's own tiles, maps and palettes. It also:

- matched every round's opening screen to the original, and built the loops
  only from original columns;
- fixed one-frame playfield drops caused by the HUD split timing;
- made the source build start from the original ROM alone, with no data from
  earlier patches;
- removed slowdown in 5-3 and 2-2 while keeping each stage's load time equal
  to the original's;
- matched every area change and stage load to the original's frame count;
- made the Level Select refill Ryu's health and wrote the illustrated
  options guide;
- recorded frame-synchronized original-versus-Enhanced comparison runs of
  every parallax stage and checked the cinemas after each full stage;
- wrote the original-versus-Enhanced comparison tools, the measurements and
  the documentation behind these changes.

The refinement was validated in an emulator. Hardware confirmation is
attributed to the user, not to the assistants.

The original game, its code, artwork, music and embedded translations belong
to their respective rights holders. This project enables the existing English
mode; it does not claim authorship of that translation.

External development tools:

- [HuC / pceas](https://github.com/pce-devel/huc): HuC6280 assembly.
- [Geargrafx](https://github.com/drhelius/Geargrafx): emulation and debugger access.
- [BPS format](https://github.com/Sir-Walrus/Flips/blob/master/bps_spec.md): patch format implemented by the included Python utility.

External tools retain their own licenses and are not bundled. The emulator
measurements used one local Geargrafx change for headless speed, preserved as
[a patch](docs/pc-engine/emulator/geargrafx-headless-fast.patch) (GPL-3.0,
like Geargrafx); see [docs/pc-engine/EMULATOR.md](docs/pc-engine/EMULATOR.md).
