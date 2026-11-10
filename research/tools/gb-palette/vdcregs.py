"""Print VDC/VCE registers 30 frames into a stage (display timing).
usage: vdcregs.py ROM [STAGE]"""
import json
import sys
from gbtools import Session, cv

rom = sys.argv[1]
stage = int(sys.argv[2]) if len(sys.argv) > 2 else 0
with Session(rom, 0 if 'orig' not in rom else None) as g:
    cv.start_stage(g, stage)
    g.checked_step(30)
    print(json.dumps(g.call('get_huc6270_registers'))[:2000])
    print(json.dumps(g.call('get_huc6260_status'))[:800])
