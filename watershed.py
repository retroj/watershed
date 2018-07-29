#!/usr/bin/env python3

import sys
from time import sleep, time
from random import random, randint, getrandbits
from samplebase import SampleBase
from PIL import Image, ImageDraw
from dotstar import Adafruit_DotStar
import Adafruit_GPIO as GPIO
from Adafruit_GPIO.MCP230xx import MCP23017

## constants for LEDStrip colors
GREEN = 65536
RED = 256
BLUE = 1

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
            AssetManager.assets[name] = (sprite, mask, width, height)
        return AssetManager.assets[name]



class Mob ():
    spawn_time = None
    sprite = None
    mask = None
    width = 0
    height = 0
    x = 0
    y = 0

    def __init__ (self, pond, t):
        self.spawn_time = t

    def update (self, pond, t):
        return True

    @staticmethod
    def init_static ():
        pass


class LEDStripMob (Mob):
    stripsection = None
    color = (0, 0, 0)
    length = 7 ## length of pollution on strip
    start_position = (0, 0)
    speed = (0, 5)

    def __init__ (self, pond, t):
        super(LEDStripMob, self).__init__(pond, t)

    def update_coords (self, t):
        x0, y0 = self.start_position
        sx, sy = self.speed
        dt = t - self.spawn_time
        x = int(x0 + sx * dt)
        y = int(y0 + sy * dt)
        if x == self.x and y == self.y:
            return False
        else:
            self.x = x
            self.y = y
            return True

    def dim_color (self, color, dim):
        (r, g, b) = color
        return (int(r * dim), int(g * dim), int(b * dim))

    def draw_on_strip (self):
        s = self.stripsection
        for i in range(0, self.length):
            dim = (self.length - i) / self.length
            c = self.dim_color(self.color, dim)
            s.set_pixel(self.y - i, c)
        s.set_pixel(self.y - self.length, (0, 0, 0))


class Rain (LEDStripMob):
    last_spawn = time()
    color = (0, 0, 0xff)

    def __init__ (self, pond, t):
        super(Rain, self).__init__(pond, t)
        print("spawning rain "+str(int(t)))
        self.stripsection = pond.ledstrip.sections["rain"]
        self.start_position = (20, -(self.stripsection.length))

    ## Public Interface
    ##
    @staticmethod
    def maybe_spawn (pond, t):
        if t > Rain.last_spawn + 10:
            Rain.last_spawn = t
            return Rain(pond, t)

    def update (self, pond, t):
        if self.update_coords(t):
            if self.y < self.length: # at least part of tail is on strip
                self.draw_on_strip()
        if self.y >= self.length:
            print("despawning rain")
            return False
        return True


class Mana (LEDStripMob):
    last_spawn = time()
    color = (0, 0, 0xff)

    def __init__ (self, pond, t):
        super(Mana, self).__init__(pond, t)
        print("spawning mana "+str(int(t)))
        self.stripsection = pond.ledstrip.sections["mana"]
        self.start_position = (30, -(self.stripsection.length))

    ## Public Interface
    ##
    @staticmethod
    def maybe_spawn (pond, t):
        if t > Mana.last_spawn + 10:
            Mana.last_spawn = t
            return Mana(pond, t)

    def update (self, pond, t):
        if self.update_coords(t):
            if self.y < self.length: # at least part of tail is on strip
                self.draw_on_strip()
        if self.y >= self.length:
            print("despawning mana")
            return False
        return True


class Pollution (LEDStripMob):
    last_spawn = time()
    color = (0xff, 0, 0)
    speed = (-0.2, 5)

    def __init__ (self, pond, t):
        super(Pollution, self).__init__(pond, t)
        print("spawning pollution "+str(int(t)))
        self.sprite, self.mask, self.width, self.height = \
            AssetManager.get("Pollution", Pollution.draw_sprite)
        self.stripsection = pond.ledstrip.sections["pollution"]
        self.start_position = (40, -(self.stripsection.length))

    @staticmethod
    def draw_sprite ():
        img = Image.new("RGBA", (3, 3))
        draw = ImageDraw.Draw(img)
        draw.ellipse((0,0,2,2), fill=(255,0,0))
        return img

    ## Public Interface
    ##
    @staticmethod
    def maybe_spawn (pond, t):
        if t > Pollution.last_spawn + 10:
            Pollution.last_spawn = t
            return Pollution(pond, t)

    @staticmethod
    def definitely_spawn (pond, t):
        pond.mobs.append(Pollution(pond, t))

    def update (self, pond, t):
        if self.update_coords(t):
            if self.y < self.length: # at least part of tail is on strip
                self.draw_on_strip()
        if self.y >= 0 and self.y < 32: # matrix
            #pond.canvas.paste(self.sprite, (32, 16), self.mask)
            pond.canvas.putpixel((self.x, self.y), self.color)
        if self.y >= 31:
            return False
        return True


