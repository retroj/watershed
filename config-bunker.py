
from Rain import Rain
from Fish import Fish
from Bubbles import Bubbles

Switches.i2c_address = 0x20
Switches.throttle = 0.5

LEDStrip.datapin = 24
LEDStrip.clockpin = 25

LEDStrip.sections_spec = [
    { "name": "wave", "length": 80, "direction": -1 },
    { "name": "rain", "length": 121, "direction": 1,
      "voffset": -1, "vmul": -1 },
    { "name": "gooddroplet", "length": 65, "direction": -1,
      "voffset": -1, "vmul": -1 },
    { "name": "baddroplet", "length": 66, "direction": 1,
      "voffset": -1, "vmul": -1 }]

Pond.healthsteps = 120
Pond.active_spawners = [Fish, Rain, Bubbles]
Pond.initial_level = 0.7

Mud.update_rate = 0.5
# Mud.decay = 0.002

Rain.length = 7
Rain.color = (0, 0, 0xff)
Rain.start_x = 0
Rain.airspeed = (1.5, 8)
Rain.waterspeed = (1.5, 8)
Rain.fadetime = 3.5

Droplet.trailfadetime = 2.0

GoodDroplet.length = 7
GoodDroplet.color = (0, 0, 0xcc)
GoodDroplet.start_x = 20
GoodDroplet.airspeed = (1.5, 16)
GoodDroplet.waterspeed = (1.5, 12)

BadDroplet.length = 7
BadDroplet.color = (0x66, 0, 0)
BadDroplet.start_x = 48
BadDroplet.airspeed = (-1.5, 16)
BadDroplet.waterspeed = (-1.5, 12)

## how many seconds after a switch is pressed to reset the game (None to disable)
ModeGameplay.auto_reset = None
