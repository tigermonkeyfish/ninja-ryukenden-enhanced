; Active flags: bit 0 = original background, bit 1 = no contact damage,
; bit 2 = Use NES Firewheel logic (no menu row yet; see docs/ARCHITECTURE.md).
; Two bytes at the bottom of the CPU stack page. The native stack grows
; downward from $21FF; validation watches the reserved low margin.
OPTIONS = $2100
DRAFT = $2101
NES_FIREWHEEL = 4
; The protection rule (src/nes-firewheel, bank 3, mapped at $C000 whenever
; the gate's callers run): carry clear = no damage and no knockback.
NES_FIREWHEEL_RULE = $dc00
 .bank 0
 ; Contact damage (bank 1 $8F70, A = damage). Its only callers are the
 ; enemy contact check in bank 2 ($A1C8, $A1D0); timer expiry enters at
 ; native_damage_entry. Returning early skips the damage and the knockback,
 ; with A, X, Y and P as on entry (like the native immunity checks).
 .org $fe20
damage_gate:
 php
 pha
 lda OPTIONS
 bit #2
 bne ignore_damage
 and #NES_FIREWHEEL
 beq native_damage
 jsr NES_FIREWHEEL_RULE
 bcc ignore_damage
native_damage:
 pla
 plp
native_damage_entry:
 bbs5 <$36,damage_return
 jmp $8f73
damage_return:
 rts
ignore_damage:
 pla
 plp
 rts
damage_gate_end:
 .if (damage_gate_end > $fe40)
 .fail
 .endif

 .bank 1
 .org $8f70
 jmp damage_gate
 ; Timer expiry is a distinct native caller with a full-health damage value.
 ; Preserve its original immunity checks and death behavior in either mode.
 .org $9bc3
 jmp native_damage_entry
 .bank $46
 .org $5840
renderer_gate:
 lda OPTIONS
 and #1
 bne original_background
 lda $224a
 jmp $4003
original_background:
 cla
 rts
renderer_gate_end:

 .bank $45
 .org $4000
menu:
 lda <$25
 pha
 lda <$26
 pha
 lda <$27
 pha
 lda <$11
 pha
 lda #1
 sta <$11
 st0 #1
 st1 #0
 st2 #7
 lda #2
 sta <$11
 st0 #2
 ldx #32
backup_row1:
 lda $0002
 pha
 lda $0003
 pha
 dex
 bne backup_row1
 lda #1
 sta <$11
 st0 #1
 st1 #$40
 st2 #7
 lda #2
 sta <$11
 st0 #2
 ldx #32
backup_row2:
 lda $0002
 pha
 lda $0003
 pha
 dex
 bne backup_row2
 jsr open_rows
 lda $2e5f
 cmp #22
 bcc valid_stage
 cla
valid_stage:
 sta <$25
 stz <$26
 ; The draft carries every flag the menu knows, NES Firewheel included,
 ; so Run (accept) keeps it although the menu has no row for it yet.
 lda OPTIONS
 and #7
 sta DRAFT
redraw:
 stz <$27
 jsr draw_values
menu_loop:
 jsr $fd67
 inc <$27
 jsr draw_values
 ; Select cancels and Run accepts (newly pressed buttons: 4 Select, 8 Run).
 lda $2e57
 and #4
 bne cancel
 lda $2e57
 and #8
 bne accept
 lda $2e57
 and #$50
 beq horizontal
 and #$40
 beq option_up
 inc <$26
 lda <$26
 cmp #3
 bcc redraw
 stz <$26
 bra redraw
option_up:
 lda <$26
 bne option_decrement
 lda #3
 sta <$26
option_decrement:
 dec <$26
 bra redraw
horizontal:
 lda $2e57
 and #$a0
 beq menu_loop
 ldx <$26
 beq stage_change
 lda DRAFT
 eor option_masks-1,x
 sta DRAFT
 bra redraw
stage_change:
 and #$20
 beq previous_stage
 inc <$25
 lda <$25
 cmp #22
 bcc redraw
 stz <$25
 bra redraw
previous_stage:
 lda <$25
 bne stage_decrement
 lda #22
 sta <$25
stage_decrement:
 dec <$25
 bra redraw
cancel:
 lda #$ff
 sta <$25
 bra choose
accept:
 lda DRAFT
 sta OPTIONS
choose:
 jsr $fd67
 lda $2e55
 and #$0f
 bne choose
 jsr close_rows
 lda #$5f
 sta <$26
restore_row2:
 stz <$11
 st0 #0
 lda <$26
 sta $0002
 lda #7
 sta $0003
 lda #2
 sta <$11
 st0 #2
 pla
 sta <$27
 pla
 sta $0002
 lda <$27
 sta $0003
 dec <$26
 lda <$26
 cmp #$3f
 bne restore_row2
 lda #$1f
 sta <$26
restore_row1:
 stz <$11
 st0 #0
 lda <$26
 sta $0002
 lda #7
 sta $0003
 lda #2
 sta <$11
 st0 #2
 pla
 sta <$27
 pla
 sta $0002
 lda <$27
 sta $0003
 dec <$26
 bpl restore_row1
 ldx <$25
 pla
 sta <$11
 sta $0000
 pla
 sta <$27
 pla
 sta <$26
 pla
 sta <$25
 txa
 cmp #$ff
 beq selection_return
 sta $2241
 tay
 lda selected_next_sequence,y
 sta $2247
 stz $2248
 ; A chosen stage starts with full health, as after a respawn (native $8DFC).
 lda #16
 sta $2ead
 txa
selection_return:
 rts

; The four menu rows (layout and value fields: menu.txt, generated into
; menu-text.inc) cover HUD rows 28-30 and the blank band under the HUD
; (row 31). The selected value blinks: shown for 16 frames, blank for 16.
draw_values:
 lda #STAGE_AT
 jsr position
 ldx #5
 lda #0
 jsr blank_value
 bne spaces
 ; "W-S" from the world/stage digits, then " A".." C" for the 6-4 phases.
 ldy <$25
 lda stage_numbers,y
 pha
 lsr a
 lsr a
 lsr a
 lsr a
 ora #$a0
 jsr character
 lda #$9a
 jsr character
 pla
 and #$0f
 ora #$a0
 jsr character
 lda #$9f
 jsr character
 cpy #19
 lda #$9f
 bcc stage_suffix
 tya
 adc #$6c
stage_suffix:
 jsr character
 lda #PARALLAX_AT
 jsr position
 ldx #3
 lda #1
 jsr blank_value
 bne spaces_then_damage
 lda DRAFT
 and #1
 asl a
 asl a
 tay
parallax_loop:
 lda parallax_labels,y
 jsr character
 iny
 dex
 bne parallax_loop
draw_damage:
 lda #DAMAGE_AT
 jsr position
 ldx #3
 lda #2
 jsr blank_value
 bne spaces
 lda DRAFT
 and #2
 asl a
 tay
damage_loop:
 lda damage_labels,y
 jsr character
 iny
 dex
 bne damage_loop
 rts
spaces_then_damage:
 jsr spaces
 bra draw_damage
 ; X spaces.
spaces:
 lda #$9f
 jsr character
 dex
 bne spaces
 rts
 ; A = field. Z clear while the selected field blinks off.
blank_value:
 cmp <$26
 bne shown_value
 lda <$27
 and #$10
 rts
shown_value:
 lda #0
 rts
character:
 sta $0002
 lda #$f7
 sta $0003
 rts
position:
 ldx #7
 jmp $fc34

 ; The HUD's third row (BAT row 30, VRAM $0780: lives, ninpo, enemy bar)
 ; holds menu text while the menu is open. The stack has no room for a third
 ; row (see ARCHITECTURE.md), so the row is parked in the HUD font's blank
 ; tiles $7AB-$7AC; the menu's '.', ':' and '/' glyphs use tiles $7AA, $7AD
 ; and $7B9. Row 31 holds 32 blank HUD tiles and those tiles are zero in
 ; every gameplay state (VRAM write audit, 1.10), so closing the menu copies
 ; row 30 back and writes those values again.
open_rows:
 stz <$11
 st0 #0
 st1 #$b0
 st2 #$7a
 lda #1
 sta <$11
 st0 #1
 st1 #$80
 st2 #7
 lda #2
 sta <$11
 st0 #2
 ldx #32
 jsr copy_words
 clx
 lda #$7a
 ldy #$a0
 jsr upload_glyph
 lda #$7a
 ldy #$d0
 jsr upload_glyph
 lda #$7b
 ldy #$90
 jsr upload_glyph
 stz <$26
 lda #0
 jsr row_text
 lda #$40
 jsr row_text
 lda #$80
 jsr row_text
 lda #$c0
row_text:
 jsr position
 ldy <$26
 ldx #32
row_loop:
 lda menu_rows,y
 jsr character
 iny
 dex
 bne row_loop
 sty <$26
 rts
close_rows:
 stz <$11
 st0 #0
 st1 #$80
 st2 #7
 lda #1
 sta <$11
 st0 #1
 st1 #$b0
 st2 #$7a
 lda #2
 sta <$11
 st0 #2
 ldx #32
 jsr copy_words
 jsr glyph_address
 ldx #64
 jsr zero_words
 stz <$11
 st0 #0
 st1 #$90
 st2 #$7b
 lda #2
 sta <$11
 st0 #2
 ldx #16
 jsr zero_words
 lda #$c0
 jsr position
 ldx #32
clear_band:
 lda #$9f
 jsr character
 dex
 bne clear_band
 rts
 ; X words from the read address to the write address.
copy_words:
 lda $0002
 ldy $0003
 sta $0002
 sty $0003
 dex
 bne copy_words
 rts
 ; A:Y = VRAM address of a tile; X = its 16 bytes in menu_glyphs (advances
 ; by 16). Planes 0-1 come from the table; plane 2, the HUD font's colour-4
 ; background, is every pixel the glyph leaves clear; plane 3 is empty.
upload_glyph:
 stz <$11
 st0 #0
 sty $0002
 sta $0003
 lda #2
 sta <$11
 st0 #2
 ldy #8
glyph_planes01:
 lda menu_glyphs,x
 sta $0002
 lda menu_glyphs+1,x
 sta $0003
 inx
 inx
 dey
 bne glyph_planes01
 txa
 sec
 sbc #16
 tax
 ldy #8
glyph_planes23:
 lda menu_glyphs,x
 ora menu_glyphs+1,x
 eor #$ff
 sta $0002
 stz $0003
 inx
 inx
 dey
 bne glyph_planes23
 rts
 ; X zero words at the write address.
zero_words:
 stz $0002
 stz $0003
 dex
 bne zero_words
 rts
glyph_address:
 stz <$11
 st0 #0
 st1 #$a0
 st2 #$7a
 lda #2
 sta <$11
 st0 #2
 rts
option_masks:
 .db 1,2
 .include "options-text.inc"
 .include "menu-text.inc"
 ; '.', ':' and '/' in the HUD font's style, for tiles $7AA, $7AD and $7B9:
 ; planes 0 and 1, row by row (colours 1-3 as in the font's own glyphs).
menu_glyphs:
 ; '.': the bottom two rows of the HUD font's '1' stem, three pixels wide.
 .db $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$20,$18,$18,$38,$00,$00
 ; ':': the same dot at rows 1-2 (shaded like the font's top rows) and 4-5.
 .db $00,$00,$38,$00,$38,$00,$00,$00,$20,$18,$20,$18,$00,$00,$00,$00
 ; '/': a three-pixel diagonal, shaded like the '1' stem row by row.
 .db $0e,$00,$1c,$00,$1c,$00,$38,$00,$40,$30,$40,$30,$60,$e0,$00,$00
menu_end:
