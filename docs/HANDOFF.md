# Start here when resuming development
- **timing-cleanup** (2026-11-15): D4+D5 (`src/dispatch/main.asm`), D3 Option
  2A-1 (`src/stage22/main.asm`), and D2 Option A (`src/palette/main.asm`)
  fixed on `align-combined` (code commit `846e0b9`), plus D6/D7/D11/D13 and
  60 outside-window investigations; ROM `ea176297…3ace1` (`1.11-dev`,
  `/workspace/roms/Ninja Ryukenden - Enhanced v1.11-dev (apocalypse, reset 2,
  palette timing 3, original load timing, 2-2 start, cinema lock, timing
  cleanup).pce`, plus both BPS patches). Record:
  [validation/timing-cleanup.md](validation/timing-cleanup.md) and
  [DEFICIENCIES.md](DEFICIENCIES.md) (emulator only).
- **align-combined** (2026-11-13): `start-pos` + `cinema-lock` + `exit-frames`
  in one ROM, `2f134a80...8880` (`1.11-dev`, `/workspace/roms/` file with the
  suffix `2-2 start, cinema lock`, plus both BPS patches). Gates, the
  whole-playthrough replays, the 48-event survey and the cinema check:
  [validation/align-combined.md](validation/align-combined.md) (emulator only).

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
  no new fixed-bank range: the damage gate at `$FE20` grew from 21 to 30
  bytes inside the options module's existing range (ROM `0x1E35-0x1E3D`,
  `$FF` in 1.10) and calls the rule at `$DC00`, so it depends on bank 3
  being mapped at `$C000`.
- **The build to test on hardware** (since 2026-11-12 the `v111-reset` build below, which is this one with only the menu changed; 1.11-dev, branch `v111-final` =
  `v111` + `dark-lift-fix`, merged with conflicts in two documents only):
  everything below in one ROM, `f3114ade…a0a0`, delivered in
  `/workspace/roms/` as `Ninja Ryukenden - Enhanced v1.11-dev (all
  palettes, dark lift 2, settings save).pce` with a patch for each
  original. It is byte for byte the union of its parents (it differs from
  each only in the other's bytes: `options` and `bram` against the fix
  build, `palette` against `v111`), so their records carry over; the
  interactions were checked on it: boot, power cycles (also on the
  lock-modelling emulator, with its negative controls), the menu's options
  part, the 11 stored runs in SMS and HELL equal to the fix build's in
  every frame, and a cold boot with SMS or HELL loaded from backup RAM
  played to a stage end (black before the load, no flash). The transition
  survey the fix record had left open is finished: no flash and nothing
  left unwritten at any stage change in SMS, HELL and GB DMG. Emulator
  only; **waiting for the maintainer's hardware test**
  ([record](validation/v111-final.md),
  [test list](validation/bram-save-hardware-checklist.md)). Not merged
  into `main`; `v111` and `dark-lift-fix` are both contained in it.
