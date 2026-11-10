# Ninja-specific architecture

Read the [reusable method](pc-engine/README.md) separately. The addresses and
available storage below are findings about this particular game and build.

## Rendering

The patch intercepts the original early/late background paths. The dispatcher
recognizes background profiles using native geometry and selects a renderer.
ORIGINAL bypasses the enhanced renderer and executes the native routine.

Enhanced renderers combine neighboring background tiles into eight horizontal
pixel phases. A phase atlas is uploaded into reserved VRAM slots, and the tile
map refers to the appropriate shifted tiles. Native foreground words and
palettes must remain intact. Larger profiles use additional tile slots and
generated transfer blocks; castle profiles also update animated star tiles.

The shared coordinate calculation uses the absolute camera C:

```text
anchor = floor(C_entry / 2) - floor(C_entry / 8)
D      = floor(C / 8) + anchor
offset = D - C
```

This retains the old opening composition while slowing subsequent movement.
Stage 2-2 uses a separately researched 200-pixel mountain repeat; its coarse
tile selection must use the same absolute coordinate as the fine phase.
Stage 6-1 has a stationary upper sky and a separate moving lower horizon.

The native backdrops are screen-locked (no parallax), apart from an 8px
jitter that depends on travel history. Each native profile is a 34-tile-wide
map; columns 32-33 are filler for the jitter (in the castle they break the
ground rows' 8-tile period). At a round entered at camera 0 the original shows
columns 0-31; at a round entered at camera C > 0 (a multiple of 16) it shows
column 1 at the left edge, so column 32 is visible too.

## Original graphics, maps and palettes

Decoded statically by `scripts/native_gfx.py`; every stage's backdrop tile
sets were checked word for word against the original's VRAM, and palettes
against the VCE (docs/validation).

| Item | Location / format |
| --- | --- |
| Graphics loader | Bank 0 `$EE6F`, A = request; VRAM base word address in `$19/$1A` |
| Requests | `$E860 + 4n`: asset, type<<3, first tile, count |
| Assets | `$EAD3` kind (low nibble) and mode ((v>>3)&6), `$EB50` base tile, `$EBCD` count, `$ECC7`/`$ED44`/`$EDC1` address and bank (`$EC4A` span) |
| Kind handlers | `$EEF2` table: 1 tiles (`$EEFB`, header `$EF5B`), 2 sprite patterns, 3 rows |
| Tile packing | `$F13F`: per 16-byte half tile both byte lanes restart at 0; a control byte per 8 bytes, MSB first, alternating low/high lane; 1 = literal, 0 = repeat the lane's last byte. Modes 2/4/6 (`$F05F`/`$F07C`/`$F09C`) pack fewer planes |
| Backdrop maps | Profile table `0x221F` (height, cutoff, address); 34 words a row at ROM `0x7A000 + address - 0xA000` |
| Backdrop tile sets | Two requests per stage, to VRAM `$1000` and `$2000` (e.g. 2-2: `$64`, `$65` in bank 1 `$87E8`) |
| Palettes | Set table bank `$37:$6000` (address, colour count); loader `$F211` (A = set) unpacks into the RAM palette `$2286`: per 8 colours a byte of bit-8 values (MSB first), then 8 low bytes |
| Profile → palette set | 1-1: 1, 2-2: 4, 3-1/3-2: 6, 4-1: 8, 4-2: 9, 5-2: 13, castle (5-3/5-4/6-1): 14, 6-3: 16 |
| Playfield split | VDC scanline interrupt at RCR `$6F` (IRQ1 vector `$FCD7`); the handler (`$FD26`) waits (3 × `jsr $FD8C`), then writes BYR (`$FD3B`) and BXR from `$2E4D/$2E4E` and `$2E4B/$2E4C`, ~69.9 lines after vblank. Geargrafx shows the playfield a line low if the BYR write lands after ~70.9 |
| Stage timer | Three digits, units first: `$2EDB-$2EDD` (5-2 starts at 150); running out kills Ryu |

## Enhanced backdrops (1.03-dev to 1.05-dev)

Every backdrop is regenerated at build time from the original ROM
(`scripts/native_backdrops.py`). Each loop keeps the native picture in order as
far as the round starts show it, then repeats original columns
(`native_gfx.LOOPS`, chosen by `scripts/native_seams.py`):

| Stage | Loop (tiles) | After the round-start columns | Seams (joins the original never draws) |
| --- | --- | --- | --- |
| 1-1 | 35 | 18-20 | 3 joins, cloud rows 1-2 |
| 2-2 | 50 | 32-33, 9-24 (all rows) | 13 joins: the original's non-repeating left edge |
| 3-1 | 40 | 2-9 | none |
| 3-2 | 32 | — | 6 joins at the wrap (rows 7-9, 14, 18-19) |
| 4-1 | 46 | 17-23, 3, 4, 26-30 | none |
| 4-2 | 34 | 32-33 | 12 joins, clouds and ground |
| 5-2 | 33 | 32 | 22 joins at the vista edge (seen only through the cliff opening) |
| castle, 6-1 | 33 | 32 | 8 joins, horizon: the low cloud meets the tall cloud |
| 6-3 | 35 | 32, 3, 4 | 1 join (row 16) |

The castle sky (rows 0-13) uses the same 33-column loop; 6-1's stationary sky
map holds native columns 0-33 and then plain sky.

Renderer mechanics (all profiles): `loop.inc` (generated) defines
`LOOP_LENGTH`, `LOOP_SPAN` (8 x length), `MAP_WRAP` (64 mod length) and the
per-round `OPENING_n` offsets. The loop entry of BAT column b is
floor((D + LOOP_SPAN - C%8)/8) + (b - left column) + round offset, mod
LOOP_LENGTH, from the absolute coordinate D the first `jsr $FFD0` left in
`<$29/<$2a`. Map rows hold 64 entries (loop position mod length); a run that
reaches entry 64 continues at `MAP_WRAP`. Round offsets come from the entry
cameras: 0 at camera 0, otherwise (1 - C/16) mod length (this reproduces
every offset measured for the 1.02-dev loops). 5-2 keeps a fixed anchor
instead of the entrance anchor: `FIXED_ANCHOR` = 8 x length - 56 puts native
column 1 at the left edge at camera 512. 5-2 and 6-3 write columns with
unrolled code (`column_entry_*`), like 2-2, 4-2 and the castle.

Formats and space:

- Phase atlases (1-1, 3-1, 3-2, 4-1): 1-1 pairs at tiles `$280-$2D2` in
  merged palette 1 (the native palette 1 is scenery-only); others at `$80+`.
  3-1's atlases must end at `$7240` in banks `$48-$4B` (the tails belong to
  2-2 and the castle).
