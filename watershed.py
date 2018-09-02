#!/usr/bin/env python3

import sys
from math import *
from time import sleep, time
from random import random, randint, getrandbits
from samplebase import SampleBase
from PIL import Image, ImageDraw
from dotstar import Adafruit_DotStar
import Adafruit_GPIO as GPIO
from Adafruit_GPIO.MCP230xx import MCP23017

tau = asin(1.0) * 4 ## not needed if python >= 3.6


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

class LEDStripSection ():
    offset = 0
    length = 0
    direction = 1
    voffset = 0
    vmul = 1
    buffer = None

    def __init__ (self, owner, offset, length, direction, voffset, vmul):
        self.owner = owner
        self.offset = offset
        self.length = length
        self.direction = direction
        self.voffset = voffset
        self.vmul = vmul
        start = offset * 4
        end = start + length * 4
        self.buffer = memoryview(owner.buffer)[start:end]

    def set_pixel (self, i, color):
        i = i * self.vmul + self.voffset
        if i < 0 or i >= self.length:
            return
        if self.direction < 0:
            i = self.length - 1 - i
        i *= 4
        (r, g, b) = color
        self.buffer[i+1:i+4] = bytearray((b, g, r))


class LEDStrip ():
    npixels = 0
    strip = None
    buffer = None
    sections = None

    def __init__ (self, datapin=24, clockpin=25, sections=[]):
        self.npixels = self.calc_npixels(sections)
        self.strip = Adafruit_DotStar(self.npixels, datapin, clockpin)
        self.buffer = bytearray(self.npixels * 4)
        for i in range(0, self.npixels):
            self.buffer[i * 4] = 0xff
        self.sections = {}
        for spec in sections:
            self.add_section(**spec)
        self.strip.begin()

    def calc_npixels (self, sections):
        npixels = 0
        for spec in sections:
            if not "offset" in spec or spec["offset"] is None:
                spec["offset"] = npixels
            npixels = max(npixels, spec["offset"] + spec["length"])
        return npixels

    def add_section (self, name = None, offset = None, length = 0,
                     direction = 1, voffset = 0, vmul = 1):
        self.sections[name] = LEDStripSection(self, offset, length, direction, voffset, vmul)


class AssetManager ():
    """
    AssetManager manages a table of images for the sprites. They are
    generated on demand by the first call to the 'get' method. They can be
    files on disk or a 'generate' procedure that creates the Image.
    """
    assets = {}

    @staticmethod
    def get (name, generate=None):
        if not name in AssetManager.assets:
            if generate:
                img = generate()
            else:
                img = Image.open(name)
            r, g, b, a = img.split()
            sprite = Image.merge("RGB", (r, g, b))
            mask = Image.merge("L", (a,))
            width, height = img.width, img.height
            AssetManager.assets[name] = (name, sprite, mask, width, height)
        return AssetManager.assets[name]



class Mob ():
    """
    Base class for sprites.
    """
    spawn_time = None
    sprite = None
    mask = None
    width = 0
    height = 0
    position = (0, 0)
    start_position = (0, 0)
    speed = (0, 5)
    z = 0

    def __init__ (self, pond, t):
        self.spawn_time = t

    def update (self, pond, t):
        return True

    def update_position (self, t):
        x0, y0 = self.start_position
        sx, sy = self.speed
        dt = t - self.spawn_time
        self.position = (int(x0 + sx * dt), int(y0 + sy * dt))
        return self.position

    @staticmethod
    def init_static ():
        pass


class LEDStripMob (Mob):
    """
    A Mob that exclusively, or also, appears on a LED strip.
    """
    name = "unknown LEDStripMob"
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
        print("spawning "+self.name+" "+str(int(t)))
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
            print("despawning "+self.name)
            return False
        return True

    @staticmethod
    def maybe_spawn (pond, t):
        if t > Rain.last_spawn + 10:
            Rain.last_spawn = t
            return Rain(pond, t)


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
            print("despawning "+self.name)
            return False
        return True

    @staticmethod
    def maybe_spawn (pond, t):
        if t > Rain2.last_spawn + 10:
            Rain2.last_spawn = t
            return Rain2(pond, t)



