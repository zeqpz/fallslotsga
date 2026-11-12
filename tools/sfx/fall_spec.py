"""The fall / Thanksgiving sound pass (2026-11-03): what Seed Audio is asked for and where each sound goes.

name -> (prompt, takes, kind, (min s, max s, keep, mode override), out)
  kind  drives the trim/clean rules (process2.K, clean3.HP); "sting" is added here: a short musical or
        animal flourish kept whole (activity merged over 0.6 s gaps)
  out   ("set", stem, target momentary-max LUFS, SFX_SETS key, level, what) -> sfx_<stem>_1..keep.wav
        ("files", [file names], target, what)                            -> those single files, in place
fall.py runs it: generate -> candidates -> pick -> clean (clean3) -> frontend/assets/*.wav (+ .ogg via
encode_new.js)."""

PRE = "[Sound effect only. No voice, no speech, no music.] "
PRE_ANIMAL = "[Sound effect only. No human voice, no speech, no words, no music.] "
PRE_STING = "[Sound effect only. No voice, no speech, no singing.] "
CLOSE = " Close-up, dry, clean studio foley recording, crisp and punchy, no background noise, no room hiss."

S = {
    # ---------------- in place of the street sounds (same files, same roles) ----------------
    "f_shake": (PRE + "Shaking a bundle of dry corn husks and straw quickly twice in one hand: a crisp, crackly, "
                "papery rustling shake, shk-shk.", 6, "foley", (.3, .8, 2, "gesture"),
                ("set", "can_shake", -23, "canShake", .34, "spin pressed: a corn-husk / straw shake")),
    "f_sweep_short": (PRE + "One quick stroke of a stiff straw broom sweeping across a dry wooden barn floor: a crisp, "
                      "airy, scratchy swish lasting half a second.", 6, "whoosh", (.35, .55, 3, "sustain"),
                      ("set", "spray_short", -22, "sprayLineShort", .36, "straw broom swish, short line")),
    "f_sweep_long": (PRE + "One long smooth stroke of a stiff straw broom sweeping steadily across a dry wooden barn "
                     "floor: a crisp, airy, scratchy swish that keeps going evenly for about one and a half seconds "
                     "and stops cleanly.", 10, "whoosh", (.9, 1.5, 2, "sustain"),
                     ("set", "spray_long", -22, "sprayLineLong", .32, "straw broom swish, long line")),
    "f_gravy_drop": (PRE + "A single fat drop of thick warm gravy falling into a full gravy boat: one tiny, soft, wet, "
                     "round plop.", 8, "drop", (.06, .3, 5, None),
                     ("set", "paint_drip", -24, "paintDrip", .3, "one gravy drop plop")),
    "f_squash": (PRE + "A small ripe pumpkin squashing open: a juicy, pulpy, wet squelch pop with a short splat.",
                 6, "hit", (.12, .7, 3, None),
                 ("set", "paint_burst", -22, "paintBurst", .4, "pumpkin squelch pop, icon burst")),
    "f_cork": (PRE + "Pulling a cork out of a cider bottle: one crisp, satisfying, hollow cork pop.", 6, "click",
               (.03, .2, 2, None), ("set", "cap_pop", -24, "capPop", .38, "cider cork pop (bonus open)")),
    "f_tumble": (PRE + "A handful of acorns and small apples tumbling and rolling down onto a wooden table in a "
                 "quick short clatter of woody knocks and soft thuds.", 6, "hit", (.3, 1.0, 2, "gesture"),
                 ("set", "cascade", -23, "cascade", .3, "acorns and apples tumbling")),
    "f_plop": (PRE + "One soft, round, muffled, cartoony plop, like a spoonful of mashed potato dropped onto a plate: "
               "a gentle, short bloop.", 8, "drop", (.08, .6, 6, None),
               ("files", ["sfx_drip_a.wav", "sfx_drip_b.wav", "sfx_drip_c.wav", "sfx_drip_d.wav", "sfx_drip_e.wav",
                          "sfx_drip_f.wav"], -24.5, "soft plops (dripLand = drip_b on every icon landing)")),
    "f_scatter": (PRE_ANIMAL + "A magical golden chime ringing out bright and sparkling, followed right away by a "
                  "short comical turkey gobble-gobble.", 6, "sting", (1.2, 3.0, 1, None),
                  ("files", ["sfx_scatter_land.wav"], -21.5, "golden chime + turkey gobble (bonus symbol lands)")),
    "f_bonus": (PRE_STING + "A quick, bright, cheerful cartoon fiddle flourish running up to a high note, followed "
                "immediately by a short rooster crow, cock-a-doodle-doo.", 6, "sting", (1.0, 1.7, 1, None),
                ("files", ["sfx_bonus_start.wav"], -23, "fiddle flourish up to a high note (free spins start); the "
                 "takes' rooster comes later in them, so the 1.7 s cap keeps only the fiddle")),
    "f_rooster": (PRE_ANIMAL + "A rooster crowing once: one loud, proud cock-a-doodle-doo, close.", 5, "sting",
                  (.9, 2.2, 2, None), ("set", "rooster", -23, "rooster", .3, "rooster crow (optional, see README)")),
    "f_bust": (PRE_STING + "A comical sad 'wah-wah-wah-waaah' made by blowing into an empty clay jug: four "
               "descending hollow hooting tones, the last one sliding down and fading, like a sad trombone.",
               6, "sting", (2.5, 4.8, 2, None),
               ("files", ["sfx_bust_a.wav", "sfx_bust_b.wav"], -16.5, "sad jug wah-wah (Multis landed, nothing used them)")),

    # ---------------- board foley: what each symbol is made of, as it lands ----------------
    "land_platter": (PRE + "A heavy porcelain serving platter with a roast turkey on it set down on a wooden table: a "
                     "solid low ceramic clunk with a soft meaty thud.", 5, "hit", (.08, .45, 3, None),
                     ("set", "land_platter", -24, "landPlatter", .28, "H1 turkey platter: ceramic clunk + thud")),
    "land_pie": (PRE + "A pie in a thin metal pie tin set down on a wooden table: a soft muffled thud with a light "
                 "tinny tick.", 5, "hit", (.06, .4, 3, None),
                 ("set", "land_pie", -24, "landPie", .26, "H2 pumpkin pie: soft thud + tin tick")),
    "land_wicker": (PRE + "A wicker basket dropped onto a wooden table: a short dry crunchy wicker creak and thump.",
                    5, "hit", (.08, .45, 3, None),
                    ("set", "land_wicker", -24, "landWicker", .28, "H3 cornucopia: wicker creak + thump")),
    "land_hat": (PRE + "A stiff felt hat dropped onto a wooden table: a soft muffled flop with a tiny metal buckle "
                 "tick.", 5, "hit", (.06, .35, 2, None),
                 ("set", "land_hat", -24, "landHat", .28, "H4 pilgrim hat: felt flop + buckle tick")),
    "land_jug": (PRE + "A heavy clay jug set down on a wooden table: a hollow ceramic clunk with a little liquid "
                 "slosh inside.", 5, "hit", (.1, .5, 3, None),
                 ("set", "land_jug", -24, "landJug", .28, "H5 moonshine jug: hollow clay clunk + slosh")),
    "land_corn": (PRE + "An ear of corn in its dry husk dropped onto a wooden table: a short dull knock with a crisp "
                  "papery husk crackle.", 5, "hit", (.08, .4, 3, None),
                  ("set", "land_corn", -24, "landCorn", .26, "H6 ear of corn: knock + husk crackle")),
    "land_pumpkin": (PRE + "A small pumpkin set down on a wooden table: one soft, hollow, round, deep thud.", 5, "hit",
                     (.06, .4, 3, None), ("set", "land_pumpkin", -24, "landPumpkin", .3, "H7 pumpkin: hollow soft thud")),
    "land_leaf": (PRE + "A dry autumn maple leaf landing on a small pile of dry leaves: a short light crisp crinkle.",
                  5, "hit", (.06, .35, 3, None), ("set", "land_leaf", -25, "landLeaf", .24, "L1 maple leaf: crisp crinkle")),
    "land_acorn": (PRE + "An acorn dropped onto a wooden table: one short light woody tick with a tiny bounce.", 5,
                   "hit", (.04, .3, 3, None), ("set", "land_acorn", -25, "landAcorn", .24, "L2 acorn: woody tick")),
    "land_apple": (PRE + "A firm apple dropped onto a wooden table: one short solid soft thud.", 5, "hit",
                   (.05, .3, 3, None), ("set", "land_apple", -24, "landApple", .26, "L3 green apple: solid soft thud")),
    "land_grapes": (PRE + "A bunch of grapes dropped onto a wooden table: a soft, squishy, bumpy thud.", 5, "hit",
                    (.06, .35, 2, None), ("set", "land_grapes", -24, "landGrapes", .26, "L4 grapes: squishy bumpy thud")),
    "land_sunflower": (PRE + "A big dried sunflower head dropped onto a wooden table: a soft papery thump with a "
                       "quick little rattle of seeds.", 5, "hit", (.08, .45, 2, None),
                       ("set", "land_sunflower", -25, "landSunflower", .24, "L5 sunflower: papery thump + seed rattle")),
    "land_candy": (PRE + "A few small hard candy pieces dropped onto a wooden table: a short light clicky clatter.",
                   5, "hit", (.1, .5, 3, "gesture"),
                   ("set", "land_candy", -25, "landCandy", .24, "L6 candy corn: light clicky clatter")),
    "land_feather": (PRE + "A large feather landing on a table: one very soft, quick, airy feathery swish.", 5, "foley",
                     (.08, .4, 2, None), ("set", "land_feather", -26, "landFeather", .22, "L7 turkey feather: airy swish")),
    "land_jelly": (PRE + "A wobbly jellied cranberry sauce dropped onto a plate: a short wet jiggly squelch and wobble.",
                   5, "hit", (.1, .5, 3, None),
                   ("set", "land_jelly", -24, "landJelly", .26, "L8 cranberry sauce: wet jelly wobble")),
    "land_porcelain": (PRE + "A small porcelain gravy boat set down on a porcelain saucer: one short bright delicate "
                       "ceramic clink.", 5, "hit", (.08, .5, 3, None),
                       ("set", "land_porcelain", -25, "landPorcelain", .24, "L9 gravy boat: porcelain clink")),
    "land_hay": (PRE + "A small bale of hay dropped onto a wooden floor: a soft heavy crunchy thump of packed dry "
                 "straw.", 5, "hit", (.1, .5, 3, None),
                 ("set", "land_hay", -24, "landHay", .28, "L10 hay bale: crunchy straw thump")),
    "land_bottle": (PRE + "A thick glass cider bottle set down hard on a wooden table: one solid glassy clunk with a "
                    "short ring.", 5, "hit", (.08, .5, 3, None),
                    ("set", "land_bottle", -21, "landBottle", .34, "M cider bottle: glassy clunk (the Multi)")),

    # ---------------- the scarecrow's foley ----------------
    "hiccup": (PRE_ANIMAL + "One single cartoon hiccup: a short, comical, squeaky 'hic' gulp from a cartoon "
               "character's throat. Just one hiccup, no words.", 6, "foley", (.08, .45, 3, None),
               ("set", "hiccup", -25, "hiccup", .12, "cartoon hiccup")),
    "straw_rustle": (PRE + "Dry straw stuffing rustling inside an old burlap shirt as a scarecrow shifts on his pole: a "
                     "short crisp crackly rustle.", 5, "foley", (.3, .8, 3, None),
                     ("set", "straw_rustle", -26, "strawRustle", .08, "straw stuffing rustle")),
    "crow_caw": (PRE_ANIMAL + "One single crow caw: a harsh, loud, raspy caw from a black crow, close.", 6, "foley",
                 (.25, .8, 3, None), ("set", "crow_caw", -24, "crowCaw", .12, "one crow caw (2 of the 3 asked for came out clean)")),
    "jug_slosh": (PRE + "Liquid sloshing and glugging inside a heavy clay jug as it swings: a short hollow glug-glug "
                  "slosh.", 5, "foley", (.3, 1.0, 2, None),
                  ("set", "jug_slosh", -26, "jugSlosh", .1, "moonshine jug glug / slosh")),
    "rope_creak": (PRE + "An old rope creaking as it tightens against a wooden post: a short dry woody creak.", 5,
                   "foley", (.3, 1.0, 2, None), ("set", "rope_creak", -26, "ropeCreak", .08, "rope creak on the pole")),
    "wing_flap": (PRE + "A crow flapping its wings hard to take off: a quick burst of four feathery wing flaps.", 5,
                  "foley", (.4, 1.2, 2, None), ("set", "wing_flap", -25, "wingFlap", .1, "crow wing flaps, taking off")),
    "crow_peck": (PRE + "A bird's beak pecking once on a stiff felt hat: one short soft woody tock.", 6, "hit",
                  (.03, .25, 3, None), ("set", "crow_peck", -25, "crowPeck", .1, "crow beak peck on the hat")),

    # ---------------- the cider bottle (bigBottle): the Multi going off, 2026-11-03 ----------------
    "b_swing_in": (PRE + "A heavy glass bottle swung quickly through the air right past the microphone: one short, "
                   "deep, airy whoosh.", 5, "whoosh", (.3, .75, 2, None),
                   ("set", "bottle_whoosh", -24, "bottleWhoosh", .32, "the big bottle swinging in")),
    "b_glove": (PRE + "A leather work glove gripping a glass bottle tightly: one short squeaky rub of leather on "
                "glass.", 5, "foley", (.12, .5, 2, None),
                ("set", "glove_grip", -26, "gloveGrip", .22, "the gloves taking hold of the bottle")),
    "b_slosh": (PRE + "Shaking a full glass bottle of fizzy cider hard back and forth: liquid sloshing and splashing "
                "around inside the glass, fizzing more and more.", 5, "foley", (.5, 1.3, 2, "gesture"),
                ("set", "bottle_slosh", -24, "bottleSlosh", .32, "the bottle shaken: cider sloshing in the glass")),
    "b_fizz": (PRE + "Pressure building up inside a shaken champagne bottle: a rising hiss of fizz and bubbles with "
               "the cork creaking and straining, getting louder.", 5, "spray", (.6, 1.3, 2, "sustain"),
               ("set", "bottle_fizz", -24, "bottleFizz", .3, "the fizz-up: rising hiss, the cork straining")),
    "b_pop": (PRE + "A big champagne cork shooting out of a bottle: one loud, explosive, satisfying POP.", 6, "hit",
              (.05, .4, 3, None), ("set", "bottle_pop", -18, "bottlePop", .55, "the big cork POP")),
    "b_gush": (PRE + "Champagne gushing and spraying out of a bottle right after the cork pops: a wet, foamy, "
               "fizzing gush of liquid splashing out for about one second.", 5, "spray", (.6, 1.3, 2, "sustain"),
               ("set", "bottle_gush", -22, "bottleGush", .36, "the cider gushing out of the neck")),
    "b_swing_out": (PRE + "A heavy glass bottle swung quickly away from the microphone: one short airy whoosh "
                    "fading out.", 5, "whoosh", (.3, .75, 2, None),
                    ("set", "bottle_whoosh_out", -25, "bottleWhooshOut", .28, "the big bottle swinging away")),
    "c_whirr": (PRE + "A cork spinning fast end over end through the air: a short whirring, fluttering whoosh that "
                "rises and falls.", 5, "whoosh", (.4, 1.0, 2, None),
                ("set", "cork_whirr", -25, "corkWhirr", .26, "the cork tumbling through the air")),
    "c_bonk": (PRE + "A cork hitting a piece of fruit hard: one hollow, comical, woody bonk with a tiny cartoon "
               "boing.", 6, "hit", (.1, .55, 3, None), ("set", "cork_bonk", -20, "corkBonk", .45, "the cork bonking the icon")),
    "c_splash": (PRE + "A big wet splash of fizzy cider landing on a wooden table: one juicy splat with droplets "
                 "spattering around it.", 5, "hit", (.2, .75, 3, None),
                 ("set", "cider_splash", -22, "ciderSplash", .4, "the splash on the hit icon")),
    "c_fizzpop": (PRE + "Lots of tiny bubbles fizzing and popping in a glass of cider: a short, crackly, sparkling "
                  "fizz.", 5, "foley", (.4, 1.0, 2, None),
                  ("set", "cider_fizz", -26, "ciderFizz", .22, "bubbles fizzing on the hit icon")),
    "c_drip": (PRE + "A few drops of cider dripping off a table edge onto a wooden floor: soft, small, wet plips.", 5,
               "drop", (.1, .45, 3, None), ("set", "cider_drip", -26, "ciderDrip", .2, "drips running off the icon")),
    "c_bubble": (PRE + "One single big soapy bubble popping: a short, wet, cartoony pop.", 5, "drop",
                 (.05, .3, 3, None), ("set", "bubble_pop", -24, "bubblePop", .3, "a neighbour popping, fizzy")),
}

# ---------------- 2026-11-04: the rest of the street / Casino Machines sounds, made harvest (same files) ----------------
# Targets are the originals' own momentary-max LUFS, so the mix in index.html stays where it was.
H = {
    # the spin and the HUD singles (SFX map)
    "h_spin": (PRE + "Turning the wooden hand crank of an old cider press once, quickly: a short ratcheting "
               "wooden clack-clack-clack rising into a soft woody whir.", 5, "foley", (.45, 1.0, 1, "gesture"),
               ("files", ["sfx_spin.wav"], -27, "spin: cider-press crank, ratchet into a whir")),
    "h_bet": (PRE + "An acorn tapped once on the lid of a wooden barrel: one short, hollow, woody tock.", 5, "click",
              (.04, .32, 1, None), ("files", ["sfx_bet.wav"], -26.5, "bet +/-: acorn tock on a barrel lid")),
    "h_toggle": (PRE + "Flipping a small wooden latch on a barn door: one quick crisp woody click-clack.", 5, "click",
                 (.04, .32, 1, None), ("files", ["sfx_toggle.wav"], -26.5, "a switch: wooden latch click")),
    "h_skip": (PRE + "A dry corn stalk swiped quickly through the air: one short, light, papery swish.", 5, "whoosh",
               (.15, .4, 1, None), ("files", ["sfx_skip.wav"], -30, "skip: corn-stalk swish")),
    "h_line": (PRE_STING + "A quick bright banjo pluck running up three notes and ringing: plink-plink-plinnng.", 5,
               "sting", (.4, 1.0, 1, None), ("files", ["sfx_line.wav"], -17, "a cluster lights: banjo three-note run")),
    "h_bonus_end": (PRE_STING + "A short cheerful fiddle cadence that resolves and ends on one long bright final "
                    "note, like the end of a country hoedown tune.", 5, "sting", (1.0, 1.7, 1, None),
                    ("files", ["sfx_bonus_end.wav"], -16, "free spins over: fiddle cadence (fetched, not played yet)")),
    "h_bell": (PRE + "One strike of a small brass farmhouse dinner bell: a bright, clear ding ringing out and "
               "fading.", 5, "tone", (.7, 1.5, 1, "gesture"), ("files", ["sfx_bell.wav"], -19.5, "tally end: dinner-bell ding")),
    "h_medium_win": (PRE_STING + "A cheerful bright bluegrass banjo strum on one big major chord with a fiddle "
                     "accent, ringing out for two seconds.", 5, "sting", (1.4, 3.0, 1, None),
                     ("files", ["sfx_medium_win.wav"], -17.5, "total screen marks: banjo + fiddle chord (pitched up per mark)")),
    "h_trophy": (PRE + "A big deep old harvest bell in a wooden bell tower tolling once: one warm, rich, low BONG "
                 "with a long ringing decay.", 5, "tone", (1.4, 2.5, 1, "gesture"),
                 ("files", ["sfx_trophy.wav"], -23, "the total arrives: one deep harvest-bell bong")),
    "h_coins_rain": (PRE + "A big basket of acorns and walnuts poured out onto a wooden barn floor: a lively "
                     "pattering clatter of nuts bouncing and rolling for about four seconds, thinning out at the end.",
                     5, "foley", (2.5, 4.9, 1, "gesture"),
                     ("files", ["sfx_coins_rain.wav"], -21, "the total arrives: acorns and walnuts raining down")),
    "h_pop": (PRE + "A single kernel of corn popping into popcorn in a hot pan: one bright, puffy, cartoony pop.", 6,
              "hit", (.06, .8, 1, None), ("files", ["sfx_pop.wav"], -20, "an icon popping off: popcorn pop")),
    # ---------------- every icon its own pop (owner, 2026-11-12) ----------------
    "pop_h1": (PRE + 'A crispy roast turkey drumstick snapped off the bird: one crisp crackly crunch-snap with a small juicy squish.', 5, "hit",
               (.06, .8, 2, None), ("set", "pop_h1", -20, "popH1", .4, "the turkey popping off the board")),
    "pop_h2": (PRE + 'A soft pumpkin pie squashed flat by a hand: one soft creamy splat with a short flaky crust crunch.', 5, "hit",
               (.06, .8, 2, None), ("set", "pop_h2", -20, "popH2", .4, "the pie popping off the board")),
    "pop_h3": (PRE + 'A dry wicker basket bursting apart: one sharp woody crackling snap of breaking wicker and a couple of apples thudding out.', 5, "hit",
               (.06, .8, 2, None), ("set", "pop_h3", -20, "popH3", .4, "the wicker popping off the board")),
    "pop_h4": (PRE + 'A brass belt buckle pinging off and flying away: one bright metallic ping with a quick flap of felt cloth.', 5, "hit",
               (.06, .8, 2, None), ("set", "pop_h4", -20, "popH4", .4, "the buckle popping off the board")),
    "pop_h5": (PRE + 'A small clay cider jug shattering on a stone floor: one short ceramic crack and shatter with a small splash.', 5, "hit",
               (.06, .8, 2, None), ("set", "pop_h5", -20, "popH5", .4, "the jug popping off the board")),
    "pop_h6": (PRE + 'A handful of popcorn kernels popping all at once in a hot pan: one quick rapid burst of four bright puffy pops.', 5, "hit",
               (.06, .8, 2, None), ("set", "pop_h6", -20, "popH6", .4, "the corn popping off the board")),
    "pop_h7": (PRE + 'A big ripe pumpkin smashing open: one heavy hollow thump and a wet pulpy splat.', 5, "hit",
               (.06, .8, 2, None), ("set", "pop_h7", -20, "popH7", .4, "the pumpkin popping off the board")),
    "pop_l1": (PRE + 'A handful of dry autumn leaves crushed hard in a fist: one crisp papery crunch.', 5, "hit",
               (.06, .8, 2, None), ("set", "pop_l1", -20, "popL1", .4, "the leaf popping off the board")),
    "pop_l3": (PRE + 'A crisp green apple cracked in half by hand: one loud juicy crunchy snap.', 5, "hit",
               (.06, .8, 2, None), ("set", "pop_l3", -20, "popL3", .4, "the apple popping off the board")),
    "pop_l4": (PRE + 'A bunch of ripe grapes squished in a fist: one quick run of small wet juicy pops and squirts.', 5, "hit",
               (.06, .8, 2, None), ("set", "pop_l4", -20, "popL4", .4, "the grapes popping off the board")),
    "h_multi_hit": (PRE + "A heavy wooden mallet striking an empty oak cider barrel: one big hollow resonant boom, "
                    "with a bright cowbell clank on top.", 5, "impact", (.5, 1.55, 1, None),
                    ("files", ["sfx_multi_hit.wav"], -20.5, "a Multi going off: barrel boom + cowbell")),
    "h_alert_a": (PRE + "A big cowbell rung hard three times in quick succession: clank-clank-clank, ringing out.", 5,
                  "tone", (.7, 1.6, 1, "gesture"),
                  ("files", ["sfx_jackpot_alert_a.wav", "sfx_jackpot_a.wav"], -18.5, "Cork Storm / Full Harvest: cowbell x3")),
    "h_alert_b": (PRE + "A brass dinner triangle rung rapidly around its inside: a bright, fast, jangling ring.", 5,
                  "tone", (.7, 1.55, 1, "gesture"),
                  ("files", ["sfx_jackpot_alert_b.wav", "sfx_jackpot_b.wav"], -18, "Cider Line: dinner triangle rung fast")),
    "h_win_text": (PRE_STING + "A quick bright banjo 'ta-da': two fast plucked chords stepping up, the second one "
                   "ringing.", 5, "sting", (.35, .9, 1, None),
                   ("files", ["sfx_win_text.wav"], -20.5, "the win amount pops up: banjo ta-da")),
    "h_auto_start": (PRE + "A heavy wooden lever on an old farm machine pulled down: a short wooden creak, then one "
                     "solid wooden clunk.", 5, "foley", (.3, .8, 1, None),
                     ("files", ["sfx_auto_start.wav"], -20, "autoplay on: wooden lever pulled, creak + clunk")),
    "h_auto_stop": (PRE + "A heavy wooden lever pushed back up into place: one solid wooden clunk followed by a short "
                    "squeak.", 5, "foley", (.3, .75, 1, None),
                    ("files", ["sfx_auto_stop.wav"], -17.5, "autoplay off: lever pushed back, clunk + squeak")),
    "h_menu_open": (PRE + "A small wooden cupboard door creaking open quickly: one short, soft, woody creak.", 5,
                    "foley", (.3, .7, 1, None), ("files", ["sfx_menu_open.wav"], -26.5, "a panel opens: cupboard creak")),
    "h_menu_close": (PRE + "A small wooden cupboard door swung shut: a short creak ending in one soft wooden clap.",
                     5, "foley", (.3, .8, 1, None), ("files", ["sfx_menu_close.wav"], -26.5, "a panel closes: creak + clap")),
    # the loops: a steady stretch of the take, crossfaded end-into-start (fall.py `loop`), no gate
    "h_reels": (PRE + "An old wooden cart wheel rolling steadily along a bumpy dirt farm road: a continuous, even, "
                "rhythmic wooden rattle and clatter that keeps going for five seconds.", 4, "foley", (1.2, 1.2, 1, None),
                ("files", ["sfx_reels.wav"], -30, "reels spinning (loop, pitch follows the reels): cart-wheel rattle")),
    "h_coins": (PRE + "Dry corn kernels pouring steadily from a scoop into a tin pail: a continuous, even, bright, "
                "rattling patter that keeps going for five seconds.", 4, "foley", (.96, .96, 1, None),
                ("files", ["sfx_coins.wav"], -31, "win tally (loop): corn kernels pouring into a tin pail")),
    "h_hover": (PRE + "A cozy wood fire crackling softly in a stone hearth: gentle steady crackles and pops over a "
                "low warm rumble, continuous for six seconds.", 4, "foley", (4.0, 4.0, 1, None),
                ("files", ["sfx_hover_loop.wav"], -22, "Bonus button hover (loop): hearth fire crackle")),
    # ---- the street pass's own sets (SFX_SETS), the same stems and take counts ----
    # the studio ident
    "h_intro_rise": (PRE_STING + "A fiddle bow tremolo that rises steadily in pitch and gets louder and louder for two "
                     "seconds, building tension, and stops at its loudest, highest point.", 6, "sting",
                     (1.0, 3.0, 3, None), ("set", "intro_rise", -18, "introRise", .5, "ident: rising fiddle tremolo, ends at its peak")),
    "h_intro_whoosh": (PRE + "A quick gust of wind sweeping a swirl of dry autumn leaves right past the microphone: "
                       "one short rushing whoosh.", 5, "whoosh", (.45, .9, 3, None),
                       ("set", "intro_whoosh", -21, "introWhoosh", .45, "ident: leaf-gust whoosh")),
    "h_intro_hit": (PRE + "A huge heavy wooden barn door slamming shut: one deep booming wooden thud with a long "
                    "rumbling decay inside a big empty barn.", 5, "impact", (.5, 2.8, 2, "gesture"),
                    ("set", "intro_hit", -13.5, "introHit", .72, "ident: the logo lands, barn-door boom")),
    "h_intro_shimmer": (PRE + "Small brass and glass wind chimes stirred by a light breeze: a soft, airy, glassy "
                        "shimmering tinkle.", 5, "tone", (.8, 1.3, 3, "gesture"),
                        ("set", "intro_shimmer", -22, "introShimmer", .42, "ident: wind-chime shimmer")),
    "h_intro_out": (PRE + "A soft gust of wind rushing away and carrying dry leaves off with it: one breathy whoosh "
                    "fading out.", 5, "whoosh", (.6, .9, 2, None),
                    ("set", "intro_out", -21.5, "introOut", .45, "ident out: wind whoosh away")),
    # the win presentation
    "h_glow": (PRE + "A soft warm breathy note blown across the mouth of an empty clay jug, swelling gently up and "
               "fading away: one soft 'hooo'.", 5, "tone", (.6, 1.0, 2, "gesture"),
               ("set", "glow_pulse", -25, "glowPulse", .26, "a symbol lights: soft jug-blow swell")),
    "h_shine": (PRE_STING + "A quick light upward strum across the strings of an autoharp, ending in two tiny bright "
                "plinks.", 5, "tone", (.35, .7, 2, "gesture"),
                ("set", "shine", -24, "shine", .3, "a shine across a symbol: autoharp strum + two plinks")),
    "h_sparkle": (PRE + "A light quick run of tiny glass wind chimes tinkling, delicate and sparkling.", 5, "tone",
                  (.4, .95, 3, "gesture"), ("set", "sparkle", -24, "sparkle", .28, "glitter: tiny glass chimes")),
    "h_glint": (PRE + "One single light tap on a small empty glass cider bottle with a spoon: one clear, bright, "
                "pure ting, ringing briefly.", 6, "tone", (.25, .8, 4, "hit"),
                ("set", "glint", -25, "glint", .24, "one bright ting per lit symbol (pitched to a scale): glass bottle tap")),
    "h_count_tick": (PRE + "One acorn tapped on a wooden tabletop: a tiny, dry, crisp woody tick.", 5, "click",
                     (.015, .06, 3, None), ("set", "count_tick", -26, "countTick", .26, "the figure counting: acorn tick")),
    "h_count_end": (PRE + "A heavy wooden barrel lid set down with a solid clunk, followed right away by one bright "
                    "ding of a brass farm bell ringing out.", 5, "tone", (.8, 1.75, 1, "gesture"),
                    ("set", "count_end", -21, "countEnd", .5, "the figure lands: barrel-lid clunk + bell")),
    "h_slam": (PRE + "A heavy wooden mallet slamming down on the top of an oak barrel: one deep, punchy, solid thump.",
               5, "impact", (.2, .45, 3, None), ("set", "mult_slam", -17, "multSlam", .62, "the x<N> slams on: mallet on a barrel")),
    "h_count_whoosh": (PRE + "A gust of autumn wind rising quickly, with dry leaves rustling and swirling upward: one "
                       "rising whoosh.", 5, "whoosh", (.8, 1.4, 2, None),
                       ("set", "count_whoosh", -23.5, "countWhoosh", .4, "the count climbs again: rising leaf gust")),
    "h_float": (PRE + "A soft breeze carrying a few dry leaves away, the rustle drifting off and fading into the "
                "distance.", 5, "whoosh", (.9, 1.8, 2, None),
                ("set", "float_away", -24, "floatAway", .36, "the figure floats away: leaves drifting off")),
    # board / HUD
    "h_reel_stop": (PRE + "A small wooden crate set down firmly on a wooden barn floor: one short, solid wooden thunk.",
                    5, "hit", (.06, .25, 3, None), ("set", "reel_stop", -22, "reelStop", .3, "a column's last tile down: crate thunk")),
    "h_click": (PRE + "A small wooden peg pushed firmly into a wooden board: one tiny, crisp, woody click.", 5, "click",
                (.015, .08, 3, None), ("set", "ui_click", -27, "uiClick", .32, "any button: wooden peg click")),
    "h_hover_tick": (PRE + "A fingernail flicking a dry corn husk once: one tiny, soft, papery tick.", 5, "click",
                     (.01, .035, 2, None), ("set", "ui_hover", -30, "uiHover", .14, "pointer on a button: corn-husk tick")),
    "h_ratchet": (PRE + "An old wooden ratchet gear turned by one notch: one single tiny, crisp, woody click.", 6, "click",
                  (.015, .06, 2, None), ("set", "slider_tick", -27, "sliderTick", .22,
                                         "volume notch: wooden ratchet click (its takes also make sfx_money_tick, fall.py ticks)")),
    "h_swish_in": (PRE + "A burlap sack whipped quickly through the air: one soft, low, airy fabric swish.", 5, "whoosh",
                   (.2, .55, 2, None), ("set", "swish_in", -25, "swishIn", .3, "under menuOpen: burlap swish")),
    "h_swish_out": (PRE + "A burlap sack swung quickly away through the air: one soft, low, airy fabric swish that "
                    "fades off.", 5, "whoosh", (.2, .55, 2, None),
                    ("set", "swish_out", -25, "swishOut", .28, "under menuClose: burlap swish away")),
    "h_buy": (PRE + "A brass farmhouse dinner bell rung twice: a bright ding-ding, ringing out.", 5, "tone",
              (.8, 1.4, 1, "gesture"), ("set", "buy_confirm", -21, "buyConfirm", .5, "a bonus bought: dinner bell ding-ding")),
    "h_fs_tick": (PRE + "A wooden clothespin snapping shut: one short, crisp, woody clack.", 5, "click",
                  (.03, .13, 2, None), ("set", "fs_tick", -25, "fsTick", .32, "free spins counter: clothespin clack")),
}
S.update(H)
# made by fall.py `loop` (a seamless loop cut from the take, not build): name -> crossfade seconds
LOOP = {"h_reels": .12, "h_coins": .1, "h_hover": .6}
# made by fall.py `ticks` from h_ratchet's picks: the money counter's loop, one click every 125 ms, 22 of them
TICKS = {"sfx_money_tick.wav": dict(src="h_ratchet", period=.125, n=22, tgt=-20)}
# after the clean: keep only this many seconds ending at the loudest moment (the ident's rise ends at its peak)
ENDPEAK = {"h_intro_rise": 1.62}
# fall.py `shape`, after build / texture: what the takes could not give (see shape's doc)
SHAPE = {"h_intro_rise": {"rise": 5}, "h_intro_hit": {"lead": 1}, "h_line": {"lead": 1, "compact": (.15, -26)},
         "h_sparkle": {"lead": 1, "compact": (.06, -24)}, "h_menu_open": {"lead": 1}, "h_menu_close": {"lead": 1},
         "h_count_whoosh": {"swell": 1}, "h_float": {"away": 1}, "h_intro_out": {"away": 1},
         "h_swish_in": {"pass": .4}, "h_swish_out": {"pass": .2}}

