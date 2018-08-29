#!/bin/sh -e

convert `: use morphology to make black edge pixels`        \
         -density 3 -background black Fish1.svg             \
         -bordercolor black -border 2 -white-threshold 0    \
         -morphology dilate disk:0.5                        \
         -channel rgb -negate +channel -transparent white   \
         -channel a -evaluate multiply 0.6                  \
                                                            \
         `: compose another copy of the fish over the edge` \
         -background none Fish1.svg                         \
         -gravity center -compose over -composite           \
                                                            \
         `: darken the whole image a bit`                   \
         -channel rgb -evaluate multiply 0.4                \
                                                            \
         -trim +repage                                      \
                                                            \
         `: save left-facing and right-facing versions`     \
          -write Fish1-left.png -flop Fish1-right.png
