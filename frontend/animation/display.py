from asciimatics.effects import Effect
from asciimatics.screen import Screen

from pyfiglet import Figlet

import re
import ftfy
import unicodedata


class FirstBloodDisplay(Effect):

    def __init__(self, screen, team, challenge, duration=None, color=None, shade_colors=None, team_color=None, chall_color=None, **kwargs):
        super(FirstBloodDisplay, self).__init__(screen, **kwargs)

        if duration is None: duration = 60
        if color is None: color = Screen.COLOUR_RED
        if shade_colors is None: shade_colors = []
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
            FIRST = self._new_drifter(screen, render("First"), color, shade_colors, 5, 0, drift_dist)
            BLOOD = self._new_drifter(screen, render("Blood"), color, shade_colors, FIRST["x1"] + FIRST["w"] + 2, 2, drift_dist)
            TEAM  = self._new_drifter(screen, team["name"], team_color, [], 12, FIRST["h"]+2, drift_dist)
            CHALL = self._new_drifter(screen, challenge["name"], chall_color, [], TEAM["x1"] + 4, TEAM["y"]+1, drift_dist)

            if FIRST["w"] + BLOOD["w"] + 7 < screen.width:
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
    def _new_drifter(self, screen, text, color, shade_colors, x, y, drift_dist):

        # Phase 0: Invisible
        # Phase 1: Smashing in at light speed
        # Phase 2: Drifting slowly leftward

        lines = text.split("\n")
        width = max([ len(l) for l in lines] )
        return {
                 "text": text, "w": width, "h": len(lines),
                 "color": color, "shade_colors": shade_colors,
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
                if frame_no % self._v2 == 0:
                    d["x"] -= 1

            lines = d["text"].split("\n")
            for dy in range(len(lines)):
                txt = lines[dy]
                x = int(d["x"] + 0.5)
                y = d["y"] + dy

                # Pad out with whitespace to properly clear stuff to the right
                txt += " "*(W - len(txt))

                txt = txt[:W - x]
                self._screen.print_at(txt, x, y, d["color"], transparent=False)

                # Optionally, drifting text gets a shady background around its edges
                # to help with the illusion of a slower drift. It's pretty neat.
                if d["phase"] == 2:
                    if len(d["shade_colors"]) > 0 and len(txt.strip()) > 0:

                        # Identify every leading and trailing edge of the text
                        lead_edges  = [ i for i in range(-1, len(txt)-1)  if (i == -1 or txt[i] == " ") and txt[i+1] != " " ]
                        trail_edges = [ i for i in range(1, len(txt))     if (txt[i] == " " or i == len(txt)-1) and txt[i-1] != " " ]

                        shades = d["shade_colors"]

                        drift_progress = (frame_no % self._v2) / self._v2
                        shade_idx  = int((len(shades) + 1) * drift_progress) - 1

                        #
                        # Leading shade
                        #

                        # Overwrite the last whitespace just before the text begins
                        for text_start in lead_edges:
                            lead_text = txt[text_start+1]
                            lead_x = x + text_start

                            if shade_idx >= 0:
                                self._screen.print_at(lead_text, lead_x, y, shades[shade_idx], transparent=False)

                        #
                        # Trailing shade
                        #
                        for text_end in trail_edges:
                            trail_text = txt[text_end-1]
                            trail_x = x + text_end - 1

                            if shade_idx >= 0:
                                self._screen.print_at(trail_text, trail_x, y, shades[len(shades) - shade_idx - 1], transparent=False)


# XXX: Should this be a Renderer?
class ScoreboardDisplay(Effect):

    def __init__(self, screen, conf, attr=None, focused_attr=None, awards_attr=None, **kwargs):
        super(ScoreboardDisplay, self).__init__(screen, **kwargs)

        self.conf = conf

        self.attr = {
            "default": { "colour": 7,   "bg": Screen.COLOUR_BLACK },
            "focused": { "colour": 213, "bg": Screen.COLOUR_BLACK },
            "awards":  { "colour": 220, "bg": Screen.COLOUR_BLACK },
        }

        if attr is not None: self.attr["default"] = attr
        if focused_attr is not None: self.attr["focused"] = focused_attr
        if awards_attr is not None: self.attr["awards"] = awards_attr

        self._limits(screen)

        self.teams = {}

    def update_scores(self, teams):
        self.teams = teams

    def reset(self):
        pass

    @property
    def stop_frame(self):
        return 1

    def _sanitize(self, text):
        cleaned = ftfy.fix_text(text, normalization="NFKC")

        # Remove all that line-crossing garbage in the Marks characters
        cleaned = u"".join( x for x in cleaned if not unicodedata.category(x).startswith("M") )

        return cleaned

    def _limits(self, screen):
        # At most, as many places as will fit in the window
        max_len = screen.height - 1
        if "max-count" in self.conf:
            self.max_count = min(self.conf["max-count"], max_len)
        else:
            # Nobody specified, so let's default to a full screen of scores
            self.max_count = max_len

    # Provide a team object
    def _team_is_focused(self, team):
        for expr in self.conf["focus-teams"]:
            if re.match(expr, team["name"]) != None: return True
        return False

    def _attr_by_team(self, team):
        if self._team_is_focused(team):
            return self.attr["focused"]
        else:
            return self.attr["default"]

    # Generate two lists of teams which should go on the toplist
    # This takes care of cropping the top list to fit the focused teams underneath
    # returns (toplist, extra_focused_teams)
    def _make_toplist(self):
        # Pick out which teams to even show
        ranking = [ (team["place"], team) for tid,team in self.teams.items() ]
        ranking = sorted(ranking, key=lambda x: x[0])

        boundary = self.max_count
        toplist = ranking[:boundary]

        focused = []
        for r,team in ranking[boundary:]:
            if self._team_is_focused(team):
                focused.append((r,team))

        if len(toplist) + len(focused) > boundary:
            toplist = toplist[:boundary - len(focused)]

        return toplist, focused

    def _print_table(self, screen):
        columns = [
                    (" ",  "marker"),
                    ("#",  "place"),
                    ("Score", "score"),
                    ("          ", "awards"),   # Prints up to 5x unicode trophy, which may be quite wide.
                    ("Team",  "name"),
                  ]

        toplist, focused = self._make_toplist()

        toplist = toplist + focused

        # Each cell is a tuple of (text, attr)
        # The +1 gives us a header line at the top
        table = [ [ "" for c in columns ] for _ in range(len(toplist) + 1) ]

        for c in range(len(columns)):
            header,field = columns[c]

            table[0][c] = ( header, self.attr["default"])

            for i in range(len(toplist)):
                team = toplist[i][1]

                text = self._sanitize(str(team[field]))

                # Some fields are colored differently
                attr = self.attr["default"]
                if field == "name": attr = self._attr_by_team(team)
                elif field == "awards": attr = self.attr["awards"]

                table[i+1][c] = (text, attr)


        column_widths = [ max([ len(row[c][0]) for row in table ]) for c in range(len(columns)) ]

        # X-coordinate of each column, based on the widest of all preceding columns
        padding = 1
        col_offset = lambda c: sum(column_widths[:c]) + (padding * (c - 1))

        h,w = self.screen.dimensions

        # Center the table
        x0 = (w - col_offset(len(columns))) // 2
        y0 = (h - len(table)) // 2

        # Super big tables don't fall outside the window
        x0 = max(0, x0)
        y0 = max(0, y0)

        for r in range(len(table)):
            for c in range(len(columns)):
                text,attr = table[r][c]
                x = x0 + col_offset(c)
                y = y0 + r

                # Don't overflow the window
                if y > h: break

                if len(text) > w-x:
                    text = text[:w-x-3] + "..."

                screen.print_at(text, x, y, transparent=True, **attr)


    def _update(self, frame_no):

        self.screen.clear_buffer(self.attr["default"]["colour"],
                                 Screen.A_NORMAL,
                                 self.attr["default"]["bg"])

        self._print_table(self.screen)

        self.screen.refresh()

