#!/usr/bin/env python3

import os, sys
from math import *
from time import sleep, time
from random import random, randint, getrandbits
from rgbmatrix import RGBMatrix, RGBMatrixOptions
from PIL import Image, ImageDraw
try:
    from dotstar import Adafruit_DotStar
except:
    from mocks import Adafruit_DotStar
try:
    import Adafruit_GPIO as GPIO
except:
    from mocks import GPIO
try:
    from Adafruit_GPIO.MCP230xx import MCP23017
except:
    from mocks import MCP23017
from AssetManager import AssetManager

version = (1, 0, 0)

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
    datapin = 24
    clockpin = 25
    npixels = 0
    strip = None
    buffer = None
    sections_spec = []
    sections = None

    def __init__ (self):
        self.npixels = self.calc_npixels(self.sections_spec)
        self.strip = Adafruit_DotStar(self.npixels, self.datapin, self.clockpin)
        self.buffer = bytearray(self.npixels * 4)
        for i in range(0, self.npixels):
            self.buffer[i * 4] = 0xff
        self.sections = {}
        for spec in self.sections_spec:
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


class Mob ():
    """
    Base class for sprites.
    """
    sprite = None
    mask = None
    width = 0
    height = 0
    position = (0, 0)
    start_position = (0, 0)
    start_position_time = None
    speed = (0, 5)
    z = 0

    def __init__ (self, pond, t):
        self.start_position_time = t

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
    name = "unknown droplet"
    start_x = 30
    airspeed = (1.5, 8)
    waterspeed = (1.5, 8)
    trailfadetime = 0.8

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


class Switches ():
    ## config
    ##
    i2c_address = 0x20
    throttle = 0.5

    ## internal
    ##
    ioexpander = None
    last_init_attempt = time()
    last_poll = None
    bindings = None
    last_press = time()

    def __init__ (self):
        self.last_poll = tuple([True for _ in range(0, 16)])
        self.bindings = {}
        self.ioexpander = MCP23017(address = self.i2c_address)
        for i in range(0, 16):
            self.ioexpander.setup(i, GPIO.IN)
            self.ioexpander.pullup(i, True)

    def poll (self, t):
        try:
            state = self.ioexpander.input_pins(range(0, 16))
        except OSError as e:
            raise GameError("switches.poll failed", (0x33, 0x11, 0))
        for i,(now,prev) in enumerate(zip(state, self.last_poll)):
            if now is False and prev is True and self.last_press < t - self.throttle:
                self.last_press = t
                if i in self.bindings:
                    self.bindings[i]()
        self.last_poll = state

    def bind (self, i, thunk):
        self.bindings[i] = thunk

    def clearbindings (self):
        self.bindings = {}


class Mud ():
    ## config
    update_rate = 0.75
    decay = None

    ## internal
    lastupdate = time()
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
        if y >= 0:
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
            for y in range(31, max(0, level - 1), -1):
                c = self.canvas.getpixel((x, y))
                if c == (0,0,0):                 ## space
                    sp = y ## if multiple spaces, this will be the top one
                else:                            ## droplet
                    if self.decay and random() < self.decay: ## random decay
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
        if t >= self.lastupdate + self.update_rate:
            self.runphysics(pond, t)
            self.lastupdate = t
        pond.canvas.paste(self.canvas, (0, 0), self.mask)


class Mode ():
    pond = None

    def __init__ (self, pond):
        self.pond = pond
        pond.switches.clearbindings()
        pond.switches.last_press = time()


class ModeGameplay (Mode):
    auto_reset = None

    def __init__ (self, pond):
        super(ModeGameplay, self).__init__(pond)
        print("Mode: Gameplay")
        pond.set_level(pond.initial_level)
        pond.switches.bind(5, lambda: self.reset())
        pond.switches.bind(6, lambda: GoodDroplet.spawn(pond, time()))
        pond.switches.bind(7, lambda: BadDroplet.spawn(pond, time()))

    def reset (self):
        pond = self.pond
        pond.current_mode = ModeReset(pond)

    def adjust_level (self):
        pond = self.pond
        l = pond.level
        rand = random()
        threshold = 0.0001
        if rand < threshold:
            sign = 1 if rand >= threshold * 0.5 else -1
            l = l + 1/32.0 * sign
            pond.set_level(max(min(l, 0.9), 0.4))

    def runframe (self, t):
        pond = self.pond
        try:
            pond.switches.poll(t)
        except GameError as e:
            pond.error = e
            print(e)

        if self.auto_reset and t >= pond.switches.last_press + self.auto_reset:
            pond.current_mode = ModeReset(pond)

        ## compute state
        ##
        self.adjust_level()
        pond.spawn_mobs(t)

        ## draw internal canvas
        ##
        pond.draw_bg()
        pond.mud.draw(pond, t)
        pond.draw_mobs(t)


