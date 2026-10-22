 .org $4400
 .incbin "mountain-map.bin"
; Scratch bytes used here are saved by the shared renderer entry at $FE46.
 .org $4a00
upload_row:
 ; The short TIA trampoline temporarily occupies saved main-loop scratch.
 ; IRQ routines do not use $2029..$2030. FE46 restores these bytes on return.
 lda <$06
 pha
 lda <$07
 pha
 lda <$2d
 pha
 lda <$2f
 pha
 lda <$30
 pha
 ldx <$27
 lda phase_pointer_lo,x
 sta <$06
 lda phase_pointer_hi,x
 sta <$07
 ldy #0
 lda <$28
 cmp #23
 beq upload_group_pointer
 ldy #2
upload_group_pointer:
 lda [<$06],y
 sta <$25
 iny
 lda [<$06],y
 sta <$07
 lda <$25
 sta <$06
 ldy #0
 lda [<$06],y
 beq upload_done
 sta <$0a
 iny
 sty <$0b
 lda #$e3
 sta <$29
 lda #2
 sta <$2c
 stz <$2d
 lda #32
 sta <$2e
 stz <$2f
 lda #$60
 sta <$30
upload_next:
 ldy <$0b
 lda [<$06],y
 tam #3
 iny
 stz <$11
 st0 #0
 lda [<$06],y
 sta $0002
 iny
 lda [<$06],y
 sta $0003
 iny
 lda #2
 sta <$11
 st0 #2
 lda [<$06],y
 sta <$2a
 iny
 lda [<$06],y
 sta <$2b
 iny
 lda [<$06],y
 tax
 iny
 sty <$0b
upload_run:
 jsr $2029
 lda <$2a
 clc
 adc #32
 sta <$2a
 bcc upload_no_carry
 inc <$2b
upload_no_carry:
 dex
 bne upload_run
 dec <$0a
 bne upload_next
upload_done:
 pla
 sta <$30
 pla
 sta <$2f
 pla
 sta <$2d
 pla
 sta <$07
 pla
 sta <$06
 rts
upload_row_end:

 .org $4b00
animate_stars:
 ; Shared Enhanced coordinate, anchored at stage entry.
 jsr $ffd0
 nop
 nop
 nop
 nop
 nop
 nop
 nop
 nop
 nop
 nop

 and #7
 sta <$27
 tax
 lda phase_variant_offset,x
 sta <$0a
 lda #$e3
 sta <$29
 lda #2
 sta <$2c
 stz <$2d
 lda #32
 sta <$2e
 stz <$2f
 lda #$60
 sta <$30
 stz <$25
star_next:
 ldx <$25
 lda star_table_lo,x
 sta <$06
 lda star_table_hi,x
 sta <$07
 lda star_group,x
 cmp #2
 bne group3
 ldx $3176
 lda variant2,x
 bra variant_ready
group3:
 ldx $3177
 lda variant3,x
variant_ready:
 asl a
 clc
 adc <$0a
 tay
 lda [<$06],y
 sta <$08
 iny
 lda [<$06],y
 cmp #3
 beq extra_tile
 clc
 adc #$7d
 tam #3
 lda #$60
 bra source_page
extra_tile:
 lda #$5d
source_page:
 sta <$09
 lda <$08
 lsr a
 lsr a
 lsr a
 clc
 adc <$09
 sta <$2b
 lda <$08
 asl a
 asl a
 asl a
 asl a
 asl a
 sta <$2a
 ldx <$25
 lda star_dest,x
 jsr seek_tile
 jsr $2029
 inc <$25
 lda <$25
 cmp #11
 beq stars_done
 jmp star_next
stars_done:
 rts

seek_tile:
 ; A is an atlas slot offset from pattern $80 / VRAM word $0800.
 pha
 stz <$11
 st0 #0
 asl a
 asl a
 asl a
 asl a
 sta $0002
 pla
 lsr a
 lsr a
 lsr a
 lsr a
 clc
 adc #8
 sta $0003
 lda #2
 sta <$11
 st0 #2
 rts
