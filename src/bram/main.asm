; Saved settings: the options byte ($2100) and the language ($3227) are kept
; in the console's backup RAM (BRAM) when there is one, as a System Card
; style file named "NR ENHANCE" (docs/ARCHITECTURE.md, "Saved settings").
;
; A HuCard has no System Card BIOS, so the backup RAM is used directly: it
; is bank $F7 (2 KiB, here in MPR4 at $8000-$87FF), unlocked by writing
; $48, $75, $80 to $1807 (CD hardware and emulators look at bit 7 of the last
; write; the Tennokoe 2 wants the three bytes) and locked again by reading
; $1803. The CPU runs at low speed (csl) while it is mapped, interrupts are
; off throughout, and MPR4, the zero page used and the registers are put
; back.
;
; Format (as the System Card and HuC's bm_ routines use it):
;   $8000 "HUBM"; $8004 end of the memory ($8800; $A000 from some emulators'
;   pre-format: only the first 2 KiB is trusted here); $8006 the first free
;   byte, which holds the directory's 00 00 terminator; $8008-$800F zero.
;   Entries from $8010, back to back: length (2 bytes, this 16-byte header
;   included), checksum (2 bytes: minus the 16-bit sum of every byte after
;   it), a 2-byte id (00 00) and a 10-character name, then the data.
; Our entry is ENTRY_SIZE ($18) long: 8 bytes of data, byte 0 the format
; version (1), byte 1 $2100, byte 2 $3227, bytes 3-7 zero.
;
; Rules (the memory also holds other games' saves, and a Duo's may be half
; lost when its capacitor ran down):
; - Nothing is written unless "HUBM" is there and the whole directory is
;   sound (scan), or the memory is provably blank and writable (format).
; - Nothing is ever deleted, moved or resized. A new entry goes after the
;   last one if it fits; an existing entry of our name is rewritten in place
;   only if it has our length.
; - Load (reset) only reads. Save (the menu's Run) writes only when
;   something has to change, and reads back what it wrote.
; SAVE_STATUS tells the menu what happened (the ST_ values; the menu's
; texts for them are in src/options/menu.txt, in this order).

OPTIONS = $2100
SAVE_STATUS = $2105         ; bottom of the stack page, after $2100-$2104
LANGUAGE = $3227            ; native: 0 Japanese, 1 English, 2 Chinese
DEFAULT_LANGUAGE = 1
NATIVE_INIT = $fcbe
PALETTE_BOOT = $5b00        ; src/palette, bank $46 (= CODE_BANK): jsr $4B00, then WAITR         ; what the reset code called before the patch

CODE_BANK = $46
BRAM_BANK = $f7
BRAM = $8000                ; in MPR4
BRAM_END = $8004
BRAM_NEXT = $8006
BRAM_FIRST = $8010
BRAM_TOP = $8800            ; the 2 KiB every backup RAM has
BRAM_UNLOCK = $1807
BRAM_LOCK = $1803
ENTRY_SIZE = $18
PAYLOAD = 16                ; the data's offset in an entry
FORMAT_VERSION = 1
NAME_FIRST = $4e            ; "N", the first character of our entry's name

ST_NONE = 0                 ; no "HUBM": no backup RAM, or blank and not writable
ST_OK = 1                   ; Run: settings saved (read back, or already there);
                            ; inside the module also scan's "directory sound"
ST_READY = 2                ; reset: formatted, no settings yet, room for them
ST_FULL = 3                 ; no settings entry and no room for one: nothing written
ST_UNFORMATTED = 4          ; Run: no "HUBM" and not blank: nothing written
ST_CORRUPT = 5              ; the directory is not sound: nothing written
ST_SIZE = 6                 ; an entry of our name with another length: nothing written
ST_VERIFY = 7               ; Run: what was written did not read back
ST_DATA = 8                 ; reset: our entry does not check out (sum, version, values):
                            ; defaults kept; the next Run rewrites it
ST_LOADED = 9               ; reset: settings loaded (since v111-reset; before, ST_OK)
ST_COUNT = 10

; Zero page borrowed; pushed and restored by `service`.
ZP_FIRST = $22
ZP_LAST = $2c
LIMIT = $22                 ; and $23: min(end, BRAM_TOP) - 2, the last place for a terminator
LENGTH = $24                ; scan: an entry's length, low byte; load: the options read
PTR = $26                   ; and $27: scan: the entry read; after it: the terminator
NEXT = $28                  ; and $29: the terminator the header's pointer must name
FOUND = $2a                 ; and $2B: our entry; $2B = 0 when there is none
TMP = $2c

 .bank 0
 ; Reset: after the RAM clear ($E025) the native code calls NATIVE_INIT
 ; (jsr $fcbe). Interrupts are off; MPR2 holds nothing the native code has
 ; set yet, and is put back as found.
 .org $e02c
 jsr boot_settings
 .org $ffe6
boot_settings:
 tma #2
 pha
 lda #CODE_BANK
 tam #2
 jsr PALETTE_BOOT           ; src/palette: boot_load ($4B00), then its RAM wait
 pla
 tam #2
 jmp NATIVE_INIT
boot_settings_end:
 .if (boot_settings <> $ffe6)
 .fail
 .endif
 .if (boot_settings_end > $fff6)  ; the vectors start at $FFF6
 .fail
 .endif

 .bank CODE_BANK
 .org $4b00
 ; Entry points (fixed addresses: the reset trampoline and src/options).
 jmp boot_load              ; $4B00
 jmp save_settings          ; $4B03: the menu, once Run has set $2100 and $3227

 ; Reset: the defaults (all of RAM is zero: English is the one non-zero
 ; default), then the saved settings over them when a sound entry holds
 ; them. A, X, Y and the flags the native code could see are as they were
 ; with the old 8-byte English initialization (it left A to NATIVE_INIT).
boot_load:
 lda #DEFAULT_LANGUAGE
 sta LANGUAGE
 cla
 bra service
 ; The menu's Run: A, X and Y are not kept.
save_settings:
 lda #1
 ; A = 0 load, else save. Sets SAVE_STATUS.
service:
 php
 sei
 cld
 phx
 phy
 tay
 ldx #ZP_FIRST
save_zero_page:
 lda <$00,x
 pha
 inx
 cpx #ZP_LAST+1
 bne save_zero_page
 tma #4
 pha
 lda #BRAM_BANK
 tam #4
 csl
 lda #$48
 sta BRAM_UNLOCK
 lda #$75
 sta BRAM_UNLOCK
 lda #$80
 sta BRAM_UNLOCK
 tya
 beq service_load
 jsr save
 bra service_done
service_load:
 jsr load
service_done:
 sta SAVE_STATUS
 lda BRAM_LOCK              ; reading it locks the backup RAM
 csh
 pla
 tam #4
 ldx #ZP_LAST
restore_zero_page:
 pla
 sta <$00,x
 dex
 cpx #ZP_FIRST-1
 bne restore_zero_page
 ply
 plx
 plp
 rts

 ; ---------------------------------------------------------------------
 ; The directory. A = ST_NONE (no "HUBM"), ST_CORRUPT, or ST_OK with
 ; PTR = the terminator, LIMIT set and FOUND = the first entry of our name
 ; (FOUND+1 = 0: none). Reads only, and only the 2 KiB.
scan_none:
 lda #ST_NONE
 rts
scan:
 ldx #3
scan_tag:
 lda BRAM,x
 cmp header,x
 bne scan_none
 dex
 bpl scan_tag
 ; LIMIT = min(end, BRAM_TOP) - 2.
 ldx BRAM_END
 lda BRAM_END+1
 cmp #high(BRAM)
 bcc scan_corrupt
 cmp #high(BRAM_TOP)
 bcc scan_end
 lda #high(BRAM_TOP)
 clx
scan_end:
 sta <LIMIT+1
 txa
 sec
 sbc #2
 sta <LIMIT
 bcs scan_first
 dec <LIMIT+1
scan_first:
 lda #low(BRAM_FIRST)
 sta <PTR
 lda #high(BRAM_FIRST)
 sta <PTR+1
 stz <FOUND+1
 ; Each pass moves on by 16 bytes or more and stops at the 2 KiB's end: at
 ; most 127. An entry that does not fit, or anything after LIMIT, is found
 ; out at the terminator (it must not be past LIMIT), or runs off the end.
 ; This loop is the reset's cost: about 79 CPU cycles an entry at low speed.
scan_entry:
 lda [PTR]
 sta <LENGTH
 ldy #1
 lda [PTR],y
 tax                        ; X = the length's high byte
 bne scan_name
 lda <LENGTH
 beq scan_terminator
 cmp #16
 bcc scan_corrupt           ; shorter than its own header
scan_name:
 ldy #6
 lda [PTR],y
 cmp #NAME_FIRST            ; most entries differ at once
 beq scan_match
scan_advance:
 clc
 lda <PTR
 adc <LENGTH
 sta <PTR
 txa
 adc <PTR+1
 bcs scan_corrupt
 sta <PTR+1
 cmp #high(BRAM_TOP)-1
 bcc scan_entry
 bne scan_corrupt           ; past the 2 KiB
 ; The last page. From $87EF on an entry (16 bytes and a terminator) no
 ; longer fits: only the terminator may be there, and not at $87FF.
 lda <PTR
 cmp #low(BRAM_TOP-17)
 bcc scan_entry
 cmp #$ff
 beq scan_corrupt
 lda [PTR]
 ldy #1
 ora [PTR],y
 beq scan_terminator
scan_corrupt:
 lda #ST_CORRUPT
 rts
 ; The rest of the name, then the id; the first entry of our name counts.
scan_match:
 lda <FOUND+1
 bne scan_advance
 ldy #7
scan_match_byte:
 lda [PTR],y
 cmp entry_name-4,y
 bne scan_advance
 iny
 cpy #16
 bne scan_match_byte
 ldy #4
 lda [PTR],y
 iny
 ora [PTR],y
 bne scan_advance
 lda <PTR
 sta <FOUND
 lda <PTR+1
 sta <FOUND+1
 bra scan_advance
 ; The terminator must leave the directory inside the memory the header
 ; gives, and the header's first-free pointer must name it ...
scan_terminator:
 lda <LIMIT
 cmp <PTR
 lda <LIMIT+1
 sbc <PTR+1
 bcc scan_corrupt
 lda BRAM_NEXT
 cmp <PTR
 bne scan_stale
 lda BRAM_NEXT+1
 cmp <PTR+1
 bne scan_corrupt
scan_ok:
 lda #ST_OK
 rts
 ; ... or our own entry when that is the last one: `save` makes the entry
 ; visible (its length byte) before it moves the pointer, high byte first,
 ; so a save cut off between those writes leaves the pointer's low byte
 ; naming our entry and its high byte the old or the new one. The next
 ; save finishes the job (save_pointer).
scan_stale:
 ldx <FOUND+1
 beq scan_corrupt
 cmp <FOUND
 bne scan_corrupt
 clc
 adc #ENTRY_SIZE
 sta <TMP
 txa
 adc #0
 cmp <PTR+1
 bne scan_corrupt
 lda <TMP
 cmp <PTR
 bne scan_corrupt           ; our entry is not the last one
 lda BRAM_NEXT+1
 cmp <PTR+1
 beq scan_ok
 cmp <FOUND+1
 beq scan_ok
 bra scan_corrupt

 ; Carry set: an entry and the terminator after it fit at PTR. NEXT = the
 ; new terminator's place.
room:
 clc
 lda <PTR
 adc #ENTRY_SIZE
 sta <NEXT
 lda <PTR+1
 adc #0
 sta <NEXT+1
 lda <LIMIT
 cmp <NEXT
 lda <LIMIT+1
 sbc <NEXT+1
 rts

 ; Z set: the entry at FOUND has our length.
entry_sized:
 ldy #1
 lda [FOUND],y
 bne entry_sized_done
 lda [FOUND]
 cmp #ENTRY_SIZE
entry_sized_done:
 rts

 ; The checksum the entry at FOUND should have: A = high byte, TMP = low.
entry_checksum:
 clx
 cla
 ldy #4
checksum_byte:
 clc
 adc [FOUND],y
 bcc checksum_next
 inx
checksum_next:
 iny
 cpy #ENTRY_SIZE
 bne checksum_byte
 eor #$ff
 clc
 adc #1
 sta <TMP
 txa
 eor #$ff
 adc #0
 rts

 ; Z set: the entry at FOUND has the checksum its bytes give.
entry_summed:
 jsr entry_checksum
 ldy #3
 cmp [FOUND],y
 bne entry_summed_done
 dey
 lda <TMP
 cmp [FOUND],y
entry_summed_done:
 rts

 ; ---------------------------------------------------------------------
 ; Reset. A = the status. Writes nothing to the backup RAM.
load:
 jsr scan
 cmp #ST_OK
 bne load_done
 lda <FOUND+1
 bne load_entry
 jsr room
 lda #ST_READY
 bcs load_done
 lda #ST_FULL
load_done:
 rts
load_entry:
 jsr entry_sized
 beq load_sized
 lda #ST_SIZE
 rts
load_sized:
 jsr entry_summed
 bne load_bad
 ldy #PAYLOAD
 lda [FOUND],y
 cmp #FORMAT_VERSION
 bne load_bad
 ; The options: bit 6 clear, a palette mode the menu offers (bits 3-5 not
 ; $20 or $30), bit 7 set exactly with SMS ($38).
 iny
 lda [FOUND],y
 sta <LENGTH
 bit #$40
 bne load_bad
 and #$28
 cmp #$20
 beq load_bad
 lda <LENGTH
 and #$38
 cmp #$38                   ; carry: SMS
 lda #0
 ror a                      ; bit 7 as it must be
 eor <LENGTH
 bmi load_bad
 iny
 lda [FOUND],y
 cmp #3
 bcs load_bad
 sta LANGUAGE
 lda <LENGTH
 sta OPTIONS
 lda #ST_LOADED
 rts
load_bad:
 lda #ST_DATA
 rts

 ; ---------------------------------------------------------------------
 ; The menu's Run. A = the status.
save:
 jsr scan
 cmp #ST_NONE
 bne save_scanned
 jsr format
 bcs save_done
 jsr scan
save_scanned:
 cmp #ST_OK
 bne save_done              ; corrupt (or the new header did not take): not touched
 lda <FOUND+1
 bne save_update
 ; A new entry at the terminator: everything after its length first, then
 ; the terminator after it, then its length (from here on the directory
 ; holds it), last the header's pointer.
 jsr room
 bcs save_create
 lda #ST_FULL
save_done:
 rts
save_create:
 lda <PTR
 sta <FOUND
 lda <PTR+1
 sta <FOUND+1
 ldy #15
save_name:
 lda entry_name-4,y
 sta [FOUND],y
 dey
 cpy #3
 bne save_name
 jsr write_payload
 ldy #ENTRY_SIZE+1
 cla
 sta [FOUND],y
 dey
 sta [FOUND],y
 lda #ENTRY_SIZE
 sta [FOUND]                ; (the high byte is the old terminator's zero)
 bra save_pointer
save_update:
 jsr entry_sized
 beq save_sized
 lda #ST_SIZE
 rts
save_sized:
 lda <PTR
 sta <NEXT
 lda <PTR+1
 sta <NEXT+1
 jsr payload_current
 bne save_rewrite
 ; The entry holds these settings already: done, unless the pointer is
 ; stale (scan_stale).
 lda BRAM_NEXT
 cmp <NEXT
 bne save_pointer
 lda BRAM_NEXT+1
 cmp <NEXT+1
 bne save_pointer
 lda #ST_OK
 rts
save_rewrite:
 jsr write_payload
 ; The header's first-free pointer = NEXT, the terminator: the high byte
 ; first (see scan_stale). A byte that is right already is not written.
save_pointer:
 lda <NEXT+1
 cmp BRAM_NEXT+1
 beq save_pointer_low
 sta BRAM_NEXT+1
save_pointer_low:
 lda <NEXT
 cmp BRAM_NEXT
 beq save_verify
 sta BRAM_NEXT
 ; Read it all back: the directory, the pointer, our entry.
save_verify:
 jsr scan
 cmp #ST_OK
 bne save_failed
 lda <FOUND+1
 beq save_failed
 lda BRAM_NEXT
 cmp <PTR
 bne save_failed
 lda BRAM_NEXT+1
 cmp <PTR+1
 bne save_failed
 jsr entry_sized
 bne save_failed
 jsr payload_current
 bne save_failed
 lda #ST_OK
 rts
save_failed:
 lda #ST_VERIFY
 rts

 ; The data of the entry at FOUND, then its checksum.
write_payload:
 ldy #PAYLOAD
 lda #FORMAT_VERSION
 sta [FOUND],y
 iny
 lda OPTIONS
 sta [FOUND],y
 iny
 lda LANGUAGE
 sta [FOUND],y
 cla
write_zero:
 iny
 sta [FOUND],y
 cpy #ENTRY_SIZE-1
 bne write_zero
 jsr entry_checksum
 ldy #3
 sta [FOUND],y
 dey
 lda <TMP
 sta [FOUND],y
 rts

 ; Z set: the entry at FOUND holds exactly what write_payload would write.
payload_current:
 ldy #PAYLOAD
 lda [FOUND],y
 cmp #FORMAT_VERSION
 bne payload_done
 iny
 lda [FOUND],y
 cmp OPTIONS
 bne payload_done
 iny
 lda [FOUND],y
 cmp LANGUAGE
 bne payload_done
payload_zero:
 iny
 lda [FOUND],y
 bne payload_done
 cpy #ENTRY_SIZE-1
 bne payload_zero
 jmp entry_summed
payload_done:
 rts

 ; ---------------------------------------------------------------------
 ; No "HUBM". Carry clear: the memory was blank and is formatted now.
 ; Carry set: A = ST_NONE (nothing there to write to) or ST_UNFORMATTED
 ; (something is there: not touched).
 ; Bytes $8001-$8012 all alike but neither $00 nor $FF is no memory at all
 ; (a console without backup RAM: what an unmapped bank reads is not
 ; documented, but one instruction reads the same every time): ST_NONE,
 ; nothing written.
 ; The memory is formatted only when it is blank and real:
 ; - every byte from $8012 up reads $00, or every one $FF;
 ; - bytes $8001-$8011 are blank too, or already what a format puts there
 ;   (a format cut short, ours or another's, is finished here: the bytes
 ;   after them prove that nothing was ever stored);
 ; - the first byte takes two patterns and its old value back. It is tried
 ;   before the 2 KiB are read (a console without backup RAM leaves here
 ;   after a few instructions), but only after the header bytes passed.
format:
 lda BRAM+18
 sta <TMP                   ; the blank value
 ldx #17
format_alike:
 cmp BRAM,x
 bne format_mixed
 dex
 bne format_alike
 cmp #0
 beq format_real
 cmp #$ff
 beq format_real
format_absent:
 lda #ST_NONE
 sec
 rts
format_refused:
 lda #ST_UNFORMATTED
 sec
 rts
format_mixed:
 lda <TMP
 beq format_header
 cmp #$ff
 bne format_refused
format_header:
 ldx #17
format_header_byte:
 lda BRAM,x
 cmp <TMP
 beq format_header_next
 cmp header,x
 bne format_refused
format_header_next:
 dex
 bne format_header_byte
format_real:
 lda BRAM
 sta <LENGTH
 lda #$55
 sta BRAM
 cmp BRAM
 bne format_restore
 asl a
 sta BRAM
 cmp BRAM
 bne format_restore
 lda <LENGTH
 sta BRAM
 cmp BRAM
 bne format_absent
 ; Blank from $8012 to $87FF: offsets 18-255 of all eight pages, then
 ; offsets 0-17 of the last seven.
 lda <TMP
 ldx #18
format_blank:
 cmp BRAM,x
 bne format_stored
 cmp BRAM+$100,x
 bne format_stored
 cmp BRAM+$200,x
 bne format_stored
 cmp BRAM+$300,x
 bne format_stored
 cmp BRAM+$400,x
 bne format_stored
 cmp BRAM+$500,x
 bne format_stored
 cmp BRAM+$600,x
 bne format_stored
 cmp BRAM+$700,x
 bne format_stored
 inx
 bne format_blank
 ldx #17
format_blank_low:
 cmp BRAM+$100,x
 bne format_stored
 cmp BRAM+$200,x
 bne format_stored
 cmp BRAM+$300,x
 bne format_stored
 cmp BRAM+$400,x
 bne format_stored
 cmp BRAM+$500,x
 bne format_stored
 cmp BRAM+$600,x
 bne format_stored
 cmp BRAM+$700,x
 bne format_stored
 dex
 bpl format_blank_low
 ; The header after the tag and the first terminator, then the tag: until
 ; its last byte is there, nothing takes the memory for formatted.
 ldx #17
format_write:
 lda header,x
 sta BRAM,x
 dex
 bpl format_write
 clc
 rts
format_restore:
 lda <LENGTH
 sta BRAM                   ; as it was, if anything took
 lda #ST_NONE
 sec
 rts
format_stored:
 lda #ST_UNFORMATTED
 sec
 rts

 ; A formatted, empty backup RAM's first 18 bytes: the tag, the end, the
 ; first free byte, 8 zero bytes, the terminator.
header:
 .db $48,$55,$42,$4d        ; "HUBM"
 .db low(BRAM_TOP),high(BRAM_TOP),low(BRAM_FIRST),high(BRAM_FIRST)
 .db 0,0,0,0,0,0,0,0
 .db 0,0
 ; Bytes 4-15 of our entry: the id, then "NR ENHANCE".
entry_name:
 .db 0,0
 .db $4e,$52,$20,$45,$4e,$48,$41,$4e,$43,$45
bram_end:
 ; The module's claim in bank $46 (src/modules.json): $4B00-$4FFF.
 .if (bram_end > $5000)
 .fail
 .endif
 .if (ST_COUNT <> 10)       ; the menu's status texts (src/options/menu.txt)
 .fail
 .endif
