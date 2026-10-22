 .bank $44
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
 ; Stationary sky; one tile right of the earlier layout so 6-1 opens like the original.
 lda $2e4b
 eor #$ff
 inc a
 clc
 adc #8
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
 lda $2257
 eor #$ff
 inc a
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
 ; The previous frame's coarse offset, computed as above (including the +8).
 lda $2257
 eor #$ff
 inc a
 clc
 adc #8
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
 lda <$30
 bne rows_due
 ; No map entries change: only the phase upload.
 lda <$2d
 beq done
 jmp $ff20
rows_due:
 stz <$06
 lda #$44
 sta <$07
 stz <$08
 stz <$09
 lda #14
 sta <$28
 lda <$2d
 beq sky_ready
 jsr $ff20
sky_ready:
 jsr plan_sky
 lda <$29
 bne sky_wrapped
row_loop:
 ldy <$2e
 lda <$2f
 jsr set_ports
 ldx <$25
 jsr dispatch
 jsr next_row
 dec <$28
 bne row_loop
done:
 rts
sky_wrapped:
 ; The run crosses the BAT row end. Row 0's second chunk (from column 0) is
 ; copied first; every later second chunk continues straight on from the
 ; previous row's first chunk: BAT rows are 64 entries apart, the map index
 ; runs on, and the write-address bias stays the same.
 lda <$25
 lsr a
 clc
 adc <$2e
 tay
 cla
 jsr set_ports
 ldx <$29
 jsr dispatch
wrap_loop:
 ldy <$2e
 lda <$2f
 jsr set_ports
 ldx <$25
 jsr dispatch
 dec <$28
 beq done
 jsr next_row
 ldx <$29
 jsr dispatch
 bra wrap_loop
next_row:
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
 rts
castle_main_end:
 .if (castle_main_end > $4200)
 .fail
 .endif
 .org $4319
plan_sky:
 ; Every sky row (0-13) copies <$30 entries from BAT column <$2f, starting at
 ; the same map index <$2e: rows hold sky columns 0-33 (castle_horizon.py),
 ; read from the left column's entry without wrapping, so the right edge
 ; column (left + 32) reads entry +32. Only the BAT row end splits the run:
 ; <$25, <$29 = twice the length of the two chunks.
 lda $2e4b
 lsr a
 lsr a
 lsr a
 sta <$2c
 lda $2e4c
 lsr a
 bcc left_known
 lda <$2c
 ora #32
 sta <$2c
left_known:
 lda <$2f
 sec
 sbc <$2c
 and #63
 sta <$2c
 lda <$2f
 clc
 adc <$26
 and #31
 clc
 adc <$2c
 sta <$2e
 lda #64
 sec
 sbc <$2f
 cmp <$30
 bcc sky_two
 lda <$30
 asl a
 sta <$25
 stz <$29
 rts
sky_two:
 asl a
 sta <$25
 lda <$30
 asl a
 sec
 sbc <$25
 sta <$29
 rts
dispatch:
 jmp [column_entry,x]
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
