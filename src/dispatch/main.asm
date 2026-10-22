 .bank $46
 .org $4000
find_renderer:
 jmp $5840
 beq missing
 clx
lookup:
 lda $224c
 cmp heights,x
 bne next
 lda $224d
 cmp cutoffs,x
 bne next
 lda $224e
 cmp lows,x
 bne next
 lda $224f
 cmp highs,x
 bne next
 jmp $5800
 nop
next:
 inx
 cpx #9
 bne lookup
missing:
 cla
 rts
heights:
 .db 12,12,20,12,16,22,24,24,23
cutoffs:
 .db 32,16,16,16,48,16,16,16,32
lows:
 .db 0,144,0,40,192,80,48,116,88
highs:
 .db 160,169,177,188,172,182,163,197,191
banks:
 .db 64,71,76,81,86,103,115,120,124
 .bank 0
 .org $fe00
multi_hook:
 jsr lookup_wrapper
 beq finished
 sta <$2f
 tma #2
 pha
 tma #3
 pha
 lda <$2f
 tam #2
 jsr $4000
 pla
 tam #3
 pla
 tam #2
finished:
 rts
 .org $ff00
multi_late:
 jsr lookup_wrapper
 bne late_done
 jmp $8097
late_done:
 rts
 .org $ffb0
lookup_wrapper:
 phx
 phy
 tma #2
 pha
 lda #$46
 tam #2
 jsr $4000
 tax
 pla
 tam #2
 txa
 ply
 plx
 cmp #0
 rts
 .bank 0
 .org $fe40
early:
 jsr $e3f2
 jsr $abd7
 php
 pha
 phx
 phy
 lda <$06
 pha
 lda <$07
 pha
 lda <$08
 pha
 lda <$09
 pha
 lda <$0a
 pha
 lda <$0b
 pha
 lda <$25
 pha
 lda <$26
 pha
 lda <$27
 pha
 lda <$28
 pha
 lda <$29
 pha
 lda <$2a
 pha
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
 lda <$30
 pha
 jsr $fe00
 pla
 sta <$30
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
 pla
 sta <$2a
 pla
 sta <$29
 pla
 sta <$28
 pla
 sta <$27
 pla
 sta <$26
 pla
 sta <$25
 pla
 sta <$0b
 pla
 sta <$0a
 pla
 sta <$09
 pla
 sta <$08
 pla
 sta <$07
 pla
 sta <$06
 ply
 plx
 pla
 plp
 rts

 .bank 0
 .org $ff2c
area_background:
 ; Area change (bank 1 $85B4). The native picture fills most of this frame,
 ; so the Enhanced draw waits for the next main-loop frame (deferred_draw),
 ; which the original spends waiting for vblank.
 jsr $80ab
 lda #$fe
 sta $2258
 rts
init_background:
 ; Stage load (bank 1 $82CD). Neither caller reads A or the flags $80AB
 ; returns: the load path loads A next, the area path calls $85B7.
 jsr $80ab
 lda #$ff
 sta $2257
 sta $2258
 bra draw_now
deferred_draw:
 ; Main loop, every frame (selector hook). $FE, an impossible camera high
 ; byte, marks an area change's pending draw; the renderers initialize on $FF.
 lda $2258
 cmp #$fe
 bne draw_done
 inc a
 sta $2258
draw_now:
 ; 6-1 opens on the native picture, which Enhanced's matches: its first
 ; gameplay update draws, so loading takes as long as the original's.
 lda $2e5f
 cmp #16
 beq draw_done
 lda $224f
 cmp #$ac
 beq draw
 cmp #$a3
 beq draw
 cmp #$bf
 bne draw_done
draw:
 jmp $fe46
draw_done:
 rts
init_hook_end:
