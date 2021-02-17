from asciimatics.effects import Effect
from asciimatics.screen import Screen

from pyfiglet import Figlet


class FirstBloodDisplay(Effect):

    def __init__(self, screen, team, challenge, duration=None, color=None, team_color=None, chall_color=None, **kwargs):
        super(FirstBloodDisplay, self).__init__(screen, **kwargs)

        if duration is None: duration = 60
        if color is None: color = Screen.COLOUR_RED
        if team_color is None: team_color = Screen.COLOUR_WHITE
        if chall_color is None: chall_color = Screen.COLOUR_WHITE

        self._duration = duration

        # This screen has four things on it.
        # 0 and 1: FIRST and BLOOD
        # 2: Team name
        # 3: Challenge name

        # The animation smacks each part in quickly from the right,
        # and once in place it drifts slowly leftward

        # Keep trying different fonts until one fits on screen
        for font in [ "poison",
                      "cricket",
                      "rectangles",
                      "thin",
                      None   # No figlet at all. Boo.
                    ]:

            render = lambda txt: txt
            if font is not None:
                figlet = Figlet(font=font)
                render = figlet.renderText

            drift_dist = 5
            FIRST = self._new_drifter(screen, render("First"), color, 5, 0, drift_dist)
            BLOOD = self._new_drifter(screen, render("Blood"), color, FIRST["x1"] + FIRST["w"] + 2, 2, drift_dist)
            TEAM  = self._new_drifter(screen, team["name"], team_color, 12, FIRST["h"]+2, drift_dist)
            CHALL = self._new_drifter(screen, challenge["name"], chall_color, TEAM["x1"] + 4, TEAM["y"]+1, drift_dist)

            if FIRST["w"] + BLOOD["w"] + 15 < screen.width:
                break
            continue

        self._v1 = 12  # Chars per frame (Fast speed)
        self._v2 = 15  # Frames per char (Slow speed)

        # Set up the timing of the animations
        FIRST["t1"] = 1
        FIRST["t2"] = FIRST["t1"] + duration // 10
        BLOOD["t1"] = FIRST["t2"]
        BLOOD["t2"] = BLOOD["t1"] + duration // 10
        TEAM["t1"]  = BLOOD["t2"]
        TEAM["t2"]  = TEAM["t1"] + duration // 10
        CHALL["t1"] = TEAM["t2"]
        CHALL["t2"] = CHALL["t1"] + duration // 10

        self._drifters = [ FIRST, BLOOD, TEAM, CHALL ]


    # Pass in the x and y where the text should start drifting slowly
    def _new_drifter(self, screen, text, color, x, y, drift_dist):

        # Phase 0: Invisible
        # Phase 1: Smashing in at light speed
        # Phase 2: Drifting slowly leftward

        lines = text.split("\n")
        width = max([ len(l) for l in lines] )
        return {
                 "text": text, "w": width, "h": len(lines), "color": color,
                 "phase": 0, "x": screen.width, "y": y,
                 "x1": x, "x2": x-drift_dist,
               }

    def reset(self):
        pass

    @property
    def stop_frame(self):
        return self._duration

    def _update(self, frame_no):
        H,W = self._screen.dimensions

        if (frame_no == 1):
            self._screen.clear()
            self._screen.refresh()

        for d in self._drifters:
            if frame_no == d["t1"]: d["phase"] = 1
            if frame_no == d["t2"]: d["phase"] = 2

            if d["phase"] == 0:
                continue

            if d["phase"] == 1:
                dt = d["t2"] - frame_no - 1
                d["x"] = d["x1"] + (dt * self._v1)

            # Sync up phase 2 so they drift together
            elif d["phase"] == 2:
                if frame_no % 15 == 0:
                    d["x"] -= 1

            lines = d["text"].split("\n")
            for dy in range(len(lines)):
                txt = lines[dy]
                x = int(d["x"] + 0.5)
                y = d["y"] + dy

                # Pad out with whitespace to properly clear stuff to the right
                txt += " "*(W - len(txt))

                txt = txt[:W - x]
                self._screen.print_at(txt, int(d["x"] + 0.5), y, d["color"], transparent=False)