- REV5 code (2-2, 4-2, `rev5_texture.py`). 4-2: 173 pairs, 11 code banks
  `$68-$72` plus the renderer bank's tail. 2-2: 269 pairs in palettes 1, 0
  and merged palettes 13/14 (rows 12-14 and 15), 15 code banks `$57-$65`
  plus bank `$7B` and the `$48`/`$49` tails (`$7240-$7FFF`), all moved from
  4-2. 2-2 slots: tiles `$80-$FF`, `$6C0-$72F` (cleared again at cinema
  entry), then native 2-2 backdrop tiles `$140-$14B`, `$150-$15B`, ...
  (`rev5_texture.PROFILES`). Those native tiles are referenced by no
  foreground BAT cell in any sample of any 2-2 area (217 samples), by no
  sprite (2-2 sprite patterns stay in `$3000-$66BF`) and are never rewritten
  mid-area; the next stage's initialization reloads `$1000-$1FFF`.
- TIA (5-2, 6-3): data banks hold the phases (5-2: 2 per bank, 6-3: 4),
  routines per (row, phase within bank) follow the row tables in the
  renderer bank. 32-byte TIAs with a NOP between blocks: back-to-back blocks
  delayed the playfield split past its line (1.04-dev). The 6-1 sky upload
  (`stage61-upload`) does the same (1.06-dev; 16-byte pairs before).
