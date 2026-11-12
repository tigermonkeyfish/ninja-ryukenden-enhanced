; Active flags: bit 0 = original background, bit 1 = no contact damage,
; bit 2 = Use NES Firewheel logic, bits 3-5 = palette mode (src/palette),
; bit 7 = set with the SMS palette mode only (a copy src/palette tests);
; bit 6 unassigned (zero). Before 1.11-dev's SMS mode bits 5-7 were the
; palette module's state; that is in $2104 now (see docs/ARCHITECTURE.md).
; Two bytes at the bottom of the CPU stack page. The native stack grows
; downward from $21FF; validation watches the reserved low margin.
OPTIONS = $2100
DRAFT = $2101
SAVE_STATUS = $2105         ; src/bram: what the backup RAM said (ST_ values)
SAVE_SETTINGS = $4b03       ; src/bram, this bank: save $2100 and $3227
NES_FIREWHEEL = 4
; The protection rule (src/nes-firewheel, bank 3, mapped at $C000 whenever
; the gate's callers run): carry clear = no damage and no knockback.
NES_FIREWHEEL_RULE = $dc00
 .bank 0
 ; Contact damage (bank 1 $8F70, A = damage). Its only callers are the
 ; enemy contact check in bank 2 ($A1C8, $A1D0); timer expiry enters at
 ; native_damage_entry. Returning early skips the damage and the knockback,
 ; with A, X, Y and P as on entry (like the native immunity checks).
 .org $fe20
damage_gate:
 php
 pha
 lda OPTIONS
 bit #2
 bne ignore_damage
 and #NES_FIREWHEEL
 beq native_damage
 jsr NES_FIREWHEEL_RULE
 bcc ignore_damage
native_damage:
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
 .if (damage_gate_end > $fe40)
 .fail
 .endif

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
 ; The menu's glyphs (below; read with this bank in MPR2 like the rest of
 ; the menu) after the gate, in the options module's claim $5840-$58FF:
 ; they moved here from the menu's $4400-$4AFF when the reset row filled it.
 ; '.', ':' and '/' in the HUD font's style, for tiles $7AA, $7AD and $7B9:
 ; planes 0 and 1, row by row (colours 1-3 as in the font's own glyphs).
menu_glyphs:
 ; '.': the bottom two rows of the HUD font's '1' stem, three pixels wide.
 .db $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$20,$18,$18,$38,$00,$00
 ; ':': the same dot at rows 1-2 (shaded like the font's top rows) and 4-5.
 .db $00,$00,$38,$00,$38,$00,$00,$00,$20,$18,$20,$18,$00,$00,$00,$00
 ; '/': a three-pixel diagonal, shaded like the '1' stem row by row.
 .db $0e,$00,$1c,$00,$1c,$00,$38,$00,$40,$30,$40,$30,$60,$e0,$00,$00
menu_glyphs_end:
 .if (menu_glyphs_end > $5900)
 .fail
 .endif

; ---------------------------------------------------------------------------
; The in-game menu: a popup window over the playfield (docs/ARCHITECTURE.md,
; "Menu display"). Called by the Select hook (src/selector-hook, $FF70) with
; this bank in MPR2; returns A = the stage to start, or $FF (cancelled or
; refused: nothing changed).
;
; The window is drawn straight into the playfield's BAT (64 x 32): BOX_ROWS
; rows from BAT row BOX_TOP, BOX_WIDTH columns from the BAT column at screen
; column BOX_LEFT, wrapping at column 63. The BAT words it covers are copied
; first into the sprite-table buffer the game is building (VRAM $7E00 or
; $7F00, named by $2B81; the game rewrites all 256 words of it before it
; points the VDC at it, later in this same frame) and, for the last row,
; into the HUD font's blank tiles $7AB-$7AC; closing copies them back. The
; HUD rows 28-30 are not touched; row 31, the blank band under the HUD,
; shows the version and credit while the window is open. Sprites are hidden
; (VDC control register bit 6) while it is open; the register is rewritten
; from the game's shadow <$0E on close.
MENU_ENTRY = $4400          ; the hook's jsr target (src/selector-hook)
OPTION_BITS = $3f           ; draft bits copied to $2100 on Run
PALETTE_BITS = $38          ; previewed live while the menu is open
PALETTE_FAMILY = $18        ; the upload family (src/palette): $08 NES-A and NES-B
PALETTE_NES = $08           ; reloads palette data (src/nes-palette): shown after Run
PALETTE_SMS = $38
SMS_FLAG = $80              ; $2100 bit 7: set exactly with SMS (src/palette)
OPENED_OPTIONS = $2103      ; ,X after tsx in preview_palette: $2100 as the menu opened
                            ; (menu_open pushed it; above it preview_palette's return)
LANGUAGE = $3227            ; native: 0 Japanese, 1 English, 2 Chinese
BOX_TOP = 7                 ; BAT row of the window's top row
BOX_LEFT = 3                ; screen column of its left edge
SAT_BUILD = $2b81           ; native: the sprite-table buffer being built (0, 1)
SAT_HIGH = $faa2            ; native: its VRAM address, high byte ($7E, $7F)
CR_SHADOW = $0e             ; native: VDC control register, low byte
PLAYFIELD_X = $2e4b         ; and $2E4C: the playfield's BXR (mod 512)
PLAYFIELD_Y = $2e4d         ; and $2E4E: its BYR (0 in gameplay)
PAD_NEW = $2e57             ; newly pressed: 1 I, 2 II, 4 Select, 8 Run,
                            ; $10 Up, $20 Right, $40 Down, $80 Left
PAD_HELD = $2e55
RYU_STATE = $2eab           ; native: Ryu's state, 10 from his death on
RYU_DEAD = 10
RYU_HEALTH = $2ead
QUEUE_COUNT = $2260         ; native palette upload queue: entries
QUEUE_ALL = $f394           ; native: queue colours 0-511, under the lock
WAIT_VBLANK = $fd67
SOUND_FLAGS = $387e         ; sound driver (bank $38, run by the vblank interrupt at
                            ; $FD16): bit 6 music, bit 7 effect channels played
SET_WRITE = $fc34           ; native: VRAM write address = X:A, register 2
SPACE = $9f
; Zero page borrowed by the menu; saved on entry and restored on exit.
STAGE = $25                 ; Level Select entry shown
ROW = $26                   ; row selected (0 STAGE, 1.. options, FIELDS reset)
BLINK = $27                 ; frame counter: value hidden while bit 4 is set
BAT_ROW = $28               ; drawing/copy cursor: BAT row
BAT_COL = $29               ; and column (0-63)
PTR = $2a                   ; and $2B: data pointer / backup VRAM address
SCRATCH = $2a
DIRECTION = $2c             ; copy_box: bit 7 clear BAT -> backup, set back
ZP_FIRST = $25
ZP_LAST = $2c

 .bank $46
 .org MENU_ENTRY
menu:
 ; Refused (A = $FF, nothing touched) while Ryu is dead: from the death
 ; (native $8E57: state 10, health 0) through the respawn or continue,
 ; whose stage reload rewrites both sprite-table buffers. The hook's own
 ; conditions ($2E63 = 0, $2201 != 0) let the death animation through.
 lda RYU_STATE
 cmp #RYU_DEAD
 beq menu_refused
 lda RYU_HEALTH
 beq menu_refused
 ; ... and unless the playfield is at vertical scroll 0: the window's rows
 ; must stay clear of the HUD's rows 28-31.
 lda PLAYFIELD_Y
 ora PLAYFIELD_Y+1
 beq menu_open
menu_refused:
 lda #$ff
 rts
menu_open:
 ldx #ZP_FIRST
save_zero_page:
 lda <$00,x
 pha
 inx
 cpx #ZP_LAST+1
 bne save_zero_page
 lda <$11
 pha
 ; The sound holds while the window is open: with SOUND_FLAGS bits 6-7
 ; clear the driver's vblank tick advances nothing and only silences each
 ; channel (bank $38 $5066: volume 0), so on return the driver goes on
 ; from exactly the state it had here, and every interrupt after the menu
 ; takes the time it takes in the run without the menu. (A driver that
 ; played on through the menu took other time in each vblank afterwards,
 ; so the main loop was a few cycles elsewhere at frame ends: seen while an
 ; area change redraws the BAT across frames; docs/validation/all-palettes.md.)
 lda SOUND_FLAGS
 pha
 and #$3f
 sta SOUND_FLAGS
 ; The options as they were, for the palette preview's cancel.
 lda OPTIONS
 pha
 jsr open_window
 lda $2e5f
 cmp #22
 bcc valid_stage
 cla
valid_stage:
 sta <STAGE
 stz <ROW
 ; The draft: the options (bits 0-5) and the language (bits 6-7).
 lda LANGUAGE
 and #3
 asl a
 asl a
 asl a
 asl a
 asl a
 asl a
 sta <SCRATCH
 lda OPTIONS
 and #OPTION_BITS
 ora <SCRATCH
 sta DRAFT
redraw:
 stz <BLINK
 jsr preview_palette
 jsr draw_values
menu_loop:
 jsr WAIT_VBLANK
 inc <BLINK
 jsr draw_values
 lda PAD_NEW
 bit #4
 bne cancel
 bit #8
 bne choose
 and #$50
 beq horizontal
 and #$40
 beq field_up
 inc <ROW
 lda <ROW
 cmp #FIELDS+1              ; the rows: STAGE, the options, the reset row
 bcc redraw
 stz <ROW
 bra redraw
field_up:
 lda <ROW
 bne field_decrement
 lda #FIELDS+1
 sta <ROW
field_decrement:
 dec <ROW
 bra redraw
horizontal:
 ldx <ROW
 cpx #FIELDS
 beq reset_row
 lda PAD_NEW
 and #$a0
 beq menu_loop
 cpx #0
 beq stage_change
 jsr choice_change
 bra redraw
 ; The reset row: I or II sets the draft's options and language to the
 ; defaults (menu.txt: the first value of each option; the power-on
 ; settings without saved ones, src/bram). STAGE is kept; Run applies the
 ; draft and Select discards it, as after any change. Left/Right do nothing.
reset_row:
 lda PAD_NEW
 and #3
 beq menu_loop
 lda #DEFAULT_DRAFT
 sta DRAFT
 bra redraw
stage_change:
 and #$20
 beq previous_stage
 inc <STAGE
 lda <STAGE
 cmp #22
 bcc redraw
 stz <STAGE
 bra redraw
previous_stage:
 lda <STAGE
 bne stage_decrement
 lda #22
 sta <STAGE
stage_decrement:
 dec <STAGE
 bra redraw
cancel:
 lda #$ff
 sta <STAGE
choose:
 ; Return once Select, Run, I and II are all released.
 jsr WAIT_VBLANK
 lda PAD_HELD
 and #$0f
 bne choose
 jsr close_window
 ; The vblank upload reads $2100's palette bits, so $2100 is changed with
 ; interrupts held off.
 pla
 and #PALETTE_BITS
 sta <SCRATCH
 lda <STAGE
 cmp #$ff
 beq cancelled
 ; Run: the draft's options, and its language. The palette mode first,
 ; through set_palette: an NES value was not previewed (the live mode is
 ; still the one the menu opened in), and set_palette writes bit 7 with it.
 lda DRAFT
 and #PALETTE_BITS
 jsr set_palette
 lda DRAFT
 and #OPTION_BITS
 sta <SCRATCH
 php
 sei
 lda OPTIONS
 and #$ff - OPTION_BITS     ; bit 7 as set_palette left it
 ora <SCRATCH
 sta OPTIONS
 plp
 lda DRAFT
 lsr a
 lsr a
 lsr a
 lsr a
 lsr a
 lsr a
 sta LANGUAGE
 ; The settings to the backup RAM, if there is one (src/bram; interrupts
 ; off for its length: the window is closed, the sound still held, and the
 ; stage restarts next).
 jsr SAVE_SETTINGS
 bra closed
cancelled:
 ; Select: the palette mode as it was (the preview may have changed it).
 lda <SCRATCH
 jsr set_palette
 ; Let the palette module put the colours back before the game runs on (a
 ; full upload at once in Original; in GB DMG and SMS about 136 colours,
 ; then 16 a vblank left over, about 25 vblanks for all 512; HELL about
 ; 12): a vblank, then more
 ; while its queue holds work, at most 48 in all; then one more, so the
 ; game resumes after an interrupt with no upload (a full upload takes about
 ; 27 lines and would move the update's first writes against the raster).
 ldx #48
settle_palette:
 jsr WAIT_VBLANK
 lda QUEUE_COUNT
 beq settled
 dex
 bne settle_palette
settled:
 jsr WAIT_VBLANK
closed:
 pla
 sta SOUND_FLAGS            ; the next vblank plays on from where the sound stopped
 pla
 sta <$11
 sta $0000
 ldy <STAGE
 ldx #ZP_LAST
restore_zero_page:
 pla
 sta <$00,x
 dex
 cpx #ZP_FIRST-1
 bne restore_zero_page
 tya
 cmp #$ff
 beq selection_return
 sta $2241
 lda selected_next_sequence,y
 sta $2247
 stz $2248
 ; A chosen stage starts with full health, as after a respawn (native $8DFC).
 lda #16
 sta $2ead
 tya
selection_return:
 rts

 ; The live palette mode follows the draft's, so the choice shows at once;
 ; cancel puts the old mode back. NES colours (NES-A, NES-B) are not a
 ; mapping of the RAM palette but other palette data, loaded with the stage
 ; (src/nes-palette): they show after Run, which restarts the stage. While
 ; an NES value is highlighted, the live mode is the one the menu opened in,
 ; so the colours on screen do not change. (Opened in an NES mode, the RAM
 ; palette holds NES colours: ORIGINAL shows them unmapped, the mapped modes
 ; map them.)
preview_palette:
 lda DRAFT
 and #PALETTE_FAMILY
 cmp #PALETTE_NES
 bne preview_draft
 tsx
 lda OPENED_OPTIONS,x       ; $2100 as the menu found it (pushed in menu_open)
 bra preview_masked
preview_draft:
 lda DRAFT
preview_masked:
 and #PALETTE_BITS
 ; A = palette bits: make them the live mode. When they change, all 512
 ; colours are queued (native $F394, under the palette lock) and src/palette
 ; re-uploads them in the new mode's colours at the next vblanks: its state
 ; bit tells only whether the VCE holds mapped colours, not which table
 ; (GB DMG, HELL or SMS), so a change between those needs the full queue.
 ; $2100 bit 7 is set with SMS and only then (src/palette tells SMS from
 ; HELL by it).
set_palette:
 sta <SCRATCH
 lda OPTIONS
 and #PALETTE_BITS
 cmp <SCRATCH
 beq palette_kept
 lda <SCRATCH
 cmp #PALETTE_SMS
 bne palette_flagged
 ora #SMS_FLAG
 sta <SCRATCH
palette_flagged:
 php
 sei
 lda OPTIONS
 and #$ff - PALETTE_BITS - SMS_FLAG
 ora <SCRATCH
 sta OPTIONS
 plp
 jmp QUEUE_ALL
palette_kept:
 rts

 ; X = option field (1..FIELDS-1). Y = its choice entry for the draft's
 ; value (the field's first entry if none matches).
choice_entry:
 lda DRAFT
 and choice_mask-1,x
 sta <SCRATCH
 ldy choice_end-1,x
choice_search:
 dey
 lda choice_value,y
 cmp <SCRATCH
 beq choice_found
 tya
 cmp choice_first-1,x
 bne choice_search
 tay
choice_found:
 rts

 ; X = option field, A = Right ($20) or Left ($80): the next or previous
 ; choice, wrapping.
choice_change:
 pha
 jsr choice_entry
 pla
 and #$20
 beq choice_previous
 iny
 tya
 cmp choice_end-1,x
 bcc choice_set
 ldy choice_first-1,x
 bra choice_set
choice_previous:
 tya
 cmp choice_first-1,x
 bne choice_decrement
 ldy choice_end-1,x
choice_decrement:
 dey
choice_set:
 lda choice_mask-1,x
 eor #$ff
 and DRAFT
 ora choice_value,y
 sta DRAFT
 rts

 ; Every value field and the reset field; the selected one blinks (16 frames
 ; shown, 16 blank).
draw_values:
 ldx #FIELDS                ; the reset field, then the value fields
value_loop:
 phx
 jsr draw_field
 plx
 dex
 bpl value_loop
 rts
draw_field:
 jsr field_seek
 cpx <ROW
 bne field_shown
 lda <BLINK
 and #$10
 beq field_shown
 ldy field_width,x
field_blank:
 lda #SPACE
 jsr put
 dey
 bne field_blank
 rts
field_shown:
 txa
 beq draw_stage
 lda field_width,x
 pha
 ldy #RESET_TEXT_AT
 cpx #FIELDS
 beq reset_label
 jsr choice_entry
 lda choice_text_at,y
 tay
reset_label:
 pla
 sta <SCRATCH
label_loop:
 lda choice_text,y
 jsr put
 iny
 dec <SCRATCH
 bne label_loop
 rts
 ; "W-S" from the world/stage digits, then " A".." C" for the 6-4 phases.
draw_stage:
 ldy <STAGE
 lda stage_numbers,y
 pha
 lsr a
 lsr a
 lsr a
 lsr a
 ora #$a0
 jsr put
 lda #$9a
 jsr put
 pla
 and #$0f
 ora #$a0
 jsr put
 lda #SPACE
 jsr put
 cpy #19
 lda #SPACE
 bcc stage_suffix
 tya
 adc #$6c
stage_suffix:
 jmp put

 ; X = field: the drawing cursor at its first cell. X is kept.
field_seek:
 lda field_row,x
 clc
 adc #BOX_TOP
 sta <BAT_ROW
 jsr box_column
 clc
 adc field_col,x
 and #63
 sta <BAT_COL
 phx
 jsr seek
 plx
 rts

 ; A = the BAT column at screen column BOX_LEFT: (BXR >> 3) + BOX_LEFT.
box_column:
 lda PLAYFIELD_X+1
 lsr a
 lda PLAYFIELD_X
 ror a
 lsr a
 lsr a
 clc
 adc #BOX_LEFT
 and #63
 rts

 ; The VRAM write address = BAT_ROW x 64 + BAT_COL. Keeps Y.
seek:
 lda <BAT_ROW
 lsr a
 lsr a
 tax
 lda <BAT_ROW
 lsr a
 ror a
 ror a
 and #$c0
 ora <BAT_COL
 jmp SET_WRITE

 ; A = character: one HUD-font cell (palette 15) at the cursor, which moves
 ; right and wraps from BAT column 63 to 0. Keeps Y.
put:
 sta $0002
 lda #$f7
 sta $0003
 inc <BAT_COL
 lda <BAT_COL
 cmp #64
 bne put_done
 stz <BAT_COL
 jmp seek
put_done:
 rts

open_window:
 jsr WAIT_VBLANK
 ; Sprites off: the control register's low byte without bit 6 (the shadow
 ; keeps the game's value, written back on close).
 lda #5
 sta <$11
 st0 #5
 lda <CR_SHADOW
 and #$bf
 sta $0002
 stz <DIRECTION
 jsr copy_box
 clx
 lda #$7a
 ldy #$a0
 jsr upload_glyph
 lda #$7a
 ldy #$d0
 jsr upload_glyph
 lda #$7b
 ldy #$90
 jsr upload_glyph
 ; The window's text, row by row.
 lda #low(box_text)
 sta <PTR
 lda #high(box_text)
 sta <PTR+1
 lda #BOX_TOP
 sta <BAT_ROW
draw_row:
 jsr box_column
 sta <BAT_COL
 jsr seek
 cly
draw_cell:
 lda [PTR],y
 jsr put
 iny
 cpy #BOX_WIDTH
 bne draw_cell
 tya
 clc
 adc <PTR
 sta <PTR
 bcc draw_next
 inc <PTR+1
draw_next:
 inc <BAT_ROW
 lda <BAT_ROW
 cmp #BOX_TOP+BOX_ROWS
 bne draw_row
 ; The save status (src/bram), in its field: what the reset found in the
 ; backup RAM, or what the last Run's save came to.
 lda #BOX_TOP+STATUS_ROW
 sta <BAT_ROW
 jsr box_column
 clc
 adc #STATUS_COL
 and #63
 sta <BAT_COL
 jsr seek
 lda SAVE_STATUS
 cmp #STATUS_COUNT
 bcc status_known
 cla
status_known:
 ; A x STATUS_WIDTH, in Y.
 tax
 cla
 clc
status_offset:
 dex
 bmi status_draw
 adc #STATUS_WIDTH
 bra status_offset
status_draw:
 tay
 lda #STATUS_WIDTH
 sta <SCRATCH
status_loop:
 lda status_text,y
 jsr put
 iny
 dec <SCRATCH
 bne status_loop
 ; The band under the HUD: version and credit.
 jsr band_address
band_loop:
 lda band_text,y
 jsr character
 iny
 cpy #32
 bne band_loop
 rts

close_window:
 lda #$80
 sta <DIRECTION
 jsr copy_box
 ; The glyph tiles $7AA-$7AD (with the backup's $7AB-$7AC) and $7B9 are
 ; zero in every gameplay state (VRAM audit, 1.10): written back as such.
 stz <$11
 st0 #0
 st1 #$a0
 st2 #$7a
 lda #2
 sta <$11
 st0 #2
 ldx #64
 jsr zero_words
 stz <$11
 st0 #0
 st1 #$90
 st2 #$7b
 lda #2
 sta <$11
 st0 #2
 ldx #16
 jsr zero_words
 ; Row 31 holds 32 blank HUD cells in gameplay.
 jsr band_address
clear_band:
 lda #SPACE
 jsr character
 iny
 cpy #32
 bne clear_band
 ; Sprites as the game had them.
 lda #5
 sta <$11
 st0 #5
 lda <CR_SHADOW
 sta $0002
 rts

band_address:
 lda #$c0
 ldx #7
 jsr SET_WRITE
 cly
 rts
character:
 sta $0002
 lda #$f7
 sta $0003
 rts

 ; Copy the window's BAT cells to the backup (DIRECTION bit 7 clear) or
 ; back. Rows 0 to BOX_ROWS-2 go to the sprite-table buffer being built,
 ; the last row to the HUD font's blank tiles $7AB-$7AC.
copy_box:
 ldx SAT_BUILD
 lda SAT_HIGH,x
 sta <PTR+1
 stz <PTR
 lda #BOX_TOP
 sta <BAT_ROW
copy_row:
 lda <BAT_ROW
 cmp #BOX_TOP+BOX_ROWS-1
 bne copy_row_cells
 lda #$b0
 sta <PTR
 lda #$7a
 sta <PTR+1
copy_row_cells:
 jsr box_column
 sta <BAT_COL
 ; Cells before the BAT row wraps: 64 - column, at most BOX_WIDTH.
 lda #64
 sec
 sbc <BAT_COL
 cmp #BOX_WIDTH
 bcc copy_split
 ldx #BOX_WIDTH
 jsr copy_piece
 bra copy_next
copy_split:
 pha
 tax
 jsr copy_piece
 stz <BAT_COL
 pla
 eor #$ff
 sec
 adc #BOX_WIDTH
 tax
 jsr copy_piece
copy_next:
 inc <BAT_ROW
 lda <BAT_ROW
 cmp #BOX_TOP+BOX_ROWS
 bne copy_row
 rts

 ; X words between the BAT cursor and the backup address PTR (which
 ; advances by X).
copy_piece:
 phx
 lda <BAT_ROW
 lsr a
 lsr a
 tay
 lda <BAT_ROW
 lsr a
 ror a
 ror a
 and #$c0
 ora <BAT_COL
 bit <DIRECTION
 bmi copy_to_bat
 jsr set_read
 lda <PTR
 ldy <PTR+1
 jsr set_write
 bra copy_start
copy_to_bat:
 jsr set_write
 lda <PTR
 ldy <PTR+1
 jsr set_read
copy_start:
 lda #2
 sta <$11
 st0 #2
 pla
 tax
 clc
 adc <PTR
 sta <PTR
 bcc copy_words
 inc <PTR+1
 ; X words from the read address to the write address.
copy_words:
 lda $0002
 ldy $0003
 sta $0002
 sty $0003
 dex
 bne copy_words
 rts
 ; Y:A to the VDC's read (set_read) or write (set_write) address.
set_read:
 pha
 lda #1
 sta <$11
 st0 #1
 bra set_address
set_write:
 pha
 stz <$11
 st0 #0
set_address:
 pla
 sta $0002
 sty $0003
 rts

 ; A:Y = VRAM address of a tile; X = its 16 bytes in menu_glyphs (advances
 ; by 16). Planes 0-1 come from the table; plane 2, the HUD font's colour-4
 ; background, is every pixel the glyph leaves clear; plane 3 is empty.
upload_glyph:
 stz <$11
 st0 #0
 sty $0002
 sta $0003
 lda #2
 sta <$11
 st0 #2
 ldy #8
glyph_planes01:
 lda menu_glyphs,x
 sta $0002
 lda menu_glyphs+1,x
 sta $0003
 inx
 inx
 dey
 bne glyph_planes01
 txa
 sec
 sbc #16
 tax
 ldy #8
glyph_planes23:
 lda menu_glyphs,x
 ora menu_glyphs+1,x
 eor #$ff
 sta $0002
 stz $0003
 inx
 inx
 dey
 bne glyph_planes23
 rts
 ; X zero words at the write address.
zero_words:
 stz $0002
 stz $0003
 dex
 bne zero_words
 rts
 .include "options-text.inc"
 .include "menu-text.inc"
menu_end:
 ; The menu's claim in bank $46 (src/modules.json): $4400-$4AFF (src/bram
 ; owns $4B00-$4FFF).
 .if (menu_end > $4b00)
 .fail
 .endif
 ; The backup: BOX_ROWS-1 rows in one 256-word sprite-table buffer, the last
 ; row in the two tiles $7AB-$7AC (32 words).
 .if ((BOX_ROWS - 1) * BOX_WIDTH > 256)
 .fail
 .endif
 .if (BOX_WIDTH > 32)
 .fail
 .endif
 ; Clear of the HUD (BAT rows 28-31) at vertical scroll 0.
 .if (BOX_TOP + BOX_ROWS > 28)
 .fail
 .endif
 ; The status texts are indexed with one byte.
 .if (STATUS_COUNT * STATUS_WIDTH > 256)
 .fail
 .endif
