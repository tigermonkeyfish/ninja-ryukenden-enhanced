"""Machine-specific paths for the research tools, from the environment.

GEARGRAFX           headless Geargrafx build (see docs/CUTSCENE-AUDIT.md and
                    geargrafx-headless-fast.patch here)
PCEAS               HuC's pceas assembler
NINJA_ORIGINAL_ROM  the original headered ROM (524,800 bytes)
NINJA_ENHANCED_ROM  an Enhanced build to compare against
"""
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SCRIPTS = REPO / 'scripts'
EMULATOR = Path(os.environ.get('GEARGRAFX', 'geargrafx'))
PCEAS = os.environ.get('PCEAS', 'pceas')
ORIGINAL = Path(os.environ.get('NINJA_ORIGINAL_ROM', 'original.pce'))
ENHANCED = Path(os.environ.get('NINJA_ENHANCED_ROM', str(REPO / 'dist' / 'enhanced.pce')))
CAPTURES = REPO / 'captures' / 'bg-fidelity'
# Where probes write their results (ignored by Git, like all captures).
WORK = Path(os.environ.get('NINJA_TOOLS_WORK', str(REPO / 'captures' / 'tools')))
WORK.mkdir(parents=True, exist_ok=True)
