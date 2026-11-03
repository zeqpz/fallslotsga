# Fall Slots (working title)

Stake Engine slot, 7x7 cluster pays, being reskinned to a Fall / Thanksgiving farm theme.

Started 2026-11-03 as a copy of the newest engine.io build of `zeqpz/slotsgame` (commit `caf600f`, the
"Smukiez & Skelly" build: front end + math v5), without that repo's history or its older versions.
The math is unchanged; see `DESIGN.md` for the rules and `HANDOFF-engine-io.md` for uploading.

- `frontend/` - the game as uploaded to engine.io (`frontend/mock_rgs.py` is the local test server)
- `math-sdk/` - the Stake Math SDK with the game's module `games/smukiez_tag_run` and its publish files
- `engine/` - Slot Engine panel + LGS dev tools
- `tools/` - asset pipelines (Blender symbol and character animation in `tools/blender`)
