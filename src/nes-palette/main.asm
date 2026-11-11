; NES palette mode ($2100 bits 3-4 = 01): the stages' colours read as the
; corresponding stages of NES Ninja Gaiden. The colours are data
; (src/nes-palette/*.json; scripts/nes_palette.py generates nes-tables.inc
; and nes-sets.inc at build time); this module only chooses them.
;
; All the game's palette data is in bank $37: the colour sets (table at
; $6000, loader $F211, A = set) and the sprite palettes ($7180 + 18n, loader
; $F1C0). Both map bank $37 into MPR3 and unpack with $F2BE (source <$19/<$1A,
; first colour <$15/<$16, count <$17/<$18) into the RAM palette $2286. In NES
; gameplay their jsr $F2BE comes here, and a set or sprite palette that has
; an NES copy is unpacked from it instead. Everything else in the game
; (fades, the backup $2686, the vblank upload) works on the RAM palette, so it
; carries the NES colours on by itself; the palette module (src/palette)
; uploads mode 01 natively. The HUD colours (bank 1 $83C3, table $83E5) and
; the 1-1 / 2-2 Enhanced palettes (stage11, stage22) choose theirs the same way.
;
; Cinemas, the title and the ending ($2240 != 0) keep the original colours.
; A set may have a variant for one stage ($2E5F): 3-2 shares set 6 with 3-1.

OPTIONS = $2100
PALETTE_BITS = $18
PALETTE_NES = $08
MASTER_STATE = $2240        ; 0 gameplay, 1 cinema or title, 2 ending
STAGE = $2e5f               ; Level Select numbering, 0-21
NES_BANK = $45
DATA_BANK = $37             ; the original palette data
UNPACK = $f2be              ; native: unpack colours from [<$19] (MPR3)
SET_COLOUR = $f23c          ; native: RAM palette entry A = $2284/$2285, queued
HUD_COUNTER = $2e88         ; the native HUD routine's entry counter
NEW_COLOUR = $2284          ; and $2285: the colour SET_COLOUR writes
HUD_TABLE = $83e5           ; bank 1: the original HUD colours, 7 words
SETS = 22
WINDOW = $2000              ; this bank runs in MPR2 ($4000), F2BE reads MPR3 ($6000)

 ; The two loaders' unpack calls (native: jsr $f2be), with bank $37 in MPR3.
 .bank 0
 .org $f1dc
 jsr nes_unpack_hook        ; $F1C0, sprite palettes
 .org $f234
 jsr nes_unpack_hook        ; $F211, colour sets

 ; In bank $37's free tail ($FF in the original from $7C30): MPR3 holds this
 ; bank whenever the loaders call. Outside NES mode it goes straight on to
 ; the native unpack, with nothing pushed.
 .bank DATA_BANK
 .org $7fe0
nes_unpack_hook:
 lda OPTIONS
 and #PALETTE_BITS
 cmp #PALETTE_NES
 beq nes_unpack_banked
 jmp UNPACK
nes_unpack_banked:
 tma #2
 pha
 lda #NES_BANK
 tam #2
 jsr nes_unpack
 pla
 tam #2
 rts
nes_unpack_hook_end:
 .if (nes_unpack_hook_end > $8000)
 .fail
 .endif

 ; The HUD colours (native: 7 words from $83E5 to entries $F1-$F7 through
 ; $F23C). Bank 1 is mapped at $8000 here; the routine leaves A, X, Y, the
 ; flags and $2E88 as the native one did (A = the last colour's high byte,
 ; X = 14, compare equal).
 .bank 1
 .org $83c3
hud_colours:
 tma #2
 pha
 lda #NES_BANK
 tam #2
 jsr nes_hud
 pla
 tam #2
 lda NEW_COLOUR+1
 cpx #14
 rts
hud_colours_end:
 .if (hud_colours_end > HUD_TABLE)
 .fail
 .endif

 .bank NES_BANK
 .org $4000
 ; From nes_unpack_hook (MPR2 = this bank, MPR3 = bank $37, F2BE's
 ; arguments set; <$21 = the set number when $F211 called). X and Y are
 ; kept, MPR3 is bank $37 again on return, <$19/<$1A as they came.
nes_unpack:
 lda MASTER_STATE
 bne unpack_original
 phx
 phy
 ; A sprite palette with an NES copy (by its source address)?
 ldx #NES_SPRITE_COUNT-1
 bmi set_lookup
sprite_find:
 lda <$19
 cmp nes_sprite_src_lo,x
 bne sprite_next
 lda <$1a
 cmp nes_sprite_src_hi,x
 bne sprite_next
 ldy nes_sprite_hi,x
 lda nes_sprite_lo,x
 bra unpack_nes
sprite_next:
 dex
 bpl sprite_find
set_lookup:
 ; A colour set: <$21 holds the set, and its table entry must name this
 ; source (only $F211 unpacks from below $7180).
 lda <$21
 cmp #SETS
 bcs unpack_original_pop
 asl a
 asl a
 tax
 lda $6000,x
 cmp <$19
 bne unpack_original_pop
 lda $6001,x
 cmp <$1a
 bne unpack_original_pop
 ; A variant of this set for the stage being loaded (3-2)?
 ldx <$21
 ldy STAGE
 cpy #SETS
 bcs set_copy
 txa
 cmp nes_variant_set,y
 bne set_copy
 lda nes_variant_lo,y
 pha
 lda nes_variant_hi,y
 tay
 pla
 bra unpack_nes
set_copy:
 ldy nes_set_hi,x
 beq unpack_original_pop    ; no NES copy: title and cinema sets
 lda nes_set_lo,x
unpack_nes:
 ; A/Y = the NES copy in the $6000 window of this bank.
 tax
 lda <$19
 pha
 lda <$1a
 pha
 stx <$19
 sty <$1a
 lda #NES_BANK
 tam #3
 jsr UNPACK
 lda #DATA_BANK
 tam #3
 pla
 sta <$1a
 pla
 sta <$19
 ply
 plx
 rts
unpack_original_pop:
 ply
 plx
unpack_original:
 jmp UNPACK

 ; The HUD colours, in NES gameplay from nes_hud_colours, else from bank 1
 ; $83E5, written as the native routine does.
nes_hud:
 lda #$f0
 sta HUD_COUNTER
 clx
 lda OPTIONS
 and #PALETTE_BITS
 cmp #PALETTE_NES
 bne hud_native
 lda MASTER_STATE
 bne hud_native
hud_nes:
 inc HUD_COUNTER
 lda nes_hud_colours,x
 sta NEW_COLOUR
 inx
 lda nes_hud_colours,x
 sta NEW_COLOUR+1
 lda HUD_COUNTER
 jsr SET_COLOUR
 inx
 cpx #14
 bne hud_nes
 rts
hud_native:
 inc HUD_COUNTER
 lda HUD_TABLE,x
 sta NEW_COLOUR
 inx
 lda HUD_TABLE,x
 sta NEW_COLOUR+1
 lda HUD_COUNTER
 jsr SET_COLOUR
 inx
 cpx #14
 bne hud_native
 rts
nes_code_end:

 ; Tables, the HUD words, sprite palettes and variant sets.
 .include "nes-tables.inc"
nes_tables_end:
 .if (nes_tables_end > $4400)
 .fail
 .endif

 ; The NES copies of the colour sets: bank $45 $5200-$5FFF
 ; (stage61-upload ends before $5200).
 .org $5200
 .include "nes-sets.inc"
nes_sets_end:
 .if (nes_sets_end > $6000)
 .fail
 .endif