class Droplet (LEDStripMob):
    name = "unknown droplet"
    start_x = 30
    airspeed = (1.5, 8)
    waterspeed = (1.5, 8)

    def draw_on_matrix (self, pond, t):
        trail_length = len(self.matrix_trail)
        r,g,b = [x / 255.0 for x in self.color]
        for i,((tx,ty),tt) in enumerate(self.matrix_trail):
            if ty < pond.level_px:
                f = i / trail_length * 200 - (t - tt) * 150
                r2, g2, b2 = int(f * r), int(f * g), int(f * b)
                if r2 or g2 or b2:
                    pond.canvas.putpixel((tx, ty), (r2, g2, b2))
        pond.canvas.putpixel(self.position, self.color)
        x, y = self.position
        if y < pond.level_px:
            self.matrix_trail.append((self.position, t))

    ## Public Interface
    ##
    def update (self, pond, t):
        (x1, y1) = self.position
        (x2, y2) = self.update_position(t)
        # if y2 >= pond.level_px:
        #     self.speed = self.waterspeed
        if x2 != x1 or y2 != y1: # ledstrip only needs update on change
            if y2 < self.length: # at least part of tail is on strip
                self.draw_on_strip()
        if y2 >= 0 and y2 < pond.height: # matrix
            self.draw_on_matrix(pond, t)
        if y2 + 1 >= pond.mud.levels[x2] or y2 + 1 >= pond.height:
            ## turn this over to the mud
            print("despawning "+self.name)
            pond.mud.add(self)
            return False
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


class Fish (Mob):
    name = "fish"
    sprites = None
    width = 0
    height = 0
    start_position = (0, 0)
    speed = (0, 5)

    def __init__ (self, pond, t, y, spriteleft, spriteright):
        super(Fish, self).__init__(pond, t)
        direction = bool(getrandbits(1))
        if direction:
            _, self.sprite, self.mask, self.width, self.height = \
                AssetManager.get(spriteright)
            start_x = -self.width
            self.speed = (random() * 6 + 2, 0)
        else:
            _, self.sprite, self.mask, self.width, self.height = \
                AssetManager.get(spriteleft)
            start_x = pond.width
            self.speed = (-(random() * 6 + 2), 0)
        self.start_position = (start_x, y)


    ## Public Interface
    ##
    def update (self, pond, t):
        (x, y) = self.update_position(t)
        (sx, sy) = self.speed
        if sx > 0 and x >= pond.width:
            print("despawning "+self.name)
            return False
        elif sx < 0 and x < -self.width:
            print("despawning "+self.name)
            return False
        pond.canvas.paste(self.sprite, self.position, self.mask)
        return True

    @staticmethod
    def init_static ():
        Fish.sprites = []
        Fish.sprites.append(("fish1", AssetManager.get("assets/sprites/Fish1/Fish1-left.png"),
                             AssetManager.get("assets/sprites/Fish1/Fish1-right.png")))
        Fish.sprites.append(("fish2", AssetManager.get("assets/sprites/Fish2/Fish2-left.png"),
                             AssetManager.get("assets/sprites/Fish2/Fish2-right.png")))

    @staticmethod
    def maybe_spawn (pond, t):
        shortname, left, right  = Fish.sprites[randint(0, len(Fish.sprites)-1)]
        leftname,_,_,_,height = left
        rightname,_,_,_,_ = right
        ymin = pond.level_px + int(height * 0.5)
        ymax = pond.height - int(height * 1.5)
        if random() * pond.health**0.125 < 0.0005 and pond.health > 0.3 and ymin < ymax:
            print("spawning "+shortname)
            return Fish(pond, t, randint(ymin, ymax), leftname, rightname)


class Wave ():
    length = 0
    interval = 0.2
    last_update = 0
    stripsection = None
    tilelength = 16
    tileoffset = 0

    def __init__ (self, stripsection):
        self.stripsection = stripsection
        length = self.stripsection.length
        self.tileoffset = length - 1 % self.tilelength
        for i in range(0, length):
            self.stripsection.set_pixel(i, self.get_color_for_pixel(i))
        buffersize = length * 4
        self.fr = memoryview(self.stripsection.buffer)[4:buffersize]
        self.to = memoryview(self.stripsection.buffer)[0:buffersize - 4]
        self.lst = memoryview(self.stripsection.buffer)[buffersize - 4:]
        last_update = time()

    def get_color_for_pixel (self, i):
        ## to lower the troughs, use a higher exponent.
        norm = (sin(i / self.tilelength * tau) * 0.5 + 0.5) ** 2
        b = int(norm * 255)
        return (0, 0, b)

    def update (self, t):
        if t < self.last_update + self.interval:
            return
        self.last_update = time()
        self.to[:] = self.fr[:]
        self.tileoffset = (self.tileoffset + 1) % self.tilelength
        (r, g, b) = self.get_color_for_pixel(self.tileoffset)
        self.lst[1:] = bytearray((b, g, r))