- Block-transfer rule (all renderers): the renderer is still running at the
  split's raster line, so the longest uninterruptible stretch delays it.
  Keep it to one 32-byte TIA, or two adjacent 16-byte TIAs (measured worst
  BYR write 70.51-70.55 against a ~70.9 cut-off).
- Castle and 6-1 (`castle_horizon.py`): horizon upload lists name exactly the
  slots the map uses. A pair whose eight phase images an atlas slot holds
  (a horizon slot of the sky atlas, or one of the 11 fixed phase-invariant
  slots) takes that VRAM tile; the other 4 use borrowed tiles `$238-$23B`
  (from `$238-$23D`, `$240-$257`, unreferenced in Enhanced 5-3/5-4/6-1; see
  the 1.02-dev audit). The native 6-1 picture, on screen until the first
  update, uses `$23D`, `$243`, `$245-$247`, `$24C-$24F` and `$252`, so the
  borrowed tiles come from `$238` first. The castle module stores every listed image (74 tiles
  x 8 phases), generated from the original art, phase by phase in tile order
  in banks `$35-$36` (unused `$FF` in the original) and the bank `$4A`
  tail (`$4B` tail spare), so each phase uploads 12-13 runs; the fixed
  slots split the rest. Run count matters: an area's first frame redraws
  everything with both upload groups, and about 17 extra runs per phase
  cost 5-3 a frame at the area 4 entry (1.05-dev validation). Horizon rows
  14-15 stars use the castle sky's animated star slots; 6-1 leaves them out.
- Castle sky atlas (`castle_horizon.atlas`): the sky/star images in banks
  `$7D-$7F` and each castle/6-1 module's `$5D00` page, and the 32-column base
  map, are regenerated from the original in the first castle builder's layout.
  Stars: the original copies frame pairs `$100+n/$101+n` over tiles
  `$198/$199` (group 2) and `$162/$163` (group 3) following the
  `$FF`-terminated lists at bank 2 `$AD68`/`$AD6D`; the renderer follows the
  game's counters `$3176/$3177` and uploads one image per (phase, frame).
  The static sky upload lists, fixed uploads and star tables in
  `castle-generated.inc` must match the regenerated atlas.

### Redraw cost (1.06-dev)

A parallax update uploads the phase tiles every update (the backdrop moves
7/8 of the camera relative to the BAT) and rewrites every visible map entry
when the backdrop crosses a tile (every ~9 camera pixels). The rewrite plus
the uploads made 5-3 area 2 and 2-2 area 0 miss vblank.

- Column copy (castle, 6-1 sky and mountains, 2-2): the BAT high byte alone
  is read (reading `$0003` advances the read address). Foreground (castle and
  6-1: palette >= 2; 2-2: palette >= 3, except 13-15 in rows 12-15) is not
  written; a second, unsynced
  chain skips it and `seek_write` moves the write address (bias `<$0a/<$0b`,
  2-2 `<$29/<$2a`, = BAT address minus map index) at the next backdrop cell.
  5-3's interior areas are 96-98% foreground. A chunk that ends in the
  unsynced chain must re-seek before more entries are written in sequence
  (map-row end; the 6-1 sky's copy re-seeks on return).
- The column split (BAT row end, map row end) is planned once per update or
  group (`plan_columns`, 6-1 `plan_sky`), not per row. The 6-1 sky continues
  a row's second chunk straight from the previous row's first one.
- 2-2 rows whose map entries are all equal (`uniform_rows`, generated) are
  skipped when the backdrop crosses a tile; they only get the camera's new
  edge column.
- Updates with no map change only upload (no 23-row walk). The shared speed
  bridge divides by 8 with three shifts (it ran a 16-step loop each update).
- Loads: `init_background` draws the whole backdrop while loading, except in
  6-1 (1.07-dev): there the round opens on the native picture, which
  Enhanced's matches, and the first gameplay update draws (it fits in one
  frame).
