 .bank 0
 .org $febe
notice_wrapper:
 sta $31b2
 cmp #0
 bne notice_return
 lda $31b3
 bne notice_return
 phx
 phy
 tma #2
 pha
 lda #$46
 tam #2
 jsr $4100
 pla
 tam #2
 ply
 plx
notice_return:
 lda $31b2
 rts
 ; All native cinema entries call this after their screen reset. Keep the
 ; native sprite reset, then release the gameplay atlas's borrowed VRAM.
 ; $FEE0-$FEFF is padding in this module's existing fixed-bank allocation.
 .org $fee0
cinema_sprite_init:
 jsr $f728
 php
 pha
 phx
 tma #2
 pha
 lda #$46
 tam #2
 jsr cinema_blank_sprite
 pla
 tam #2
 plx
 pla
 plp
 rts
 .bank $46
 .org $4100
fan_notice:
 php
 sei
 lda <$0e
 pha
 and #$3f
 sta <$0e
 jsr $fc5e
 ; Initialize the complete 64x32 BAT and the private notice font.
 stz <$11
 st0 #0
 st1 #0
 st2 #0
 lda #2
 sta <$11
 st0 #2
 tia notice_map,$0002,4096
 stz <$11
 st0 #0
 st1 #0
 st2 #$10
 lda #2
 sta <$11
 st0 #2
 tia notice_font,$0002,notice_font_end-notice_font
 ; Palette 0: black/white. Palette 1: black/gold.
 stz $0402
 stz $0403
 stz $0404
 stz $0405
 lda #$ff
 sta $0404
 lda #1
 sta $0405
 lda #16
 sta $0402
 stz $0403
 stz $0404
 stz $0405
 lda #$b8
 sta $0404
 lda #1
 sta $0405
 lda #$ff
 sta $2288
 lda #1
 sta $2289
 sta $22a9
 lda #$b8
 sta $22a8
 lda <$0e
 ora #$80
 sta <$0e
 jsr $fc5e
 cli
 ; Accept a held Run as well as a fresh press, including during cold boot.
notice_wait:
 jsr $fd67
 lda $2e55
 and #8
 beq notice_wait
 sei
 pla
 sta <$0e
 jsr $fc5e
 ; Original initialization immediately reloads the title assets and palettes.
 stz $2288
 stz $2289
 stz $22a8
 stz $22a9
 stz $0402
 stz $0403
 stz $0404
 stz $0405
 stz $0404
 stz $0405
 lda #16
 sta $0402
 stz $0404
 stz $0405
 stz $0404
 stz $0405
 plp
 rts
notice_code_end:
 .org $4300
cinema_blank_sprite:
 ; Sprite pattern $0390 (32x32) occupies VDC words $7200-$72FF.
 ; Native cinemas reference it as an empty sprite without reloading it.
 ; The expanded 2-2 atlas uses this space, so restore it at the ownership
 ; transition. This is before the new cinema's graphics are loaded.
 ; Preserve the VDC register selector. Like native F728, use the existing
 ; increment=1 configuration. No new persistent RAM is needed.
 sei
 lda <$11
 pha
 stz <$11
 st0 #0
 st1 #0
 st2 #$72
 lda #2
 sta <$11
 st0 #2
 clx
cinema_blank_loop:
 stz $0002
 stz $0003
 dex
 bne cinema_blank_loop
 pla
 sta <$11
 sta $0000
 rts
cinema_blank_sprite_end:
 .org $4400
notice_font:
 .incbin "font.bin"
notice_font_end:
 .org $4800
notice_map:
 .incbin "map.bin"
notice_end:
