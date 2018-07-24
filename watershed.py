#!/usr/bin/env python3

import sys
from time import sleep, time
from random import random, randint
from samplebase import SampleBase
from PIL import Image, ImageDraw
from dotstar import Adafruit_DotStar

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

    def update (self, pond, t):
        if self.update_coords(t):
            if self.y < self.length: # at least part of tail is on strip
                self.draw_on_strip()
        if self.y >= 0: # matrix
            #pond.canvas.paste(self.sprite, (32, 16), self.mask)
            pond.canvas.putpixel((self.x, self.y), self.color)
        if self.y >= 31:
            return False
        return True


class Fish (Mob):
    start_x = 0
    direction = 0
    speed = 0

    def __init__ (self, pond, t):
        super(Fish, self).__init__(pond, t)
        self.direction = 1 if random() < 0.5 else -1
        self.speed = random() * 6 + 2
        if self.direction == 1:
            self.sprite, self.mask, self.width, self.height = \
                AssetManager.get("assets/sprites/Fish1/Fish1-right.png")
        else:
            self.sprite, self.mask, self.width, self.height = \
                AssetManager.get("assets/sprites/Fish1/Fish1-left.png")
        self.start_x = -self.width if self.direction == 1 else pond.width
        ##XXX: this math can allow the lower level to be above the upper level,
        ##     resulting in an error
        self.y = randint(pond.level_px + self.height * 0.5, pond.height - self.height * 1.5)


    ## Public Interface
    ##
    @staticmethod
    def maybe_spawn (pond, t):
        if pond.level > 0.5 and pond.health > 0.5 and random() < 0.001:
            print("spawning fish")
            return Fish(pond, t)

    def update (self, pond, t):
        self.x = int(self.start_x + self.speed * self.direction * (t - self.spawn_time))
        if self.direction == 1 and self.x >= pond.width:
            print("despawning fish")
            return False
        elif self.direction == -1 and self.x < -self.width:
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


class Pond (SampleBase):
    ledstrip = None
    width = 0
    height = 0
    canvas = None
    health = 1.0
    level = 0.7
    level_px = 0
    mobs = None

    def __init__ (self, *args, **kwargs):
        super(Pond, self).__init__(*args, **kwargs)
        self.mobs = []
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
        if rand < 0.001:
            sign = 1 if rand >= 0.0005 else -1
            l = l + 1/32.0 * sign
            self.level = max(min(l, 1.0), 0.0)
            self.level_px = int(self.level * -32 + 32)

    def spawn_mobs (self, t):
        for x in [Fish, Rain, Mana, Pollution]:
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
