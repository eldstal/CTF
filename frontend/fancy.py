import sys
import re
import string
import time
import threading
import queue
import multiprocessing
import queue
import select
import ftfy
import unicodedata

from asciimatics.screen import Screen
from asciimatics.scene import Scene
from asciimatics.effects import Cycle, Mirage, RandomNoise
from asciimatics.renderers import FigletText
from asciimatics.exceptions import ResizeScreenError

from frontend.animation.wipe import *
from frontend.animation.util import *
from frontend.animation.display import *

# A frontend which uses asciimatics to draw with super fancy animations
class FrontEnd:
    @staticmethod
    def help():
        return [
                 "focus-teams: one or more teams (name) to always show",
                 "max-count:   max length of scoreboard"
               ]

    @staticmethod
    def needs_main_thread():
        return True

    def __init__(self, conf):
        self.conf = conf

        # Everything we know about the players
        # This includes not only data from the middle-end, but
        # some of our own data as well.
        self.teams = {}

        # Likewise, everything we know about the challenges
        self.challenges = {}

        # Incoming events from the middle-end
        # Also contains self-posted actions, like "redraw"
        self.events = queue.Queue()


        pass

    def run(self):
        self.running = True

        # If the terminal size changes, wrapper() will terminate and
        # we need to create a new Screen to keep executing
        while self.running:
            try:
                Screen.wrapper(self._main)
            except ResizeScreenError:
                pass

    # An event from the middle-end about something that changed
    def handle_event(self, event):
        self.events.put(event)


    def _palette(self, screen):
        self.color = {
            "bg": Screen.COLOUR_BLACK,
            "fg": 7,   # Light grey
            "focus": 213,   # Pink
            "accent": 255,  # White
            "award": 220,  # GOLD
            "firstblood": 196,  # GOLD
        }

        # Double-splat these into Screen.print_at()
        self.attr = {
            "default": { "colour": self.color["fg"],    "bg": self.color["bg"] },
            "focused": { "colour": self.color["focus"], "bg": self.color["bg"] },
            "awards":  { "colour": self.color["award"], "bg": self.color["bg"] },
        }


    def _poll_events(self):
        try:
            return self.events.get(timeout=1)
        except queue.Empty:
            return None

    def _main(self, screen):
        self.screen = screen
        self._palette(screen)
        self._redraw()
        while self.running:
            # This should be two different queues, but there's no select() implementation.
            # Oh, well
            ev = self._poll_events()

            if screen.has_resized():
                # Ehm... pretend we never took it.
                self.events.put(ev)
                break

            if ev is not None:
                self._parse_event(ev)


    def _schedule_redraw(self):
        self.events.put(("redraw", None))

    def _parse_action(self, a):
        msg, data = a
        if msg == "redraw":
            self._redraw()

        elif msg == "shutdown":
            self.running = False
            self.actions.put(("dummy", None))

        else:
            return False

        # We handled this event, so it must have been an internal event
        return True

    def _parse_event(self, event):
        msg,data = event

        if self._parse_action(event):
            # It was an internal action
            return

        elif msg == "boot":
            for t in data["scoreboard"]["scores"]:
                tid = t["team_id"]
                t["name"] = self._sanitize(t["name"])
                self.teams[tid] = t
                self._team_add_stats(self.teams[tid])
            if "challenges" in data:
                for c in data["challenges"]["challenges"]:
                    cid = c["challenge_id"]
                    self.challenges[cid] = c

        elif msg == "new_team":
            tid = data["team_id"]
            data["name"] = self._sanitize(data["name"])
            self.teams[tid] = data
            self.teams[tid]["old_place"] = data["place"]
            self.teams[tid]["marker"] = ""
            self._team_add_stats(self.teams[tid])

        elif msg == "place":
            tid = data["team_id"]
            if tid in self.teams:
                self.teams[tid]["place"] = data["place"]
                self.teams[tid]["old_place"] = data["old_place"]
                self._team_add_stats(self.teams[tid])

        elif msg == "score":
            tid = data["team_id"]
            if tid in self.teams:
                self.teams[tid]["score"] = data["score"]
                self._team_add_stats(self.teams[tid])

        elif msg == "solve":
            cid = data["challenge_id"]
            tid = data["team_id"]
            self.challenges[cid]["solves"].append(tid)
            if data["first"]:
                self.teams[tid]["firsts"].append(cid)
                self._team_add_stats(self.teams[tid])
                self._animate_firstblood(self.challenges[cid], self.teams[tid])

        elif msg == "new_challenge":
            cid = data["challenge_id"]
            self.challenges[cid] = data

        else:
            # It was an unknown message from the middle-end. Nevermind
            return

        self._schedule_redraw()

    # Add/calculate additional fields for our internal use
    def _team_add_stats(self, team):
        if "old_place" not in team:
            team["old_place"] = team["place"]

        if "firsts" not in team:
            team["firsts"] = []

        award_char = "🏆"
        team["awards"] = "".join([ award_char for _ in team["firsts"] ])
        n_awards = len(team["firsts"])
        if n_awards > 4:
            team["awards"] = f"{n_awards}x {award_char}"

        team["marker"] = " "
        if team["old_place"] > team["place"]:
            team["marker"] = "▲"


    def _sanitize(self, text):
        cleaned = ftfy.fix_text(text, normalization="NFKC")

        # Remove all that line-crossing garbage in the Marks characters
        cleaned = u"".join( x for x in cleaned if not unicodedata.category(x).startswith("M") )

        return cleaned

    # Generate two lists of teams which should go on the toplist
    # This takes care of cropping the top list to fit the focused teams underneath
    # returns (toplist, extra_focused_teams)
    def _make_toplist(self):
        # Pick out which teams to even show
        ranking = [ (team["place"], team) for tid,team in self.teams.items() ]
        ranking = sorted(ranking, key=lambda x: x[0])

        boundary = self.conf["max-count"]
        toplist = ranking[:boundary]

        focused = []
        for r,team in ranking[boundary:]:
            if self._team_is_focused(team):
                focused.append((r,team))

        if len(toplist) + len(focused) > boundary:
            toplist = toplist[:boundary - len(focused)]

        return toplist, focused

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

    # Return a list of strings, aligned properly
    # Will also color the focused team(s)
    def _print_table(self, screen):
        columns = [
                    (" ",  "marker"),
                    ("#",  "place"),
                    ("Score", "score"),
                    ("          ", "awards"),   # Prints up to 5x unicode trophy, which may be quite wide.
                    ("Team                          ",  "name"),
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
                text = text[:w-x]

                screen.print_at(text, x, y, transparent=True, **attr)


    def _redraw(self):

        self.screen.clear_buffer(self.color["fg"],
                                 Screen.A_NORMAL,
                                 self.color["bg"])

        self._print_table(self.screen)

        self.screen.refresh()

    # Generate a scene with a snapshot of the screen overwritten by some list of transition effects
    def _trans(self, effects):
        if type(effects) != list:
            effects = [ effects ]

        # Make a snapshot of the screen state, so that the wipes don't start from a clear screen
        snap = ScreenShot(self.screen)
        return Scene( [snap] + effects, clear=False)

    def _animate(self, scenes):
        if type(scenes) != list:
            effects = [ effects ]

        self.screen.play(scenes, repeat=False, stop_on_resize=True)

        self._redraw()

    # Animations for events!
    def _animate_firstblood(self, chall, team):
        attr = self._attr_by_team(team)
        self._animate([
                   self._trans(NoiseWipe(self.screen, 30)),
                   Scene([FirstBloodDisplay(self.screen, team, chall, color=self.color["firstblood"], team_color=attr["colour"])])
                 ])