class Fish (Mob):
    width = 0
    height = 0
    start_position = (0, 0)
    speed = (0, 5)

    def __init__ (self, pond, t, y):
        super(Fish, self).__init__(pond, t)
        direction = bool(getrandbits(1))
        if direction:
            self.sprite, self.mask, self.width, self.height = \
                AssetManager.get("assets/sprites/Fish1/Fish1-right.png")
            start_x = -self.width
            self.speed = (random() * 6 + 2, 0)
        else:
            self.sprite, self.mask, self.width, self.height = \
                AssetManager.get("assets/sprites/Fish1/Fish1-left.png")
            start_x = pond.width
            self.speed = (-(random() * 6 + 2), 0)
        self.start_position = (start_x, y)


    ## Public Interface
    ##
    @staticmethod
    def init_static ():
        _, _, Fish.width, Fish.height = \
            AssetManager.get("assets/sprites/Fish1/Fish1-right.png")

    @staticmethod
    def maybe_spawn (pond, t):
        ymin = pond.level_px + Fish.height * 0.5
        ymax = pond.height - Fish.height * 1.5
        if random() * pond.health < 0.001 and pond.health > 0.3 and ymin < ymax:
            print("spawning fish")
            return Fish(pond, t, randint(ymin, ymax))

    def update (self, pond, t):
        (x0, y0) = self.start_position
        (sx, sy) = self.speed
        dt = t - self.spawn_time
        self.x = int(x0 + sx * dt)
        self.y = int(y0 + sy * dt)
        if sx > 0 and self.x >= pond.width:
            print("despawning fish")
            return False
        elif sx < 0 and self.x < -self.width:
            print("despawning fish")
            return False
        pond.canvas.paste(self.sprite, (self.x, self.y), self.mask)
        return True


class Wave ():
    interval = 0.2
    last_update = 0
    owner = None
    stripsection = None
    buffersize = 0
    tmp = None

    def __init__ (self, owner):
        self.owner = owner
        self.stripsection = owner.ledstrip.sections["wave"]
        length = self.stripsection.length
        offset = self.stripsection.offset
        for i in range(0, length):
            color = (0, 0, 255 if i % 4 == 0 else 0)
            self.stripsection.set_pixel(i, color)
        self.buffersize = length * 4
        self.tmp = bytearray(4)
        self.fst = memoryview(self.stripsection.buffer)[0:4]
        self.fr = memoryview(self.stripsection.buffer)[4:self.buffersize]
        self.to = memoryview(self.stripsection.buffer)[0:self.buffersize - 4]
        self.lst = memoryview(self.stripsection.buffer)[self.buffersize - 4:]
        last_update = time()

    def update (self, t):
        if t < self.last_update + self.interval:
            return
        self.last_update = time()
        self.tmp[:] = self.fst[:]
        self.to[:] = self.fr[:]
        self.lst[:] = self.tmp[:]


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


class Pond (SampleBase):
    active_spawners = [Fish, Rain, Mana]
    ledstrip = None
    switches = None
    width = 0
    height = 0
    canvas = None
    health = 1.0
    level = 0.7
    level_px = 0
    mobs = None

    def __init__ (self, *args, **kwargs):
        super(Pond, self).__init__(*args, **kwargs)
        for spawner in self.active_spawners:
            spawner.init_static()
        self.mobs = []
        self.switches = Switches(address = 0x20)
        self.switches.bind(7, lambda: Pollution.definitely_spawn(self, time()))
        self.ledstrip = LEDStrip(
            datapin=24, clockpin=25,
            sections=[{ "name": "wave", "length": 37, "direction": -1 },
                      { "name": "rain", "length": 37, "direction": -1,
                        "voffset": -1, "vmul": -1 },
                      { "name": "mana", "length": 37, "direction": 1,
                        "voffset": -1, "vmul": -1 },
                      { "name": "pollution", "length": 37, "direction": -1,
                        "voffset": -1, "vmul": -1 }])
        self.wave = Wave(self)

    def adjust_level (self):
        l = self.level
        rand = random()
        threshold = 0.001
        if rand < threshold:
            sign = 1 if rand >= threshold * 0.5 else -1
            l = l + 1/32.0 * sign
            self.level = max(min(l, 0.9), 0.4)
            self.level_px = int(self.level * -32 + 32)
            print("level: {}     px: {}".format(self.level, self.level_px))

    def spawn_mobs (self, t):
        for x in self.active_spawners:
            f = x.maybe_spawn(self, t)
            if f:
                self.mobs.append(f)

    def draw_bg (self):
        """draw the pond onto self.canvas up to the level represented by self.level"""
        w, h = self.width, self.height
        level_px = int(self.level * -32 + 32)
        self.draw.rectangle((0,0,w-1,level_px-1), "#000033")
        self.draw.rectangle((0,level_px,w-1,h-1), "#0000aa")

    def draw_mobs (self, t):
        self.mobs = [mob for mob in self.mobs if mob.update(self, t)]

    def run (self):
        double_buffer = self.matrix.CreateFrameCanvas()
        self.width = double_buffer.width
        self.height = double_buffer.height
        self.canvas = Image.new("RGB", (self.width, self.height))
        self.draw = ImageDraw.Draw(self.canvas)

        while True:
            t = time()

            self.switches.poll()

            ## compute state
            ##
            self.adjust_level()
            self.spawn_mobs(t)

            ## draw internal canvas
            ##
            self.draw_bg()
            self.draw_mobs(t)

            ## write canvas to matrix
            ##
            double_buffer.SetImage(self.canvas)
            double_buffer = self.matrix.SwapOnVSync(double_buffer)

            ## write led strip
            ##
            self.wave.update(t)
            self.ledstrip.strip.show(self.ledstrip.buffer)

            sleep(0.01)


if __name__ == "__main__":
    pond = Pond()
    try:
        if (not pond.process()):
            pond.print_help()
    except KeyboardInterrupt:
        print("Exiting\n")
        pond.ledstrip.strip.clear()
        pond.ledstrip.strip.show()
        sys.exit(0)
