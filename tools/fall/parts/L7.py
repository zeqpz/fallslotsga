"""L7 Turkey Feather, cut into parts (tools/fall/cut_parts.py). Icon px of art/fall-src/icons/L7.png.

A chain from the quill to the peacock-eye tip: the feather is sliced straight across its shaft (cut "poly") into the
bare quill, three vane pieces and the eye. Each piece rides the one before it and turns about the point where the
shaft crosses its lower seam, so the feather bends link by link. Every piece but the eye runs on OVERLAP px past its
upper seam, tucked under the next piece (which is drawn in front of it): when a joint bends, what opens up at the
seam is the feather itself, not a gap. No plates - nothing moves off anything."""
import math

B = (85, 910)                                    # the quill's open end, on the shaft line
D = (0.6936, -0.7204)                            # along the shaft, quill -> tip (unit)
N = (-D[1], D[0])                                # across it
W = 650                                          # half-width of a slice: past the sticker on both sides
OVERLAP = 34
CUTS = [-200, 200, 410, 610, 790, 1500]          # seams, px along the shaft from the quill end


def at(s, w=0.0):
    return (round(B[0] + D[0] * s + N[0] * w), round(B[1] + D[1] * s + N[1] * w))


def slab(s0, s1):
    return [at(s0, -W), at(s1, -W), at(s1, W), at(s0, W)]


PLATES = {}
NAMES = ["quill", "vane1", "vane2", "vane3", "eye"]
LAYERS = []
for k, name in enumerate(NAMES):
    s0, s1 = CUTS[k], CUTS[k + 1]
    LAYERS.append(dict(name=name, src="art", cut="poly", poly=slab(s0, s1 + (OVERLAP if k < len(NAMES) - 1 else 0)),
                       pivot=at(60) if k == 0 else at(s0), parent="root" if k == 0 else NAMES[k - 1]))