castle_runtime_end:
; Horizon upload lists (group 1) are shared with 6-1; castle_horizon.py
; generates them (the placeholders below are replaced at build time).
 .org $5000
phase_rows:
 .dw upload_0_0,upload_0_1,upload_1_0,upload_1_1,upload_2_0,upload_2_1,upload_3_0,upload_3_1,upload_4_0,upload_4_1,upload_5_0,upload_5_1,upload_6_0,upload_6_1,upload_7_0,upload_7_1
upload_0_0:
 .db 14
 .db 125,16,8,32,96,2
 .db 125,112,8,32,96,1
 .db 125,128,8,96,96,1
 .db 125,144,8,64,96,1
 .db 125,160,8,128,96,4
 .db 125,16,9,32,96,1
 .db 125,32,9,0,97,1
 .db 125,48,9,32,96,1
 .db 125,64,9,32,97,4
 .db 125,160,9,32,96,1
 .db 125,176,9,160,97,4
 .db 125,240,9,64,96,1
 .db 125,0,10,32,96,1
 .db 125,16,10,32,98,4
upload_0_1:
 .db 0
upload_1_0:
 .db 12
 .db 125,16,8,32,96,1
 .db 125,32,8,224,104,1
 .db 125,112,8,32,96,1
 .db 125,128,8,0,105,1
 .db 125,144,8,224,104,1
 .db 125,160,8,32,105,4
 .db 125,16,9,32,96,1
 .db 125,32,9,160,105,6
 .db 125,160,9,96,106,5
 .db 125,240,9,224,104,1
 .db 125,0,10,32,96,1
 .db 125,16,10,0,107,4
upload_1_1:
 .db 0
upload_2_0:
 .db 12
 .db 125,16,8,32,96,1
 .db 125,32,8,0,115,1
 .db 125,112,8,32,96,1
 .db 125,128,8,32,115,1
 .db 125,144,8,0,115,1
 .db 125,160,8,64,115,4
 .db 125,16,9,32,96,1
 .db 125,32,9,192,115,6
 .db 125,160,9,128,116,5
 .db 125,240,9,0,115,1
 .db 125,0,10,32,96,1
 .db 125,16,10,32,117,4
upload_2_1:
 .db 0
upload_3_0:
 .db 9
 .db 125,16,8,32,96,1
 .db 125,32,8,32,125,1
 .db 125,112,8,64,125,7
 .db 125,16,9,32,96,1
 .db 125,32,9,32,126,6
 .db 125,160,9,224,126,5
 .db 125,240,9,32,125,1
 .db 125,0,10,128,127,4
 .db 126,64,10,0,96,1
upload_3_1:
 .db 0
upload_4_0:
 .db 9
 .db 126,16,8,128,103,1
 .db 125,32,8,32,96,1
 .db 126,112,8,160,103,7
 .db 126,16,9,128,104,1
 .db 125,32,9,32,96,1
 .db 126,48,9,160,104,5
 .db 126,160,9,64,105,5
 .db 126,240,9,128,103,1
 .db 126,0,10,224,105,5
upload_4_1:
 .db 0
upload_5_0:
 .db 11
 .db 126,16,8,160,113,1
 .db 125,32,8,32,96,1
 .db 126,112,8,192,113,1
 .db 125,128,8,32,96,1
 .db 126,144,8,224,113,5
 .db 126,16,9,128,114,1
 .db 125,32,9,32,96,1
 .db 126,48,9,160,114,5
 .db 126,160,9,64,115,5
 .db 126,240,9,160,113,1
 .db 126,0,10,224,115,5
upload_5_1:
 .db 0
upload_6_0:
 .db 13
 .db 126,16,8,224,123,1
 .db 125,32,8,32,96,1
 .db 126,112,8,0,124,1
 .db 125,128,8,32,96,1
 .db 126,144,8,32,124,4
 .db 125,208,8,32,96,1
 .db 126,16,9,160,124,1
 .db 125,32,9,32,96,1
 .db 126,48,9,192,124,5
 .db 126,160,9,96,125,5
 .db 126,240,9,224,123,1
 .db 126,0,10,0,126,4
 .db 125,64,10,32,96,1
upload_6_1:
 .db 0
upload_7_0:
 .db 13
 .db 127,16,8,224,101,1
 .db 125,32,8,32,96,1
 .db 127,112,8,0,102,1
 .db 125,128,8,32,96,1
 .db 127,144,8,32,102,4
 .db 125,208,8,32,96,1
 .db 127,16,9,160,102,1
 .db 125,32,9,32,96,1
 .db 127,48,9,192,102,5
 .db 127,160,9,96,103,5
 .db 127,240,9,224,101,1
 .db 127,0,10,0,104,4
 .db 125,64,10,32,96,1
upload_7_1:
 .db 0
upload_lists_end:
horizon_start:
 ; <$2e = horizon loop entry for BAT column <$2f (castle_horizon.py, loop.inc):
 ; floor((D + LOOP_SPAN - C%8)/8) + (<$2f - left column) + round offset,
 ; mod LOOP_LENGTH.
 jsr $ffd0
 lda <$29
 clc
 adc #LOW(LOOP_SPAN)
 sta <$29
 lda <$2a
 adc #HIGH(LOOP_SPAN)
 sta <$2a
 lda $2e4b
 and #7
 sta <$2c
 lda <$29
 sec
 sbc <$2c
 sta <$29
 lda <$2a
 sbc #0
 sta <$2a
 lsr <$2a
 ror <$29
 lsr <$2a
 ror <$29
 lsr <$2a
 ror <$29
horizon_mod:
 lda <$2a
 bne horizon_sub
 lda <$29
 cmp #LOOP_LENGTH
 bcc horizon_offset
horizon_sub:
 lda <$29
 sec
 sbc #LOOP_LENGTH
 sta <$29
 lda <$2a
 sbc #0
 sta <$2a
 bra horizon_mod
horizon_offset:
 ldx $2e60
 cpx #7
 bcc horizon_area
 ldx #0
horizon_area:
 lda <$2f
 sec
 sbc $225a
 and #63
 clc
 adc <$29
 clc
 adc horizon_open,x
horizon_wrap:
 cmp #LOOP_LENGTH
 bcc horizon_ready
 sbc #LOOP_LENGTH
 bra horizon_wrap
horizon_ready:
 sta <$2e
 rts
