import re
import time
from datetime import datetime
import traceback

from bs4 import BeautifulSoup
import requests
from requests.exceptions import ReadTimeout

class BackEnd:

    @staticmethod
    def help():
        return [
            "url: index page of CTF",
            "poll-interval: seconds",
        ]

    @staticmethod
    def supports(conf, url):
        # Return True if the url seems like a system we support
        # The frontend uses javascript to do most of the work,
        # and the api is on a different domain. huh.
        # For now, let's use this as a heuristic
        return "ctf.zer0pts.com" in url

    def __init__(self, conf, middleend):
        self.conf = conf
        self.middle = middleend

        if conf["url"] == "":
            raise RuntimeError("This backend requires a URL")


        self.session = requests.Session()

        try:
            self.URL = self._identify_api_server(conf["url"])
        except Exception as e:
            print("The zer0pts backend does not support this CTF system. Perhaps a patch is necessary.")
            traceback.print_exc()

        print(f"Attempting to use zer0pts instance at {self.URL}")


    def _identify_api_server(self, url):
        # The webpage works on javascript.
        base = re.sub("/index.html.*", "", url)

        landing = self.session.get(base + "/index.html#/")

        # Find the javascript for the webapp.
        # It can tell us where the API endpoint actually is.
        # ouff.
        jspath = re.match(".*(/js/app.*.js).*", landing.text)[1]

        js = self.session.get(base + jspath)
        api_server = re.match(".*\"(http(s?)://api[^\"]*[^\"/])(/?)\".*", js.text)[1]
        print(f"Identified API server {api_server}")

        return api_server

    def run(self):
        self.running = True
        while self.running:

            stats = self._get_scoreboard_and_challenges()

            if stats is not None:
                scoreboard,challs = stats

                if scoreboard is not None:
                    self.middle.handle_snapshot(("scoreboard", { "scores": scoreboard }))

                if challs is not None:
                    self.middle.handle_snapshot(("challenges", { "challenges": challs }))

            time.sleep(self.conf["poll-interval"])

    def stop(self):
        self.running = False


    def update(self):
        pass


    def _get_scoreboard_and_challenges(self):

        teams = []
        challs = []

        failed = False

        # Handy dandy matrix of everything
        # Sadly, we have to parse the table, but that's allright
        try:
            resp = self.session.get(self.URL + "/info-update")
            data = resp.json()
        except:
            failed = True

        if failed or resp.status_code != 200:
            print("Chall fetch failed")
            print(resp)
            return None

        for chall in data["ranking"]["tasks"]:
            # TODO: This
            continue
            c = {}
            c["challenge_id"] = chall["challenge_id"]
            c["name"] = chall["challenge"]
            c["categories"] = []
            c["points"] = chall["points"]
            c["solves"] = []
            challs.append(c)

        #print(challs)

        for team in data["ranking"]["standings"]:

            t = {}
            t["team_id"] = team["team_id"]
            t["name"] = team["team"]
            t["score"] = team["points"]
            t["place"] = team["pos"]

            teams.append(t)

            for s in team["taskStats"]:
                # TODO: Solves
                pass

        return teams,challs