- Area changes (1.08-dev): the native transition calls `$80AB` in its fourth
  frame and the native picture takes about 0.8 of that frame, so an Enhanced
  draw there (0.8 frame in 2-2) pushed the rest of the transition a frame
  later. `area_background` only marks the draw pending (`$2258 = $FE`, an
  impossible camera high byte); the next main-loop frame (`$83F3`, Select
  hook) turns it into `$FF` and draws 2-2, 5-2 and the castle stages there,
  in a frame the original spends waiting for vblank (`$FD6F`). Other
  renderers see `$FF` and draw on their first update, as before. The
  renderers initialize only on `$FF`, so `$FE` must never reach them; the
  main-loop hook always runs before the first update. Measured with delay-loop ROMs, a 6-1 load-time draw of up to 71,749
  cycles kept the original's load length and 72,053 added a frame; the
  shortest achieved was 72,603. The 6-1 sky module uploads the shared fixed
  tiles; the mountains do not repeat that.

## Source map

| Modules | Purpose |
| --- | --- |
| `dispatch`, `native-hooks` | Profile detection, original/early/late hooks, preserved scratch state |
| `stage11`, `stage22`, `stage31`, `stage32`, `stage41`, `stage42`, `stage52`, `stage63` | Stage-specific background renderers |
| `castle` | Shared 5-3 / 5-4 castle rendering and star animation |
| `stage61-*` | Sky/mountain separation, sky upload and dispatch |
| `speed` | Shared divisor-8 coordinate and entrance anchor |
| `selector-hook`, `options` | Stage selection, progression synchronization, parallax/damage settings and the menu's version/credit line; a chosen stage starts with full health (`$2EAD = 16`, 1.09-dev) |
| `cinema-sprite`, `english` | Cinema sprite-pattern reset (below); native English initialization. Enhanced has no boot screen since 1.10-dev |

The canonical bank allocations are in
[`src/modules.json`](../src/modules.json). Do not use old experimental `.sym`
files to allocate free space.

## RAM contracts

| CPU address | Meaning / constraint |
| --- | --- |
| `$2100` | Active options: bit 0 Original, bit 1 No Damage, bit 2 Use NES Firewheel logic (1.11-dev, no menu row yet); bits 3-7 unused. Zero = the defaults |
| `$2101` | Draft menu options (the menu copies bits 0-2, so Run keeps the NES Firewheel bit) |
| `$2102–$2103` | Entrance anchor |
| `$2104–$213F` | Watched stack margin; not general-purpose spare RAM |
| `$220F–$2210` | Absolute foreground camera |
| `$2241` | Current master stage parameter |
| `$2247` | Next master-script cursor; must match selected stage |
| `$2248` | Pending progression state; cleared on selection |
| `$2251–$2256` | Native background geometry; preserve across deaths |
| `$2257–$225A` | Enhanced renderer cache; `$2258 = FF` invalidates it |
| `$2E4B–$2E4C` | Render-time camera, modulo 512; can lag the later camera sample |
| `$2E5F / $2E60` | Visible stage / subarea |
| `$2EAD / $2EAE / $2EAF` | Health / hurt timer / lives |
| `$2ED0–$2ED5` | Score digits, least significant first (decimal 0-9 each) |
| `$2EAB` | Ryu's state; 9 while hurt (knockback) |
| `$2EDF / $2EE0–$2EF3` | Enemy slot being updated / enemy type per slot (`$FF` empty); `$2FBC,slot` bit 7 = killed |
| `$310C / $310D / $310E–$3112` | Item effect count / slot being processed / effect type per slot (`$FF` empty): 0-2 art projectiles, 3 Jump & Slash, 4 time freeze, 5 Fire Wheel |
| `$3127,slot / $3136,slot` | Type 5 with NES Firewheel: the wheel's update count (the wheel's handler never uses these fields; the effect constructor clears them) |
| `$3157 / $3179` | Time freeze active / its remaining ticks |
| `$3158` | Ryu's art: 0-3, 6 = none (set by `$A7F7`, which also draws the HUD icon) |
| `$3035 / $3036,slot` | Boss health / boss already hit by the current contact |
| `$317A` | Fire Wheel counter: 10 at pickup, one less per stage-timer tick; the effect ends at 0 |
| `$3035` | Boss health in the 5-4 boss room (16, like Ryu's) |
| `$2240 / $2241` | Native master state (0 gameplay, 1 cinema, 2 ending) / scene id |
| `$3227` | Native language: 0 Japanese, 1 English, 2 Chinese |

The CPU stack grows down from `$21FF`; the menu backs up two HUD rows on it.
Reserved low-stack variables were checked with memory guards. Changes to
call depth or menu backups need fresh guard checks.

## CPU entry points and hazards

| Address | Purpose |
| --- | --- |
| `$8097 / $80AB` | Native background render / initialization |
| `$8244` | Native stage initialization (stage in A) |
| `$8457 / $8478` | Gameplay loop / native completion path |
| `$8457-$845C` | Gameplay loop calls `$E3F2`, `$ABD7`; Enhanced: `jsr $FE40` (which makes both calls) and three NOPs |
| `$FE20` | Damage gate (bank 1 `$8F70`): No Damage, then the NES Firewheel protection rule (`$DC00`, bank 3); timer expiry explicitly bypasses optional immunity (`$9BC3` jumps to `$FE34`). `$FE3E–$FE3F` unused in the options range |
| `$FEBE–$FEDF` | Free (`$FF`; the 1.09 splash wrapper, removed in 1.10-dev) |
| `$FE40 / $FE46` | Early wrapper / preserved-scratch renderer entry |
| `$FEE0` | Development cinema sprite reset wrapper (bank 04 `$802D` hook) |
| `$FF2C` | Area change (bank 1 `$85B4`): native init, marks the Enhanced draw pending (`$2258 = $FE`) |
| `$FF35` | Stage load (bank 1 `$82CD`): native init, cache invalidation, entrance draw |
| `$FF42` | Pending area-change draw, called every main-loop frame by the Select hook |
| `$FF70` | Gameplay Select hook |
| `$FFB0` | Banked renderer lookup |
| `$FFD0–$FFE5` | Shared speed bridge |
| `$FFE6–$FFED` | English reset initialization — occupied production code |
| `$FFEE–$FFF5` | Free (`$FF`) |
| `$FFF6–$FFFF` | Native interrupt/reset vectors |

Earlier timing tests temporarily used `$FFE6` as a stub; that range is now
occupied by English initialization. Do not boot with such a stub installed.

Preserve caller registers, processor flags, bank mappings and all borrowed
zero-page scratch. The early renderer saves `$06–$0B` and `$25–$30`. IRQ
behavior and individual block-transfer lengths matter in addition to total
frame cost. Existing 16/32-byte transfers are intentional.

## Contact damage and NES Firewheel

Every enemy, projectile and boss runs the contact check `$A186` (bank 2,
mapped at `$A000`) before its kill check (`$A1D4`, bosses `$A211`): contact
(`jsr $94DF`) sets the knockback direction (`<$37` bit 0) and calls
`$8F70` with A = 1 from `$A1C8`/`$A1D0`, the routine's only `jsr` callers.
`$8F70` returns at once while Ryu is immune (`<$36` bit 5, `<$37` bit 2);
otherwise it takes the damage and starts the knockback (Ryu's state
`$2EAB = 9`). Timer expiry (`$9BC3`, A = 16) jumps there too; pits do not.

The Fire Wheel (item 7 of the pickup table at bank 2 `$A6D6`: `$A6A6`, then
`$A919`) is item effect type 5 in the effect slots `$310E–$3112`; `$A919` is
the only code that creates type 5. Its handler (`$AF21`, from the effect
table at `$AB12`) counts `$317A` down from 10 at each stage-timer tick and
removes the effect at 0 (about 650 updates); the initialization sequence at
bank 1 `$82A2` clears the slots (`$A75D`). The effect kills what it touches through `$AA74` in the enemy's kill
check, after the contact check, and its hitbox reaches only a few pixels
below Ryu's feet: an enemy Ryu falls onto faster than that, and anything the
kill check does not kill (bosses, some types, e.g. 48 in 6-4 A), touch Ryu
first and hurt him.

**Use NES Firewheel logic** (`$2100` bit 2, 1.11-dev; module
`src/nes-firewheel`) makes the wheel behave like the NES game's Invincible
Fire Wheel. All its code is in bank 3's unused tail (`$DC00–$DD95` of the
claimed `$DC00–$DFFF`; bank 3 is mapped at `$C000` whenever object code
runs), reached from 3-byte hooks in bank 2; with the bit clear each hook
runs the instruction it replaced. The option adds no fixed-bank bytes.

| Hook | NES behaviour with the bit set |
| --- | --- |
| Damage gate `$FE20` → rule `$DC00` | No damage, knockback, hurt state or sound from any contact while a type 5 effect exists; pits and the timer still kill; no grace period when it ends |
| `$AA8A` (box in `$AA74`) | The wheel's box is Ryu X-9..X+12, feet-25..feet with the native strict tests (NES: X − Ryu X in [−(hw+8), hw+11], feet difference in [−24, h−1]); native box X±20, feet-35..feet+3 |
| `$A211` (boss kill check) | While a wheel touches the boss, its hit flag `$3036` is cleared, so it loses a point every update (native: one per contact); at 0 the native death takes over |
| `$AF2D` (wheel handler countdown) | 516 updates counted only while the stage timer runs (`$2EDA` 1-65 at the handler; `$FF` from a boss's defeat through the tally), the native tick sound at 96 and every 60, hidden on alternate updates in the last 180, ends at once when health is 0 (native: 10 timer ticks, about 650 updates) |
| `$A6AB` (wheel pickup) | Art set to none (6), art projectiles (types 0-2) removed, a time freeze ended as its own end does (`$AEFA`), a second wheel restarts the first |
| `$A6B5/$A6BF/$A6C9/$A6D3`, `$A682` (art and time-freeze pickups) | Remove the wheel at once |

Not reproduced (open decisions): enemy types the native code never gives
a kill check (7, 8, 11, 48 per the audit; 11 and 48 seen in 5-4 and 6-4 A)
stay unkillable; a boss dies on the update its health reaches 0 (NES: the
next touching frame); the HUD shows no art while the wheel spins (NES: the
wheel's icon); the tick sound is the native wheel tick. Up+attack shows the
throw pose with no projectile and no ninpo, as on the NES. Evidence:
[validation/nes-firewheel.md](validation/nes-firewheel.md).

A menu row would only toggle bit 2 of the draft (`DRAFT eor #4`, as
`option_masks` does for bits 0-1) and draw its value; accept already copies
the draft to `$2100`.

## Facts kept from retired build scripts

These were recorded only in the pre-1.00 builders and release notes, which are
no longer in the repository.

- **Stage indices** (Level Select, `$2241`, `start_stage`): 0 1-1, 1 1-2,
  2 2-1, 3 2-2, 4 2-3, 5 3-1, 6 3-2, 7 3-3, 8 4-1, 9 4-2, 10 4-3, 11 4-4,
  12 5-1, 13 5-2, 14 5-3, 15 5-4, 16 6-1, 17 6-2, 18 6-3, 19-21 6-4 A-C.
- **Menu text encoding** (`scripts/menu_text.py`, `src/options/options-text.inc`):
  letter = `$80` + position in the alphabet (A = `$80`, Z = `$99`),
  digit = `$A0` + digit, `$9A` is '-', `$9F` is a space. For example
  `$92 $93 $80 $86 $84` = "STAGE". `$AA` ('.') and
  `$AD` (':') are the menu's own glyphs (see the menu display below). Since
  1.10 the menu text is generated from `src/options/menu.txt`.
- **Level Select next-script table** (`selected_next_sequence`, also
  `NEXT_SEQUENCE` in `scripts/comparison_video.py`): the native master script
  is 38 two-byte records (kind, parameter) at headerless ROM offset `$805`.
  Kind 0 starts the stage whose index is the parameter. The table holds each
  stage's record index + 1, because the dispatcher increments its cursor
  after selecting a record; this gives `4, 5, 7, ..., 35` (re-derived from the
  original ROM for this document).
- **Stages without a renderer:** captures of 1-2, 2-1, 2-3, 3-3, 4-3, 4-4,
  5-1, 6-2 and the three 6-4 boss phases showed their native parallax
  disabled (REV6-era audit, 2026-09). They have no backdrop for the patch to
  replace; they are not missing renderers.
- **Interrupts and banking:** the audio interrupt code (bank `$38`) saves and
  restores the mapper banks it uses, read in its disassembly during the REV6
  work. This is what makes changing MPR2/MPR3 in the main loop safe.
- **First playfield line:** the native raster split leaves the first
  playfield line (screenshot row 50) different from an ordinary backdrop row;
  REV5-era pixel checks compared that line with the original's output rather
  than with a decoded model.
- **Boot sequence:** native and byte-identical since 1.10-dev, which removed
  the community notice (splash) that 1.09 ran before the publisher scene
  through a bank 4 `$8001` hook and a fixed `$FEBE` wrapper; both are the
  original bytes again. An earlier build (REV6A) shortened the publisher
  screen; REV6B reverted that.

## Menu display

The menu draws four rows, laid out in `src/options/menu.txt` (generated into
`menu-text.inc` by `scripts/menu_text.py`; `#` runs mark the STAGE, PARALLAX
and NO DAMAGE value fields, whose BAT positions become `STAGE_AT`,
`PARALLAX_AT` and `DAMAGE_AT`): the HUD's rows 28-30 and the blank band
under the HUD, row 31. The selected value blinks (16 frames shown, 16 blank;
counter in zero page `$27`, saved by the menu). Its `.` and `:` are glyphs
in the native style uploaded to the HUD font's blank tiles `$7AA` and `$7AD`, and
`/` to the blank tile `$7B9` after the health-bar pieces (glyph planes 0-1 are
stored; plane 2, the font's background, is computed).

- Rows 28-29 (score/stage, timer/ninja) are backed up on the stack, as in
  1.09. The stack has no room for a third row: with two the menu reaches
  `$215B`, 27 bytes above the watched margin.
- Row 30 (lives, ninpo, item box, enemy bar; VRAM `$0780-$079F`) is parked
  word by word in the blank tiles `$7AB-$7AC` (`$7AB0-$7ACF`).
- Row 31 holds 32 blank HUD words (`$F79F`) in gameplay and is written back
  as such.

Closing the menu (**Run** accepts, **Select** cancels) copies row 30 back, zeroes tiles
`$7AA-$7AD` and `$7B9` and blanks row 31; this adds no stack depth. The held item's
icon is a sprite over the item box (columns 13-14 of rows 29-30), in front of
the HUD, so the layout keeps those columns blank and the generator rejects
text there. Ryu can still cover the HUD if the menu is opened while he is
above the playfield, as in normal play. The left column starts at the
screen's first column (`PARALLAX: OFF` fills the 13 columns left of the item
box).

Evidence (1.10, emulated): VRAM write watches over `$7AA0-$7ADF`, `$7B90-$7B9F` and row 31
during all 22 Level Select stage loads and the 11 comparison runs (area
changes included) saw only zeros and `$F79F` in gameplay; the stage loads
write those values. A cinema writes `$0100` into row 31 (seen after 4-1, 5-3
and 6-3); the menu cannot open there, and the next stage load restores the
row. `scripts/check_menu.py` opens the menu throughout the stored runs and in
every Level Select entry and requires VRAM, the sprite table and the palette
to be unchanged on return, and RAM except where the interrupt or the menu
legitimately writes. Re-audit if the HUD, the font loader or the menu's open
conditions change.

## Cinema VRAM ownership

Enhanced 2-2 uses VRAM words `$7200–$72FF` for its tile atlas. Native cinemas
reference the same 512 bytes as blank 32×32 sprite pattern `$0390`, without
reloading it. The native `$F728` sprite reset clears SAT buffers at
`$7E00–$7FFF`, not this pattern. Residual mountain tiles therefore become
visible garbage sprites above the story picture after 2-2.

The bank 04 `$802D` hook calls fixed `$FEE0`: first the original `$F728`, then
bank `$46:$4300` to zero exactly those 256 VRAM words before cinema graphics
load. The wrapper preserves A, X, P, and MPR2; Y is untouched. The helper
preserves the VDC selector shadow/register and uses the increment-one mode
already assumed by the preceding native reset. It allocates no new RAM.
This is a gameplay-to-cinema ownership handoff, not an atlas or art change.
