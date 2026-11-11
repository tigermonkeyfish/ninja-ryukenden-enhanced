# Popup menu (1.11-dev): validation record

Emulator evidence only (Geargrafx `78fc3d7` with the headless patch,
[EMULATOR.md](../pc-engine/EMULATOR.md)); no real hardware yet, audio not
compared. Design: [architecture, menu display](../ARCHITECTURE.md#menu-display).

Build under test: branch `popup-menu`, ROM SHA-256
`43db8b4c9c3f662c6edd4d22dd03d62385b0e84748ff8d898cb936a12aa6ecb5` (the
same from either original). Baseline for the menu-never-opened comparison:
branch `gb-palette` at `aa967bf`,
`d08e2ec57751b4dddf632a165b7843671a0da1a3de8a8d8951a0caba53d40a37`.

## What changed in the ROM

Against the `gb-palette` build only these bytes differ: bank 0 `$FF8B` and
`$FF90` (the Select hook's bank, `$45` to `$46`, and its call, `$4000` to
`$4400`); bank `$45` `$4000-$43FD` (the old menu, now `$FF`); bank `$46`
`$4400-$49F9` (the new menu, 1,530 bytes). No RAM is added: the menu uses
`$2101` (its draft, as before), zero page `$25-$2C` saved on the stack, and
borrowed VRAM (the sprite-table buffer being built and HUD tiles
`$7AA-$7AD`, `$7B9`).

Space (bank `$46`): claimed `$4400-$4AFF` (262 bytes of it unused); unowned
`$4100-$42FF` (512) and `$4B00-$4FFF` (1,280, contiguous), all `$FF`. Bank
`$45` `$4000-$43FF` (1,024) is unowned again. Fixed bank: no new bytes; the
free `$FECF-$FEDF` and `$FFEE-$FFF5` are untouched. The NES palette data
(about 4.7 KiB) does not fit any of these gaps; it needs another bank.

## Checks

`scripts/check_menu.py` (parts `runs`, `sweep`, `select`, `options`; its
docstring defines each comparison). A cancelled menu is compared with the
same saved state run without the menu: VRAM at the menu's return except the
borrowed sprite-table buffer; then, for 20 frames (900 in the long cases),
every frame's picture and its VRAM, sprite table and palette at the frame's
end, and RAM at the next update boundary except the interrupt's own bytes,
the music driver's and the dead stack. With `--same-music` the run without
the menu gets the music driver's RAM as the menu left it.

| Part | Result |
| --- | --- |
| Stored runs, parallax ON, `--same-music` (every 300 frames and 30 frames after each area change) | 140 cycles, all exact: every picture, every frame's video state, RAM. 32 windows wrapped at BAT column 63; 44 of the 64 start columns covered. 5-4 is the boss room; 5-3, 6-3 the heaviest sprite use |
| Stored runs, parallax OFF, palette previewed (GB DMG then back) before cancel, `--same-music` | 140 cycles: video state and RAM agree in all; 4 cycles show one frame with a few pixels on one line different (4-1 and 6-3 at frame 150 in the first frame after the return; 3-1 at 1650 frame 18; 6-3 at 1950 frame 15) |
| Sweep: Select at every frame of a 1-1 time-out death and respawn, the 5-4 idle death and continue, and frames -5..+45 of every area change in 1-1, 5-3, 6-3 | 1,237 presses: 629 opened and exact, 524 refused (death, area changes, fades, stage loads), 82 not seen by any update; 2 opened cycles before 5-3 area changes showed different video state for 2-3 frames with the music as played, and are exact with `--same-music` (5-3 re-sweep: all 360 openings exact) |
| Level Select, from a cold boot | LANGUAGE reads ENGLISH, `$3227` = 1; exact cycle in all 22 entries; Run on each next entry starts it with health 16, options unchanged, HUD row 30, row 31 and the borrowed tiles as in play, sprites on |
| Options | Each row accepted with Run: `$2100` = `$01`, `$02`, `$04`, `$10` (`$90` with the module's bit 7), `$3227` = 0 and 2; GB DMG's VCE equals the GB table applied to the RAM palette and border; back to ORIGINAL gives the VCE of two plain Runs exactly; cancel after changing every row, from Original and from GB DMG, compared for 900 frames: exact |
| Language | CHINESE or JAPANESE chosen in the menu and Run, then the next cinema: 1,200 frames identical to the same with `$3227` written by the debugger, and different from English |
| Menu never opened (`research/tools/popup-menu/identity.py`), against `gb-palette` | all 11 stored runs, 35,084 frames (each run plus 60 idle frames): every frame's screenshot, RAM, sprite table and palette identical, all of VRAM every 30 frames and at the end |
| `scripts/check_boot.py` | idle frames 1-899 identical to the original; mashing Run reaches the first update on frame 163 as the original; defaults English, Enhanced, damage on |

HUD rows 28-30: a VRAM write watch on words `$0700-$07BF` was armed in every
opened cycle while the menu was open; it never fired. Row 31 showed the
version line while open and 32 blank words after every close. Sprites: VDC
register 5 bit 6 clear while open.

Stack: the deepest use in any cycle, palette uploads in the interrupt
included, reached `$21D3` (hook at `$21FB`); the watched margin
`$2104-$213F` is 148 bytes below.

### The differences that are not the menu's

With the music as played, some cycles show single frames whose picture
differs while each frame ends with the same VRAM, sprite table and palette
(at parallax ON: 2-2 at 450 frame 7, 6-3 at 450 frame 9; one line, three
pixels of a HUD digit at its change), or video state differing for 2-3
frames before an area change (5-3). The music driver plays on while the
menu waits, so afterwards its interrupt work takes different time and the
same writes land at other raster positions. Copying the music driver's RAM
into the run without the menu removes every one of them (all parallax-ON
cycles and the 5-3 sweep). The four remaining preview cases are of the same
kind (identical video state at every frame end, a few pixels in one frame);
the palette preview's cancel adds a full palette upload in the menu's last
vblanks, and the cause of the residue was not isolated further.

After a cancelled palette preview from Original, `$2100` can read `$20`
instead of `$00` (bit 5, the module's left-over flag; the menu never writes
bits 5-7). In Original mode nothing reads bits 5-6 (the module tests only
bits 3-4 and 7 there; every other reader masks its own bit); the 900-frame
comparison above is exact with it. The palette upload's scratch
(`$2205-$220C`, written in full before every use by `$E108`, `$E7F5` and
`$F3B5`; `$2284-$2285`; queue entries past the count) may also differ.

## Screenshots

Kept privately (`build/popup-menu/shots/`, `shots.py`): 1-1, 2-2 with
parallax on and off, 5-3 (dark castle), 5-4 (boss), 6-3 (enemies and Ryu
under the window position; they are hidden while it is open), and 1-1 in GB
DMG (preview, and reopened after Run). The guide's committed images
(`docs/images/options/menu*.png`) still show the 1.10 menu.

## Not covered

Real hardware; audio; a pit death (every death goes through `$8E57`, which
the refusal keys on); opening during the Level Select stage load itself
(the hook does not run there); the title screen's language after a menu
change (a reset restores English by design). The title's own switch still
cycles English, Chinese, Japanese, English with the expected `$3227`
(`scripts/guide_screenshots.py`'s capture steps, which also check the
menu's draft; its image composition needs ffmpeg and was not run).
