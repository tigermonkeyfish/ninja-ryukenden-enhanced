# Experiment: <game / question / date>

## Identity

- Source ROM size, header and SHA-256:
- Candidate patch/source revision and output SHA-256:
- Tool versions/commits:
- Emulator or physical hardware:
- Version shown on screen by the candidate:
- Fidelity policy (original data only? new art approved by whom?):

## Problem and reproduction

- Visible symptom and expected result:
- Stage/subarea, camera landmark and options:
- Inputs from cold boot, including deaths/warps/Continue:
- How the native effect moves (measured, not assumed):

## Hypothesis

- Proposed cause:
- Predicted observation that would support it:
- Observation that would rule it out:
- Confidence before testing:

## Resource and lifecycle audit

- CPU addresses **and physical bank/ROM offsets**:
- RAM bytes, owners, lifetimes and guard evidence:
- Tile slots, palettes and foreground/sprite overlap:
- Registers, flags, bank mappings and scratch to preserve:
- IRQ timing, maximum transfer chunk and update budget:
- Raster-split register write time against the original:
- Load length in frames (entry, respawn, area change) against the original:

## Experiment and evidence

- Smallest code/data change:
- Test-only modifications, if any (opt-in per tool, named in output):
- Emulator session: start state, fresh session per recording, step checks:
- Input replay / capture procedure:
- Compared outputs and tolerance (VRAM/VCE/SAT state, not only screenshots):
- RAM bytes excluded from equality, with reasons; audio compared or not:
- Evidence file paths and hashes:
- Result: observed / inferred / inconclusive:

## Lifecycle checks

- Entrance, movement, reverse, wrap, maximum exposure:
- Crowded encounter:
- Death (through a native path), respawn plus jump, Continue, compared with the original on the same path:
- Warp from another stage and native stage exit:
- Relevant real-hardware result:

## Conclusion and preservation

- Accepted or rejected hypothesis and reason:
- What is specific to this game:
- What another project may reuse:
- Assumptions it must re-check:
- Remaining unknowns:
- Tool, guide or regression test updated:
