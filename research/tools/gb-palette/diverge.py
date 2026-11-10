"""First frame at which two record.py traces differ, per gameplay field,
with the frames around it. usage: diverge.py DIR TAG_A TAG_B RUN [RUN...]"""
import json
import sys
from pathlib import Path

d, a, b = sys.argv[1:4]
for name in sys.argv[4:]:
    A = json.loads((Path(d) / f'{a}-{name}.json').read_text())
    B = json.loads((Path(d) / f'{b}-{name}.json').read_text())
    first = {k: next((i for i, (x, y) in enumerate(zip(A, B)) if x[k] != y[k]), None)
             for k in ('timer', 'ryu', 'cam', 'sat', 'area', 'health')}
    print(name, first)
    f = min((v for v in first.values() if v is not None), default=None)
    if f is not None:
        for i in range(max(0, f - 3), min(len(A), f + 3)):
            print('  ', i, 'A', A[i]['timer'], A[i]['ryu'][:16], A[i]['q'], A[i]['lock'],
                  '| B', B[i]['timer'], B[i]['ryu'][:16], B[i]['q'], B[i]['lock'])
