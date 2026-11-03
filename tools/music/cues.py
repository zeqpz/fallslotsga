"""The game's five music cues: where each plays, what Lyria is asked for, and how build.py cuts it.

Fall pass (2026-11-03): the game is a Thanksgiving harvest farm with one figure, a drunk scarecrow tied
to his pole with a moonshine jug and a crow on the crossbar. Every cue is instrumental cartoon jug-band
Americana - fiddle, banjo, acoustic guitar, upright bass, washboard and brushed drums, a blown jug,
accordion, a little glockenspiel - slightly tipsy and swaying. G major for the base game, the menu and
the TOTAL WIN, D major (its dominant) for the free spins' intro and the free spins themselves, so every
crossfade sits in related keys. Lyria takes the tempo but not the key, so takes were kept for their key
(chroma readout); the kept ones are in art/music-src/.

  bars       the loop's length in bars (4/4)
  head       None: the cue is only the loop. A number: the take's opening plays once and the loop
             starts that many seconds in (snapped to the take's beat), cut from wherever after
             loop_from fits best; the opening keeps ringing under it for `tail` seconds (default 2)
  start      seconds cut off the take's front before anything else (head and loop_from count from there)
  loop_from  seconds into the take before which no loop may start (past its intro)
  game_lufs  how loud the cue should sit in the game (the music bar at 100); sets its MUSIC level.
             The street loops sat at -24.5 (base) and -22 (bonus)
"""

NO_VOX = ("Strictly instrumental: no vocals, no singing, no humming, no shouts, no yee-haws, no spoken words. ")

CUES = {
    "base": {
        "where": "the base game",
        "bpm": 101, "bars": 32, "head": None, "loop_from": 0, "game_lufs": -24.5,
        "prompt": (
            "Instrumental only. Key: G major. Tempo: 104 BPM. " + NO_VOX +
            "A cosy, bouncy Thanksgiving harvest-fair jug band tune for a cartoon slot game, 104 BPM, G major, 4/4. "
            "Warm Americana folk: a gentle fiddle melody, rolling clawhammer banjo, strummed acoustic guitar, a walking "
            "upright bass doubled by a comedic blown jug going 'oom-pah', light washboard scratches and brushed snare, "
            "a little accordion and a few soft glockenspiel notes. A slightly wobbly, swaying, good-natured feel, like a "
            "goofy scarecrow tapping his boot at a county fair. Relaxed and friendly, never busy or fatiguing: "
            "background music that can play for a long time. Chords G - C - D - G with an Em now and then. "
            "Structure: [Short intro] -> [Main groove] -> [Main groove with fiddle and banjo trading the tune] -> "
            "[Main groove]. No breakdown, no big ending, no fade-out."),
    },
    "menu": {
        "where": "the bonus buy menu",
        "bpm": 100, "bars": 16, "head": None, "loop_from": 0, "game_lufs": -27,
        "prompt": (
            "Instrumental only. Key: G major (G, B, D). Tempo: 96 BPM. " + NO_VOX +
            "Mellow back-porch picking on a cool autumn evening: the same cartoon jug-band world, heard quietly while "
            "deciding something. 96 BPM, G major, 4/4. Soft fingerpicked acoustic guitar, a gentle banjo roll, a "
            "lazy upright bass, a soft blown jug on the low notes, a little brushed snare and a faint sustained "
            "accordion chord, a few soft glockenspiel twinkles. Calm, cosy and a little sleepy and lazy, low energy "
            "but still gently swinging, at a rock-steady tempo: the upright bass and jug on every beat and a brushed "
            "snare on 2 and 4 keep strict time throughout. The same relaxed groove from start to finish: no build-ups, "
            "no rubato, no fiddle solo, no big ending, no fade-out."),
    },
    "intro": {
        "where": "the YOU WON n FREE SPINS screen (waits for a click)",
        "bpm": 136, "bars": 8, "head": 5.76, "tail": .6, "loop_from": 9, "game_lufs": -23.5,
        "prompt": (
            "Instrumental only. Key: D major. Tempo: 136 BPM. " + NO_VOX +
            "A cartoon barn-dance announcement for a bonus round: 136 BPM, D major, 4/4. It opens instantly with a big "
            "comedic fanfare hit - a crash cymbal, a fast fiddle run up to a high note, a banjo strum and a deep blown "
            "jug 'boom' - then settles into an excited, bouncing vamp that holds steady and keeps repeating: chugging "
            "banjo and guitar on D and A, a steady upright bass and jug 'oom-pah', snappy washboard and brushed snare, "
            "short fiddle stabs, an accordion pumping chords. The excited feeling just before the hoedown starts. "
            "Structure: [Fanfare hit] -> [Steady bouncing vamp, repeating]. No big drop, no ending, no fade-out."),
    },
    "bonus": {
        "where": "the free spins",
        "bpm": 136, "bars": 32, "head": None, "loop_from": 0, "game_lufs": -22,
        "prompt": (
            "Instrumental only. Key: D major. Tempo: 136 BPM. " + NO_VOX +
            "A fast, rowdy, joyful harvest hoedown for a slot game's free spins: 136 BPM, D major, 4/4. A lively "
            "fiddle reel melody, fast rolling bluegrass banjo, driving boom-chick acoustic guitar, a bouncing upright "
            "bass doubled by a comedic blown jug, a busy washboard and snappy brushed snare, a pumping accordion, "
            "sparkling glockenspiel accents. Cartoon jug band at full tilt at a Thanksgiving barn dance, with a "
            "goofy swagger. Energetic and fun from the first bar: [Main section] -> [Main section, fiddle "
            "and banjo trading licks] -> [Main section with variations] -> [Main section]. No intro, no breakdown, "
            "no ending, no fade-out."),
    },
    "total": {
        "where": "the bonus's TOTAL WIN screen (waits for a click)",
        "bpm": 123, "bars": 8, "start": 1.3, "head": 4.44, "tail": 1.2, "loop_from": 11.2, "game_lufs": -22.5,
        "prompt": (
            "Instrumental only. Key: G major. Tempo: 120 BPM. " + NO_VOX +
            "A triumphant barn-dance finale celebrating a huge win: 120 BPM, G major, 4/4. It opens with a big "
            "celebratory hit - a crash cymbal, a bright fiddle flourish, a banjo roll and a glockenspiel glissando - "
            "then a joyful, swinging victory groove: stomping kick and brushed snare, washboard, a bouncing upright "
            "bass and blown jug, strummed guitar and banjo, the fiddle and accordion playing a big happy tune over "
            "G - D - C - G, sparkling glockenspiel. Uplifting, victorious and goofy, like the whole harvest "
            "fair dancing. Structure: [Celebration hit] -> [Joyful groove, steady and repeating]. No breakdown, no "
            "ending, no fade-out."),
    },
}
