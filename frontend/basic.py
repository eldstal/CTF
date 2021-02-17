from tabulate import tabulate
import sys
import string
import re

import time
import ftfy
import unicodedata


# A frontend which just clears the terminal and prints the scoreboard
class FrontEnd:
    @staticmethod
    def help():
        return [
                 "focus-teams: one or more teams (name) to always show",
                 "max-count:   max length of scoreboard"
               ]

    @staticmethod
    def needs_main_thread():
        return False

    def __init__(self, conf):
        self.conf = conf

        self.teams = {}

        pass

    def run(self):
        self.running = True
        while self.running:
            time.sleep(1)


    # An event from the middle-end about something that changed
    def handle_event(self, event):
        msg,data = event

        if msg == "boot":
            for t in data["scoreboard"]["scores"]:
                tid = t["team_id"]
                self.teams[tid] = t
                self.teams[tid]["old_place"] = t["place"]

        if msg == "new_team":
            tid = data["team_id"]
            self.teams[tid] = data
            self.teams[tid]["old_place"] = data["place"]

        if msg == "place":
            tid = data["team_id"]
            if tid in self.teams:
                self.teams[tid]["place"] = data["place"]
                self.teams[tid]["old_place"] = data["old_place"]

        if msg == "score":
            tid = data["team_id"]
            if tid in self.teams:
                self.teams[tid]["score"] = data["score"]

        self._redraw()

    def _sanitize(self, text):
        cleaned = ftfy.fix_text(text, normalization="NFKC")

        # Remove all that line-crossing garbage in the Marks characters
        cleaned = u"".join( x for x in cleaned if not unicodedata.category(x).startswith("M") )

        return cleaned


    def _redraw(self):
        ranking = [ (tid, t["place"]) for tid,t in self.teams.items() ]
        ranking = sorted(ranking, key=lambda x: x[1])

        table = []
        for tid,place in ranking:
            team = self.teams[tid]

            marker = " "
            if team["old_place"] > team["place"]: marker = "▲"
            #elif team["old_place"] < team["place"]: marker = "▼"

            table.append([
                place,
                marker,
                self._sanitize(team["name"]),
                team["score"]
            ])


        # Only show top 20 if the user didn't specify further
        boundary = self.conf["max-length"]

        cropped = table[:boundary]

        # Additionally, if any of the focused teams fall outside that list,
        # add them to the bottom

        focused = []
        for t in table[boundary:]:
            for expr in self.conf["focus-teams"]:
                print(expr)
                if re.match(expr, t[2]) != None:
                    print(f"Focused {t[2]} due to {expr}")
                    focused.append(t)
                    break

        if len(cropped) + len(focused) > boundary:
            cropped = cropped[:boundary - len(focused)]


        # Clear screen
        print("\033[2J")
        print(tabulate(cropped + focused))
