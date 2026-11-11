"""Minimal text extraction for a PDF with hex strings and ToUnicode maps
(the Turbo EverDrive Pro manual), for machines without a PDF tool.
usage: python3 -I pdftext.py FILE.pdf"""
import re
import sys
import zlib

d = open(sys.argv[1], 'rb').read()
objs = {}
for m in re.finditer(rb'(\d+) 0 obj(.*?)endobj', d, re.S):
    objs[int(m.group(1))] = m.group(2)


def stream(body):
    m = re.search(rb'stream\r?\n(.*?)\r?\nendstream', body, re.S)
    if not m:
        return None
    s = m.group(1)
    try:
        return zlib.decompress(s)
    except Exception:
        return s


def cmap(body):
    table = {}
    s = stream(body) or b''
    for block in re.findall(rb'beginbfchar(.*?)endbfchar', s, re.S):
        for a, b in re.findall(rb'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>', block):
            table[int(a, 16)] = bytes.fromhex(b.decode()).decode('utf-16-be', 'replace')
    for block in re.findall(rb'beginbfrange(.*?)endbfrange', s, re.S):
        for a, b, c in re.findall(rb'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>', block):
            for k in range(int(a, 16), int(b, 16) + 1):
                table[k] = chr(int(c, 16) + k - int(a, 16))
    return table


fonts = {}
for n, body in objs.items():
    for name, ref in re.findall(rb'/(F\d+) (\d+) 0 R', body):
        font = objs.get(int(ref), b'')
        t = re.search(rb'/ToUnicode (\d+) 0 R', font)
        if t:
            fonts[name] = cmap(objs[int(t.group(1))])

lines = []
for n in sorted(objs):
    s = stream(objs[n])
    if not s or b'BT' not in s or b'Tf' not in s:
        continue
    for block in re.findall(rb'BT(.*?)ET', s, re.S):
        font = re.search(rb'/(F\d+) [\d.]+ Tf', block)
        table = fonts.get(font.group(1), {}) if font else {}
        pos = re.search(rb'([\d.\-]+) ([\d.\-]+) Td', block)
        width = 4 if max(table, default=0) > 255 else 2
        text = ''
        for h in re.findall(rb'<([0-9A-Fa-f]+)>', block):
            for k in range(0, len(h), width):
                text += table.get(int(h[k:k + width], 16), '?')
        lines.append((n, pos.group(2) if pos else b'', text))
out, last = [], None
for n, y, text in lines:
    if (n, y) == last:
        out[-1] += ' ' + text
    else:
        out.append(text)
    last = (n, y)
print('\n'.join(out))
