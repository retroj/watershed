
from watershed import *

class Rain2 (LEDStripMob):
    """
    A version of Rain that the trail go all the way down into the water.
    """
    name = "rain"
    last_spawn = time()
    color = (0, 0, 0xff)
    start_x = 10
    airspeed = (1.5, 8)
    waterspeed = (1.5, 8)
    z = -1
    fadetime = 2.8
    trailfadetime = 0.8
    time_entered_water = None

    def draw_on_matrix (self, pond, t):
        trail_length = len(self.matrix_trail)
        stilldrawing = False

        ## trail
        for i,((tx,ty),tt) in enumerate(self.matrix_trail):
            factor = (t - tt) / self.trailfadetime
            if factor < 1.0:
                stilldrawing = True
                tcolor = color_blend(self.color, pond.watercolor, factor)
                pond.canvas.putpixel((tx, ty), tcolor)

        ##XXX: we may still need to draw the trail, but do we need to draw
        ##     the lead pixel?

        ## lead pixel
        if self.time_entered_water is None:
            color = self.color
            factor = 0.0
        else:
            factor = (t - self.time_entered_water) / self.fadetime
            color = color_blend(self.color, pond.watercolor, factor)
        if factor < 1.0:
            stilldrawing = True
            pond.canvas.putpixel(self.position, color)
            x, y = self.position
            #if y < pond.level_px:
            self.matrix_trail.append((self.position, t))
        return stilldrawing


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
        if t > Rain2.last_spawn + 10:
            Rain2.last_spawn = t
            return Rain2(pond, t)