class ModeStartGame (Mode):
    start_time = None

    def __init__ (self, pond):
        super(ModeStartGame, self).__init__(pond)
        print("Mode: StartGame")
        t = time()
        self.start_time = t
        pond.health = 1.0
        pond.mud = Mud()


    def runframe (self, t):
        pond = self.pond

        ## fill the pond
        ##
        pond.set_level((t - self.start_time) / 5 * pond.initial_level)
        if pond.level >= pond.initial_level:
            pond.current_mode = ModeGameplay(pond)

        ## draw internal canvas
        ##
        pond.draw_bg()
        pond.mud.draw(pond, t)
        pond.draw_mobs(t)



class ModeReset (Mode):
    start_time = None
    board_clear_time = None
    pond_start_level = None
    lower_level_last_time = time()

    def __init__ (self, pond):
        super(ModeReset, self).__init__(pond)
        print("Mode: Reset")
        t = time()
        self.start_time = t
        scramtime = 0
        for mob in pond.mobs:
            scramtime = max(scramtime, mob.scram(pond, t))
        self.board_clear_time = self.start_time + scramtime

    def runframe (self, t):
        pond = self.pond

        ## drain the pond (sorry, fish!)
        ##
        if t >= self.board_clear_time:
            self.pond_start_level = self.pond_start_level or pond.level
            drain_duration = self.pond_start_level * 5
            pond.set_level(self.pond_start_level - \
                ((t - self.board_clear_time) / drain_duration * self.pond_start_level))
            if pond.level_px >= pond.height:
                pond.current_mode = ModeStartGame(pond)

        ## draw internal canvas
        ##
        pond.draw_bg()
        pond.mud.draw(pond, t)
        pond.draw_mobs(t)


class Pond ():
    ## config
    healthsteps = 10
    active_spawners = []
    initial_level = 0.7

    ## internal
    matrix = None
    mud = None
    ledstrip = None
    switches = None
    width = 0
    height = 0
    canvas = None
    health = 1.0
    watercolor = None
    level = 0
    level_px = 0
    mobs = None
    current_mode = None

    def __init__ (self, *args, **kwargs):
        super(Pond, self).__init__(*args, **kwargs)
        for spawner in self.active_spawners:
            spawner.init_static()
        self.mobs = []
        self.switches = Switches()
        self.ledstrip = LEDStrip()
        self.wave = Wave(self.ledstrip.sections["wave"])
        self.current_mode = ModeStartGame(self)

    def log_status (self):
        print("[h:{:4.2f}] {}".format(
            self.health,
            " ".join([x.name for x in self.mobs])))

    def add_mob (self, m):
        z = m.z
        i = next((i for i,x in enumerate(self.mobs) if x.z > z), len(self.mobs))
        self.mobs.insert(i, m)

    def set_level (self, level):
        self.level = level
        self.level_px = int(self.level * -32 + 32)

    def spawn_mobs (self, t):
        newmobs = False
        for x in self.active_spawners:
            f = x.maybe_spawn(self, t)
            if f:
                newmobs = True
                self.add_mob(f)
        if newmobs:
            self.log_status()

    def draw_bg (self):
        """draw the pond onto self.canvas up to the level represented by self.level"""
        self.health = max(0.0, min(1.0, (self.healthsteps + self.mud.value) / self.healthsteps))
        healthycolor = (0x11, 0x22, 0x44)
        pollutedcolor = (0x66, 0x66, 0)
        self.watercolor = [int((a - b) * self.health + b)
                           for a,b in zip(healthycolor, pollutedcolor)]
        colorname = "rgb({},{},{})".format(*self.watercolor)
        w, h = self.width, self.height
        self.draw.rectangle((0,0,w-1,self.level_px-1), "#000000")
        self.draw.rectangle((0,self.level_px,w-1,h-1), colorname)

    def draw_mobs (self, t):
        nmobs = len(self.mobs)
        self.mobs = [mob for mob in self.mobs if mob.update(self, t)]
        if nmobs != len(self.mobs):
            self.log_status()

    def run (self):
        options = RGBMatrixOptions()
        options.rows = 32
        options.cols = 64
        options.chain_length = 1
        options.parallel = 1
        options.row_address_type = 0
        options.multiplexing = 0
        options.pwm_bits = 11
        options.brightness = 100
        options.pwm_lsb_nanoseconds = 130
        options.led_rgb_sequence = "RGB"
        self.matrix = RGBMatrix(options = options)

        double_buffer = self.matrix.CreateFrameCanvas()
        self.width = double_buffer.width
        self.height = double_buffer.height
        self.canvas = Image.new("RGB", (self.width, self.height))
        self.draw = ImageDraw.Draw(self.canvas)
        self.set_level(self.level)

        while True:
            self.error = None
            t = time()

            self.current_mode.runframe(t)

            ## if there was an error, set visual indicator
            if self.error:
                self.canvas.putpixel((63, 0), self.error.color)

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
    selfdir = os.path.dirname(__file__)
    AssetManager.root = selfdir
    argc = len(sys.argv)
    if argc != 2:
        print("Usage: watershed.py <config>")
        sys.exit(1)
    configpath = sys.argv[1]
    with open(configpath) as f:
        code = compile(f.read(), configpath, 'exec')
        exec(code)
    pond = Pond()
    try:
        pond.run()
    except KeyboardInterrupt:
        print("Exiting\n")
        pond.ledstrip.strip.clear()
        pond.ledstrip.strip.show()
        sys.exit(0)
