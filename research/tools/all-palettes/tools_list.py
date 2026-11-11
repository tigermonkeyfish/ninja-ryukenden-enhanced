"""Print the emulator server's tool names (research reference): which calls exist (e.g. PSG state)."""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ.setdefault('GB_WORK', '/workspace/build/all-palettes')
sys.path.insert(0, str(HERE.parent / 'gb-palette'))
from gbtools import Session  # noqa: E402

with Session(sys.argv[1], 0) as g:
    tools = g.emu.tools
    names = [t['name'] for t in (tools.get('tools') if isinstance(tools, dict) else tools)]
    print(' '.join(sorted(names)))
    if len(sys.argv) > 2:
        print(g.call(sys.argv[2]))
