#!/bin/sh
# The survey's capture set on one build, all six modes (research reference).
# usage: capall.sh WORK ROM OUT [JOBS]   (WORK: original.pce, seed.state)
# Run from the repository root inside the emulator environment (run-check.sh).
W=$1; ROM=$2; OUT=$3; JOBS=${4:-2}
export GB_WORK=$W NG_DEBUGGER_FAST=1
for m in ${MODES:-original nes-a nes-b gb-dmg hell sms}; do
  echo "$m run 4-1 250,700,1150,1450,1750"
  echo "$m warp 12"
  echo "$m warp 17"
  echo "$m boss 19 60,200,400,700"
  echo "$m boss 20 60,200,400,700"
  echo "$m boss 21 60,200,400,700"
done | xargs -P $JOBS -L 1 python3 research/tools/dark-lift/cap.py $ROM $OUT
echo finished
