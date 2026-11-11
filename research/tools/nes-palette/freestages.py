"""Free-ROM audit over Level Select entries (adds the boss rooms and the
stages without a stored run to the run/boot audits of freewatch.py): a
read/execute watch over ROM file offsets LO-HI while each entry plays FRAMES
frames holding right (health refilled; the area exit moved onto Ryu every
PER frames as areawarp.py does, so later areas load too). Run it on the
build before the change: the range must never be touched.
usage: freestages.py ROM FRAMES PER LO HI [LO HI ...]"""
import json
import sys

from ntools import Session, cv

rom, frames, per = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
spans = list(zip(sys.argv[4::2], sys.argv[5::2]))
stops, total = [], 0
for stage in range(22):
    with Session(rom, 0x02) as g:
        cv.start_stage(g, stage)
        for lo, hi in spans:
            g.call('set_breakpoint_range', {'start_address': lo, 'end_address': hi, 'memory_area': 'rom',
                                            'read': True, 'execute': True})
        g.press({'right'})
        n = 0
        while n < frames:
            g.write(0xead, bytes([16]))
            if n and n % per == 0:
                r = g.read(0xe9f, 1)[0]
                box = g.read(0xeb5, 6)
                g.write(0xe87, bytes([r]))
                g.write(0xe81, bytes([(box[0] + box[3]) // 2, (box[2] + box[5]) // 2]))
            if g.step(1) is None:
                st = g.call('get_huc6280_status')
                stops.append({'stage': stage, 'frame': n, 'pc': st['PC'], 'mpr': [m['value'] for m in st['MPR']]})
                if len(stops) > 50:
                    break
                continue
            n += 1
        total += n
    print(stage, 'frames', n, 'stops', len(stops), flush=True)
print(json.dumps({'frames': total, 'stops': stops}))
