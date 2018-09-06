
from watershed import *

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

    def scram (self, t):
        (sx, sy) = self.speed
        direction = -1 if sx < 0 else 1
        self.change_trajectory(t, (direction * 20, sy))
        (x1, _) = self.position
        (sx, _) = self.speed
        x2 = -self.width if direction < 0 else pond.width
        return (x2 - x1) / sx ## time to clear board

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
