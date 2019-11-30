
from time import time
from mobs import LEDStripMob, Droplet
from utils import *

class Rain (LEDStripMob):
    name = "rain"
    last_spawn = time()
    color = (0, 0, 0xff)
    start_x = 10
    airspeed = (1.5, 8)
    waterspeed = (1.5, 8)
    z = -1
    fadetime = 3.5
    time_entered_water = None

    def draw_on_matrix (self, pond, t):
        trail_length = len(self.matrix_trail)
        for i,((tx,ty),tt) in enumerate(self.matrix_trail):
            if ty < pond.level_px:
                blue = int(i / trail_length * 200 - (t - tt) * 150)
                if blue > 0:
                    pond.canvas.putpixel((tx, ty), (0, 0, blue))
        if self.time_entered_water is None:
            color = self.color
        else:
            factor = (t - self.time_entered_water) / self.fadetime
            color = color_blend(self.color, pond.watercolor, factor)
            if factor >= 1.0:
                return False
        pond.canvas.putpixel(self.position, color)
        x, y = self.position
        if y < pond.level_px:
            self.matrix_trail.append((self.position, t))
        return True


    ## Public Interface
    ##
    def update (self, pond, t):
        alive = True
        (x1, y1) = self.position
        (x2, y2) = self.update_position(t)
        if x2 != x1 or y2 != y1: # ledstrip only needs update on change
            if y2 < self.length: # at least part of tail is on strip
                self.draw_on_strip()
        if y2 >= 0 and y2 < pond.height: # matrix
            self.time_entered_water = self.time_entered_water or t
            alive = self.draw_on_matrix(pond, t)
        if alive is False or y2 >= pond.height:
            pond.mobcounter.remove(self)
            return False
        return True

    @staticmethod
    def maybe_spawn (pond, t):
        if t > Rain.last_spawn + 10:
            Rain.last_spawn = t
            droplet = next((x for x in pond.mobs if isinstance(x, Droplet)), None)
            if not droplet:
                return Rain(pond, t)
