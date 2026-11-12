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
| Palettes | Set table bank `$37:$6000` (address, colour count; 22 sets, data to `$717F`); loader `$F211` (A = set) unpacks into the RAM palette `$2286`: per 8 colours a byte of bit-8 values (MSB first), then 8 low bytes. Sprite palettes: `$F1C0` (A = palette n, X = sprite row) unpacks 16 colours from `$37:$7180 + 18n` (Ryu: 96 at `$7840`; the highest used, 151, ends at `$7C2F`). Both map bank `$37` in MPR3 and unpack with `$F2BE` (source `<$19/<$1A`, first colour `<$15/<$16`, count `<$17/<$18`); no other code maps bank `$37`. HUD colours: bank 1 `$83C3` writes 7 words from `$83E5` to entries `$F1-$F7` through `$F23C` (stage load, every area change, `$86A7`) |
| Profile → palette set | 1-1: 1, 2-2: 4, 3-1/3-2: 6, 4-1: 8, 4-2: 9, 5-2: 13, castle (5-3/5-4/6-1): 14, 6-3: 16 |
| Stage → set (`$F211` at the stage load, all 22 entries) | 1, 2, 3, 4, 5, 6, 6, 7, 8, 9, 10, 11, 12, 13, 14, 14, 14, 15, 16, 17, 17, 18; sets 0 and 19-21 are the title's and cinemas'. No set loads at area changes (sprite palettes and the HUD do) |
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
| `selector-hook`, `options` | Stage selection, progression synchronization, the popup menu (all options and the language) and its version/credit line; a chosen stage starts with full health (`$2EAD = 16`, 1.09-dev) |
| `cinema-sprite` | Cinema sprite-pattern reset (below). Enhanced has no boot screen since 1.10-dev |
| `bram` | Saved settings (1.11-dev): the reset trampoline with the defaults (the old `english` module: English is `DEFAULT_LANGUAGE`), the loader and the menu's save, in backup RAM ([saved settings](#saved-settings-backup-ram)) |

The canonical bank allocations are in
[`src/modules.json`](../src/modules.json). Do not use old experimental `.sym`
files to allocate free space.

## RAM contracts

