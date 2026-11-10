; Use NES Firewheel logic ($2100 bit 2, 1.11-dev): the Fire Wheel (item 7,
; item effect type 5) behaves like the NES game's Invincible Fire Wheel.
; With the bit clear every hook below runs the original instruction it
; replaced and nothing else. The protection from damage is the damage gate's
; rule (src/options); this module holds the rest.
;
; Code lives in bank 3's unused tail ($FF in the original, never read or
; executed in the audited boot and stored runs; docs/validation/
; nes-firewheel.md). Bank 3 is mapped at $C000 whenever the object code
; runs: the enemy dispatch jumps to bank 3 handlers. Every hook is in bank 2
; object code ($A000) and calls this code directly; no fixed-bank bytes.

OPTIONS = $2100
NES_FIREWHEEL = 4
WHEEL = 5                       ; item effect type of the Fire Wheel

EFFECT = $310D                  ; effect slot being processed
EFFECT_TYPE = $310E             ; per slot (5 slots), $FF = free
EFFECT_SPRITE = $3118
; Per-slot fields the wheel's handler never uses; the effect constructor
; ($A9D5) clears both for every new effect. They count the wheel's updates.
WHEEL_COUNT_LO = $3127
WHEEL_COUNT_HI = $3136

RYU_X = $2E9E                   ; 16-bit, centre
RYU_Y = $2EA0                   ; feet
RYU_HEALTH = $2EAD
ENEMY_SLOT = $2EDF
BOSS_HEALTH = $3035
BOSS_HIT = $3036                ; per enemy slot: hit already counted
SPRITE_Y_HIGH = $2D82           ; per sprite object

; Effect box built by native $95D6, tested by $9489 against the enemy box.
BOX_LEFT = $2EC7                ; 16-bit
BOX_TOP = $2EC9
BOX_RIGHT = $2ECA               ; 16-bit
BOX_BOTTOM = $2ECC

WHEEL_LIFE = 516                ; updates: 96, then seven intervals of 60
FLICKER_FROM = WHEEL_LIFE - 180

 .bank 2
 ; Effect-versus-enemy box (in $AA74, every kill check): A = effect type.
 .org $aa8a
 jsr nes_effect_box
 ; Boss kill check entry ($A211, replaces lda $2EB2).
 .org $a211
 jsr nes_boss_check
 ; Fire Wheel handler: its lifetime countdown ($AF2D, replaces lda $2EDA).
 .org $af2d
 jmp nes_wheel_timer

 .bank 3
 .org $dc00
; Hitbox. NES: the wheel hits an object whose X - Ryu X is within
; [-(hw+8), hw+11] and whose feet - Ryu's feet is within [-24, h-1], on the
; ground and in the air, whatever his facing. The native test ($9489) needs
; enemy right > left, left < right, bottom > top and top < bottom, so the
; same set is left = X-9, right = X+12, top = feet-25, bottom = feet.
; Other effects keep the native box ($AABD).
nes_effect_box:
 cmp #WHEEL
 bne native_effect_box
 lda OPTIONS
 and #NES_FIREWHEEL
 beq native_effect_box
 lda RYU_X
 sec
 sbc #9
 sta BOX_LEFT
 lda RYU_X+1
 sbc #0
 sta BOX_LEFT+1
 lda RYU_X
 clc
 adc #12
 sta BOX_RIGHT
 lda RYU_X+1
 adc #0
 sta BOX_RIGHT+1
 lda RYU_Y
 sta BOX_BOTTOM
 sec
 sbc #25
 bcs wheel_top
 cla                            ; above the screen top, as native $95D6
wheel_top:
 sta BOX_TOP
 rts
native_effect_box:
 jmp $aabd

; Bosses. Native: one point per contact (the hit flag stays set while any
; sword or effect still touches). NES: the wheel takes one point every
; update it touches. While a wheel touches this boss, clear its hit flag so
; the native check counts this update. At 0 the native death takes over.
nes_boss_check:
 lda OPTIONS
 and #NES_FIREWHEEL
 beq boss_native
 lda BOSS_HEALTH
 beq boss_native
 phx
 phy
 lda EFFECT
 pha
 ldy #4
boss_scan:
 lda EFFECT_TYPE,y
 cmp #WHEEL
 bne boss_next
 sty EFFECT
 phy
 jsr nes_effect_box
 jsr $9489                      ; A = 0: the boxes overlap
 ply
 cmp #0
 bne boss_next
 ldx ENEMY_SLOT
 stz BOSS_HIT,x
 bra boss_done
boss_next:
 dey
 bpl boss_scan
boss_done:
 pla
 sta EFFECT
 ply
 plx
boss_native:
 lda $2eb2
 rts

; Lifetime. Native: 10 stage-timer ticks (about 650 updates), a sound at
; each, faster spin in the last three, ten fast ticks once Ryu is dead.
; NES: 516 updates, a tick at 96 and every 60 after (the last ends it), drawn
; only on alternate updates in the last 180, cleared at death.
nes_wheel_timer:
 lda OPTIONS
 and #NES_FIREWHEEL
 bne nes_timer
 lda $2eda
 jmp $af30
nes_timer:
 ldy EFFECT
 lda RYU_HEALTH
 beq wheel_end
 ; Count only while the stage timer runs: its update counter ($2EDA,
 ; 65..1) is left at 0 once a boss is beaten (tally) and at a time-out. The
 ; handler does not run during pause or loads.
 lda $2eda
 beq timer_done
 lda WHEEL_COUNT_LO,y
 clc
 adc #1
 sta WHEEL_COUNT_LO,y
 lda WHEEL_COUNT_HI,y
 adc #0
 sta WHEEL_COUNT_HI,y
 ldx #7
timer_boundary:
 lda WHEEL_COUNT_LO,y
 cmp boundary_lo,x
 bne timer_next
 lda WHEEL_COUNT_HI,y
 cmp boundary_hi,x
 beq timer_tick
timer_next:
 dex
 bpl timer_boundary
 bra timer_flicker
timer_tick:
 phx
 lda #$16                       ; the native wheel tick
 jsr $ea84
 plx
 ldy EFFECT
 cpx #7
 beq wheel_end
timer_flicker:
 lda WHEEL_COUNT_LO,y
 cmp #LOW(FLICKER_FROM)
 lda WHEEL_COUNT_HI,y
 sbc #HIGH(FLICKER_FROM)
 bcc timer_done
 lda WHEEL_COUNT_LO,y
 lsr a
 bcc timer_done
 ; Hidden this update: the handler placed the sprite already; move it below
 ; the display. The next update's placement ($946D) clears this byte.
 ldx EFFECT_SPRITE,y
 lda #1
 sta SPRITE_Y_HIGH,x
timer_done:
 rts
wheel_end:
 jmp $aaa5                      ; native: mark the effect for removal
boundary_lo:
 .db LOW(96),LOW(156),LOW(216),LOW(276),LOW(336),LOW(396),LOW(456),LOW(WHEEL_LIFE)
boundary_hi:
 .db HIGH(96),HIGH(156),HIGH(216),HIGH(276),HIGH(336),HIGH(396),HIGH(456),HIGH(WHEEL_LIFE)
nes_firewheel_end:
 .if (nes_firewheel_end > $e000)
 .fail
 .endif
