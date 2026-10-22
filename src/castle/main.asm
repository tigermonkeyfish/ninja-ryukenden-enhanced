 .include "loop.inc"
 .bank $7c
 .org $4000
smooth:
 jsr animate_stars
 ; Original background workspace is available while its renderer is replaced.
 lda $2e4b
 cmp $2257
 bne changed
 lda $2e4c
 cmp $2258
 bne changed
 rts
changed:
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

 pha
 and #7
 sta <$27
 pla
 lsr a
 lsr a
 lsr a
 sta <$26
 lda $2e4b
 lsr a
 lsr a
 lsr a
 sta <$25
 lda $2e4c
 and #1
 beq low_half
 lda <$25
 ora #32
 sta <$25
low_half:
 ; The original geometry at $2251-$2256 must survive death/respawn.
 ; Only $2257-$225A (old renderer's bank saves and cursor) may be reused.
 stz <$2d
 lda $2258
 cmp #$ff
 beq phase_changed
 lda $2259
 and #7
 cmp <$27
 beq same_phase
phase_changed:
 inc <$2d
same_phase:
 lda $2e4b
 and #7
 cmp #1
 lda #32
 adc #0
 sta <$30
 lda <$25
 sta <$2f
 lda $2258
 cmp #$ff
 beq initialize
 lda $2259
 lsr a
 lsr a
 lsr a
 cmp <$26
 bne cache
 ; The existing tile-map entries are still correct except at a new edge.
 stz <$30
 lda <$25
 sec
 sbc $225a
 and #63
 beq cache
 cmp #1
 beq new_right
 cmp #63
 beq new_left
 lda $2e4b
 and #7
 cmp #1
 lda #32
 adc #0
 sta <$30
 bra cache
new_right:
 lda <$25
 clc
 adc #32
 and #63
 sta <$2f
new_left:
 inc <$30
 bra cache
initialize:
 jsr upload_fixed
cache:
 lda $2e4b
 sta $2257
 lda $2e4c
 sta $2258
 lda <$26
 asl a
 asl a
 asl a
 ora <$27
 sta $2259
 lda <$25
 sta $225a
 lda <$30
 bne rows_due
 ; No map entries change: only the phase uploads.
 lda <$2d
 beq done
 lda #23
 sta <$28
 jsr upload_row
 lda #9
 sta <$28
 jmp upload_row
rows_due:
 stz <$06
 lda #$44
 sta <$07
 stz <$08
 stz <$09
 lda #23
 sta <$28
row_loop:
 ; Each group (sky from row 0, horizon from row 14) uploads its phase tiles,
 ; then plans the column copy once; group uploads use $2029-$2030.
 lda <$28
 cmp #23
 beq group_start
 cmp #9
 bne row_draw
group_start:
 lda <$2d
 beq group_ready
 jsr upload_row
group_ready:
 jsr horizon_start
 jsr plan_columns
row_draw:
 jsr draw_row
 lda <$06
 clc
 adc #64
 sta <$06
 bcc map_no_carry
 inc <$07
map_no_carry:
 lda <$08
 clc
 adc #64
 sta <$08
 bcc bat_no_carry
 inc <$09
bat_no_carry:
 dec <$28
 bne row_loop
done:
 rts
plan_columns:
 ; Every row copies <$30 entries from BAT column <$2f and map index <$2e.
 ; The run can cross the end of the BAT row (continue at column 0) and of
 ; the map row (continue at MAP_WRAP), in either order: <$25, <$29, <$2a =
 ; twice the length of each chunk, <$2b = what ends after chunks 1 and 2
 ; (bits 0-1, 2-3; bit 0 BAT row, bit 1 map row).
 stz <$29
 stz <$2a
 stz <$2b
 lda #64
 sec
 sbc <$2f
 tax
 lda #64
 sec
 sbc <$2e
 tay
 stx <$25
 cpy <$25
 beq plan_same
 bcc plan_map_first
 lda #1
 sty <$2c
 bra plan_first
plan_map_first:
 stx <$2c
 tya
 tax
 lda #2
 bra plan_first
plan_same:
 lda #3
 ldy #255
 sty <$2c
plan_first:
 cpx <$30
 bcs plan_one
 sta <$2b
 stx <$25
 lda <$2c
 cmp <$30
 bcs plan_two
 lda <$2b
 eor #3
 asl a
 asl a
 tsb <$2b
 lda <$30
 sec
 sbc <$2c
 asl a
 sta <$2a
 lda <$2c
 sec
 sbc <$25
 asl a
 sta <$29
 bra plan_c1
plan_two:
 lda <$30
 sec
 sbc <$25
 asl a
 sta <$29
plan_c1:
 asl <$25
 rts
plan_one:
 lda <$30
 asl a
 sta <$25
 rts
castle_main_end:
 .if (castle_main_end > $4200)
 .fail
 .endif
 .org $4319
draw_row:
 ldy <$2e
 lda <$2f
 jsr set_ports
 ldx <$25
 jsr dispatch
 ldx <$29
 beq draw_done
 lda <$2b
 jsr row_end
 ldx <$29
 jsr dispatch
 ldx <$2a
 beq draw_done
 lda <$2b
 lsr a
 lsr a
 jsr row_end
 ldx <$2a
dispatch:
 jmp [column_entry,x]
draw_done:
 rts
row_end:
 ; A bit 1: map row ended (Y = MAP_WRAP); bit 0: BAT row ended (seek
 ; column 0, which also sets the write-address bias for the new Y).
 bit #2
 beq row_end_bat
 ldy #MAP_WRAP
 bit #1
 bne row_end_bat
 ; Same BAT address, new Y: move the bias and the write pointer (the chunk
 ; may have ended on foreground, which leaves the write pointer behind).
 lda <$0a
 clc
 adc #64 - MAP_WRAP
 sta <$0a
 bcc row_end_seek
 inc <$0b
row_end_seek:
 jmp seek_write
row_end_bat:
 cla
set_ports:
 ; Read and write pointers at BAT column A of this row; <$0a/<$0b = that
 ; address minus Y (map index) for the column copy's write-pointer seeks.
 clc
 adc <$08
 tax
 lda <$09
 adc #0
 sta <$0b
 lda #1
 sta <$11
 st0 #1
 stx $0002
 lda <$0b
 sta $0003
 stz <$11
 st0 #0
 stx $0002
 sta $0003
 lda #2
 sta <$11
 st0 #2
 stx <$0a
 tya
 eor #$ff
 sec
 adc <$0a
 sta <$0a
 lda <$0b
 adc #$ff
 sta <$0b
 rts
castle_helpers_end:
 .if (castle_helpers_end > $4400)
 .fail
 .endif
 .include "castle-generated.inc"
