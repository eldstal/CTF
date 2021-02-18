#!/usr/bin/env python3
# Try out the various transitions that the fancy frontend uses

import time

from asciimatics.screen import Screen
from asciimatics.scene import Scene
from asciimatics.effects import Cycle
from asciimatics.renderers import FigletText
from asciimatics.exceptions import ResizeScreenError

from tabulate import tabulate

from frontend.animation.wipe import *
from frontend.animation.util import *
from frontend.animation.display import *


# Draw some dummy text for a transition to wipe
def draw_background(screen):
    table = [
        [ "#",   "🏆",  "SCORE",  "TEAM" ],
        [ "1",   " ",  "1337",   "Belschnickel" ],
        [ "2",   " ",  "1200",   "k6" ],
        [ "3",   "^",  "337",    "Kenny's Krew" ],
        [ "4",   "v",  "50",     "RymdensHjalmar" ],
        [ "5",   " ",  "1",      "KurwaBlyat" ],
    ]

    txt = tabulate(table)
    lines = txt.split("\n")

    w = max(len(r) for r in lines)
    h = len(lines)

    H,W = screen.dimensions

    x0 = (W - w) // 2
    y0 = (H - h) // 2

    for y in range(h):
        screen.print_at(lines[y], x0, y0+y, transparent=True)

def draw_func(screen):

    team = { "team_id": "rhj", "name": "RymdensHjalmar", "score": "50", "place": 4 }
    chall = { "challenge_id": "bbyrop", "name": "babyROP", "points": "500" }

    effect_chains = [
                #[RainbowWipe(screen, 15)],
                #[ NoiseWipe(screen, 40) ],
                [ FirstBloodDisplay(screen, team, chall, duration=60, shade_colors=[ 196, 82, 27 ]) ]
              ]


    while not screen.has_resized():
        for e in effect_chains:
            try:
                draw_background(screen)
                screen.refresh()

                time.sleep(1)

                # Make a snapshot of the screen state, so that the wipes don't start from a clear screen
                snap = ScreenShot(screen)
                screen.play([ Scene( [snap] + e, clear=False) ], repeat=False, stop_on_resize=True)
            except ResizeScreenError:
                return



def main():
    # If the terminal is resized, the function terminates
    # The proper solution is to make a new screen.
    while True:
        Screen.wrapper(draw_func)




if __name__ == "__main__":
    main()
