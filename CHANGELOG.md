# Changelog

## 1.09 — 2026-10-21

The first public release. A patch for the Japanese PC Engine Ninja Ryukenden
(Ninja Gaiden), headered or headerless original.

Game:

- Smooth parallax in 11 stage entries (1-1, 2-2, 3-1, 3-2, 4-1, 4-2, 5-2,
  5-3, 5-4, 6-1, 6-3): the backgrounds scroll smoothly and slower than the
  playfield. Every Enhanced backdrop is generated at build time from the
  original ROM's own tiles, maps and palettes; no art is edited or added.
  Every round opens exactly like the original, and 6-1 has a stationary
  moon in a twinkling sky.
- Timing parity: in emulator tests, all 11 stages play frame for frame like
  the original with the same button input (sprites, Ryu, enemies, timer,
  health, camera). Stage loads, respawns and area changes take the same
  number of frames as in the original, and no scrolling update takes longer
  than the original's.
- Level Select / options menu (Select during play): jump to any of 22 stage
  entries (Ryu starts with full health), switch between Enhanced and
  Original backgrounds, and turn No Damage on or off. Defaults: Enhanced, No
  Damage off.
- English by default, using the game's built-in translation; the original
  title-screen language switch (English, Chinese, Japanese) is kept.
- The cinema after every stage is identical to the original's, including
  after a full play of each enhanced stage.
- A splash screen with the version and the project address; Run leaves it
  without delay.

Project:

- Source build from the original ROM alone (`scripts/project.py build`), and
  release patches for both ROM formats.
- Player guide with screenshots ([docs/OPTIONS.md](docs/OPTIONS.md)).
- Original-versus-Enhanced comparison videos of every enhanced stage, from
  stored button input replayed on both games
  ([docs/COMPARISON-VIDEOS.md](docs/COMPARISON-VIDEOS.md)).
- Reusable PC Engine knowledge: hardware notes, emulator harness, case
  studies and research probes ([docs/pc-engine/](docs/pc-engine/README.md)).

Evidence: emulator validation in
[docs/validation/background-fidelity.md](docs/validation/background-fidelity.md);
the release bytes were played on an NEC PC Engine Duo-RX with a Krikzz Turbo
EverDrive PRO. See [docs/VALIDATION.md](docs/VALIDATION.md) for scope.
