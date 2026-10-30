 .bank 0
 ; All native cinema entries call this after their screen reset. Keep the
 ; native sprite reset, then release the gameplay atlas's borrowed VRAM.
 ; $FEE0-$FEFF is original padding.
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