| CPU address | Meaning / constraint |
| --- | --- |
| `$2100` | Active options: bit 0 Original, bit 1 No Damage, bit 2 Use NES Firewheel logic, bits 3-5 palette mode (1.11-dev; [palette modes](#palette-modes): `$00` Original, `$08` NES-A, `$28` NES-B, `$10` GB DMG, `$18` HELL, `$38` SMS; `$20` and `$30` unassigned), bit 6 unassigned (zero), bit 7 set exactly when bits 3-5 are SMS (a copy the upload tests; SMS is `$B8` in `$2100`). All eight bits are settings: a saved-settings record stores the byte as it is. Whoever changes bits 3-5 writes bit 7 with them and, while a mapped mode is live, also queues all 512 colours (`$F394`). Zero = the defaults |
| `$2101` | The menu's draft while it is open: bits 0-5 the options (copied into `$2100` on Run, bits 6-7 of `$2100` kept), bits 6-7 the language (written to `$3227` on Run). Meaningless while the menu is closed |
| `$2260-$2280` | Native palette upload queue: count, then 8 entries of byte count (low `$2261`, high `$2269`) and first colour (low `$2271`, high `$2279`); `$F350` adds one under the lock and drops it when 8 are queued; `$F394` replaces the queue with all 512 colours |
| `$2281-$2283` | Border colour (written to VCE entry `$100` after each upload) / upload lock |
| `$2286-$2685` / `$2686-$2A85` | RAM palette (512 words, the source of every upload) / its backup (`$F718` copies to it, `$F720` back; fades compute `$2286` from it) |
| `$2102–$2103` | Entrance anchor |
| `$2104` | The palette module's state (1.11-dev SMS; before it `$2100` bits 5-7): bit 5 a left-over palette entry is queued, bit 6 the main loop was busy at the last vblank with palette work, bit 7 the VCE holds mapped colours (GB DMG, HELL or SMS); bits 0-4 zero. Not a setting: never saved; zero at reset (the RAM clear `$E023`), and clearing it costs at most one needless full re-upload |
| `$2105` | Save status (1.11-dev, `src/bram` ST_ values 0-8: what the reset found in backup RAM, then what the last Run's save came to); the menu shows it. Not a setting; zero (NONE) from the RAM clear until the loader sets it |
| `$2106–$213F` | Watched stack margin; not general-purpose spare RAM |
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

The CPU stack grows down from `$21FF`. Since 1.11-dev the menu keeps only
11 bytes there (zero page `$25-$2C`, the VDC selector `<$11`, `$2100`); its
backup is in VRAM. Its deepest use, with the vblank interrupt's palette work
on top, reached `$21D3` from the hook's `$21FB` (1.10's menu, with two HUD
rows on the stack, reached `$215B`). Reserved low-stack variables were
checked with memory guards. Changes to call depth or menu backups need fresh
guard checks.

## CPU entry points and hazards

| Address | Purpose |
| --- | --- |
| `$8097 / $80AB` | Native background render / initialization |
| `$8244` | Native stage initialization (stage in A) |
| `$8457 / $8478` | Gameplay loop / native completion path |
| `$8457-$845C` | Gameplay loop calls `$E3F2`, `$ABD7`; Enhanced: `jsr $FE40` (which makes both calls) and three NOPs |
| `$FE20` | Damage gate (bank 1 `$8F70`): No Damage, then the NES Firewheel protection rule (`$DC00`, bank 3); timer expiry explicitly bypasses optional immunity (`$9BC3` jumps to `$FE34`). `$FE3E–$FE3F` unused in the options range |
| `$FD13` | Vblank interrupt's palette upload (native `jsr $F3B5`): `jsr $FEC0` |
| `$FEBE–$FECE` | Palette trampoline (1.11-dev, 17 bytes): `$FEBE` palette_now (stage modules: write colours X..X+Y-1 of the RAM palette to the VCE at once, in the mode's colours), `$FEC0` vblank upload; both map bank `$46` into MPR2 and restore the MPR2 they found (the SMS mode switches MPR2 to bank `$3B` on the way) |
| `$FECF–$FEDF` | Free (`$FF`, 17 bytes) |
| `$F1DC`, `$F234` | The sprite-palette and colour-set loaders' unpack calls (native `jsr $F2BE`): `jsr $7FE0`, the NES palette hook in bank `$37`'s free tail (MPR3 holds bank `$37` at both; 1.11-dev) |
| `$CE98-$CE9C` (bank 3) | The animation-set setup's table pointer (native `lda #$32 / ldy #$CF / plx`): `plx / jsr $D400 / nop`, the NES copy of the animation table in NES gameplay (1.11-dev) |
| `$FE40 / $FE46` | Early wrapper / preserved-scratch renderer entry |
| `$FEE0` | Development cinema sprite reset wrapper (bank 04 `$802D` hook) |
| `$FF2C` | Area change (bank 1 `$85B4`): native init, marks the Enhanced draw pending (`$2258 = $FE`) |
| `$FF35` | Stage load (bank 1 `$82CD`): native init, cache invalidation, entrance draw |
| `$FF42` | Pending area-change draw, called every main-loop frame by the Select hook |
| `$FF70` | Gameplay Select hook |
| `$FFB0` | Banked renderer lookup |
| `$FFD0–$FFE5` | Shared speed bridge |
| `$FFE6–$FFF5` | Reset trampoline (1.11-dev, `src/bram`, 16 bytes: the English initialization's 8 and the 8 free bytes after it): maps bank `$46` in MPR2, calls the settings loader `$4B00`, restores MPR2, jumps to the native `$FCBE` — occupied production code |
| `$FFF6–$FFFF` | Native interrupt/reset vectors |

Earlier timing tests temporarily used `$FFE6` as a stub; that range is now
occupied by the reset trampoline. Do not boot with such a stub installed.

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

The menu's **NES FIREWHEEL** row (1.11-dev) sets bit 2 of the draft; Run
copies it to `$2100`.

## Palette modes

`$2100` bits 3-5 (1.11-dev; module `src/palette`). Bits 3-4 are the upload
family, bit 5 a variant within it; bit 7 is set exactly when the mode is
SMS. **Names:** the mode called HELL in the source (`hell.json`,
`PALETTE_HELL`, `HELL_*`, `hell_*` scripts and validation records) is the
one the player sees as **APOCALYPSE** (menu value and guides, since the
reset-row build); same value `$18`, same colours.

| Value | Mode | Upload |
| --- | --- | --- |
| `$00` | Original (default) | native |
| `$08` | NES-A (other palette data loaded into the RAM palette, [NES palette mode](#nes-palette-mode)) | native |
| `$28` | NES-B (the re-lit NES data, loaded the same way) | native |
| `$20` | unassigned | native (as Original) |
| `$10` | GB DMG | mapped, GB DMG table |
| `$30` | unassigned | as GB DMG |
| `$18` | HELL | HELL's own upload (bank `$43`) |
| `$38` (`$B8` with bit 7) | SMS | GB DMG's upload with the SMS table (bank `$3B`) |

The upload masks `$2100` with `$98` (bits 3, 4 and 7) and compares with
`$10`, the instructions it had before SMS with another mask: equal is GB
DMG, below (carry clear) the native upload, above family 11, where the N
flag of the same compare tells SMS (`$98 - $10`) from HELL (`$18 - $10`).
So the SMS copy in bit 7 costs nothing to tell apart; whoever writes bits
3-5 writes bit 7 with them (the menu's `set_palette` does). A test for "an
NES mode" is `and #$18 / cmp #$08` (the `nes-palette` branch's test,
unchanged); "which NES" is bit 5 (`and #$20`, or `bit #$20` with A already
holding `$2100`). Bit 6 is free for a further option. Evidence:
[validation/gb-palette.md](validation/gb-palette.md),
[validation/hell-palette.md](validation/hell-palette.md),
[validation/sms-palette.md](validation/sms-palette.md).

The native game writes colours only into the RAM palette `$2286` and queues
ranges (`$F350`); the vblank interrupt (`$FCD7`) uploads the queue at `$FD13`
(`$F3B5`: one TIA per entry from `$2205`, then the border colour to entry
`$100`; nothing while the lock `$2283` is set). Fades queue the whole range
each step and compute `$2286` from the backup `$2686`. In the original game
only `$F3B5` writes the VCE; in Enhanced also the 1-1 and 2-2 renderers'
merged palettes (below).

The upload goes through the trampoline at `$FEC0` to bank `$46` `$5000`:

- Original, NES-A and NES-B (and `$20`), or `$2240` != 0 (cinema, title,
  ending): the native `$F3B5`. NES colours are not a mapping: they are other
  palette data, loaded into the RAM palette ([NES palette mode](#nes-palette-mode)).
- GB DMG in gameplay: the same queue, each colour looked up in a 512-entry
  table (`scripts/palette_tables.py` from `src/palette/gb-dmg.json`:
  luminance thresholds and four shades; four 256-byte pages at
  `$5400-$57FF`). The mapped loop costs about 156 master clocks a colour
  against the TIA's 42, so a vblank uploads only what fits two limits. It
  must end before the display: at most 168 colours, 6 fewer for each further
  queue entry (the first display line is about 22.8 lines after the vblank
  interrupt). And it may take no longer than the native upload of the same
  entries: 0.266 mapped colours per native one, less 6 per further entry,
  at least 16, because in the frames around an area change the native main
  loop has under a line to spare (6-3); the stored runs' worst mapped upload
  ends 18.2 lines after the interrupt. Small new entries go before a
  left-over one, fade steps (512 colours) after it; what
  is left becomes one entry that starts where the upload stopped and runs on
  past colour 511 to 0 far enough to cover the rest (only this upload ever
  sees such an entry: the native one always gets a full re-queue first),
  marked by `$2104` bit 5. A left-over entry alone gets 16 colours a vblank when the main loop was
  waiting for vblank (interrupted PC in `$FD67-$FD6F`) at this vblank and at
  the last one with palette work (bit 6), otherwise none. A full queue (8
  entries: `$F350` may have dropped one) leaves all 512 colours over.
  The fade rule (branch `dark-lift-fix`; GB DMG, SMS and HELL): while the
  native fade's level `$2A8A` is `$FF` (bit 7: the stage-end fade-out,
  bank 1 `$8510` and `$F422`, has computed its last step, all black, and no
  fade has begun since) a left-over entry gets 136 colours a vblank instead
  of 16, under the same idle condition. The game loads the next stage 8
  ticks after that step, holds the lock and empties the queue when it
  starts the fade-in (`$F436` calls `$F345`), so whatever the upload has
  not written by then stays in the VCE as the step before black while the
  new stage's tiles are drawn; 136 colours (what a fade step gets in its
  first vblank) complete the black four ticks before the load. The level
  byte sets the pace only: the colours come from the RAM palette through
  the table. The paths without that state take the cycles they took before
  the rule. Cuts to black that are not fades (an area change's fill of
  colours 0-255 with the load at the next tick, the fill after a boss) are
  still uploaded at the old pace and arrive late or not at all
  ([validation/dark-lift.md](validation/dark-lift.md)).
- HELL in gameplay: the same queue and the same budget rules, but only VCE
  entries 0-239 (background palettes 0-14) are looked up, in the HELL table
  (`src/palette/hell.json`: the owner's mock-up "Lava" retuned as candidate
  D, the owner's choice of 2026-11-11 "1-1 more like 2-2": cool greys and
  dull teals take 2-2's column golds; ported operation for operation), with
  one per-stage override (below) and, since branch `dark-lift`, the dark
  lift (the dark-lift study's "Hb"): the dark ends of the green, grey and
  steel ramps are raised and saturated pure greens (hue 100-140 degrees,
  saturation at least 0.9) have a ramp of their own, the optional "leaf"
  family (`leaf_ramp`, `leaf_windows`, `leaf_mix`), so 21 colours show
  lighter and no colour but black shows black (candidate D sent `$040`
  there and the trunks and fill of 4-1's back layer to one near-black).
  The darkest grey `$049` now shows R3 G1 B0, lighter than the next grey
  `$092` (R1 G0 B0, unchanged; open, see
  [validation/dark-lift.md](validation/dark-lift.md)). Each chunk stops at entry 240; from there on (the HUD palette
  15, the sprite palettes and the border, entry `$100`, which is sprite
  palette 0's transparent colour) the colours go unchanged by a TIA that the
  upload builds on the stack (`tia src,$0404,len / rts`) and calls, at the
  native 42 master clocks a colour; such a chunk of n colours is charged
  n/4 + n/32 + 3 colours of the budget (measured: about 0.27 n + 0.7 of a
  mapped colour's 156 clocks beyond the per-chunk work the mapped loop also
  has). The code (1,005 bytes, `$7800-$7BEC`) and the table are in bank `$43`
  `$7800-$7FFF`, mapped in MPR3 for the upload (pushed and restored; code
  running in MPR3 cannot unmap itself, so the exits that restore it are in
  bank `$46`).
- HELL's per-stage override (1.11-dev, `hell.json` `stage_overrides`): one
  stage may show one low-half colour (`$001-$0FF`) as another colour than
  the table's. Shipped: in 1-1, `$094` (R2 G2 B4: the sidewalk's fleck,
  palette 3 entry 5, and the skyline's shadow faces, Enhanced palette 1
  entry 2; also entries 1 and 181) shows `$050` (R2 G1 B0, the dark gold
  of 2-2's columns) where the table keeps crimson (R6 G0 B1) for 2-2's far
  ridge, which uses the same input colour. No RAM and no stage-load hook:
  where the upload picks its loop (each mapped chunk in `hell_chunk`, and
  `now_hell` for palette_now) it reads the visible stage `$2E5F` and
  compares it with the generated `HELL_OVERRIDE_STAGE`; in that stage it
  runs `hell_colour_ovr` / `now_hell_ovr`, the same loops with `cpx
  #HELL_OVERRIDE_KEY / beq` on the low half (4 cycles a low-half colour;
  a hit writes the immediate `HELL_OVERRIDE_LO/HI`, 4 cycles fewer than
  the lookup). Elsewhere the choice costs 9 cycles a mapped chunk (`lda
  $2E5F / cmp # / beq`). The table and the budget are unchanged, so
  `$2E5F` alone decides which colour a frame's upload writes: the colour
  follows the stage from the first upload after `$2E5F` changes (Level
  Select, the stage's own load, the popup). Without an override the
  stage equate is `$FF` (never visible). A further colour for the same
  stage is one more `cpx/beq` and hit in each loop (+4 cycles a low-half
  colour each); `scripts/palette_tables.py` (`HELL_OVERRIDES_MAX`) refuses
  more than the loops compare. Another stage needs its own compare of
  `$2E5F`. `palette_tables.hell_stage_table(stage)` gives the colours a
  stage shows (the checks use it). Evidence:
  [validation/hell-1-1.md](validation/hell-1-1.md).
- SMS in gameplay: GB DMG's upload, instruction for instruction, with the
  SMS table (`src/palette/sms.json`: each channel to the nearest of the
  Master System's four levels 0/85/170/255 in linear terms, shown as PC
  Engine 0/2/5/7, so 0-1 → 0, 2-3 → 2, 4-5 → 5, 6-7 → 7; the owner's
  mock-up candidate A; every output is one of 64 colours; since branch
  `dark-lift` with `dark_rescue`, the study's "Sa": a colour that rule
  sends to black although its luma R × 0.299 + G × 0.587 + B × 0.114 is at
  least 0.5 of 7 takes level 2 in each channel that holds 1, which is the
  four colours with green 1 and no channel above 1: `$040` → `$080`,
  `$041` → `$082`, `$048` → `$090`, `$049` → `$092`; `$001`, `$008` and
  `$009` still show black. Two side effects: the darkest fade step became
  visible, which showed VCE entries the upload had not brought to black
  when a load took the lock (6-3's floor for 7 frames after 6-2; closed by
  the fade rule above); and the four rescued colours now show lighter than
  their neighbours whose green 1 the channel rule drops (`$049` grey 222
  against `$04A` blue 002), in stills and in fade steps (open,
  [validation/dark-lift.md](validation/dark-lift.md))). Bank `$3B`
  `$5000-$57FF` holds a byte-for-byte copy of bank `$46` `$5000-$53FF`
  (assembled from the same source lines, `;@mirror` in `main.asm`, as
  `sms-mirror.inc`; a guard per label checks each copy's address) and the
  SMS table at `$5400` where bank `$46` has GB DMG's. In family 11 a `bmi`
  sends SMS to `vblank_sms` / `now_sms` (bank `$46` `$5A00-$5AFF`, with
  `fold_queue`, which moved there to make room), which do `lda #$3B / tam
  #2` and carry on at GB DMG's `vblank_gb` / `now_gb`, now bank `$3B`'s copy,
  reading the SMS table. The trampoline restores MPR2 when the upload
  returns. Because the code is GB DMG's, SMS has GB DMG's budget,
  left-over and full-queue behaviour, and timing, plus 25 CPU cycles of
  dispatch in the vblank (23 in palette_now; about 0.05 line).
- The Original and GB DMG paths take exactly the cycles they took before
  HELL: the HELL test rides on branches those paths already took (the
  vblank's `bne` for Original now leads to a `bcs` that Original falls
  through, paid for by a `bpl` turned into a `bmi`; palette_now's entry
  saves 2 cycles that the Original and GB paths spend on a `bcs` and a
  `nop`). Only the frame a mapped mode is left for Original starts its
  re-queue 4 cycles later. SMS added no instruction to them: the state
  moved from `$2100` to `$2104` with the same absolute `lda`/`sta`, and the
  SMS test rides on the compare. HELL's paths also take exactly the cycles
  they took before SMS: the family-11 `bmi` (2 cycles, not taken) is paid
  inside them. The gameplay vblank tests `$2240` before mapping bank `$43`
  (a `bne` not taken in bank `$46` instead of a taken `beq` in bank `$43`:
  31 cycles from the `bcs` to `hell_gameplay` either way); HELL's cinema
  vblank no longer maps bank `$43` and is padded to the old 42 cycles to
  `vblank_cinema` (`tma/pha/pla/tam`, an `lda`, three `nop`s, so the stack
  sees the same byte); palette_now's HELL path drops a `sec` (the dispatch's
  compare leaves carry set) and, in a cinema, leaves by a 2-cycle shorter
  exit. Since the per-stage override HELL's gameplay paths take 9 cycles
  more per mapped chunk (and per palette_now with colours below 240), and
  in 1-1 4 cycles more per low-half colour; the other modes' paths are
  unchanged (only the operand of bank `$46`'s `jmp now_hell`, a HELL-only
  instruction, and its copy in bank `$3B` moved with the HELL code).
- `$2104` bit 7 records whether the VCE holds mapped colours; when the
  colours due differ (Original against a mapped mode, cinema started or
  ended) the upload queues all 512 first (`$F394`). The bit does not say
  which table (the cycle-exact GB DMG path cannot test more), so whoever
  changes bits 3-5 between mapped modes must also call `$F394`; the menu
  does that on every change of the live mode. The RAM palette always holds
  the original colours.

1-1 (palette 1) and 2-2 (palettes 13-14) write their merged palettes into
the RAM palette and call `$FEBE` (palette_now) to write them to the VCE at
once, as the backdrop they draw shows in that frame. Before 1.11-dev the 1-1
palette existed only in the VCE, so any full re-queue (the area-1 fade in the
stored 1-1 run) put back the native palette 1 and showed the Enhanced
backdrop in wrong colours until the stage changed.

### NES palette mode

Family 01 (module `src/nes-palette`): NES-A (`$08`) and NES-B (`$28`,
bit 5 set). Every test of the family is `and #$18 / cmp #$08`; the NES-B
choice (`and #$20`) comes only after it, so Original, GB DMG, HELL and SMS
run the instructions they ran before NES-B. NES-A shows the game in NES master-palette
colours only (the 47 9-bit colours of the 2C02G composite palette) with the
PC Engine's full detail, reading as NES Ninja Gaiden: every stage's colour
set, Ryu, the HUD, every enemy, item and boss sprite palette and every colour
the game animates (owner's rules, 2026-11-11: "all the bosses should be 8
bit and all the rooms should follow"; NES colours only, TG16 detail).
Cinemas and the title stay original. Its colours are data, colour values
and role names only: `src/nes-palette/stages/*.json` (one file per colour
set, plus the 3-2 variant of set 6), `shared.json` (HUD, Ryu's sprite
palette 96), `sprites/*.json` (every other sprite palette loaded in
gameplay, grouped by object: Ryu's effects, items, enemies, one file per
boss) and `animations.json` (the animated colour lists).
`scripts/nes_palette.py` resolves the roles, checks the files' original
colours against the original ROM, fails the build on any colour outside the
NES set and generates the `nes-*.inc` files at build time (prepare step
`nes-palette`) and the NES versions of the 1-1 / 2-2 merged palettes
(`nes-enhanced-stage11`, `nes-enhanced-stage22`, after the backdrop steps).
Swapping the colours needs no code change.

4-1 (set 8, since branch `dark-lift`, the study's "Na"): the bark entries
of rows 0 and 3 (entries 6 and 8-11, the trunks of the Enhanced back layer)
have a role of their own, `backwood` (ramp `09`, `18`; strict; `08`
excluded), so they resolve above the darkest green `08` (`$040`) that the
fill behind them and the rest of the foliage take: `$080`, `$092`, `$080`
(NES-B `$090`), `$0A0`, `$090`. Only set 8 differs in the generated
includes (10 bytes in each variant); `scripts/nes_palette.py` is unchanged.

Resolution keeps detail: within each palette row (16 set entries, one sprite
palette, one animation set) distinct PC Engine colours of a role go to
distinct NES colours in the same lightness order, the role's NES hue the
anchor and the neighbouring hue columns, greys and near-greys the extension;
two colours share one only where keeping them apart would shift a colour by
more than about 30 L* (re-lighting the scene). The build prints the rows
that still merge; `nes_palette.py detail` lists them.

- Loaders: `$F211` and `$F1C0` call `$7FE0` in bank `$37` (their own MPR3
  bank; `$FF` in the original from `$7C30`) instead of `$F2BE`. The 26-byte
  hook tests bits 3-4 = 01 and otherwise jumps to `$F2BE` with nothing
  pushed (15 cycles more per load). In NES mode it maps bank `$45` into MPR2
  and calls `nes_unpack` (`$45:$4000`): only in gameplay (`$2240` = 0), a
  sprite palette (source `$7180` up: only `$F1C0`) by its number, which
  `$F1E4` leaves doubled in `<$21/<$22` (one table entry per number from the
  lowest with a copy), or a colour set (`<$21`, checked against its table
  entry) with one: the stage's variant when `$2E5F` names one (3-2, set 6),
  else the set's copy (none for the title/cinema sets 0 and 19-21). A copy's
  high byte + `$80` marks bank `$45` (mapped into MPR3 for the unpack, then
  bank `$37` back); other sprite copies sit in bank `$37`'s free tail and are
  read in place. It points `<$19/<$1A` at the copy (`$6000` window), calls
  `$F2BE` and restores `<$19/<$1A`, X and Y. Everything downstream (the
  backup `$2686`, fades, the vblank upload) works on the RAM palette, so it
  carries the NES colours with it.
- Animated colours: the stage load calls bank 3 `$CE8D` (A = animation set,
  0-14) which copies the set's records (count; per list delay, background or
  sprite, entry, list address) from the pointer table `$CF32`; every update
  `$CED7` counts each list's delay and writes its next colour word through
  `$F23C` (a word with high byte `$FF` ends a list). `$CE98` now calls
  `nes_anim_table` (bank 3 `$D400`), which gives the NES copy of the whole
  table in NES gameplay (same records, delays and list lengths; NES colours)
  and the original `$CF32` otherwise; X is kept. Sets: 0 2-3 orbs, 1 6-4C,
  2 1-1, 3 5-2, 4 3-1, 5 2-1, 6 4-2, 7 5-1, 8 1-2, 9 4-4, 10 6-2, 11 3-3,
  12 6-4A/B, 13 4-3, 14 6-3. No other code writes the RAM palette in play
  (write watch over `$2286-$2685`).
- Sprite palettes in gameplay: rows 0-2 Ryu (96, 97, 98) at every load;
  boss rooms load their boss rows in the stage loader (bank 1 `$8790-$8B1B`:
  1-2 102; 2-3 103; 3-3 104; 4-4 105; 5-4 106, 101; 6-4A 75, 107, 100; 6-4B
  108, 103, 100; 6-4C 110, 111, 112; row 13 109); other stages a row-14
  palette by stage (`$8708`, table `$8714`: 113-121) and per area a list of
  (row, palette) pairs (`$9916`, lists `$9A4A-$9B67`: 122-151).
- HUD: bank 1 `$83C3` is a 19-byte trampoline to `nes_hud` in bank `$45`,
  which writes the 7 words as the native routine did, from the NES table in
  NES gameplay, else from `$83E5`; it returns A, X, Y, the flags and `$2E88`
  as the native routine did. (The routine's old bytes `$83D6-$83E4` are dead.)
- 1-1 and 2-2 copy `extra_palette_nes` / `palette13_nes`, `palette14_nes`
  instead of their merged palettes in NES mode (a mode test before the copy).
  Each NES colour is the NES colour of the native set entries that supply
  most of the merged colour's pixels.
- NES-B (1.11-dev, `all-palettes`): `relit(data)` in `scripts/nes_palette.py`
  resolves the same role data with each role's dark PC Engine shades lifted
  into the lightness range of its NES ramp codes (from the role's darkest
  colour over its whole file, set entries and animation lists, up to the
  ramp's lightest code, linearly, never darker; near-blacks stay black
  unless the role has `lift_black`; `lift` names a floor code; `lift:
  false` keeps a role as NES-A; no data file uses these keys yet), with the
  same detail rules and NES colours only. NES-B has its own 18 sets and 3-2
  variant (bank `$3B` `$4200-$4F7D`, read through MPR3 at `$6200` up), its
  own animation table in bank 3 after NES-A's (records of its own; a list
  equal to an NES-A list points there) and its own 1-1 / 2-2 merged
  palettes (`extra_palette_nes_b`, `palette13_nes_b`, `palette14_nes_b`;
  their copy loops out of line, behind a `jmp`, so the renderers' branches
  over the initialize block stay in range). Sprite palettes, Ryu and the
  HUD are NES-A's (the build checks it). In `nes_unpack` the set lookup
  tests bit 5 after the set's table check (`set_lookup_b`: variant by
  `$2E5F`, else the set, both from `nes_b_set_*` / `nes_b_variant_*`, bank
  `$3B` mapped into MPR3 for the unpack); `nes_anim_table` tests it after
  the family and `$2240`. NES-A pays for the tests: 9 cycles per set load,
  9 per animation-table choice, 11 at the 1-1 / 2-2 start.
- Not covered: cinemas and the title (original by design); Continue and Game
  Over screens were not checked.

Space (1.11-dev, NES palette draft 2 and NES-B): bank `$45` `$4000-$43FF` (code,
tables, the HUD words and the 3-2 variant, NES-B's set addresses and lookup:
874 bytes to `$4369`; 150 free)
and `$5200-$5FFF` (the 18 NES sets, then the sprite palettes that do not fit
bank `$37`: 3,276 bytes to `$5ECB`; 309 free). Bank `$37` `$7C30-$7FDF`: 52
NES sprite palettes (936 bytes to `$7FD7`; 8 free) and the hook
`$7FE0-$7FF9`. Bank 3: `$CE98-$CE9C` (the call) and `$D400-$DBFF` claimed
(the table helper, NES-A's and NES-B's animation tables, 1,796 bytes to
`$DB03`; 252 free); `$D3FD-$D3FF` untouched (next to the original's table),
`$DC00-$DFFF` the NES Firewheel's. Bank `$3B` `$4200-$4FFF` (file
`$76200-$76FFF`): NES-B's sets and variant, 3,454 bytes to `$4F7D` (the
bank's data end at `$41CE`; read/execute watches over `$761CF-$76FFF` saw
nothing on the build before: cold boot, the 11 stored runs, all 22 Level
Select entries). `stage61-upload`'s claim ends at `$51FF` (its code
ends at `$5113`, guarded). Every region has an `.if/.fail` guard. Fixed
bank: none of the free bytes; only the two call operands change. The bank 3
call costs every stage load in every mode about 25 cycles more.

The menu's **PALETTE** row (1.11-dev) offers the values listed in
`src/options/menu.txt` (in Left/Right order ORIGINAL, APOCALYPSE (`$18`, HELL in the source), NES-A, NES-B, SMS, GB_DMG since the reset-row build, before it ORIGINAL, NES-A, NES-B, GB_DMG, HELL, SMS; the values, and so the saved settings, are the same in either order; mask `$38`). While the menu is open the live bits 3-5 follow the
draft, and every change of them queues all 512 colours (`$F394`), so the
module re-uploads every colour at the next vblanks and the choice shows at
once (the menu waits in `$FD67`, so the left-over rule gets its 16 colours a
vblank: GB DMG's and SMS's 512 in about 25 frames, HELL's in about 12);
Select puts the old bits back (queuing all 512 again if they differ) and
waits until the queue is empty (at most 48 vblanks; Original is back after
one) before the game runs on. Run keeps the bits and restarts the stage,
which reloads the palettes.

The sound holds while the window is open (1.11-dev, `all-palettes`): the
menu saves the sound driver's play flags `$387E` (bank `$38`; bit 6 music,
bit 7 effect channels) on its stack and clears bits 6-7, so the driver's
vblank tick (`$FD16` → `$EA5B` → `$38:$43F0`) advances nothing and only
writes volume 0 to each channel (`$5066`); the flags go back after the
last vblank of the menu. The driver then goes on from exactly its state at
the Select hook (only zero page `$8B`, the tick's own scratch, which every
tick clears first, differs), so every interrupt after the menu takes the
time it takes without the menu; the channels sound again from the second
vblank after the return, with every PSG register as in the run without
the menu from then on. Before, the driver played on through the menu, its
vblank work afterwards took other time, and the main loop stood a few
cycles elsewhere at frame ends; that showed while an area change redraws
the BAT across frames (`check_menu.py` sweep, 8 openings in 2-2 and 5-3;
the same at any distance before the change once the comparison window
reaches it). The native pause (`$E0C2`, Run) uses the driver's own pause
commands (`$83`/`$86` through `$EA84`), which change its state, so the menu
does not use them. What the menu cannot hold is the timer: its interrupt
(`$FCD3`) only acknowledges, but with reload `$74` its period is 143 CPU
cycles longer than a frame, so after the menu it lands elsewhere in the
frame and moves the main loop by its own length; once in the sweep's 727
openings a frame end inside the 1-1 → 1-2 load saw one VRAM word apart
(`check_menu.py` lists such frames; `--strict` fails them).
NES colours need that reload, so they show after Run: while NES-A or NES-B
is highlighted in a menu opened in another mode, the live bits stay as the
menu found them (`$2100` on the menu's stack), and Run sets the draft's mode
through the same `set_palette` (bit 7 with it). Opened in an NES mode, the
RAM palette holds NES colours, so ORIGINAL previews them unmapped and the
mapped modes map them; Run reloads the stage in the chosen mode's own data.
A live NES preview would need the RAM palette rewritten with NES data and
the exact previous palette (fade state, animated and enemy colours)
restored on cancel: 1 KiB of backup the menu does not have; not done.

Bank `$46` (1.11-dev): `$4000-$40FF` dispatch, `$4100-$41FF` the menu's
status texts (`options`, 207 bytes, since the reset-row build), `$4200-$42FF`
unowned (256 bytes, still free), `$4300-$43FF` cinema
sprite reset, `$4400-$4AFF` the menu (`options`, 1,692 bytes used to `$4A9B`), `$4B00-$4FFF`
the saved settings (`bram`, 962 bytes used to `$4EC1`; entries `$4B00`
reset loader, `$4B03` save),
`$5000-$53FF` palette code (926 bytes used), `$5400-$57FF` its GB DMG
table, `$5800-$583F` 6-1 dispatch, `$5840-$58FF` options' renderer gate and the
menu glyphs (to `$587E`),
`$5900-$59FF` speed (143 bytes used), `$5A00-$5AFF` the palette module's
`fold_queue` and SMS stubs (163 bytes used), `$5B00-$5FFF` unowned (1,280 bytes;
the `$FF` tail of speed's old claim `$5900-$5FFF`, never read or executed:
docs/validation/sms-palette.md). Bank `$45` `$4000-$43FF`, the menu's old
range: `$4000-$43FF` and `$5200-$5FFF` NES palette (`nes-palette`),
`$4400-$51FF` `stage61-upload`.

Bank `$3B` (original game data to `$761CE`, then `$FF`; file offsets
`$76000-$77FFF`): `$5000-$57FF` and `$5A00-$5AFF` in the MPR2 view (file
`$77000-$777FF`, `$77A00-$77AFF`) are the SMS copy of bank `$46`'s palette
code, dispatch and the SMS table (1.11-dev). Read/execute watches over them
on the build before saw nothing (cold boot and all 11 stored runs).
`$4200-$4FFF` (file `$76200-$76FFF`) holds NES-B's colour sets and 3-2
variant (`nes-palette`, 3,454 bytes to `$4F7D`); `$41CF-$41FF`,
`$5800-$59FF` and `$5B00-$5FFF` stay `$FF` and unowned.

Bank `$43` `$7800-$7FFF` (MPR3 view; file offsets `$87800-$87FFF`, 1.11-dev):
the palette module's HELL code (`$7800-$7B4F`, 176 bytes spare to `$7BFF`)
and HELL table (`$7C00-$7FFF`). It was the `$FF` tail of stage11's claim
(`$80000-$87FFF`, now `$80000-$877FF`): stage11's generator puts 1-1's
phases 6 and 7 in bank `$43`, at most 2 x 83 pairs x 32 bytes, so its data
ends by `$74BF` (`max_pairs`; the current build uses exactly that), and the
build rejects any module byte outside its ranges.

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

Since 1.11-dev the menu is a popup window over the playfield; the HUD rows
28-30 are never written. Select in gameplay (hook `$FF70`, unchanged open
conditions `$2E63 = 0`, `$2201 != 0`) calls bank `$46` `$4400`
(`src/options`, 1,692 bytes, `$4400-$4A9B`, of the claimed `$4400-$4AFF`,
since the reset-row build; to make room the three menu glyphs moved to
`$584F-$587E`, after the renderer gate in the module's claim
`$5840-$58FF`, and the save status texts to `$4100-$41CE`). Its layout and option
values are `src/options/menu.txt`, generated into `menu-text.inc` by
`scripts/menu_text.py`.

- **Refusal.** The menu returns at once (nothing touched) while Ryu is dead
  (`$2EAB` = 10 or `$2EAD` = 0: native `$8E57` sets both at every death and
  they stay until the respawn or continue reloads the stage), and unless the
  playfield's vertical scroll `$2E4D/$2E4E` is 0, which every probed
  gameplay update shows (the window's rows must stay clear of the HUD's).
  The hook's own conditions refuse area changes, fades and stage loads
  (`$2E63` counting down, `$2201` = 0) but let the death animation through,
  where the stage reload clears both sprite-table buffers.
- **Window.** 25 x 11 cells (26 x 10 before the reset row's blank line,
  `v111-reset`) in the HUD font (palette 15, `$F7xx`, opaque:
  the font's colour-4 background), BAT rows 7-17 (screenshot y 106-193),
  starting at BAT column `((BXR >> 3) + 3) & 63` with BXR the playfield's
  `$2E4B/$2E4C`, so it sits at screen columns 3-27 (less the fine scroll).
  A row reaching BAT column 63 continues at column 0 (copied and drawn in
  two pieces). No frame: there is no audited tile space for frame graphics.
- **Backup.** The 275 covered BAT words go to VRAM: rows 0-9 (250 words) to
  the sprite-table buffer the game is building (`$7E00` or `$7F00`, chosen
  by `$2B81` and the native table `$FAA2`), row 10 to the HUD font's blank
  tiles `$7AB-$7AC` (`$7AB0-$7AC8`). (A 26-column window of 11 rows would
  need 260 words in the 256-word buffer, or a row split between the two
  places; so the eleventh row cost the window its blank last column.) The building buffer is free at the
  hook: the main loop (`$E061`) runs the update (which contains the hook)
  and then `$F8E0`, which writes all 64 entries (256 words; `$2E44` is 64)
  of that buffer and only then points the VDC's SATB register (`$13`) at it
  and flips `$2B81`; DCR is 0 (no automatic SATB DMA), and no other gameplay
  code writes `$13` (`$F728`, the sprite reset, clears both buffers). So the
  buffer the menu borrowed is rewritten in the same update the menu returns
  to, before it is ever shown. Tiles `$7AA-$7AD` and `$7B9` are zero in
  every gameplay state (1.10 audit; the 1.11 probe saw `$7AB` zero at every
  frame end) and are zeroed on close.
- **Sprites** are hidden while the window is open: the VDC control
  register's low byte is written without bit 6 (sprites), from the game's
  shadow `<$0E`, which is left unchanged and written back on close (in
  banks 0-3 the register is selected only by `$FC14`, `$FC24`, `$FC5E` and
  `$FC73`, which all write it from that shadow; the other `st0 #5` byte
  pairs there are data, and none is in the interrupt path). Hiding all sprites is one register
  write with nothing to restore but the shadow; hiding only the sprites
  over the window would mean editing and restoring the displayed sprite
  table. The held item's icon (a sprite) disappears with them.
- **Band.** BAT row 31, blank (`$F79F`) in gameplay, shows the version and
  credit while the window is open: `V1.11-DEV TIGERMONKEYFISH`, or with
  `GITHUB.COM/` when the line fits 32 columns (a release version: `V1.11
  GITHUB.COM/TIGERMONKEYFISH`); the generator fails the build if it does not
  fit. Close writes the 32 blank words back.
- **Glyphs.** `.`, `:` and `/` in the native style are uploaded to the HUD
  font's blank tiles `$7AA`, `$7AD` and `$7B9` (planes 0-1 stored, plane 2
  computed), as in 1.10.
- **Controls.** Up/Down choose a row (the value blinks: 16 frames shown, 16
  blank; counter in zero page `$27`), Left/Right change it, Run accepts and
  restarts the stage shown (health refilled, timer reset, palettes
  reloaded) and saves the settings to backup RAM when there is one
  ([saved settings](#saved-settings-backup-ram)), Select cancels. The
  window's top row shows the save status (`$2105`; one of the `?` line's
  texts in `menu.txt`, 23 columns, plain statements such as `SETTINGS
  SAVED` or `NO BACKUP MEMORY` since the reset-row build, before it the
  last row with `SAVE:` and a short name), drawn once when the window
  opens; a blank row parts it from the options. The texts are in bank
  `$46` `$4100-$41FF` (options' third claim; 207 bytes). A blank row parts
  the reset row from the controls line, the window's last row. The menu returns once Select, Run, I and II are
  released. Rows: STAGE (22 entries), SMOOTH PARALLAX (bit 0 clear = ON),
  NO DAMAGE (bit 1), NES FIREWHEEL (bit 2), PALETTE (bits 3-5), LANGUAGE
  (`$3227`; draft bits 6-7), then RESET OPTIONS (row index `FIELDS`, 6;
  Up/Down wrap over all seven). On the reset row Left/Right do nothing and
  I or II (pad bits 0-1 newly pressed) writes `DEFAULT_DRAFT` (`$40`: each
  `@` line's first value, the power-on settings without saved ones,
  `$2100` = 0 and `$3227` = 1) to the draft `$2101` and redraws, so the
  palette preview follows as for any PALETTE change; STAGE is untouched.
  Run and Select then treat the draft as always (Run applies, saves and
  restarts the STAGE row's stage; Select discards it). Its field (`!` in
  `menu.txt`, `PRESS I`) is the field tables' last entry and blinks like a
  value. Each option row is a mask and a value list in `menu.txt`
  (`choice_*` tables): the draft's value is looked up in the list (an
  unlisted value shows the first entry) and Left/Right step through it.
- **Language.** Only the title (bank 4 `$8610-$8643`, `$91B8`) and the story
  text engine (bank 5) read `$3227` (absolute references; the patch's own
  English initialization and menu write it), so a change shows at the next
  cinema or title screen.
- **Zero page and stack.** `$25-$2C` are saved on the stack and restored
  (the vblank interrupt's palette module saves its own `$20-$26`); see the
  stack note above.

Evidence (1.11-dev, emulated; `scripts/check_menu.py`): see the 1.11-dev
popup menu record in [validation/popup-menu.md](validation/popup-menu.md).
Re-audit if the HUD, the font loader, the sprite-table code (`$F8E0`,
`$F728`) or the menu's open conditions change.

## Saved settings (backup RAM)

1.11-dev (branch `v111`: `bram-save` with `dark-lift`), module `src/bram`.
Emulator evidence only; the unlock and lock pass on a test emulator that
models the lock, hardware has not been tried: status, evidence and open
points in [validation/bram-save.md](validation/bram-save.md).

`$2100` and `$3227` are kept in the console's backup RAM (bank `$F7`, 2 KiB)
as a System Card style file `NR ENHANCE` (`$18` bytes with its header:
version 1, `$2100`, `$3227`, five zero bytes). A HuCard has no BIOS, so the
module does what the System Card's routines do
([hardware notes](pc-engine/HARDWARE.md#backup-ram-bram-from-a-hucard)):
`sei`, bank `$F7` into MPR4, `csl`, `$48 $75 $80` to `$1807` to unlock, the
work, a read of `$1803` to lock, `csh`, MPR4 back. It saves and restores
zero page `$22-$2C`, X, Y and the flags. Its deepest stack use, measured
with a guard, reached `$21D5` (the loader at reset, and the save under the
open menu: 21 bytes below its entry); the watched margin ends at `$213F`.

- **Reset:** the trampoline at `$FFE6` (16 bytes, where the 8-byte English
  initialization was, grown into the free bytes below the vectors) calls
  `$4B00` after the native RAM clear, with interrupts off, the CPU already
  at high speed and MPR0/MPR1 set by the native reset code. Defaults first
  (`$3227` = 1), then our entry's values if the directory is sound and the
  entry checks out. Read only. A and the flags are free there (the native
  init at `$FCBE` loads A first); X and Y are kept.
- **Run:** the menu calls `$4B03` after it has set `$2100` and `$3227`,
  before the stage restarts (window closed, sound still held, interrupts
  off for the save's length: about 2 ms with a few files, half a frame for
  the one format of a blank memory).
- **What may be written, and when.** Nothing unless "HUBM" is there and the
  whole directory is sound, or the memory is provably blank and writable
  (then the 18 header bytes, the tag last). Sound means: end pointer at
  least `$8000` (only the first 2 KiB is trusted, whatever the pointer
  says: Geargrafx pre-formats with `$A000`); every entry at least 16 bytes
  and inside the 2 KiB; a `00 00` terminator that ends at or below
  min(end, `$8800`); the header's first-free pointer naming that
  terminator. Nothing is deleted, moved or resized. A new entry goes at the
  terminator if it and a new terminator fit: everything after its length
  byte first, then the new terminator, then the length byte (from then on
  the directory holds the entry), then the header's pointer, high byte
  first. An existing entry of our length is rewritten in place, data first
  and checksum last, only when it differs. What was written is read back.
- **Cut saves.** A power cut between two byte writes leaves either the old
  directory, or our entry in place with the header's pointer still naming
  it (low byte; the high byte old or new). The validation accepts exactly
  that one pointer state, only when our entry is the last one, and the next
  Run moves the pointer. The pointer's high byte goes first because the
  other order could leave a pointer below the terminator, inside other
  games' files; this order can only leave it at our entry or 256 bytes
  above it in free space. An entry cut mid-rewrite fails its checksum
  (`ERROR 5`, defaults) and is rewritten by the next Run.
- **Status** in `$2105` (`ST_` values, the menu's status texts in
  `src/options/menu.txt` in the same order, `scripts/bram_image.py`
  `STATUS_TEXT`: `NO BACKUP MEMORY`, `SETTINGS SAVED`, `BACKUP MEMORY
  FOUND`, `BACKUP MEMORY FULL`, `BACKUP MEMORY ERROR n`, `SETTINGS
  LOADED`): `NONE`, `OK` (a Run saved, or found the settings saved
  already; inside the module also the scan's "directory sound"), `READY`,
  `FULL`,
  `ERROR 1` unformatted and not blank, `ERROR 2` directory not sound,
  `ERROR 3` an entry of our name with another length, `ERROR 4` not read
  back, `ERROR 5` our entry's contents do not check out, `LOADED` (9,
  since `v111-reset`; `OK` before) the reset read the settings. Only the
  load path's final `lda #ST_LOADED` differs from the build before
  (one operand byte, bank `$46` `$4CDE`).
- **No backup RAM.** With no "HUBM" the save looks at bytes `$8001-$8012`:
  all alike and neither `$00` nor `$FF` is taken for an unmapped bank
  (`NONE`); otherwise a write test of byte `$8000` (two patterns, then its
  old value) comes before the 2 KiB blank check, so a console without the
  memory leaves after a few instructions with nothing changed.
- **Boot time.** The loader's cost must stay below 59,832 master clocks
  (the time between the first, pending vblank interrupt after the reset
  code enables interrupts and the next one), or the boot runs one interrupt
  behind the original's. The walk runs at low CPU speed like every access
  to the memory and costs about 950 clocks an entry, so that happens from
  57 files when no settings are saved and from 46 other files when they
  are (18-byte files; real saves are larger and far fewer). Left as it is
  on purpose
  ([the decision](validation/bram-save.md#many-files)).
- **Whoever adds a setting:** it is saved if it lives in `$2100` (bit 6 is
  free; the loader rejects an entry with bit 6 set until its range check is
  extended) or needs a new data byte (bytes 3-7 of the entry are zero and
  ignored on load) and, for a change of meaning, a new format version. A
  build that finds another version in an entry of our length treats it as
  damaged and rewrites it at the next Run, so a version that must coexist
  with older builds needs another name or length.
- `$2104` (palette module state) is not saved: zero at reset, and the
  palette module uploads by itself when a mapped mode is live at the first
  gameplay vblank (checked for every saved palette mode and language from
  a cold boot: `research/tools/bram-save/bootmodes.py`).
- **Checks.** `scripts/check_bram.py` (image matrix, power cycles, cut
  saves, timing; `--bram-model` for the lock models and `--only lock` for
  the negative controls, on the test-only emulator of
  `research/tools/bram-save/locktest_patch.py`), `scripts/bram_image.py`
  (images, a System Card style reader, the model), `scripts/check_boot.py
  --bram`, and the probes in `research/tools/bram-save/` (random images,
  the System Card's own routines on the game's file, boot modes, stack,
  boot slack, many files). Rerun all of them after any
  change to `src/bram`; rerun the lock models after any change to the
  unlock, the lock or the order of the accesses.

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
