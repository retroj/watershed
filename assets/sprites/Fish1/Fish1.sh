#!/bin/sh

convert -density 3 -background none Fish1.svg \
        -evaluate multiply 0.4 \
        -write png32:Fish1-left.png -flop png32:Fish1-right.png
