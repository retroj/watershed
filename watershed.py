#!/usr/bin/env python3

from time import sleep, time
from random import random, randint
from samplebase import SampleBase
from PIL import Image, ImageDraw


class Sprites ():
    assets = {}

    @staticmethod
    def get (name):
        if not name in Sprites.assets:
            img = Image.open(name)
            r, g, b, a = img.split()
            sprite = Image.merge("RGB", (r, g, b))
            mask = Image.merge("L", (a,))
            width, height = img.width, img.height
            Sprites.assets[name] = (sprite, mask, width, height)
        return Sprites.assets[name]



class Mob ():
    spawn_time = None
    sprite = None
    mask = None
    width = 0
    height = 0

    def __init__ (self, pond, t):
        self.spawn_time = t

    def update (self, pond):
        return True


class Fish (Mob):
    start_x = 0
    x = 0
    y = 0
    direction = 0
    speed = 0

    def __init__ (self, pond, t):
        super(Fish, self).__init__(pond, t)
        self.direction = 1 if random() < 0.5 else -1
        self.speed = random() * 6 + 2
        if self.direction == 1:
            self.sprite, self.mask, self.width, self.height =
                Sprites.get("assets/sprites/Fish1/Fish1-right.png")
        else:
            self.sprite, self.mask, self.width, self.height =
                Sprites.get("assets/sprites/Fish1/Fish1-left.png")
        self.start_x = -self.width if self.direction == 1 else pond.width
        ##XXX: this math can allow the lower level to be above the upper level,
        ##     resulting in an error
        self.y = randint(pond.level_px + self.height * 0.5, pond.height - self.height * 1.5)

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

    @staticmethod
    def maybe_spawn (pond, t):
        if pond.level > 0.5 and pond.health > 0.5 and random() < 0.001:
            print("spawning fish")
            return Fish(pond, t)




class Pond (SampleBase):
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

    def adjust_level (self):
        l = self.level
        rand = random()
        if rand < 0.001:
            sign = 1 if rand >= 0.0005 else -1
            l = l + 1/32.0 * sign
            self.level = max(min(l, 1.0), 0.0)
            self.level_px = int(self.level * -32 + 32)

    def spawn_mobs (self, t):
        f = Fish.maybe_spawn(self, t)
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

            sleep(0.01)


if __name__ == "__main__":
    pond = Pond()
    if (not pond.process()):
        pond.print_help()