- **Menu: APOCALYPSE, reset row, status line** (1.11-dev, branch
  `v111-reset` from `v111-final`; the owner's requests of 2026-11-12):
  the palette mode HELL is shown as **APOCALYPSE** (menu and guides; the
  source keeps the name HELL, same value `$18`, same colours: palette data
  bytes unchanged); the PALETTE row steps ORIGINAL, APOCALYPSE, NES-A,
  NES-B, SMS, GB DMG (the `$2100` values unchanged, so saved settings
  load as before); a **RESET OPTIONS** row (`PRESS I`, I or II) sets the
  draft to the power-on defaults (palette preview at once, STAGE kept; Run
  applies and saves, Select discards); the save status is a plain line at
  the window's top (`SETTINGS LOADED` at power-on, `SETTINGS SAVED` after a Run, `BACKUP MEMORY FOUND`, `NO BACKUP
  MEMORY`, `BACKUP MEMORY FULL`, `BACKUP MEMORY ERROR n`) instead of
  `SAVE: …` under the controls; a blank row between the reset row and the
  controls line (the window is 25 x 11 since build "reset 2": an eleventh
  26-column row would not fit the BAT backup). Only the `options` module
  changed, and in `src/bram` one operand byte (the load's new status
  `ST_LOADED` = 9; nothing of the reads, writes, scan, format or lock
  changed). The status texts take the unowned bank `$46` `$4100-$41FF`;
  the glyphs moved to `$584F-$587E`. Build `cec5f7b3…8059` in `/workspace/roms/` as `Ninja
  Ryukenden - Enhanced v1.11-dev (apocalypse, reset 2).pce` with a patch
  for each original and the checklist copy
  `settings-save-hardware-checklist-apocalypse-reset-2-build.md` (steps
  1.8a-1.8b test the reset row); it replaces `(apocalypse, reset)`
  (`558fc5d2…c672`, 26 x 10, no blank row before the controls). Emulator only
  ([record](validation/v111-reset.md)); **waiting for the maintainer's
  look and hardware test**. The guide's menu screenshots still show the
  1.10 window.
- **Palette timing** (1.11-dev, branch `palette-lag` from `v111-reset`; the
  owner: "I do not want palette changes impacting speedrunners"): the mapped
  modes convert colours in the main loop's idle time (RAM wait `WAITR`,
  worker, `SHADOW` `$3C00-$3FFF`) and upload them at Original's cycles; NES-A/B
  loads take Original's cycles exactly (padded lookups, fast unpack); the
  menu's Run restart is as Original's. Every mode equals Original and 1.10
  in the 11 stored runs (one cinema-entry sample in 6-3 aside), all 22 stage
  loads and a power-on with saved settings; residuals (a few clocks of
  wait-loop phase, a fallback upload when an update queues too much too
  late, the cinema-entry re-upload) in the
  [record](validation/palette-lag.md). Build `4147a8b1...a8849` in
  `/workspace/roms/` as `... (apocalypse, reset 2, palette timing).pce`.
  Review ([findings](validation/palette-lag-review.md)) closed in build
  `abfe6fb8...12f1`, `... (apocalypse, reset 2, palette timing 2).pce`:
  F1 an NES value goes live in the menu preview from every mode (from GB
  DMG, APOCALYPSE or SMS the screen shows Original's colours while it is
  highlighted), so Run's restart is Original's for all 36 opened/chosen
  pairs (before: six mapped -> NES pairs lost 3-2 frames 1033 and 1104);
  F2 `FASTOK` can no longer read 1 after a fallback; F3 (GB DMG black
  around stage clears) left, no spare cycles; F4 `busy` removed,
  `step_recording` fixed (the emulator's pending frame count after a
  breakpoint). Emulator only; waiting for the owner's hardware test.
  Emulator only; RAM claim audited on the stored runs, boot and Level Select
  only.
- **Start position** (1.11-dev, branch `start-pos` from `start-align`; the
  owner: "The goal is for all of the background position starts to match
  the unmodified rom"): the 8 px at 2-2 areas 1 and 2 is the original's
  backdrop jumping a tile on the camera's first step (the frame after the
  first visible one); the starts themselves were identical. Fixed the one
  real start difference: two backdrop lines in 2-2 area 2's last black
  transition frame (2-2's area-change draw wrote palettes 13/14 to the VCE
  at once; Original and NES now leave them to the native full upload;
  mapped modes unchanged). All 48 surveyed loads and area changes: every
  frame from the black through the frame before the camera first moves
  identical to the unmodified ROM (6-1's omitted star apart). Build
  `888a8730...d1f9` in `/workspace/roms/` as `... (apocalypse, reset 2,
  palette timing 3, original load timing, 2-2 start).pce` with both patches.
  Emulator only ([record](validation/start-pos.md)); waiting for review and
  the owner's hardware test.
- **Load timing exact** (1.11-dev, branch `load-exact` from
  `palette-exact`; the owner: "stage start should appear like the
  original ... all stages and all substage/middle phases ... perfectly
  aligned"): the 2-2, 5-2 and castle (5-3/5-4) stage loads no longer draw
  the Enhanced backdrop; the renderer draws it in two pieces in the stage
  entry's short updates while every colour is still black (`$2258` =
  `$FD`/`$FC`, picked by the native entry countdown `$2E63` = `$38`/`$37`).
  2-2 and 5-4 load in the original's 16 and 17 vblanks (were 17 and 18,
  1.10 too), and the 2-2 load's three-frame palette flash is gone. All 47
  loads and area changes of the playthrough take the original's vblanks in
  every update, all six modes; the unmodified ROM and this build replay one
  recording (`full.json` with idle shifts at 53,288 and 82,966) from power-on
  to the ending on the same frames. First visible frames pixel-identical to
  palette timing 3. Build `27d1eaa0...dcf0` in `/workspace/roms/` as `...
  (apocalypse, reset 2, palette timing 3, original load timing).pce` with
  both patches. Emulator only ([record](validation/load-exact.md)); waiting
  for review and the owner's hardware test.
- **Palette timing exact** (1.11-dev, branch `palette-exact` from
  `longplay`; the owner: "I do not want palette changes impacting
  speedrunners"): the vblank interrupt calls the palette upload in RAM
  (`RENT`, `$3740`; `$FD13 jsr $3740`), the native upload byte for byte in
  ORIGINAL/NES-A/NES-B and a gated copy in the mapped modes, so the vblank
  palette path costs 1.10's clocks in every mode (palette timing 2: +228
  clocks every vblank, which lost the act 3 story scene's frame at 51,761).
  Every vblank of the whole recorded playthrough equals 1.10's in ORIGINAL
  and NES (126,002); the mapped modes differ only at cinema entries and
  area-change fallbacks. All six modes: 4-1 at 53,287 again, counters equal
  to 1.10, lost updates 654 before 5-4 (= 1.10). The adjusted recording
  `research/longplay/full-exact.json` (one idle frame less before 4-1)
  replays to the ending in all six modes. Build `a0019797...2621` in
  `/workspace/roms/` as `... (apocalypse, reset 2, palette timing 3).pce`
  with both patches. Emulator only
  ([record](validation/palette-exact.md)); waiting for review and the
  owner's hardware test.
- **Palette modes** (1.11-dev, branch `gb-palette`): `$2100` bits 3-4 (bits
  3-5 since the SMS palette, below),
  00 Original (default), 01 NES (reserved, shown as Original), 10 GB DMG
  (four dark olive shades by luminance, `src/palette/gb-dmg.json`), menu row
  `PALETTE` (previewed while the menu is open). The vblank palette upload maps the native queue in GB DMG gameplay;
  cinemas and the title stay original. 1-1 and 2-2 now keep their merged
  palettes in the RAM palette, which fixes 1-1's area-1 backdrop showing the
  native palette 1 after the re-queue there
  ([architecture](ARCHITECTURE.md#palette-modes),
  [evidence](validation/gb-palette.md), emulator only).
- **HELL palette** (shown to the player as APOCALYPSE since `v111-reset`; 1.11-dev, branch `hell-palette`): bits 3-4 = 11, menu
  value `HELL`; the owner's mock-up "Lava" (candidate C,
  `src/palette/hell.json`) applied to background palettes 0-14 only, so Ryu,
  enemies and the HUD keep their colours. Code and table in bank `$43`
  `$7800-$7FFF` (stage11's unreachable tail) via MPR3; the Original and GB
  DMG paths are cycle-for-cycle unchanged; the menu queues all colours when
  it changes the live mode
  ([architecture](ARCHITECTURE.md#palette-modes),
  [evidence](validation/hell-palette.md), emulator only). **Since branch
  `hell-1-1` (from `all-palettes`) HELL is the retuned candidate D** (the
  owner, 2026-11-11: "1-1 hell should be more like 2-2"; 1-1's walls,
  sidewalk and street and the indoor walls take 2-2's bridge and column
  golds) **with one per-stage override**: in 1-1 colour `$094` (sidewalk
  fleck, skyline shadow faces) shows 210 (R G B), 2-2's dark column gold,
  where the table keeps crimson for 2-2's far ridge (`hell.json`
  `stage_overrides`; the upload reads `$2E5F` where it picks its loop; no
  RAM, 139 bytes in bank `$43`'s tail, +6 master clocks a low-half colour in
  1-1 only, 9 cycles a mapped chunk elsewhere). Original, NES-A, NES-B, GB
  DMG and SMS are identical to `all-palettes` frame for frame
  ([architecture](ARCHITECTURE.md#palette-modes),
  [evidence](validation/hell-1-1.md), emulator only). Open for the owner:
  210 or 2-2's olive 110 for that colour (`build/hell-1-1/choose-094.png`).
- **Dark lift** (1.11-dev, branch `dark-lift`, from `hell-1-1`; the owner
  found 5-1 and 6-2 too dark and 4-1's parallax background almost
  invisible): data only, no code. SMS: the four colours with green 1 that
  went to black take the darkest SMS green, olive or grey (`sms.json`
  `dark_rescue`; `$001`, `$008`, `$009` still black). HELL: raised dark
  ends of the green, grey and steel ramps and a "leaf" ramp for pure greens
  (21 colours; nothing but black is black; the 1-1 override kept). NES-A
  and NES-B: 4-1's back trunks take a `backwood` role one NES step above
  the fill. GB DMG untouched. 50 ROM bytes differ from `hell-1-1`; the
  tables equal the mock-up study's byte for byte. Original and GB DMG are
  identical to `hell-1-1` frame for frame in the 11 runs; `check_boot.py`
  and `check_menu.py` pass. **Unfinished**: brightness measured from real
  captures, the before/after screenshots (nobody has looked at the stages
  yet), the 22 Level Select entries and the NES on-screen counts were not
  run. **Open for the owner**: in SMS, 6-3's floor flashes grey for 7
  frames on the black screen of the load after 6-2, and 3.5% of 6-3's
  picture is grey for 20 frames of its fade-in before it settles darker
  (stale and rescued darkest fade steps, now visible); in HELL the darkest
  grey `$049` is now lighter than the next grey `$092`
  ([evidence, commands and next steps](validation/dark-lift.md), emulator
  only).
- **Dark lift 2** (1.11-dev, branch `dark-lift-fix`, from `dark-lift`;
  delivered for review as build `1678b2e1…41e2ae`): the flash's cause is the stage load
  dropping the palette queue while the mapped upload was still writing the
  fade-out's last step (GB DMG has had the same flash since the mode
  exists, as its second shade; 6 of the 11 stage changes show it, up to
  10.8% of the playfield for 16 frames). The mapped uploads now give a
  left-over entry 136 colours a vblank while the native fade's level
  `$2A8A` is `$FF`, so the black is complete four ticks before the load;
  every other path keeps its cycles. Verified: the unit test of the upload
  and the timing of its paths; the 11 runs (Original, NES-A and NES-B
  identical to `dark-lift` in every frame; GB DMG, SMS and HELL differ only
  in the frames after each stage-end fade-out, gameplay equal to Original
  in every frame, no flash, nothing left unwritten at the load);
  `check_boot.py` and `check_menu.py`; every stage exit in GB DMG, SMS and
  HELL (the last four on `v111-final`, see above). **Not verified**:
  deaths, Continue, Game Over. The dark lift's own evidence
  (brightness from captures, equal to the study's predictions; the sheets,
  looked at; the 22 Level Select entries; the NES checks) is complete.
  A change to know: the cinema after a stage now begins on Original's frame
  in the mapped modes, one frame earlier than on `dark-lift`. HELL's grey
  order is left as it is (no table value keeps 1-1's sidewalk seams and the
  lift of `$049` both; four choices with their costs in the record); SMS's
  dark rescue has the same kind of reversal on a larger scale (`$049`
  lighter than `$04A`, a fifth of 6-2's picture), which is also why 6-3's
  fade-in passes through grey: open for the owner
  ([evidence](validation/dark-lift.md), emulator only).
- **SMS palette** (1.11-dev, branch `sms-palette`, from `hell-palette`):
  `$2100` = `$38`, menu value `SMS` after HELL: everything on screen in the
  Sega Master System's 64 colours (each channel to the nearest SMS level,
  shown as PC Engine 0/2/5/7; the owner's mock-up candidate A,
  `src/palette/sms.json`), border and sprites included, mapped at the
  upload like GB DMG. **The palette mode is now three bits, `$2100` bits
  3-5** (bits 3-4 the upload family as before, bit 5 a variant: `$00`
  Original, `$08` NES-A, `$28` NES-B, `$10` GB DMG, `$18` HELL, `$38` SMS,
  `$20`/`$30` unassigned) and **bit 7 is set exactly with SMS** (`$B8`; the
  upload's existing compare tells SMS from HELL by it). The palette module's
  state moved from `$2100` bits 5-7 to `$2104` bits 5-7 (same instructions;
  the watched stack margin is now `$2105-$213F`); `$2100` holds only
  settings (bit 6 free). Original, GB DMG and HELL keep their cycle counts
  exactly. The menu's
  draft keeps the options in bits 0-5 and the language in bits 6-7. SMS
  runs GB DMG's own code from a byte-identical copy in bank `$3B`
  (`$5000-$57FF`, with the SMS table at `$5400`), entered by a `bmi` on the
  dispatch's own compare and stubs in bank `$46` `$5A00-$5AFF` (speed's
  unused tail, now also holding `fold_queue`; speed claims `$5900-$59FF`); no fixed-bank bytes, no bank `$45`, `$37` or bank
  3 bytes ([architecture](ARCHITECTURE.md#palette-modes),
  [evidence](validation/sms-palette.md), emulator only). Merged with
  `nes-palette-2` in `all-palettes` (below).
- **NES palette** (1.11-dev, branches `nes-palette`, then `nes-palette-2`;
  NES-A since `all-palettes`):
  the PALETTE row's NES value (`$2100` = `$08`) shows the game in NES
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
- **All palettes** (1.11-dev, branch `all-palettes`: `sms-palette` with
  `nes-palette-2` merged): the PALETTE row offers ORIGINAL, NES-A, NES-B,
  GB DMG, HELL and SMS (`$2100` `$00`, `$08`, `$28`, `$10`, `$18`, `$B8`).
  NES-B is the re-lit NES data (`relit()` in `scripts/nes_palette.py`: each
  role's dark shades lifted into its NES ramp's lightness; own sets, 3-2
  variant, animation table and 1-1/2-2 merged palettes; sprites, Ryu and
  the HUD NES-A's; 4,529 bytes, mostly bank `$3B` `$4200-$4F7D`). Its
  re-light makes 3-1's three animated entries one colour, so 3-1's lights do
  not animate in NES-B (open for the owner). **The popup now holds the
  sound while it is open** (a behaviour change from 1.10: music and effects
  pause and continue where they stopped, as in the game's own pause): the
  sound driver playing on had made the 8 sweep failures; with it held the
  sweep is exact except one opening that differs only by the timer
  interrupt's phase, listed apart (`--strict` fails it). HELL's retuned
  candidate D and the 1-1 override followed on `hell-1-1` (above). Evidence:
  [validation/all-palettes.md](validation/all-palettes.md), emulator only.
- **Saved settings** (1.11-dev, branch `v111` = `bram-save` with
  `dark-lift` merged; **waiting for the maintainer's hardware test**): the
  menu's Run saves `$2100` and the language to the console's backup RAM
  when there is one (a System Card style file `NR ENHANCE`, 26 bytes with
  its terminator), and the reset loads them; without backup RAM, or when it
  is full, damaged or unformatted and not blank, nothing is written and
  the game starts with the defaults as before. The popup's last row showed
  the status (`SAVE: OK`, `READY`, `NONE`, `FULL`, `ERROR n`; `$2105`;
  since `v111-reset` a plain line at the top, see above).
  Code: `src/bram` (the old `src/english` folded in), bank `$46`
  `$4B00-$4FFF` and the reset trampoline `$FFE6-$FFF5`. Emulator evidence:
  the image matrix, power cycles and negative controls pass on a test
  emulator that models the lock two ways (the pinned emulator does not
  model it); the Super System Card 3.0's own `BM_` routines read, extend
  and delete around the game's file; the stored runs equal `dark-lift` in
  all six palette modes; `check_menu.py` and `check_boot.py` pass. **Not
  seen on any console**: whether the Duo's memory answers a card in the
  slot through the EverDrive is the open question.
  Read [validation/bram-save.md](validation/bram-save.md) first (results,
  rerun commands, the review, what is left); the maintainer's test list is
  [validation/bram-save-hardware-checklist.md](validation/bram-save-hardware-checklist.md)
  (copied beside the build as
  `/workspace/roms/settings-save-hardware-checklist-dark-lift-2-build.md`;
  the older copy there names the build before the merge). After the hardware report: fix what it shows, then
  the options guide's menu screenshots (they still show the old window)
  and the changelog. The emulator harness controls backup RAM per session
  (`scripts/emulator_session.py`: none unless `power_on(rom, bram=image)`);
  the lock-modelling emulator is a private build
  (`research/tools/bram-save/locktest_patch.py`,
  [EMULATOR.md](pc-engine/EMULATOR.md#backup-ram)).
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
  defaults (since the saved settings: unless backup RAM holds them). The menu (Select) offers 22 stage entries, PARALLAX ON/OFF and
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

Known deficiencies of the 1.11-dev build against the unmodified ROM are
listed in [DEFICIENCIES.md](DEFICIENCIES.md).

Hardware confirmation covers the reports in [VALIDATION.md](VALIDATION.md).
A complete damage/death/Continue pass is not claimed, and audio was not
compared. The Geargrafx keyboard issue (opposite directions filtered, so
input can feel stuck) was observed independently of the ROM and left aside;
do not silently change desktop settings or emulator input configuration.

The repository history starts at 1.09. Earlier development (internal
releases 1.00 and 1.01, the REV-era builders and test notes) is not
published; its transferable findings are in `docs/pc-engine/`, and the
maintainer keeps a private backup of the old history.
