
import os
from PIL import Image

class AssetManager ():
    """
    AssetManager manages a table of images for the sprites. They are
    generated on demand by the first call to the 'get' method. They can be
    files on disk or a 'generate' procedure that creates the Image.
    """
    root = None
    assets = {}

    @staticmethod
    def get (name, generate=None):
        if not name in AssetManager.assets:
            if generate:
                img = generate()
            else:
                if AssetManager.root:
                    path = os.path.join(AssetManager.root, name)
                else:
                    path = name
                img = Image.open(path)
            r, g, b, a = img.split()
            sprite = Image.merge("RGB", (r, g, b))
            mask = Image.merge("L", (a,))
            width, height = img.width, img.height
            AssetManager.assets[name] = (name, sprite, mask, width, height)
        return AssetManager.assets[name]