class Switches (MCP23017):
    last_poll = None
    bindings = None

    def __init__ (self, *args, **kwargs):
        super(Switches, self).__init__(*args, **kwargs)
        self.last_poll = tuple([True for _ in range(0, 16)])
        self.bindings = {}
        for i in range(0, 16):
            self.setup(i, GPIO.IN)
            self.pullup(i, True)

    def poll (self):
        state = self.input_pins(range(0, 16))
        for i,(now,prev) in enumerate(zip(state, self.last_poll)):
            if now is False and prev is True:
                if i in self.bindings:
                    self.bindings[i]()
        self.last_poll = state

    def bind (self, i, thunk):
        self.bindings[i] = thunk


class Mud ():
    lastupdate = time()
    updaterate = 0.75
    value = 0
    levels = None
    canvas = None
    mask = None

    def __init__ (self):
        self.levels = [32] * 64
        self.canvas = Image.new("RGB", (64, 32))
        self.mask = Image.new("1", (64, 32))

    def add (self, droplet):
        x, y = droplet.position
        self.levels[x] = y
        self.canvas.putpixel((x, y), droplet.color)
        self.mask.putpixel((x, y), 255)

    def runphysics (self, pond, t):
        cols = sorted(enumerate(self.levels), key=lambda x: x[1], reverse=True)
        ## we compute the value based on the colors that we find in this
        ## loop. it's not elegant but it's simple and straightforward.
        value = 0
        for x,level in cols:
            sp = None
            newlevel = level
            for y in range(31, level - 1, -1):
                c = self.canvas.getpixel((x, y))
                if c == (0,0,0):                 ## space
                    sp = y ## if multiple spaces, this will be the top one
                else:                            ## droplet
                    if random() < 0.002: ## random decay
                        ## make a hole but don't fill it in this frame
                        self.canvas.putpixel((x, y), (0, 0, 0))
                        self.mask.putpixel((x, y), 0)
                        newlevel = y + 1
                    elif sp is not None: ## fall down
                        value += 1 if c == (0, 0, 0xff) else -1
                        self.canvas.putpixel((x, y), (0, 0, 0))
                        self.mask.putpixel((x, y), 0)
                        self.canvas.putpixel((x, y + 1), c)
                        self.mask.putpixel((x, y + 1), 255)
                        sp = y
                        newlevel = y + 1
                    else: ## fall diagonally
                        value += 1 if c == GoodDroplet.color else -1
                        left = x > 0 and self.levels[x - 1] > y + 1
                        right = x < 63 and self.levels[x + 1] > y + 1
                        if left and right:
                            left = left and bool(getrandbits(1))
                        y2 = y + 1
                        if left:
                            x2 = x - 1
                        elif right:
                            x2 = x + 1
                        else:
                            newlevel = y
                            continue
                        self.canvas.putpixel((x, y), (0, 0, 0))
                        self.mask.putpixel((x, y), 0)
                        self.canvas.putpixel((x2, y2), c)
                        self.mask.putpixel((x2, y2), 255)
                        self.levels[x2] = y2
                        sp = y
                        newlevel = y + 1
            self.levels[x] = newlevel
        self.value = value

    def draw (self, pond, t):
        if t >= self.lastupdate + self.updaterate:
            self.runphysics(pond, t)
            self.lastupdate = t
        pond.canvas.paste(self.canvas, (0, 0), self.mask)


