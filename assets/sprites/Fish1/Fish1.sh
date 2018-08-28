#!/bin/sh

# convert -density 3 -background none Fish1.svg \
#         -evaluate multiply 0.4 \
#         -write Fish1-left.png -flop Fish1-right.png

magick `: use morphology to make black edge pixels`        \
        -density 3 -background black Fish1.svg             \
        -bordercolor black -border 1 -white-threshold 0    \
        -morphology edgein disk:1                          \
        -channel rgb -negate +channel -transparent white   \
                                                           \
        `: compose another copy of the fish over the edge` \
        -background none Fish1.svg                         \
        -gravity center -compose over -composite           \
                                                           \
        `: darken the whole image a bit`                   \
        -channel rgb -evaluate multiply 0.4                \
                                                           \
        `: save left-facing and right-facing versions`     \
        -write Fish1-left.png -flop Fish1-right.png


## this one no longer looks like a fish. resizing is not the way.
##
# convert -density 300 -background none Fish1.svg \
#         -channel rgb -white-threshold 0 \
#         -morphology edgein disk:60 \
#         -background black -flatten -negate \
#         -fuzz 50% -transparent white \
#         -background none Fish1.svg +swap -compose over -composite \
#         -resize 1% \
#         -write Fish1-left.png -flop Fish1-right.png
