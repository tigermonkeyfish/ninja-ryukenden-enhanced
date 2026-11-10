"""Same updates? Compare the per-frame stage timer, camera, Ryu state and area
of timing_trace.py outputs (TT_DIR/TT_TAG-<run>.json) with record.py traces
(REC_DIR/REC_TAG-<run>.json) or with other timing traces, frame by frame,
and summarise the timing windows (worst upload end, worst HUD-split entry).
usage: updates.py TT_DIR TT_TAG REF_DIR REF_TAG"""
import json
import sys
from pathlib import Path

from gbtools import RUN_NAMES

tt_dir, tt_tag, ref_dir, ref_tag = sys.argv[1:5]
for name in RUN_NAMES:
    if not (Path(tt_dir) / f'{tt_tag}-{name}.json').exists():
        continue
    T = json.loads((Path(tt_dir) / f'{tt_tag}-{name}.json').read_text())
    R = json.loads((Path(ref_dir) / f'{ref_tag}-{name}.json').read_text())
    R = R['frames'] if isinstance(R, dict) else R
    F = T['frames']
    first = {k: next((i for i, (a, b) in enumerate(zip(F, R)) if a[k] != b[k]), None)
             for k in ('timer', 'ryu', 'cam', 'area', 'master', 'sat') if k in F[0] and k in R[0]}
    W = T['vblanks']
    print(name, 'frames', len(F), len(R), 'first difference', first,
          'worst upload end', max(w['end'] for w in W),
          'worst split entry', max(w['cpu'] for w in W if w['cpu']), flush=True)
