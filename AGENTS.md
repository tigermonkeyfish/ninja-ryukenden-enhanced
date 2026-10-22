# Working on Ninja Ryukenden Enhanced

Read `docs/HANDOFF.md`, `docs/ARCHITECTURE.md`, `docs/pc-engine/LESSONS.md`
and `docs/pc-engine/HARDWARE.md` before changing ROM behavior.

- `release/current.json` and `VERSION` define the current release (1.09) and
  its two patches (headered and headerless original). Consult
  `docs/HANDOFF.md` for release and validation scope.
- Preserve published ROM/patch bytes. New changes use development outputs
  and then a new version: every reviewable build shows its own version
  (`x.yy-dev`) on the splash.
- Never commit game ROMs, states, memory dumps, generated graphics, captures,
  third-party tool checkouts or machine-specific configuration. The only
  exception is the few how-to screenshots named in `scripts/audit_public.py`
  (`GUIDE_IMAGES`, made by `scripts/guide_screenshots.py`); add no others
  without the maintainer's approval. Keep local material in the ignored
  `local/`, `captures/`, `build/` and `dist/` folders.
- Source builds start from the original ROM alone (either format). Generate
  data from the original ROM or editable source; never extract data from a
  release patch.
- Do not borrow native RAM or free ROM without a lifecycle/overlap audit.
  `$FFE6–$FFED` is occupied by English initialization.
- Verify pristine build identity, use checks appropriate to a change, and
  separate emulated evidence from real-hardware reports. Emulator replays
  follow the rules in `docs/pc-engine/EMULATOR.md` (one fresh session per
  replay, from one saved start state).
- Record reusable findings with evidence, confidence and portability limits
  in `docs/pc-engine/`; put Ninja-specific addresses in the architecture map.
  `research/tools/` holds reference probes, not maintained tools.
- Local preparation does not authorize publishing a repository or release.
