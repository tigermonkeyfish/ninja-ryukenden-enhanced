; NES palette modes ($2100 bits 3-4 = 01; bit 5 clear NES-A, set NES-B):
; the game in NES master-palette colours, read as NES Ninja Gaiden. The
; colours are data (src/nes-palette/*.json; scripts/nes_palette.py
; generates the nes-*.inc files at build time); this module only chooses
; them. NES-B is the re-lit variant of the same role data (each role's dark
; shades lifted into its NES ramp's lightness): its own colour sets, 3-2
; variant, animation table and 1-1 / 2-2 Enhanced palettes; sprite
; palettes, Ryu and the HUD are NES-A's. Every NES-B test comes after the
; NES family test, so Original, GB DMG, HELL and SMS run exactly the code
; they ran before NES-B.
;
; All the game's palette data is in bank $37: the colour sets (table at
; $6000, loader $F211, A = set) and the sprite palettes ($7180 + 18n, loader
; $F1C0). Both map bank $37 into MPR3 and unpack with $F2BE (source <$19/<$1A,
; first colour <$15/<$16, count <$17/<$18) into the RAM palette $2286. In NES
; gameplay their jsr $F2BE comes here, and a set or sprite palette that has
; an NES copy is unpacked from it instead. The colours the game animates come
; from bank 3's animation table ($CE8D, pointer table $CF32): in NES gameplay
; the stage load takes the NES copy of that table instead. Everything else in
; the game (fades, the backup $2686, the vblank upload) works on the RAM
; palette, so it carries the NES colours on by itself; the palette module
; (src/palette) uploads mode 01 natively. The HUD colours (bank 1 $83C3,
; table $83E5) and the 1-1 / 2-2 Enhanced palettes (stage11, stage22) choose
; theirs the same way.
;
; Cinemas, the title and the ending ($2240 != 0) keep the original colours.
; A set may have a variant for one stage ($2E5F): 3-2 shares set 6 with 3-1.

OPTIONS = $2100
PALETTE_BITS = $18          ; the upload family: $08 for NES-A ($08) and NES-B ($28)
PALETTE_NES = $08
PALETTE_VARIANT = $20       ; set: NES-B
MASTER_STATE = $2240        ; 0 gameplay, 1 cinema or title, 2 ending
STAGE = $2e5f               ; Level Select numbering, 0-21
NES_BANK = $45
NES_B_BANK = $3b            ; NES-B's colour sets and variant ($4200-$4FFF, unused in the original)
DATA_BANK = $37             ; the original palette data
UNPACK = $f2be              ; native: unpack colours from [<$19] (MPR3)
SET_COLOUR = $f23c          ; native: RAM palette entry A = $2284/$2285, queued
HUD_COUNTER = $2e88         ; the native HUD routine's entry counter
NEW_COLOUR = $2284          ; and $2285: the colour SET_COLOUR writes
HUD_TABLE = $83e5           ; bank 1: the original HUD colours, 7 words
SETS = 22
WINDOW = $2000              ; this bank runs in MPR2 ($4000), F2BE reads MPR3 ($6000)
IN_BANK45 = $80             ; a copy's high byte + $80: the copy is in bank $45
ANIM_TABLE = $cf32          ; bank 3: the original animation set pointers
ANIMR = $37ea               ; RAM (src/palette, palette-lag): the animation table choice

 ; Palette timing (fast_unpack): colour \1 of a group, 37 cycles: its low
 ; byte, then bit 8 from the group byte's top bit (shifted out), as the
 ; native $F2FE-$F30F writes them.
fu_colour .macro
 ldy #\1 + 1               ; 2
 lda [$29],y                ; 7
 ldy #2 * \1               ; 2
 sta [$2b],y                ; 7
 cla                        ; 2
 asl <$23                   ; 6
 rol a                      ; 2
 iny                        ; 2
 sta [$2b],y                ; 7
 .endm

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

 ; NES sprite palettes read in place (MPR3 = bank $37): $7C30-$7FDF.
 .org $7c30
 .include "nes-sprites-37.inc"
nes_sprites_37_end:
 .if (nes_sprites_37_end > nes_unpack_hook)
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

 ; The animation sets ($CE8D, bank 3 at $C000, A = set pushed): native
 ; lda #<$CF32 / ldy #>$CF32 / plx, then jsr $E13F picks the set's pointer.
 .bank 3
 .org $ce98
 plx
 jsr ANIMR                  ; palette-lag: src/palette's ANIMR in RAM ($37EA)
 nop
 .org $d400
 ; Palette timing (palette-lag): the animation set table is chosen by
 ; ANIMR, RAM code src/palette's configure writes for the mode (from these
 ; two pointers): in Original and the mapped modes lda/ldy of $CF32 and a
 ; pad, in NES-A/NES-B a test of $2240 (a cinema: $CF32) and lda/ldy of
 ; this mode's table; 24 cycles to the rts in every mode and either way,
 ; as Original's path through the routine that was here took.
 .dw nes_anim               ; $D400: NES-A's table
 .dw nes_anim_b             ; $D402: NES-B's table
 .include "nes-anim.inc"
 ; NES-B's table: its own records, lists equal to NES-A's shared.
 .include "nes-b-anim.inc"
nes_anim_end:
 .if (nes_anim_end > $dc00)
 .fail
 .endif

 .bank NES_BANK
 .org $4000
 ; From nes_unpack_hook (MPR2 = this bank, MPR3 = bank $37, F2BE's
 ; arguments set; <$21 = the set number when $F211 called, <$22:<$21 =
 ; twice the palette number when $F1C0 called). X and Y are kept, MPR3 is
 ; bank $37 again on return, <$19/<$1A as they came.
nes_unpack:
 ; Palette timing (1.11-dev, palette-lag): every way from the hook through
 ; here takes exactly the cycles of the Original way (the hook's 15 and the
 ; native unpack $F2BE's), so an NES mode adds no time to a load. Every
 ; path below reaches nu_pad's end at cycle 162 (counted from here, the
 ; jsr not counted; HuC6280 cycles as Geargrafx's table), then fast_unpack
 ; does the unpack with its first two groups of 8 colours NU_SPARE cycles
 ; shorter than the native ones (docs/validation/palette-lag.md, "NES").
 ; X and Y are kept, MPR3 is bank $37 again on return, <$19/<$1A as they
 ; came; the colours as before (the NES copy where one exists, in
 ; gameplay; else the original).
 phx                        ; 3
 phy                        ; 3
 lda <$19                   ; 4
 pha                        ; 3
 lda <$1a                   ; 4
 pha                        ; 3: 20
 lda MASTER_STATE           ; 5
 bne nu_cinema              ; 2: 27 (taken: 29)
 ; A sprite palette? Only $F1C0 unpacks from $7180 up.
 lda <$1a                   ; 4
 cmp #HIGH($7180)           ; 2
 bcc nu_set1                ; 2: 35 (taken: 37)
 bne nu_sprite1             ; 2: 37 (taken: 39)
 lda <$19                   ; 4
 cmp #LOW($7180)            ; 2
 bcc nu_set2                ; 2: 45 (taken: 47)
 bra nu_sprite              ; 4: 49
nu_set2:
 bra nu_set                 ; 4: 51
nu_cinema:
 lda #DATA_BANK             ; 2: 31
 ldx #18                    ; pad 131: 6 x 18 + 14 = 122
 jsr nu_delay
 nop                        ; 2
 php                        ; 3
 plp                        ; 4: 162
 jmp nu_go
nu_sprite1:
 nop                        ; 2
 nop
 nop
 nop
 nop                        ; 10: 49
nu_sprite:
 lda <$22                   ; 4
 lsr a                      ; 2
 lda <$21                   ; 4
 ror a                      ; 2: the palette number
 sec                        ; 2
 sbc #NES_SPRITE_FIRST      ; 2
 cmp #NES_SPRITE_COUNT      ; 2: 67 (numbers below the first wrap above the count)
 bcs nu_sprite_out          ; 2: 69 (taken: 71)
 tax                        ; 2
 ldy nes_sprite_hi,x        ; 5: 76
 beq nu_sprite_none         ; 2: 78 (taken: 80)
 lda nes_sprite_lo,x        ; 5: 83
 sta <$19                   ; 4
 tya                        ; 2
 bmi nu_sprite_45           ; 2: 91 (taken: 93)
 sta <$1a                   ; 4
 lda #DATA_BANK             ; 2: 97
 ldx #7                     ; pad 65: 56
 jsr nu_delay
 nop
 php
 plp                        ; 9: 162
 jmp nu_go
nu_sprite_45:
 and #$7f                   ; 2
 sta <$1a                   ; 4
 lda #NES_BANK              ; 2: 101
 ldx #6                     ; pad 61: 50
 jsr nu_delay
 nop
 nop
 php
 plp                        ; 11: 162
 jmp nu_go
nu_sprite_out:
 lda #DATA_BANK             ; 2: 73
 ldx #11                    ; pad 89: 80
 jsr nu_delay
 nop
 php
 plp                        ; 9: 162
 jmp nu_go
nu_sprite_none:
 lda #DATA_BANK             ; 2: 82
 ldx #11                    ; pad 80: 80
 jsr nu_delay               ; 162
 jmp nu_go
nu_set1:
 nop                        ; 2
 nop
 nop
 nop
 nop
 nop
 nop                        ; 14: 51
nu_set:
 ; A colour set: <$21 holds the set, and its table entry must name this
 ; source.
 lda <$21                   ; 4
 cmp #SETS                  ; 2
 bcs nu_set_out             ; 2: 59 (taken: 61)
 asl a                      ; 2
 asl a                      ; 2
 tax                        ; 2
 lda $6000,x                ; 5
 cmp <$19                   ; 4
 bne nu_set_other1          ; 2: 76 (taken: 78)
 lda $6001,x                ; 5
 cmp <$1a                   ; 4
 bne nu_set_other2          ; 2: 87 (taken: 89)
 ldx <$21                   ; 4
 lda OPTIONS                ; 5
 and #PALETTE_VARIANT       ; 2
 bne nu_set_b               ; 2: 100 (taken: 102)
 ; NES-A: a variant of this set for the stage being loaded (3-2)?
 ldy STAGE                  ; 5
 cpy #SETS                  ; 2
 bcs nu_set_a_copy1         ; 2: 109 (taken: 111)
 txa                        ; 2
 cmp nes_variant_set,y      ; 5
 bne nu_set_a_copy2         ; 2: 118 (taken: 120)
 lda nes_variant_lo,y       ; 5
 pha                        ; 3
 lda nes_variant_hi,y       ; 5
 tay                        ; 2
 pla                        ; 4
 bra nu_set_a_got           ; 4: 141
nu_set_a_copy1:
 nop                        ; 2
 php                        ; 3
 plp                        ; 4: 120
nu_set_a_copy2:
 ldy nes_set_hi,x           ; 5
 beq nu_set_a_none          ; 2: 127 (taken: 129)
 lda nes_set_lo,x           ; 5: 132
 nop                        ; 2
 php                        ; 3
 plp                        ; 4: 141
nu_set_a_got:
 ; A/Y = the NES copy in the $6000 window; Y + $80 marks bank $45, else
 ; it is in bank $37 (already in MPR3).
 sta <$19                   ; 4
 tya                        ; 2
 bmi nu_set_a_45            ; 2: 149 (taken: 151)
 sta <$1a                   ; 4
 lda #DATA_BANK             ; 2: 155
 php                        ; 3
 plp                        ; 4: 162
 jmp nu_go
nu_set_a_45:
 and #$7f                   ; 2
 sta <$1a                   ; 4
 lda #NES_BANK              ; 2: 159
 sxy                        ; 3: 162
 jmp nu_go
nu_set_a_none:
 lda #DATA_BANK             ; 2: 131 (no NES copy: title and cinema sets)
 ldx #1                     ; pad 31: 20
 jsr nu_delay
 nop
 nop
 php
 plp                        ; 11: 162
 jmp nu_go
nu_set_out:
 lda #DATA_BANK             ; 2: 63
 ldx #13                    ; pad 99: 92
 jsr nu_delay
 php
 plp                        ; 7: 162
 jmp nu_go
nu_set_other1:
 lda #DATA_BANK             ; 2: 80
 ldx #11                    ; pad 82: 80
 jsr nu_delay
 nop                        ; 2: 162
 jmp nu_go
nu_set_other2:
 lda #DATA_BANK             ; 2: 91
 ldx #8                     ; pad 71: 62
 jsr nu_delay
 nop
 php
 plp                        ; 9: 162
 jmp nu_go
nu_set_b:
 ; NES-B (X = the set): the variant for this stage or the set's copy, all
 ; in bank NES_B_BANK.
 ldy STAGE                  ; 5
 cpy #SETS                  ; 2
 bcs nu_set_b_copy1         ; 2: 111 (taken: 113)
 txa                        ; 2
 cmp nes_variant_set,y      ; 5
 bne nu_set_b_copy2         ; 2: 120 (taken: 122)
 lda nes_b_variant_lo,y     ; 5
 pha                        ; 3
 lda nes_b_variant_hi,y     ; 5
 tay                        ; 2
 pla                        ; 4
 bra nu_set_b_got           ; 4: 143
nu_set_b_copy1:
 nop                        ; 2
 php                        ; 3
 plp                        ; 4: 122
nu_set_b_copy2:
 ldy nes_b_set_hi,x         ; 5
 beq nu_set_b_none          ; 2: 129 (taken: 131)
 lda nes_b_set_lo,x         ; 5: 134
 nop                        ; 2
 php                        ; 3
 plp                        ; 4: 143
nu_set_b_got:
 sta <$19                   ; 4
 sty <$1a                   ; 4
 lda #NES_B_BANK            ; 2: 153
 nop                        ; 2
 php                        ; 3
 plp                        ; 4: 162
 jmp nu_go
nu_set_b_none:
 lda #DATA_BANK             ; 2: 133
 ldx #1                     ; pad 29: 20
 jsr nu_delay
 nop
 php
 plp                        ; 9: 162
 jmp nu_go
nu_go:
 ; 166 here. A = the bank holding [<$19].
 tam #3                     ; 5
 jsr fast_unpack            ; 7: 178
 lda #DATA_BANK             ; 2
 tam #3                     ; 5
 pla                        ; 4
 sta <$1a                   ; 4
 pla                        ; 4
 sta <$19                   ; 4
 ply                        ; 4
 plx                        ; 4
 rts                        ; 7: 38 after fast_unpack

nes_code_end:

 ; Tables, the HUD words and variant sets; NES-B's set addresses.
 .include "nes-tables.inc"
 .include "nes-b-tables.inc"
nes_tables_end:
 .if (nes_tables_end > $4400)
 .fail
 .endif
 .if (NES_SPRITE_FIRST + NES_SPRITE_COUNT > 256)
 .fail
 .endif

 ; Bank $45 $5120-$51FF (palette-lag; stage61-upload's code ends at $5113,
 ; guarded below $5120): the HUD colours.
 .org $5120
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
 bne hud_native_peeled
 ; Palette timing (palette-lag): the NES way reaches here 5 cycles after
 ; the Original way reaches hud_native (bne not taken 2, lda 5, bne 2,
 ; against bne taken 4), so its first colour is written 7 cycles faster
 ; than a loop pass (constants for inc/lda HUD_COUNTER, no inx/cpx/bne,
 ; ldx #2 and a bra), less a nop: the same cycles as Original's.
 lda #$f1                   ; 2 (inc HUD_COUNTER: 7, with the sta)
 sta HUD_COUNTER            ; 5
 lda nes_hud_colours        ; 5
 sta NEW_COLOUR             ; 5
 lda nes_hud_colours+1      ; 5 (inx, lda abs,x: 7)
 sta NEW_COLOUR+1           ; 5
 lda #$f1                   ; 2 (lda HUD_COUNTER: 5)
 jsr SET_COLOUR
 ldx #2                     ; 2 (inx)
 nop                        ; 2 (cpx/bne: 6; bra 4 below)
 bra hud_nes
hud_native_peeled:
 ; In a cinema the NES way reaches here 7 cycles after Original reaches
 ; hud_native: the native first colour, 7 cycles faster (as above, no nop).
 lda #$f1
 sta HUD_COUNTER
 lda HUD_TABLE
 sta NEW_COLOUR
 lda HUD_TABLE+1
 sta NEW_COLOUR+1
 lda #$f1
 jsr SET_COLOUR
 ldx #2
 bra hud_native
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
nes_hud_end:
 .if (nes_hud_end > $5200)
 .fail
 .endif

 ; The NES copies of the colour sets, then sprite palettes that did not fit
 ; bank $37: bank $45 $5200-$5FFF (stage61-upload ends before $5120).
 .org $5200
 .include "nes-sets.inc"
nes_sets_end:
 .include "nes-sprites-45.inc"
nes_sprites_45_end:

 ; Palette timing: the native unpack ($F2BE, from its pha/phy on) with
 ; the 8 colours of a group unrolled: the same RAM palette and zero-page
 ; results, the same queue call ($F350), MPR3 holding [<$19]'s bank. A
 ; group takes 363 cycles here, padded to the native 505, except the first
 ; two, which are NU_SPARE (122) shorter: nes_unpack's lookup and banking
 ; spend those 244 (and its own 16 over the native pha/phy and ply/plx/rts).
 ; Called with X free (nes_unpack keeps the caller's X and Y).
NU_SPARE = 122
FU_COUNT = $37e9            ; RAM (src/palette's audited block): short groups left
fast_unpack:
 lda <$19                   ; the native $F2C0-$F2F1, cycle for cycle (110)
 sta <$29
 lda <$1a
 sta <$2a
 lda <$15
 asl a
 sta <$2b
 lda <$16
 rol a
 sta <$2c
 lda <$2b
 clc
 adc #$86
 sta <$2b
 lda #$22
 adc <$2c
 sta <$2c
 lda <$17
 sta <$21
 lda <$18
 sta <$22
 lsr <$22
 ror <$21
 lsr <$22
 ror <$21
 lsr <$22
 ror <$21
 lda #2                     ; 2
 sta FU_COUNT               ; 5: 117
fu_group:
 cly                        ; 2
 lda [$29],y                ; 7: the group's bit-8 byte (first colour in bit 7)
 sta <$23                   ; 4: 13
 fu_colour 0
 fu_colour 1
 fu_colour 2
 fu_colour 3
 fu_colour 4
 fu_colour 5
 fu_colour 6
 fu_colour 7                ; 8 x 37: 309 (13 + 296)
 lda <$29                   ; the native $F316-$F32D (44): 353 (group cycles)
 clc
 adc #$09
 sta <$29
 cla
 adc <$2a
 sta <$2a
 lda <$2b
 clc
 adc #$10
 sta <$2b
 cla
 adc <$2c
 sta <$2c
 lda FU_COUNT               ; 5
 beq fu_full                ; 2 (taken: 4)
 dec FU_COUNT               ; 7
 bra fu_padded              ; 4: 371 (the short pad, 122 - NU_SPARE, is 0)
fu_full:
 ldx #18                    ; 131: 6 x 18 + 14 = 122
 jsr nu_delay
 nop
 php
 plp                        ; 9: 492
fu_padded:
 dec <$21                   ; 6
 beq fu_done                ; 2
 jmp fu_group               ; 4: 505 (short groups 383) as the native
                            ; bne's 4; the last group's beq (4) is 2 more
                            ; than the native last bne (2), as every
                            ; group's is: the pads above count it.
fu_done:
 jsr $f350                  ; the native unpack's queue call
 rts

 ; ldx #k / jsr nu_delay: 6 k + 14 cycles (k >= 1). X = 0 after.
nu_delay:
 dex                        ; 2
 bne nu_delay               ; 4 (2)
 rts                        ; 7

nes_bank45_end:
 .if (nes_bank45_end > $6000)
 .fail
 .endif

 ; NES-B's colour sets and 3-2 variant: bank $3B $4200-$4FFF (file
 ; $76200-$76FFF), $FF and never read in the original (the bank's data end
 ; at $41CE; docs/validation/all-palettes.md); read through MPR3 ($6200 up)
 ; by set_lookup_b. The SMS palette's copy follows at $5000 (src/palette).
 .bank NES_B_BANK
 .org $4200
 .include "nes-b-sets.inc"
nes_b_sets_end:
 .if (nes_b_sets_end > $5000)
 .fail
 .endif
