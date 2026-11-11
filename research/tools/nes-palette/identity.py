"""Evidence a: Original or GB DMG mode against the build before the change.
Replays each stored run on two ROMs from the same seed with $2100/$2101 =
FLAGS and compares every frame: screenshot, SAT, VCE and RAM; all VRAM every
30 frames and at the end. RAM excludes the dead stack (stack-page bytes at
or below the stack pointer; $2100+S+1 upward is live): the new hooks push
other return addresses there (declared, docs/pc-engine/EMULATOR.md). RAM
differences are reported per frame with their addresses, separately from
picture/SAT/VCE/VRAM differences.
usage: identity.py BASE_ROM CANDIDATE_ROM FLAGS OUT [runs,comma]"""
import collections
import hashlib
import json
import sys
from pathlib import Path

from ntools import RUN_NAMES, Session, cv, load_run


def h(b):
    return hashlib.sha1(b).hexdigest()[:16]


def trace(rom, run, flags):
    inputs = [b for c, b in run['segments'] for _ in range(c)] + [[]] * 60
    out = []
    with Session(rom, flags) as g:
        cv.start_stage(g, run['stage'])
        for f, buttons in enumerate(inputs):
            g.press(set(buttons))
            g.checked_step(1)
            s = int(g.call('get_huc6280_status')['S'], 16)
            ram = bytearray(g.read(0, 0x2000))
            ram[0x100:0x100 + s + 1] = bytes(s + 1)
            vram = h(g.read(0, 0x10000, area=4)) if f % 30 == 0 or f == len(inputs) - 1 else None
            out.append({'png': h(g.screenshot()), 'sat': h(g.read(0, 512, area=6)),
                        'vce': h(g.read(0, 1024, area=8)), 'vram': vram, 's': s, 'ram': bytes(ram)})
    return out


def main():
    base, cand, flags, outdir = sys.argv[1], sys.argv[2], int(sys.argv[3], 0), Path(sys.argv[4])
    names = sys.argv[5].split(',') if len(sys.argv) > 5 else RUN_NAMES
    outdir.mkdir(parents=True, exist_ok=True)
    report = {}
    for name in names:
        run = load_run(name)
        a = cv.retried(trace, base, run, flags)
        b = cv.retried(trace, cand, run, flags)
        video = {}
        ram_frames, addrs = [], collections.Counter()
        for f, (x, y) in enumerate(zip(a, b)):
            parts = [k for k in ('png', 'sat', 'vce', 'vram', 's') if x[k] != y[k]]
            if parts:
                video[f] = parts
            d = [i for i in range(0x2000) if x['ram'][i] != y['ram'][i]]
            if d:
                ram_frames.append(f)
                addrs.update(f'{0x2000 + i:04X}' for i in d)
        report[name] = {'frames': len(a), 'picture_sat_vce_vram_s_differing': len(video),
                        'video_first': dict(list(video.items())[:8]),
                        'ram_differing_frames': len(ram_frames), 'ram_frames': ram_frames[:40],
                        'ram_addresses': dict(addrs.most_common(24))}
        print(name, json.dumps(report[name]), flush=True)
    report['ok_video'] = all(r['picture_sat_vce_vram_s_differing'] == 0 for r in report.values() if isinstance(r, dict))
    report['ok_ram'] = all(r['ram_differing_frames'] == 0 for r in report.values() if isinstance(r, dict))
    (outdir / f'identity-{flags:#04x}.json').write_text(json.dumps(report, indent=1))
    print('identity', hex(flags), 'video', 'passed' if report['ok_video'] else 'FAILED',
          'ram', 'passed' if report['ok_ram'] else 'differs (see report)')


if __name__ == '__main__':
    main()
