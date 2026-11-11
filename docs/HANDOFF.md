# Start here when resuming development

## Current truth

- **Release 1.10** (2026-10-30) is current. `VERSION`,
  `release/current.json` and the in-game menu all say 1.10. Patches:
  `patches/ninja-ryukenden-enhanced-v1.10.bps` (headered original) and
  `patches/ninja-ryukenden-enhanced-v1.10-headerless.bps`; both produce
  `3d5c05dfa6fb6a9ea6c04209cbc36d8e952caa6666ea5fcb724864ff4923bbf6`
  (candidate 6 in the [validation record](validation/background-fidelity.md)).
  The maintainer checked the menu on these exact bytes on an NEC PC Engine
  Duo-RX with a Krikzz Turbo EverDrive PRO (2026-10-29), then played 1.10
  from each patch on it (2026-10-31): 1-1 and 1-2, a warp to 2-2, No Damage
  on, a warp to the final boss, the boss beaten and the ending cinema
  started. Everything else is emulator evidence; see
  [VALIDATION.md](VALIDATION.md).
- **Development 1.11-dev** (`VERSION`; the menu shows `V1.11-DEV`) adds
  **Use NES Firewheel logic**, `$2100` bit 2, off by default (menu row
  `NES FIREWHEEL`). With it on,
  the Fire Wheel behaves like the NES Invincible Fire Wheel: no damage while
  it spins, NES hitbox, bosses lose a point per update, 516-update life with
  flicker, NES pickup rules ([architecture](ARCHITECTURE.md#contact-damage-and-nes-firewheel),
  [evidence](validation/nes-firewheel.md), emulator only). With it off the
  game plays as 1.10. Code: `src/nes-firewheel` in bank 3's unused tail;
  no fixed-bank bytes.
- **Palette modes** (1.11-dev, branch `gb-palette`): `$2100` bits 3-4,
  00 Original (default), 01 NES (branch `nes-palette`, below), 10 GB DMG
  (four dark olive shades by luminance, `src/palette/gb-dmg.json`), menu row
  `PALETTE` (previewed while the menu is open). The vblank palette upload maps the native queue in GB DMG gameplay;
  cinemas and the title stay original. 1-1 and 2-2 now keep their merged
  palettes in the RAM palette, which fixes 1-1's area-1 backdrop showing the
  native palette 1 after the re-queue there
  ([architecture](ARCHITECTURE.md#palette-modes),
  [evidence](validation/gb-palette.md), emulator only).
- **NES palette** (1.11-dev, branches `nes-palette`, then `nes-palette-2`):
  the PALETTE row's NES value (`$2100` bits 3-4 = 01) shows the game in NES
  master-palette colours only (the 47 9-bit 2C02G colours; the build fails
  on any other) with the PC Engine's detail, read like NES Ninja Gaiden.
  Draft 2 (2026-11-11, owner: "all the bosses should be 8 bit and all the
  rooms should follow"; NES colours only, TG16 detail): every stage set,
  Ryu (re-mapped, distinct shades), the HUD, all 54 sprite palettes loaded
  in gameplay (Ryu's effects, items, enemies by hue class, each boss by part
  from its captured NES fight) and the game's animated colours (an NES copy
  of bank 3's animation table). Distinct colours of a palette row stay
  distinct unless that would shift a colour by more than about 30 L*. The
  colours are data (`src/nes-palette/`: `stages/`, `sprites/`,
  `shared.json`, `animations.json`; roles and colour values only;
  `scripts/nes_palette.py`). Cinemas and the title stay original. Still a
  **draft** the maintainer has not reviewed; review sheets are private in
  `build/nes-palette-2/sheets/`. Open: fade steps (area changes, loads,
  deaths) dim NES colours by channel, so those frames show non-NES colours;
  a few tiles of 4-3, 5-2 and 6-3 use rows their set does not load
  (leftovers), which hold original colours after a mode switch or a Level
  Select entry. Code and data in bank `$45`, bank `$37`'s free tail and
  bank 3 `$D400-$D9FF`; no fixed-bank free bytes
  ([architecture](ARCHITECTURE.md#nes-palette-mode),
  [evidence](validation/nes-palette.md), emulator only).
- **Popup menu** (1.11-dev, branch `popup-menu`): Select opens a 26 x 10
  window over the playfield (BAT rows 7-16) instead of covering the HUD:
  STAGE, SMOOTH PARALLAX, NO DAMAGE, NES FIREWHEEL, PALETTE, LANGUAGE, then
  `RUN: OK  SELECT: CANCEL`; the band under the HUD shows the version and
  credit; sprites are hidden while it is open; it refuses to open while Ryu
  is dead. Code in bank `$46` `$4400-$4AFF` (bank `$45` `$4000-$43FF` is
  free again); the covered BAT words are kept in the sprite-table buffer
  being built and HUD tiles `$7AB-$7AC`
  ([architecture: menu display](ARCHITECTURE.md#menu-display),
  [evidence](validation/popup-menu.md), emulator only). The options guide's
  menu screenshots (`docs/images/options/menu*.png`) still show the 1.10
  menu: regenerate them with `scripts/guide_screenshots.py` (already
  adapted) before a release; new rows have no screenshot of their own (new
  images need the maintainer's approval).
- **Release 1.09** (2026-10-21, tag `v1.09`) was the first public release
  (`f84a31a8…b912`), played on the same hardware. Its patches stay
  unchanged at the tag; `patches/` holds only the current release.
- **What 1.10 changed.** The splash is removed (native boot, frame for frame
  the original's, checked by `scripts/check_boot.py`). The in-game menu
  covers the HUD and the band under it, keeps the item box clear, blinks the
  selected value, and takes Run to accept and Select to cancel
  ([architecture: menu display](ARCHITECTURE.md#menu-display)); its text is
  `src/options/menu.txt`. `scripts/check_menu.py` checks it throughout play.
- **Build model.** `scripts/project.py build` assembles the runtime modules
  over the original ROM (either format) and reads nothing from any release;
  outside the module ranges the ROM is the original byte for byte.
  `--verify-release` reproduces 1.10 exactly. Every Enhanced backdrop is
  generated at build time from the original ROM's own tiles, maps and
  palettes (`scripts/native_gfx.py`, `scripts/native_backdrops.py`); no
  edited or added art remains.
- **Picture.** Every round of all 11 parallax stage entries opens exactly
  like the original (6-1 omits one star of horizon rows 14-15). Loops use
  only original columns; 3-1 and 4-1 need no join the original does not draw
  (6-3 one), and the remaining seams (1-1, 2-2, 3-2, 4-2, 5-2, castle/6-1)
  await the maintainer's in-game review before any new art.
- **Timing.** Stage loads, respawns and area changes take the original's
  frame counts; force-scrolling every area at 2 px per update, no update
  takes longer than the original's. The HUD/playfield split no longer drops
  a line (back-to-back VRAM block transfers had delayed its interrupt).
- **Options.** English, Enhanced parallax and No Damage OFF are the reset
  defaults. The menu (Select) offers 22 stage entries, PARALLAX ON/OFF and
  No Damage; applying a stage refills Ryu's health. Do not reintroduce the
  abandoned four-speed menu or the repeating 6-1 moon.
- **Comparison runs and videos.** `research/comparison-runs/` holds a
  smoothed button-input run for each of the 11 enhanced stage entries;
  `scripts/comparison_video.py` replays them on the original and on Enhanced,
  verifies identical gameplay frame by frame, renders the stacked 1440p60
  videos and checks the cinema after each full stage
  ([guide](COMPARISON-VIDEOS.md)). All 11 match on 1.10, and the cinemas after them. The maintainer
  publishes the videos on YouTube.
- Validation history, build by build, is in
  [the background-fidelity review](validation/background-fidelity.md);
  Ninja addresses are in [the architecture map](ARCHITECTURE.md).

## First actions

1. Read the README, [architecture](ARCHITECTURE.md),
   [transferable lessons](pc-engine/LESSONS.md) and the
   [PC Engine hardware notes](pc-engine/HARDWARE.md).
2. Run the ROM-free tests (`python3 -m unittest tests.test_tools`) and
   `scripts/audit_public.py`; reproduce 1.10 with `apply` and
   `build --verify-release`.
3. Reproduce the reported problem on that exact output before editing.
4. Record stage, subarea, camera position, options, language and reproduction
   sequence, including whether death or a stage jump is required.
5. Change one subsystem; build a separate development output with a new
   version in the in-game menu (`1.11-dev`); record its hash and validation
   evidence. Never change the published patches.

## Next useful work

- NES palette: the maintainer's review of draft 2 (sheets private in
  `build/nes-palette-2/sheets/`: bosses, the four once-uncaptured stages'
  areas, Ryu before/after). Then: NES-only fade steps (map fade colours to
  the nearest NES colour in the upload, best after `hell-palette`'s upload
  rewrite is merged, since it changes `src/palette`); the leftover rows
  (pad the short NES sets or snap rows past a set's end at its load);
  enemies per stage from the NES enemy palettes if the hue-class pass is
  not enough; the NES final form (not reached in the NES captures).

- After any change that could affect timing, rerun
  `scripts/comparison_video.py make` and `cinema` on all runs; a run that no
  longer finishes needs a new route search ([guide](COMPARISON-VIDEOS.md)).
- A full real-hardware playthrough in Enhanced mode, including deaths,
  Continue, stage exits, map boundaries and language persistence; a look for
  one-frame vertical playfield jumps in 5-2/6-3 and any slowdown in 5-3 and
  2-2.
- Maintainer review of the remaining backdrop seams; any new art must be
  called out in the docs with its reason.
- 3-2 drops frames only when force-scrolled at 3-4 px per update (faster than
  Ryu moves). Lighten its update if faster camera movement turns out to be
  reachable.
- Apply the reusable method to another game; start its memory and timing
  audit from scratch rather than copying Ninja addresses
  ([docs/pc-engine/](pc-engine/README.md)).

## Known boundaries

Hardware confirmation covers the reports in [VALIDATION.md](VALIDATION.md).
A complete damage/death/Continue pass is not claimed, and audio was not
compared. The Geargrafx keyboard issue (opposite directions filtered, so
input can feel stuck) was observed independently of the ROM and left aside;
do not silently change desktop settings or emulator input configuration.

The repository history starts at 1.09. Earlier development (internal
releases 1.00 and 1.01, the REV-era builders and test notes) is not
published; its transferable findings are in `docs/pc-engine/`, and the
maintainer keeps a private backup of the old history.
