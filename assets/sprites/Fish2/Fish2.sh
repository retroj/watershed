#!/bin/sh -e

convert original.png                                            \
        -channel rgb -evaluate multiply 0.3                     \
        -scale 13x7                                             \
        -write png32:Fish2-left.png -flop png32:Fish2-right.png
