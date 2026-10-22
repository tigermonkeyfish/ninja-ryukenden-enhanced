; Active flags: bit 0 = original background, bit 1 = no contact damage.
; Two bytes at the bottom of the CPU stack page. The native stack grows
; downward from $21FF; validation watches the reserved low margin.
OPTIONS = $2100
DRAFT = $2101
 .bank 0
 .org $fe20
damage_gate:
 php
 pha
 lda OPTIONS
 and #2
 bne ignore_damage
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
 lda $2e5f
 cmp #22
 bcc valid_stage
 cla
valid_stage:
 sta <$25
 stz <$26
 lda OPTIONS
 and #3
 sta DRAFT
redraw:
 jsr draw_menu
menu_loop:
 jsr $fd67
 lda $2e57
 and #2
 bne cancel
 lda $2e57
 and #1
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

draw_menu:
 lda #0
 jsr position
 clx
text1_loop:
 lda text1,x
 jsr character
 inx
 cpx #32
 bne text1_loop
 lda #$40
 jsr position
 clx
text2_loop:
 lda text2,x
 jsr character
 inx
 cpx #32
 bne text2_loop
 lda #7
 jsr position
 lda <$25
 asl a
 asl a
 asl a
 tay
 ldx #5
stage_loop:
 lda stage_labels,y
 jsr character
 iny
 dex
 bne stage_loop
 lda #23
 jsr position
 lda DRAFT
 and #1
 asl a
 asl a
 asl a
 tay
 ldx #8
parallax_loop:
 lda parallax_labels,y
 jsr character
 iny
 dex
 bne parallax_loop
 lda #$4b
 jsr position
 cly
 lda DRAFT
 and #2
 beq damage_label
 ldy #3
damage_label:
 ldx #3
damage_loop:
 lda damage_labels,y
 jsr character
 iny
 dex
 bne damage_loop
 ldx <$26
 lda cursor_positions,x
 jsr position
 lda #$9a
 ; A native hyphen marks the active field.
character:
 sta $0002
 lda #$f7
 sta $0003
 rts
position:
 ldx #7
 jmp $fc34
option_masks:
 .db 1,2
cursor_positions:
 .db 0,13,64
 .include "options-text.inc"
menu_end:
