"""Print the emulator server's tool names (research reference): which calls
exist (e.g. PSG state); with a tool name, call it and print the reply; with
'schema NAME', print that tool's input schema.
usage: tools_list.py ROM [NAME | schema NAME]"""
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ.setdefault('GB_WORK', '/workspace/build/all-palettes')
sys.path.insert(0, str(HERE.parent / 'gb-palette'))
from gbtools import Session  # noqa: E402

with Session(sys.argv[1], 0) as g:
    tools = g.emu.tools
    tools = tools.get('tools') if isinstance(tools, dict) else tools
    if len(sys.argv) > 3 and sys.argv[2] == 'schema':
        print(json.dumps(next(t for t in tools if t['name'] == sys.argv[3]), indent=1))
    else:
        print(' '.join(sorted(t['name'] for t in tools)))
        if len(sys.argv) > 2:
            print(g.call(sys.argv[2]))