class Pond (SampleBase):
    ## config
    healthsteps = 10
    active_spawners = [Fish, Rain]

    ## internal
    mud = None
    ledstrip = None
    switches = None
    width = 0
    height = 0
    canvas = None
    health = 1.0
    watercolor = None
    level = 0.7
    level_px = 0
    mobs = None
    resetstart = None

    def __init__ (self, *args, **kwargs):
        super(Pond, self).__init__(*args, **kwargs)
        self.mud = Mud()
        for spawner in self.active_spawners:
            spawner.init_static()
        self.mobs = []
        self.switches = Switches(address = 0x20)
        self.switches.bind(5, lambda: self.reset())
        self.switches.bind(6, lambda: GoodDroplet.spawn(self, time()))
        self.switches.bind(7, lambda: BadDroplet.spawn(self, time()))
        self.ledstrip = LEDStrip(
            datapin=24, clockpin=25,
            ## single strip
            sections=[{ "name": "wave", "length": 37, "direction": -1 },
                      { "name": "rain", "length": 37, "direction": -1,
                        "voffset": -1, "vmul": -1 },
                      { "name": "gooddroplet", "length": 37, "direction": 1,
                        "voffset": -1, "vmul": -1 },
                      { "name": "baddroplet", "length": 37, "direction": -1,
                        "voffset": -1, "vmul": -1 }])
            ## full
            # sections=[{ "name": "wave", "length": 37, "direction": -1 },
            #           { "name": "rain", "length": 37, "direction": -1,
            #             "voffset": -1, "vmul": -1 },
            #           { "name": "gooddroplet", "offset": 150, "length": 65, "direction": 1,
            #             "voffset": -1, "vmul": -1 },
            #           { "name": "baddroplet", "offset": 215, "length": 66, "direction": -1,
            #             "voffset": -1, "vmul": -1 }])
        self.wave = Wave(self.ledstrip.sections["wave"])

    def reset (self):
        print("reset requested")
        self.resetstart = time()

    def add_mob (self, m):
        z = m.z
        i = next((i for i,x in enumerate(self.mobs) if x.z > z), len(self.mobs))
        self.mobs.insert(i, m)

    def adjust_level (self):
        l = self.level
        rand = random()
        threshold = 0.0001
        if rand < threshold:
            sign = 1 if rand >= threshold * 0.5 else -1
            l = l + 1/32.0 * sign
            self.level = max(min(l, 0.9), 0.4)
            self.level_px = int(self.level * -32 + 32)

    def spawn_mobs (self, t):
        for x in self.active_spawners:
            f = x.maybe_spawn(self, t)
            if f:
                self.add_mob(f)

    def draw_bg (self):
        """draw the pond onto self.canvas up to the level represented by self.level"""
        self.health = max(0.0, min(1.0, (self.healthsteps + self.mud.value) / self.healthsteps))
        healthycolor = (0x11, 0x22, 0x44)
        pollutedcolor = (0x66, 0x66, 0)
        self.watercolor = [int((a - b) * self.health + b)
                           for a,b in zip(healthycolor, pollutedcolor)]
        colorname = "rgb({},{},{})".format(*self.watercolor)
        w, h = self.width, self.height
        level_px = int(self.level * -32 + 32)
        self.draw.rectangle((0,0,w-1,level_px-1), "#000000")
        self.draw.rectangle((0,level_px,w-1,h-1), colorname)

    def draw_mobs (self, t):
        self.mobs = [mob for mob in self.mobs if mob.update(self, t)]

    def mode_gameplay (self, t):
        ##XXX: what if another mode wants different bindings?
        self.switches.poll()

        ## compute state
        ##
        self.adjust_level()
        self.spawn_mobs(t)

        ## draw internal canvas
        ##
        self.draw_bg()
        self.mud.draw(self, t)
        self.draw_mobs(t)

    def run (self):
        double_buffer = self.matrix.CreateFrameCanvas()
        self.width = double_buffer.width
        self.height = double_buffer.height
        self.canvas = Image.new("RGB", (self.width, self.height))
        self.draw = ImageDraw.Draw(self.canvas)
        self.level_px = int(self.level * -32 + 32)

        while True:
            t = time()

            ##XXX: this will call 'current_mode' in order to support reset
            ##     and perhaps other modes like startup.
            self.mode_gameplay(t)

            ## write canvas to matrix
            ##
            double_buffer.SetImage(self.canvas)
            double_buffer = self.matrix.SwapOnVSync(double_buffer)

            ## write led strip
            ##
            self.wave.update(t) ##XXX: maybe also need modes for the led strip
            self.ledstrip.strip.show(self.ledstrip.buffer)

            sleep(0.01)


if __name__ == "__main__":
    with open("config.py") as f:
        code = compile(f.read(), "config.py", 'exec')
        exec(code)
    pond = Pond()
    try:
        if (not pond.process()):
            pond.print_help()
    except KeyboardInterrupt:
        print("Exiting\n")
        pond.ledstrip.strip.clear()
        pond.ledstrip.strip.show()
        sys.exit(0)
