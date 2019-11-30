
from random import random, randint, getrandbits
from utils import *

class MobCounter ():
    mobs = None

    def __init__ (self):
        self.mobs = {}

    def add (self, mob):
        if mob.name not in self.mobs:
            self.mobs[mob.name] = 0
        self.mobs[mob.name] += 1

    def remove (self, mob):
        if mob.name not in self.mobs:
            return ## mobs that don't despawn on reset
        if self.mobs[mob.name] > 1:
            self.mobs[mob.name] -= 1
        else:
            self.mobs.pop(mob.name)


class Mob ():
    """
    Base class for sprites.
    """
    name = "Mob"
    sprite = None
    mask = None
    position = (0, 0)
    start_position = (0, 0)
    start_position_time = None
    speed = (0, 5)
    z = 0

    def __init__ (self, pond, t):
        self.start_position_time = t
        pond.mobcounter.add(self)

    def update (self, pond, t):
        return True

    def change_trajectory (self, t, speed):
        if speed != self.speed:
            self.start_position = self.position
            self.start_position_time = t
            self.speed = speed

    def update_position (self, t):
        x0, y0 = self.start_position
        sx, sy = self.speed
        dt = t - self.start_position_time
        self.position = (int(x0 + sx * dt), int(y0 + sy * dt))
        return self.position

    def scram (self, pond, t):
        return 0

    @staticmethod
    def init_static ():
        pass


class LEDStripMob (Mob):
    """
    A Mob that exclusively, or also, appears on a LED strip.
    """
    name = "LEDStripMob"
    stripsection = None
    color = (0, 0, 0)
    length = 7 ## length of droplet on strip
    start_x = 32
    airspeed = (0, 8)
    waterspeed = (0, 5)
    matrix_trail = None

    def __init__ (self, pond, t):
        super(LEDStripMob, self).__init__(pond, t)
        self.speed = self.airspeed
        self.matrix_trail = []
        self.stripsection = pond.ledstrip.sections[self.name]
        self.start_position = (self.start_x, -(self.stripsection.length))

    def draw_on_strip (self):
        s = self.stripsection
        x, y = self.position
        for i in range(0, self.length):
            dim = (self.length - i) / self.length
            c = color_darken(self.color, dim)
            s.set_pixel(y - i, c)
        s.set_pixel(y - self.length, (0, 0, 0))


class Droplet (LEDStripMob):
    ## internal
    ##
    name = "unknown droplet"

    ## config
    ##
    start_x = 30
    airspeed = (1.5, 8)
    waterspeed = (1.5, 8)
    trailfadetime = 0.8
    entered_mud_time = None

    def draw_on_matrix (self, pond, t):
        trail_length = len(self.matrix_trail)

        ## trail
        for i,((tx,ty),tt) in enumerate(self.matrix_trail):
            factor = (t - tt) / self.trailfadetime
            if factor < 1.0:
                if ty < pond.level_px:
                    bgcolor = (0, 0, 0)
                else:
                    bgcolor = pond.watercolor
                tcolor = color_blend(self.color, bgcolor, factor)
                pond.canvas.putpixel((tx, ty), tcolor)

        ## lead pixel
        pond.canvas.putpixel(self.position, self.color)
        x, y = self.position
        #if y < pond.level_px:
        self.matrix_trail.append((self.position, t))


    ## Public Interface
    ##
    def update (self, pond, t):
        (x1, y1) = self.position
        (x2, y2) = self.update_position(t)
        if y2 >= pond.level_px:
            self.change_trajectory(t, self.waterspeed)
        if x2 != x1 or y2 != y1: # ledstrip only needs update on change
            if y2 < self.length: # at least part of tail is on strip
                self.draw_on_strip()
        if y2 >= 0 and y2 < pond.height: # matrix
            self.draw_on_matrix(pond, t)
        mudlevels = pond.mud.levels
        mudlevel = min(mudlevels[x2], mudlevels[x2 - 1], mudlevels[x2 + 1])
        if y2 + 1 >= mudlevel or y2 + 1 >= pond.height:
            ## need to wait self.trailfadetime
            self.entered_mud_time = self.entered_mud_time or t
            if t > self.entered_mud_time + self.trailfadetime:
                pond.mobcounter.remove(self)
                return False
            else:
                self.change_trajectory(t, (0, 0))
                ox = randint(-1,1)
                oy = randint(-1,0)
                pond.mud.add(self, (ox, oy))
        return True


class GoodDroplet (Droplet):
    name = "gooddroplet"
    color = (0, 0, 0xff)
    start_x = 30
    airspeed = (1.5, 8)
    waterspeed = (1.5, 8)

    ## Public Interface
    ##
    @staticmethod
    def spawn (pond, t):
        pond.add_mob(GoodDroplet(pond, t))


class BadDroplet (Droplet):
    name = "baddroplet"
    color = (0xaa, 0, 0)
    start_x = 40
    airspeed = (-1.5, 8)
    waterspeed = (0, 5)

    ## Public Interface
    ##
    @staticmethod
    def spawn (pond, t):
        pond.add_mob(BadDroplet(pond, t))
