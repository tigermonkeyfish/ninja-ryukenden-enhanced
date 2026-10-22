"""6-1 sky column copy: backdrop entries fall through (the sky is mostly
backdrop), and the copy always ends with the write pointer in step, so a
chunk can continue straight into the next row."""
N, SEG_S, SEG_U = 33, 6, 8
out = []
w = out.append
w('; Column copy: N map entries from Y; the BAT read and write pointers start')
w('; at the first entry and <$0a/<$0b holds its BAT address minus Y. Only the')
w('; BAT high byte is read. Foreground (palette >= 2) is left unwritten; the')
w('; write pointer is moved to the next backdrop cell (seek_write) and is back')
w('; in step when the copy returns.')
entries = list(range(N, 0, -1))
for s in range(0, N, SEG_S):
    part = entries[s:s + SEG_S]
    for n in part:
        w(f'columns_{n}:')
        w(' lda $0003')
        w(' cmp #32')
        w(f' bcs foreground_{n}')
        w(f'backdrop_{n}:')
        w(' lda [<$06],y')
        w(' tax')
        w(' lda tile_high-$80,x')
        w(' stx $0002')
        w(' sta $0003')
        w(' iny')
    nxt = entries[s + SEG_S] if s + SEG_S < N else None
    w(f' bra columns_{nxt}' if nxt else ' rts')
    for n in part:
        w(f'foreground_{n}:')
        w(f' jmp skip_{n}')
for s in range(0, N, SEG_U):
    part = entries[s:s + SEG_U]
    for n in part:
        w(f'unsynced_{n}:')
        w(' lda $0003')
        w(' cmp #32')
        w(f' bcc rejoin_{n}')
        w(f'skip_{n}:')
        w(' iny')
    nxt = entries[s + SEG_U] if s + SEG_U < N else None
    w(f' bra unsynced_{nxt}' if nxt else ' jmp seek_write')
    for n in part:
        w(f'rejoin_{n}:')
        w(' jsr seek_write')
        w(f' jmp backdrop_{n}')
w('seek_write:')
for line in (' tya', ' clc', ' adc <$0a', ' stz <$11', ' st0 #0', ' sta $0002', ' lda <$0b', ' adc #0',
             ' sta $0003', ' lda #2', ' sta <$11', ' st0 #2', ' rts', 'columns_end:', ' .if (columns_end > $5d00)',
             '  .fail', ' .endif'):
    w(line)
print('\n'.join(out))
