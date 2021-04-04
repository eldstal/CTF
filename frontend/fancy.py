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

        # A list of text line strings received as log text
        self.log_text = []



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

    def handle_log(self, msg):
        self.log_text.append(msg)
        self.log_text = self.log_text[-1000:]


    def _palette(self, screen):
        self.color = {
            "bg": Screen.COLOUR_BLACK,
            "fg": 7,   # Light grey
            "focus": 213,   # Pink
            "accent": 255,  # White
            "award": 220,  # GOLD
            "firstblood": 196,  # BLOOD RED
            "firstblood_shades": [ 52, 88, 124, 160 ]   # Dark to bright red
        }

        # Double-splat these into Screen.print_at()
        self.attr = {
            "default": { "colour": self.color["fg"],    "bg": self.color["bg"] },
            "focused": { "colour": self.color["focus"], "bg": self.color["bg"] },
            "awards":  { "colour": self.color["award"], "bg": self.color["bg"] },
        }

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


    def _displays(self, screen):
        self.display_score = ScoreboardDisplay(screen, self.conf,
                                               attr=self.attr["default"],
                                               focused_attr=self.attr["focused"],
                                               awards_attr=self.attr["awards"]
                                              )

    def _poll_events(self):
        try:
            return self.events.get(timeout=1)
        except queue.Empty:
            return None

    def _main(self, screen):
        self.screen = screen
        self._palette(screen)
        self._displays(screen)
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
                    self._chall_add_stats(self.challenges[cid])
                    for tid in self.challenges[cid]["solves"]:
                        self._register_solve(cid, tid)

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
            self._register_solve(cid, tid)
            if data["first"]:
                if tid in self.teams and cid in self.challenges:
                    self._animate_firstblood(self.challenges[cid], self.teams[tid])

        elif msg == "new_challenge":
            cid = data["challenge_id"]
            self.challenges[cid] = data
            self._chall_add_stats(self.challenges[cid])
            for tid in self.challenges[cid]["solves"]:
                self._register_solve(cid, tid)

        else:
            # It was an unknown message from the middle-end. Nevermind
            return

        self._schedule_redraw()

    def _register_solve(self, cid, tid):
        if cid not in self.challenges:
            return

        chall = self.challenges[cid]
        if tid not in chall["solves"]:
            chall["solves"].append(tid)

        if chall["solves"].index(tid) == 0:
            if tid in self.teams:
                self.teams[tid]["firsts"].append(cid)
                self._team_add_stats(self.teams[tid])

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

    # Add/calculate additional fields for our internal use
    def _chall_add_stats(self, chall):
        if "solves" not in chall:
            chall["solves"] = []

    def _sanitize(self, text):
        cleaned = ftfy.fix_text(text, normalization="NFKC")

        # Remove all that line-crossing garbage in the Marks characters
        cleaned = u"".join( x for x in cleaned if not unicodedata.category(x).startswith("M") )

        return cleaned

    def _redraw(self):
        self.display_score.update_scores(self.teams)
        scene = Scene([self.display_score], clear=True)

        self.screen.play([scene], repeat=False, stop_on_resize=True)

    # Generate a scene with a snapshot of the screen overwritten by some list of transition effects
    def _trans(self, effects):
        if type(effects) != list:
            effects = [ effects ]

        # Make a snapshot of the screen state, so that the wipes don't start from a clear screen
        snap = ScreenShot(self.screen)
        return Scene( [snap] + effects, clear=False)

    def _animate(self, scenes):
        if type(scenes) != list:
            scenes = [ scenes ]

        self.screen.play(scenes, repeat=False, stop_on_resize=True)

        self._redraw()

    # Animations for events!
    def _animate_firstblood(self, chall, team):
        attr = self._attr_by_team(team)
        self._animate([
                   self._trans(NoiseWipe(self.screen, 30)),
                   Scene([FirstBloodDisplay(self.screen, team, chall,
                                            color=self.color["firstblood"],
                                            shade_colors=self.color["firstblood_shades"],
                                            team_color=attr["colour"])])
                 ])




