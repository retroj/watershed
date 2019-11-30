
from random import *
from AssetManager import AssetManager
from mobs import Mob

class Bubbles (Mob):
    name = "bubbles"
    start_position = (0, 0)
    speed = (0, 0)
    last_spawn_time = 0
    last_x = None

    def __init__ (self, pond, t):
        super(Bubbles, self).__init__(pond, t)
        if t - Bubbles.last_spawn_time < 1:
            x = Bubbles.last_x + randint(-1,1)
        else:
            x = random() * (pond.width - 2) + 1
        Bubbles.last_x = x
        Bubbles.last_spawn_time = t
        self.start_position = (x, pond.height - 1)
        self.speed = (0, -5)


    ## Public Interface
    ##
    def update (self, pond, t):
        (x, y) = self.update_position(t)
        (sx, sy) = self.speed
        if y <= pond.level_px:
            pond.mobcounter.remove(self)
            return False
        c = tuple([min(255, x + 20) for x in pond.watercolor])
        pond.canvas.putpixel((x, y), c)
        return True

    @staticmethod
    def maybe_spawn (pond, t):
        if random() * pond.health**0.125 < 0.005 and pond.health > 0.3:
            return Bubbles(pond, t)
