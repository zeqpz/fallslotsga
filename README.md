# Tipsy Harvest

Stake Engine slot, 7x7 cluster pays with tumbling reels: a Fall / Thanksgiving farm drawn in a Rick and Morty-style
flat cartoon look, with a drunk scarecrow tied to his pole beside the board, reacting to the game.

Started 2026-11-03 as a copy of the newest engine.io build of `zeqpz/slotsgame` (commit `caf600f`, front end + math
v5), without that repo's history or its older versions, then reskinned. **The math is unchanged** (the module is
still `math-sdk/games/smukiez_tag_run`); see `DESIGN.md` for the rules and `HANDOFF-engine-io.md` for uploading.

| symbol | | symbol | |
|---|---|---|---|
| H1 | Roast Turkey | L1 | Maple Leaf |
| H2 | Pumpkin Pie | L2 | Acorn |
| H3 | Cornucopia | L3 | Green Apple |
| H4 | Pilgrim Hat | L4 | Grapes |
| H5 | Moonshine Jug | L5 | Sunflower |
| H6 | Ear of Corn | L6 | Candy Corn |
| H7 | Pumpkin | L7 | Turkey Feather |
| M | Cider Multi (booster) | L8 | Cranberry Sauce |
| BS | Golden Wishbone (bonus scatter) | L9 | Gravy Boat |
| ES | The Crow (extreme scatter) | L10 | Hay Bale |

## Layout

- `frontend/` - the game as uploaded to engine.io. Test locally with `python frontend/mock_rgs.py`
  -> http://localhost:8744/index.html?sessionID=test&rgs_url=http://localhost:8744&lang=en&device=desktop
- `math-sdk/` - the Stake Math SDK with the game module and its publish files
- `engine/` - Slot Engine panel + LGS dev tools
- `art/fall-src/` - the generated art: prompts, raw takes, cleaned icons, the scarecrow's layers and faces, UI
- `art/blender/` - the Blender scenes (`symbols/<ID>.blend`, `chars/scarecrow/scarecrow.blend`)
- `tools/fall/` - the fall pipelines; `tools/blender/pack_*.py` pack Blender renders into `frontend/assets`

## Rebuilding the art and animation

Python: `smukiez-slot/.venv` (numpy, scipy, PIL, cv2). The OpenRouter key is read from
`%USERPROFILE%\.fallslots\openrouter-key.txt` and never printed or committed.

1. Art: `tools/fall/gen_symbols.py`, `gen_faces.py`, `gen_ui.py gen|fit`, `orimg.py` (one image);
   `clean_alpha.py` strips the generator's glow haze; `prep_icons.py` lays the icons out for Blender and writes the
   flat icons; `make_fx_sprites.py` draws the effect sprites; `scarecrow_layers.py` cuts the scarecrow into the
   pole, the body (one texture per face) and the crow.
2. Symbols in Blender: `sh tools/fall/blender/render_all.sh [IDs]` (builds `art/blender/symbols/<ID>.blend`, renders
   idle / land / hit / multi at 30 fps), `python tools/fall/qa_sym.py all` (contact sheets, loop seams, rest-pose
   handovers, frame-edge clipping - read them), then `python tools/blender/pack_frames.py all`.
3. The scarecrow: `blender.exe -b --factory-startup --python tools/fall/blender/scarecrow.py -- build,render`,
   `python tools/fall/qa_char.py`, `python tools/blender/pack_chars.py scarecrow`.

The scripts also run in a live Blender over the MCP for Blender socket (import `symanim` / `scarecrow` and call
`build`), which is how the rigs were set up and checked.
