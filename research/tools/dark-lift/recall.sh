#!/bin/sh
# Record the 11 stored runs on a build in every palette mode with
# hell-1-1/record11.py (research reference, not a maintained tool).
# usage: recall.sh WORK ROM TAG   (WORK holds original.pce and seed.state;
# recordings go to WORK/rec/TAG-<mode>-<run>.json)
# MODES="orig:0 ..." and JOBS (sessions at once, default 2) can be set.
# Run from the repository root inside the emulator environment (run-check.sh).
W=$1; ROM=$2; TAG=$3
export GB_WORK=$W NES_WORK=$W NG_DEBUGGER_FAST=1
for pair in ${MODES:-orig:0 gb:0x10 sms:0xb8 hell:0x18 nesa:0x08 nesb:0x28}; do
  tag=$TAG-${pair%%:*}; fl=${pair#*:}
  echo "== $tag $fl"
  python3 research/tools/sms-palette/runmany.py $W/rec/log $tag ${JOBS:-2} all $PWD/research/tools/hell-1-1/record11.py $ROM {run} $W/rec/$tag-{run}.json $fl
done
echo finished