# one event per take for these (no second hit inside the event)
SINGLE = {"pop_h1", "pop_h2", "pop_h3", "pop_h4", "pop_h5", "pop_h6", "pop_h7", "pop_l1", "pop_l3", "pop_l4",
          "land_platter", "land_pie", "land_hat", "land_jug", "land_corn", "land_pumpkin", "land_leaf", "land_acorn",
          "land_apple", "land_grapes", "land_sunflower", "land_feather", "land_jelly", "land_porcelain", "land_hay",
          "land_bottle", "crow_peck", "f_cork", "f_gravy_drop", "f_plop", "f_squash", "b_pop", "c_bonk", "c_bubble",
          "h_bet", "h_toggle", "h_pop", "h_multi_hit", "h_intro_hit", "h_glint", "h_count_tick", "h_slam",
          "h_reel_stop", "h_click", "h_hover_tick", "h_ratchet", "h_fs_tick"}
TONAL = {"land_porcelain", "land_bottle", "f_scatter", "f_bonus", "f_bust", "land_pie",
         "h_line", "h_bonus_end", "h_bell", "h_medium_win", "h_trophy", "h_alert_a", "h_alert_b", "h_win_text",
         "h_intro_rise", "h_intro_shimmer", "h_glow", "h_shine", "h_sparkle", "h_glint", "h_count_end", "h_buy"}
FOUT = {"f_scatter": 400, "f_bonus": 250, "f_bust": 250, "jug_slosh": 120, "straw_rustle": 90, "rope_creak": 90,
        "wing_flap": 90, "f_sweep_long": 120, "crow_caw": 60,
        "h_bell": 300, "h_trophy": 500, "h_medium_win": 400, "h_bonus_end": 300, "h_line": 200, "h_win_text": 150,
        "h_alert_a": 250, "h_alert_b": 250, "h_count_end": 350, "h_buy": 300, "h_coins_rain": 400,
        "h_intro_hit": 600, "h_intro_shimmer": 250, "h_float": 300, "h_intro_out": 200, "h_glow": 200, "h_glint": 150}


# the bed allowed under a sound that is itself a noise (a broom swish fills its whole take; outside the
# sound the gate leaves exact zero anyway); everything else keeps clean3's -72 dBFS
BED = {"f_sweep_long": -56, "h_glow": -52, "h_sparkle": -52, "h_swish_in": -52}
# the continuous ones (a jangling triangle, a tremolo, a chime shimmer) are all "bed": fall.py `texture`
TEXTURE = {"h_alert_b", "h_intro_rise", "h_intro_shimmer"}
# hand picks (take files from cand/) where the scoring can't hear the difference
MANUAL = {"f_bonus": ["5_0.wav"]}      # take 5: a clean fiddle run up to a high note in its first 1.45 s
# time-compressed (WSOLA, pitch kept) after cleaning: the jug's four wah-wahs came back ~4 s long
STRETCH = {"f_bust": 2.0}


def jobs():
    for name, (prompt, takes, kind, _, _) in S.items():
        yield name, prompt + CLOSE, takes, kind
