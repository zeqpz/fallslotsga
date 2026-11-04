"""H1 Roast Turkey, cut into parts (tools/fall/cut_parts.py). Icon px of art/fall-src/icons/H1.png.

plates  the picture again with things taken away and what was behind painted in (OpenRouter edit of the icon)
layers  back to front: src "plate:<name>" (all of that plate), "diff:<a>-<b>" (where plate a differs from plate b),
        or "art" cut along the drawing's own outlines inside `poly`; pivot = where it turns; parent = the layer it
        rides on ("root" = the whole icon)"""
PLATES = {
    "platter": "Edit the attached picture: remove the roast turkey completely - its body, both drumsticks and its wings - "
               "and ALL the sage leaves and cranberries - and paint the bare, empty oval platter where they were. Keep the "
               "platter exactly the same: same position, same size, same colours, same gold rim, same outline and the same "
               "cream sticker border round it. Transparent background.",
    "body": "Edit the attached picture: remove the two drumsticks and thighs (with their white paper frills), the folded "
            "wing, and ALL the sage leaves and cranberries; paint the turkey's golden-brown body where the legs and wing "
            "were, so the body is whole and smooth, and the bare platter where the garnish was. Keep everything else "
            "exactly the same: same position, same size, platter, colours and outline. Transparent background.",
}
LAYERS = [
    dict(name="platter", src="plate:platter", pivot=(500, 760), parent="root"),
    dict(name="body", src="diff:body-platter", keep="warm", pivot=(470, 700), parent="root"),
    dict(name="leg_back", src="art", cut="poly", poly=[(548, 300), (600, 170), (640, 115), (825, 115), (825, 300),
                                                      (720, 345), (615, 345)], pivot=(590, 330), parent="body"),
    dict(name="wing", src="art", poly=[(300, 560), (390, 520), (560, 540), (590, 640), (520, 700), (360, 700), (300, 650)],
         pivot=(540, 590), parent="body"),
    dict(name="leg_front", src="art", cut="poly", poly=[(560, 560), (575, 430), (690, 365), (785, 330), (800, 220),
                                                        (995, 210), (995, 400), (880, 430), (860, 560), (810, 640),
                                                        (690, 660), (600, 630)],
         pivot=(650, 560), parent="body"),
    dict(name="garnish_l", src="art", poly=[(80, 560), (240, 560), (350, 650), (430, 780), (300, 790), (90, 720)],
         pivot=(250, 720), parent="platter"),
    dict(name="garnish_m", src="art", poly=[(480, 690), (650, 690), (650, 790), (480, 790)], pivot=(570, 760),
         parent="platter"),
    dict(name="garnish_r", src="art", poly=[(640, 580), (800, 540), (930, 580), (930, 680), (780, 760), (630, 760)],
         pivot=(760, 700), parent="platter"),
]
