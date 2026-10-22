 .bank 1
 .org $82cd
 jsr $ff35
 ; init_background (dispatch): stage load
 .org $8457
 jsr $fe40
 ; early ($fe40) makes both original calls ($e3f2, $abd7) itself.
 nop
 nop
 nop
 .org $8472
 jsr $ff00
 .org $85b4
 jmp $ff2c
 ; area_background (dispatch): area change
 .bank 4
 .org $8001
 jsr $febe
 .org $802d
 jsr $fee0
