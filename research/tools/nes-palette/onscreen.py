"""Evidence b (on screen): in NES mode every VCE entry that shows on screen
holds one of the 47 NES colours. Every STEP frames (and at the first) the
session is saved, the VCE is set to the identity (entry i = colour i), the
palette lock $2283 is set so nothing is uploaded, one frame is drawn and its
screenshot read as entry numbers (the 224 visible lines), then the state is
restored: the replay itself is untouched. The entries seen are checked in
the VCE as it was. Cinemas and the title ($2240 != 0) are counted apart.
usage: onscreen.py ROM FLAGS STEP OUT.json SPEC...
SPEC: run:NAME[:EXTRA]  (stored run plus EXTRA frames, default 60)
      ls:STAGE:FRAMES[:buttons]  (Level Select entry; health refilled)"""
import collections
import io
import json
import sys
from pathlib import Path

from PIL import Image

from ntools import Session, cv, load_run

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts'))
import nes_palette as NP  # noqa: E402

rom, flags, step, out = sys.argv[1], int(sys.argv[2], 0), int(sys.argv[3]), sys.argv[4]
IDENT = b''.join(bytes([i & 0xff, i >> 8]) for i in range(512)).hex(' ')
results = {}


def sample(g, frame, rec):
    vce = g.read(0, 1024, 8)
    words = [vce[2 * i] | (vce[2 * i + 1] & 1) << 8 for i in range(512)]
    master = g.read(0x240, 1)[0]
    st = Path(g.logdir) / 'onscreen.state'
    g.call('save_state_file', {'file_path': str(st)})
    g.call('write_memory', {'area': 8, 'offset': '0000', 'bytes': IDENT})
    g.write(0x283, b'\x01')
    g.checked_step(1)
    im = Image.open(io.BytesIO(g.screenshot())).convert('RGB').crop((0, 18, 256, 242))
    g.call('load_state_file', {'file_path': str(st)})
    to9 = lambda p: (round(p[1] * 7 / 255) << 6) | (round(p[0] * 7 / 255) << 3) | round(p[2] * 7 / 255)
    seen = collections.Counter(to9(p) for p in im.getdata())
    rec['samples'] += 1
    for i, n in seen.items():
        rec['entries'].add(i)
        if words[i] not in NP.NES_COLOURS:
            key = 'cinema' if master else 'gameplay'
            rec[key].append({'frame': frame, 'entry': i, 'colour': f'{words[i]:03X}', 'pixels': n})


for spec in sys.argv[5:]:
    kind, what, *rest = spec.split(':')
    rec = {'samples': 0, 'entries': set(), 'gameplay': [], 'cinema': []}
    with Session(rom, flags) as g:
        if kind == 'run':
            run = load_run(what)
            inputs = [b for c, b in run['segments'] for _ in range(c)]
            inputs += [[]] * (int(rest[0]) if rest else 60)
            cv.start_stage(g, run['stage'])
            hold = None
        else:
            cv.start_stage(g, int(what))
            inputs = [None] * int(rest[0])
            hold = set(rest[1].split('+')) if len(rest) > 1 and rest[1] else set()
        for n, b in enumerate(inputs):
            if n % step == 0:
                sample(g, n, rec)
            if b is None:
                g.press(hold)
                g.write(0xead, bytes([16]))
            else:
                g.press(set(b))
            g.checked_step(1)
    rec['entries'] = sorted(rec['entries'])
    results[spec] = rec
    print(json.dumps({'spec': spec, 'samples': rec['samples'], 'entries': len(rec['entries']),
                      'gameplay_bad': len(rec['gameplay']), 'cinema_bad': len(rec['cinema']),
                      'bad_entries': sorted({(e['entry'], e['colour']) for e in rec['gameplay']})[:20]}), flush=True)
Path(out).write_text(json.dumps(results, indent=1))
