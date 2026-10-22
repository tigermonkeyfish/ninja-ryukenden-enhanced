"""Assemble all modules into a kept work directory (listings included).
usage: mkwork.py OUTDIR"""
import sys, shutil
from pathlib import Path
import local
sys.path.insert(0, str(local.SCRIPTS))
import project
out = Path(sys.argv[1])
shutil.rmtree(out, ignore_errors=True); out.mkdir(parents=True)
src = local.ORIGINAL.read_bytes()
base = project.original_image(src, project.load_manifest())
rom = project.build_runtime(base, local.PCEAS, out, src[512:])
(out / 'rom.pce').write_bytes(rom)
print(project.digest(rom))
