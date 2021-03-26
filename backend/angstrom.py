import re
import time
from datetime import datetime
import ciso8601

from bs4 import BeautifulSoup
import requests
from requests.exceptions import ReadTimeout

class BackEnd:

    @staticmethod
    def help():
        return [
            "url: none",
            "poll-interval: seconds",
        ]

    @staticmethod
    def supports(conf, url):
        # Return True if the url seems like a system we support
        return "angstromctf.com" in url

    def __init__(self, conf, middleend):
        self.conf = conf
        self.middle = middleend

        if conf["url"] == "":
            raise RuntimeError("This backend requires a URL")


        # Help the user out a little bit, they can specify some various links
        self.URL = self._baseurl(conf["url"])
        self.API = "https://api.angstromctf.com"
        print(f"Attempting to use angstrom instance at {self.URL}")


        self.session = requests.Session()

        # The same web system hosts historic competitions as well.
        # They appear to be numbered.
        # The URL should contain something like "2021.angstromctf.com" which
        # tells us which competition the user actually wants.
        self.competition = self._select_competition()
        if (self.competition is None):
            raise RuntimeError("Unable to choose a specific angstrom instance.")


    def run(self):
        self.running = True
        while self.running:

            challs = self._get_challenges()

            if challs is not None:
                self.middle.handle_snapshot(("challenges", { "challenges": challs }))

            scoreboard = self._get_scoreboard()

            if scoreboard is not None:
                self.middle.handle_snapshot(("scoreboard", { "scores": scoreboard }))

            time.sleep(self.conf["poll-interval"])

    def stop(self):
        self.running = False


    def update(self):
        pass

    def _baseurl(self, url):
        url = re.sub("/about.*", "", url)
        url = re.sub("/scoreboard.*", "", url)
        url = re.sub("/challenges.*", "", url)
        return url

    def _select_competition(self):

        failed = False

        # This endpoint gives us 
        try:
            resp = self.session.get(self.API + "/competitions")
            comp_list = resp.json()
        except:
            failed = True

        if failed or resp.status_code != 200:
            print("Competition list fetch failed.")
            return None


        name = re.sub(".*/([^/.]+)\.angstromctf.com.*", "\\1", self.URL)
        print(f"Attempting to connect to instance {name}")

        # If we can't find one that matches our year or whatever,
        # pick the latest one - it's probably the only one running.
        fallback = comp_list[-1]

        for comp in comp_list:
            if comp["name"] == name:
                return comp["id"]

        print(f"Unable to find expected competition. Falling back to {fallback['name']}")
        return fallback["id"]


    def _get_solves(self, challenge_id):
        failed = False

        try:
            resp = self.session.get(self.API + f"/competitions/{self.competition}/challenges/{challenge_id}")
            resp.encoding = "utf-8"
            chall_stats = resp.json()
        except:
            failed = True

        if failed or resp.status_code not in [ 200, 304 ]:
            print("Chall solves fetch failed")
            print(resp.text)
            return []

        if "solves" not in chall_stats:
            return []

        solves = [ s["team"]["id"] for s in chall_stats["solves"] ]
        return solves

    def _get_challenges(self):
        challenges = []

        failed = False

        try:
            resp = self.session.get(self.API + f"/competitions/{self.competition}/challenges")
            resp.encoding = "utf-8"
            chall_list = resp.json()
        except:
            failed = True

        if failed or resp.status_code not in [ 200, 304 ]:
            print("Chall list fetch failed")
            #print(resp.text)
            return None

        for c in chall_list:
            chall = {}
            chall["challenge_id"] = c["id"]
            chall["name"] = c["title"]
            chall["categories"] = [ c["category"] ]
            chall["points"] = c["value"]
            chall["solves"] = self._get_solves(chall["challenge_id"])
            challenges.append(chall)


        return challenges

    def _get_scoreboard(self):

        teams = []

        failed = False

        try:
            resp = self.session.get(self.API + f"/competitions/{self.competition}/teams")
            resp.encoding = "utf-8"
            sc_list = resp.json()
        except:
            failed = True

        if failed or resp.status_code not in [ 200, 304 ]:
            print("Scoreboard fetch failed")
            #print(resp.text)
            return None

        # The scoreboard comes back in some not very interesting order.
        # It appears to be ordered by team ID, i.e. when the team was created.
        by_score = lambda t: t["score"]
        by_stime = lambda t: ciso8601.parse_datetime(t["lastSolve"]).timestamp() if t["score"] > 0 else 0
        by_ttime = lambda t: ciso8601.parse_datetime(t["created"]).timestamp()

        # Primary: score
        # Secondary: Last solve came in first
        # Third option: Which team was created first?
        sc_list = sorted(sc_list, key=by_ttime)
        sc_list = sorted(sc_list, key=by_stime)
        sc_list = sorted(sc_list, key=by_score, reverse=True)

        for i,t in enumerate(sc_list):
            team = {}
            team["team_id"] = t["id"]
            team["place"] = i+1
            team["name"] = t["name"]
            team["score"] = t["score"]
            teams.append(team)

        return teams