; Per-round offsets (loop.inc, from the rounds' entry cameras).
horizon_open:
 .db OPENING_0,OPENING_1,OPENING_2,OPENING_3,OPENING_4,OPENING_5,OPENING_6
horizon_end:
; Column copy: N map entries from Y; the BAT read and write pointers start
; at the first entry and <$0a/<$0b holds its BAT address minus Y. Only the
; BAT high byte is read. Foreground (palette >= 2) stays as it is and is not
; written; the write pointer is moved to the next backdrop cell instead
; (seek_write), so a mostly-foreground row costs a read per cell.
columns_33:
 lda $0003
 cmp #32
 bcc backdrop_33
 jmp skip_33
backdrop_33:
 lda [<$06],y
 tax
 lda tile_high-$80,x
 stx $0002
 sta $0003
 iny
columns_32:
 lda $0003
 cmp #32
 bcc backdrop_32
 jmp skip_32
backdrop_32:
 lda [<$06],y
 tax
 lda tile_high-$80,x
 stx $0002
 sta $0003
 iny
columns_31:
 lda $0003
 cmp #32
 bcc backdrop_31
 jmp skip_31
backdrop_31:
 lda [<$06],y
 tax
 lda tile_high-$80,x
 stx $0002
 sta $0003
 iny
columns_30:
 lda $0003
 cmp #32
 bcc backdrop_30
 jmp skip_30
backdrop_30:
 lda [<$06],y
 tax
 lda tile_high-$80,x
 stx $0002
 sta $0003
 iny
columns_29:
 lda $0003
 cmp #32
 bcc backdrop_29
 jmp skip_29
backdrop_29:
 lda [<$06],y
 tax
 lda tile_high-$80,x
 stx $0002
 sta $0003
 iny
columns_28:
 lda $0003
 cmp #32
 bcc backdrop_28
 jmp skip_28
backdrop_28:
 lda [<$06],y
 tax
 lda tile_high-$80,x
 stx $0002
 sta $0003
 iny
columns_27:
 lda $0003
 cmp #32
 bcc backdrop_27
 jmp skip_27
backdrop_27:
 lda [<$06],y
 tax
 lda tile_high-$80,x
 stx $0002
 sta $0003
 iny
columns_26:
 lda $0003
 cmp #32
 bcc backdrop_26
 jmp skip_26
backdrop_26:
 lda [<$06],y
 tax
 lda tile_high-$80,x
 stx $0002
 sta $0003
 iny
columns_25:
 lda $0003
 cmp #32
 bcc backdrop_25
 jmp skip_25
backdrop_25:
 lda [<$06],y
 tax
 lda tile_high-$80,x
 stx $0002
 sta $0003
 iny
columns_24:
 lda $0003
 cmp #32
 bcc backdrop_24
 jmp skip_24
backdrop_24:
 lda [<$06],y
 tax
 lda tile_high-$80,x
 stx $0002
 sta $0003
 iny
columns_23:
 lda $0003
 cmp #32
 bcc backdrop_23
 jmp skip_23
backdrop_23:
 lda [<$06],y
 tax
 lda tile_high-$80,x
 stx $0002
 sta $0003
 iny
columns_22:
 lda $0003
 cmp #32
 bcc backdrop_22
 jmp skip_22
backdrop_22:
 lda [<$06],y
 tax
 lda tile_high-$80,x
 stx $0002
 sta $0003
 iny
columns_21:
 lda $0003
 cmp #32
 bcc backdrop_21
 jmp skip_21
backdrop_21:
 lda [<$06],y
 tax
 lda tile_high-$80,x
 stx $0002
 sta $0003
 iny
columns_20:
 lda $0003
 cmp #32
 bcc backdrop_20
 jmp skip_20
backdrop_20:
 lda [<$06],y
 tax
 lda tile_high-$80,x
 stx $0002
 sta $0003
 iny
columns_19:
 lda $0003
 cmp #32
 bcc backdrop_19
 jmp skip_19
backdrop_19:
 lda [<$06],y
 tax
 lda tile_high-$80,x
 stx $0002
 sta $0003
 iny
columns_18:
 lda $0003
 cmp #32
 bcc backdrop_18
 jmp skip_18
backdrop_18:
 lda [<$06],y
 tax
 lda tile_high-$80,x
 stx $0002
 sta $0003
 iny
columns_17:
 lda $0003
 cmp #32
 bcc backdrop_17
 jmp skip_17
backdrop_17:
 lda [<$06],y
 tax
 lda tile_high-$80,x
 stx $0002
 sta $0003
 iny
columns_16:
 lda $0003
 cmp #32
 bcc backdrop_16
 jmp skip_16
backdrop_16:
 lda [<$06],y
 tax
 lda tile_high-$80,x
 stx $0002
 sta $0003
 iny
columns_15:
 lda $0003
 cmp #32
 bcc backdrop_15
 jmp skip_15
backdrop_15:
 lda [<$06],y
 tax
 lda tile_high-$80,x
 stx $0002
 sta $0003
 iny
columns_14:
 lda $0003
 cmp #32
 bcc backdrop_14
 jmp skip_14
backdrop_14:
 lda [<$06],y
 tax
 lda tile_high-$80,x
 stx $0002
 sta $0003
 iny
columns_13:
 lda $0003
 cmp #32
 bcc backdrop_13
 jmp skip_13
backdrop_13:
 lda [<$06],y
 tax
 lda tile_high-$80,x
 stx $0002
 sta $0003
 iny
columns_12:
 lda $0003
 cmp #32
 bcc backdrop_12
 jmp skip_12
backdrop_12:
 lda [<$06],y
 tax
 lda tile_high-$80,x
 stx $0002
 sta $0003
 iny
columns_11:
 lda $0003
 cmp #32
 bcc backdrop_11
 jmp skip_11
backdrop_11:
 lda [<$06],y
 tax
 lda tile_high-$80,x
 stx $0002
 sta $0003
 iny
columns_10:
 lda $0003
 cmp #32
 bcc backdrop_10
 jmp skip_10
backdrop_10:
 lda [<$06],y
 tax
 lda tile_high-$80,x
 stx $0002
 sta $0003
 iny
columns_9:
 lda $0003
 cmp #32
 bcc backdrop_9
 jmp skip_9
backdrop_9:
 lda [<$06],y
 tax
 lda tile_high-$80,x
 stx $0002
 sta $0003
 iny
columns_8:
 lda $0003
 cmp #32
 bcc backdrop_8
 jmp skip_8
backdrop_8:
 lda [<$06],y
 tax
 lda tile_high-$80,x
 stx $0002
 sta $0003
 iny
columns_7:
 lda $0003
 cmp #32
 bcc backdrop_7
 jmp skip_7
backdrop_7:
 lda [<$06],y
 tax
 lda tile_high-$80,x
 stx $0002
 sta $0003
 iny
columns_6:
 lda $0003
 cmp #32
 bcc backdrop_6
 jmp skip_6
backdrop_6:
 lda [<$06],y
 tax
 lda tile_high-$80,x
 stx $0002
 sta $0003
 iny
columns_5:
 lda $0003
 cmp #32
 bcc backdrop_5
 jmp skip_5
backdrop_5:
 lda [<$06],y
 tax
 lda tile_high-$80,x
 stx $0002
 sta $0003
 iny
columns_4:
 lda $0003
 cmp #32
 bcc backdrop_4
 jmp skip_4
backdrop_4:
 lda [<$06],y
 tax
 lda tile_high-$80,x
 stx $0002
 sta $0003
 iny
columns_3:
 lda $0003
 cmp #32
 bcc backdrop_3
 jmp skip_3
backdrop_3:
 lda [<$06],y
 tax
 lda tile_high-$80,x
 stx $0002
 sta $0003
 iny
columns_2:
 lda $0003
 cmp #32
 bcc backdrop_2
 jmp skip_2
backdrop_2:
 lda [<$06],y
 tax
 lda tile_high-$80,x
 stx $0002
 sta $0003
 iny
columns_1:
 lda $0003
 cmp #32
 bcc backdrop_1
 jmp skip_1
backdrop_1:
 lda [<$06],y
 tax
 lda tile_high-$80,x
 stx $0002
 sta $0003
 iny
 rts
; After foreground: the write pointer lags until the next backdrop cell.
unsynced_33:
 lda $0003
 cmp #32
 bcc rejoin_33
skip_33:
 iny
unsynced_32:
 lda $0003
 cmp #32
 bcc rejoin_32
skip_32:
 iny
unsynced_31:
 lda $0003
 cmp #32
 bcc rejoin_31
skip_31:
 iny
unsynced_30:
 lda $0003
 cmp #32
 bcc rejoin_30
skip_30:
 iny
unsynced_29:
 lda $0003
 cmp #32
 bcc rejoin_29
skip_29:
 iny
unsynced_28:
 lda $0003
 cmp #32
 bcc rejoin_28
skip_28:
 iny
unsynced_27:
 lda $0003
 cmp #32
 bcc rejoin_27
skip_27:
 iny
unsynced_26:
 lda $0003
 cmp #32
 bcc rejoin_26
skip_26:
 iny
 bra unsynced_25
rejoin_33:
 jsr seek_write
 jmp backdrop_33
rejoin_32:
 jsr seek_write
 jmp backdrop_32
rejoin_31:
 jsr seek_write
 jmp backdrop_31
rejoin_30:
 jsr seek_write
 jmp backdrop_30
rejoin_29:
 jsr seek_write
 jmp backdrop_29
rejoin_28:
 jsr seek_write
 jmp backdrop_28
rejoin_27:
 jsr seek_write
 jmp backdrop_27
rejoin_26:
 jsr seek_write
 jmp backdrop_26
unsynced_25:
 lda $0003
 cmp #32
 bcc rejoin_25
skip_25:
 iny
unsynced_24:
 lda $0003
 cmp #32
 bcc rejoin_24
skip_24:
 iny
unsynced_23:
 lda $0003
 cmp #32
 bcc rejoin_23
skip_23:
 iny
unsynced_22:
 lda $0003
 cmp #32
 bcc rejoin_22
skip_22:
 iny
unsynced_21:
 lda $0003
 cmp #32
 bcc rejoin_21
skip_21:
 iny
unsynced_20:
 lda $0003
 cmp #32
 bcc rejoin_20
skip_20:
 iny
unsynced_19:
 lda $0003
 cmp #32
 bcc rejoin_19
skip_19:
 iny
unsynced_18:
 lda $0003
 cmp #32
 bcc rejoin_18
skip_18:
 iny
 bra unsynced_17
rejoin_25:
 jsr seek_write
 jmp backdrop_25
rejoin_24:
 jsr seek_write
 jmp backdrop_24
rejoin_23:
 jsr seek_write
 jmp backdrop_23
rejoin_22:
 jsr seek_write
 jmp backdrop_22
rejoin_21:
 jsr seek_write
 jmp backdrop_21
rejoin_20:
 jsr seek_write
 jmp backdrop_20
rejoin_19:
 jsr seek_write
 jmp backdrop_19
rejoin_18:
 jsr seek_write
 jmp backdrop_18
unsynced_17:
 lda $0003
 cmp #32
 bcc rejoin_17
skip_17:
 iny
unsynced_16:
 lda $0003
 cmp #32
 bcc rejoin_16
skip_16:
 iny
unsynced_15:
 lda $0003
 cmp #32
 bcc rejoin_15
skip_15:
 iny
unsynced_14:
 lda $0003
 cmp #32
 bcc rejoin_14
skip_14:
 iny
unsynced_13:
 lda $0003
 cmp #32
 bcc rejoin_13
skip_13:
 iny
unsynced_12:
 lda $0003
 cmp #32
 bcc rejoin_12
skip_12:
 iny
unsynced_11:
 lda $0003
 cmp #32
 bcc rejoin_11
skip_11:
 iny
unsynced_10:
 lda $0003
 cmp #32
 bcc rejoin_10
skip_10:
 iny
 bra unsynced_9
rejoin_17:
 jsr seek_write
 jmp backdrop_17
rejoin_16:
 jsr seek_write
 jmp backdrop_16
rejoin_15:
 jsr seek_write
 jmp backdrop_15
rejoin_14:
 jsr seek_write
 jmp backdrop_14
rejoin_13:
 jsr seek_write
 jmp backdrop_13
rejoin_12:
 jsr seek_write
 jmp backdrop_12
rejoin_11:
 jsr seek_write
 jmp backdrop_11
rejoin_10:
 jsr seek_write
 jmp backdrop_10
unsynced_9:
 lda $0003
 cmp #32
 bcc rejoin_9
skip_9:
 iny
unsynced_8:
 lda $0003
 cmp #32
 bcc rejoin_8
skip_8:
 iny
unsynced_7:
 lda $0003
 cmp #32
 bcc rejoin_7
skip_7:
 iny
unsynced_6:
 lda $0003
 cmp #32
 bcc rejoin_6
skip_6:
 iny
unsynced_5:
 lda $0003
 cmp #32
 bcc rejoin_5
skip_5:
 iny
unsynced_4:
 lda $0003
 cmp #32
 bcc rejoin_4
skip_4:
 iny
unsynced_3:
 lda $0003
 cmp #32
 bcc rejoin_3
skip_3:
 iny
unsynced_2:
 lda $0003
 cmp #32
 bcc rejoin_2
skip_2:
 iny
 bra unsynced_1
rejoin_9:
 jsr seek_write
 jmp backdrop_9
rejoin_8:
 jsr seek_write
 jmp backdrop_8
rejoin_7:
 jsr seek_write
 jmp backdrop_7
rejoin_6:
 jsr seek_write
 jmp backdrop_6
rejoin_5:
 jsr seek_write
 jmp backdrop_5
rejoin_4:
 jsr seek_write
 jmp backdrop_4
rejoin_3:
 jsr seek_write
 jmp backdrop_3
rejoin_2:
 jsr seek_write
 jmp backdrop_2
unsynced_1:
 lda $0003
 cmp #32
 bcc rejoin_1
skip_1:
 iny
 rts
rejoin_1:
 jsr seek_write
 jmp backdrop_1
seek_write:
 tya
 clc
 adc <$0a
 stz <$11
 st0 #0
 sta $0002
 lda <$0b
 adc #0
 sta $0003
 lda #2
 sta <$11
 st0 #2
 rts
columns_end:
 .if (columns_end > $5d00)
  .fail
 .endif
 .org $4c00
star_type0:
 .dw 1,1,1,1,1,1,1,1,1,1,1,636,1,1,637,1,1,1,638,1,1,639,1,324,1,640,1,324,641,642,643,324,644,645,646,647,648,649,404,650,651,652,653,654,655,485,656,657,658,659,660,661,565,662,663,664
star_type1:
 .dw 665,666,667,8,668,669,670,671,672,673,77,674,675,676,677,678,679,158,680,681,682,683,684,685,241,686,687,688,689,316,690,316,691,316,690,692,397,397,397,693,397,397,694,479,479,479,479,479,479,559,559,559,559,559,559,559
star_type2:
 .dw 1,1,1,1,1,1,1,695,1,234,1,1,1,234,696,1,697,1,698,234,697,699,700,701,234,702,697,701,703,704,705,317,706,707,708,709,710,711,398,712,713,714,715,716,717,480,718,719,720,721,722,723,560,724,725,726
star_type3:
 .dw 727,728,729,3,730,731,732,733,734,735,72,736,737,738,739,740,741,153,742,743,744,745,746,747,235,748,749,750,751,403,752,318,753,754,755,756,1,757,1,758,318,754,1,1,759,1,760,1,318,1,1,318,1,1,1,1
star_type4:
 .dw 665,666,667,8,668,669,670,671,672,673,77,674,675,676,677,678,679,158,680,681,682,683,684,685,241,686,687,688,761,1,241,1,762,1,241,763,1,1,1,764,1,1,765,1,1,1,1,1,1,1,1,1,1,1,1,1
star_type5:
 .dw 727,728,729,3,730,731,732,733,734,735,72,736,737,738,739,740,741,153,742,743,744,745,746,747,235,748,749,750,766,767,768,769,770,771,772,773,397,774,397,775,776,777,479,479,778,479,779,479,780,559,559,781,559,559,559,559
star_type6:
 .dw 2,2,2,2,2,2,2,71,71,71,71,782,71,71,783,152,152,152,784,152,152,785,233,786,233,787,233,786,641,642,643,324,644,645,646,647,648,649,404,650,651,652,653,654,655,485,656,657,658,659,660,661,565,662,663,664
star_tables_end:
upload_fixed:
 lda #$7d
 tam #3
 lda #0
 jsr seek_tile
 tia $6000,$0002,32
 lda #$7d
 tam #3
 lda #56
 jsr seek_tile
 tia $6440,$0002,32
 lda #$7d
 tam #3
 lda #63
 jsr seek_tile
 tia $63e0,$0002,32
 lda #$7d
 tam #3
 lda #67
 jsr seek_tile
 tia $6020,$0002,32
 lda #$7d
 tam #3
 lda #71
 jsr seek_tile
 tia $6540,$0002,32
 lda #$7d
 tam #3
 lda #74
 jsr seek_tile
 tia $6580,$0002,32
 lda #$7d
 tam #3
 lda #81
 jsr seek_tile
 tia $6620,$0002,32
 lda #$7d
 tam #3
 lda #86
 jsr seek_tile
 tia $66a0,$0002,32
 lda #$7d
 tam #3
 lda #96
 jsr seek_tile
 tia $67c0,$0002,32
 lda #$7d
 tam #3
 lda #98
 jsr seek_tile
 tia $67e0,$0002,32
 lda #$7d
 tam #3
 lda #117
 jsr seek_tile
 tia $68a0,$0002,32
 rts
upload_fixed_end:
 .org $5d00
 .incbin "extra-tiles.bin"
extra_tiles_end:
 .org $4200
star_table_lo:
 .db LOW(star_type0),LOW(star_type1),LOW(star_type2),LOW(star_type3),LOW(star_type4),LOW(star_type2),LOW(star_type3),LOW(star_type0),LOW(star_type4),LOW(star_type5),LOW(star_type6)
star_table_hi:
 .db HIGH(star_type0),HIGH(star_type1),HIGH(star_type2),HIGH(star_type3),HIGH(star_type4),HIGH(star_type2),HIGH(star_type3),HIGH(star_type0),HIGH(star_type4),HIGH(star_type5),HIGH(star_type6)
variant2:
 .db 1,1,1,1,1,1,3,5,0,2,4,6,0,2,4,5,3,1,1,1,1,1,1,1,1,1
variant3:
 .db 3,3,5,0,2,4,6,0,2,4,5,3,1,1,1,1,1,1,1,1,1
phase_variant_offset:
 .db 0,14,28,42,56,70,84,98
; BAT high bytes for map bytes $38-$57: borrowed native backdrop tiles
; $238-$257, palette 0 (castle_horizon.py; $3E/$3F are never used).
 .org $424d
tile_high_borrowed:
 .db 2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2
phase_pointer_lo:
 .db LOW(phase_rows+0),LOW(phase_rows+4),LOW(phase_rows+8),LOW(phase_rows+12),LOW(phase_rows+16),LOW(phase_rows+20),LOW(phase_rows+24),LOW(phase_rows+28)
phase_pointer_hi:
 .db HIGH(phase_rows+0),HIGH(phase_rows+4),HIGH(phase_rows+8),HIGH(phase_rows+12),HIGH(phase_rows+16),HIGH(phase_rows+20),HIGH(phase_rows+24),HIGH(phase_rows+28)
star_dest:
 .db 3,4,5,6,14,15,16,24,25,37,38
star_group:
 .db 3,3,3,3,3,2,2,2,2,3,3
 .org $4295
tile_high:
 .db 0,16,16,16,16,16,16,16,16,16,16,16,16,16,16,16,16,16,16,16,16,16,16,16,16,16,16,16,16,16,16,16,16,16,16,16,16,16,16,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
castle_metadata_end:
 .if (castle_metadata_end > $4319) | (tile_high_borrowed <> tile_high - $48)
 .fail
 .endif
 .org $5fc0
castle_end:
 .org $5f80
column_entry:
 .dw 0,columns_1,columns_2,columns_3,columns_4,columns_5,columns_6,columns_7,columns_8,columns_9,columns_10,columns_11,columns_12,columns_13,columns_14,columns_15,columns_16,columns_17,columns_18,columns_19,columns_20,columns_21,columns_22,columns_23,columns_24,columns_25,columns_26,columns_27,columns_28,columns_29,columns_30,columns_31,columns_32,columns_33
column_entries_end:
