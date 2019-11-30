
from math import *

tau = asin(1.0) * 4 ## not needed if python >= 3.6

class GameError (Exception):
    message = None
    color = None

    def __init__ (self, message, color):
        self.message = message
        self.color = color


def color_darken (color, factor):
    r, g, b = color
    return (int(r * factor), int(g * factor), int(b * factor))


def color_blend (color1, color2, factor):
    r1, g1, b1 = color1
    r2, g2, b2 = color2
    r3 = int((r2 - r1) * factor + r1)
    g3 = int((g2 - g1) * factor + g1)
    b3 = int((b2 - b1) * factor + b1)
    return (r3, g3, b3)
