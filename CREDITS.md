# Credits and provenance

**TIGERMONKEYFISH** — project direction, visual review, gameplay feedback,
real-hardware testing and the community credit shown in the in-game menu.

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
- verified Original-versus-Enhanced timing parity across the parallax
  stages and cutscenes.

Release 1.10 (the splash removed with a boot identical to the original's
and the redesigned status-bar menu with its version and credit lines) also
used **Anthropic Claude Opus 5.5**, directed and reviewed by TIGERMONKEYFISH.

Release 1.11 (centered 25x11 popup menu with paused audio, backup-RAM
settings persistence, `RESET OPTIONS`, `NES FIREWHEEL`, `APOCALYPSE` / `NES` /
`SMS` / `DMG` palette modes including `DMG` non-gameplay screens, and cycle-
and frame-exact stage/palette timing) used the **Google Gemini** family,
directed, reviewed, and hardware-tested on an NEC PC Engine Duo-RX and a
TurboGrafx-16 with Krikzz Turbo EverDrive PRO by TIGERMONKEYFISH.

Hardware confirmation is attributed to the maintainer, not to AI tooling.

The original game, its code, artwork, music and embedded translations belong
to their respective rights holders. This project enables the existing English
mode; it does not claim authorship of that translation.

External build and patching tools (not bundled here):

- [HuC / pceas](https://github.com/pce-devel/huc): HuC6280 assembly.
- [BPS format](https://github.com/Sir-Walrus/Flips/blob/master/bps_spec.md): patch format implemented by the included Python utility.
