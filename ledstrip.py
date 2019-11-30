
try:
    from dotstar import Adafruit_DotStar
except:
    from mocks import Adafruit_DotStar


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
