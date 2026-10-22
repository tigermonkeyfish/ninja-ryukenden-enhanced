; Shared background offset: D = floor(C/divisor) + entrance anchor.
; Enhanced divisor=8 (25% of the former SMOOTH). The display uses D-C.
; $2102..$2103 are reserved alongside REV8's flags at the stack-page bottom.
 .bank 0
 .org $ffd0
speed_bridge:
 phx
 tma #2
 pha
 lda #$46
 tam #2
 jsr speed_offset
 tax
 pla
 tam #2
 txa
 plx
 rts
speed_bridge_end:
 .bank $46
 .org $5900
speed_offset:
 lda <$2b
 pha
 lda <$2c
 pha
 lda <$2d
 pha
 lda <$2e
 pha
 lda <$2f
 pha
 ; Enhanced always uses the existing divisor-8 path.
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
 nop

 ; Unsigned 16-bit divide by 8: three shifts (this runs every update; the
 ; former sixteen-step loop cost about 1,400 cycles).
 lda $2210
 lsr a
 sta <$2a
 lda $220f
 ror a
 lsr <$2a
 ror a
 lsr <$2a
 ror a
 sta <$29
 bra apply_anchor
gentle_speed:
 lda $2210
 lsr a
 sta <$2a
 lda $220f
 ror a
 sta <$29
 lsr <$2a
 ror <$29
apply_anchor:
 lda $2258
 cmp #$ff
 bne anchor_ready
 lda $2210
 lsr a
 sta <$2b
 lda $220f
 ror a
 sec
 sbc <$29
 sta $2102
 lda <$2b
 sbc <$2a
 sta $2103
anchor_ready:
 lda <$29
 clc
 adc $2102
 sta <$29
 lda <$2a
 adc $2103
 sta <$2a
 bra offset_ready
smooth_speed:
 lda $2210
 lsr a
 sta <$2a
 lda $220f
 ror a
 sta <$29
offset_ready:
 pla
 sta <$2f
 pla
 sta <$2e
 pla
 sta <$2d
 pla
 sta <$2c
 pla
 sta <$2b
 lda <$29
 sec
 sbc $220f
 rts
speed_offset_end:
