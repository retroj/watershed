#!/bin/sh

convert -density 3 -background none Fish1.svg \
        -evaluate multiply 0.4 \
        -write Fish1-left.png -flop Fish1-right.png
