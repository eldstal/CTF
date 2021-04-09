import logging
import re
import time
from datetime import datetime

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
        return "midnightsunctf.se" in url

    def __init__(self, conf, middleend):
        self.conf = conf
        self.middle = middleend
        self.log = logging.getLogger(__name__)

        if conf["url"] == "":
            raise RuntimeError("This backend requires a URL")


        # Help the user out a little bit, they can specify some various links
        self.URL = self._baseurl(conf["url"])
        self.log.info(f"Attempting to use midnightsun instance at {self.URL}")

        self.session = requests.Session()


    def run(self):
        self.running = True
        while self.running:

            scoreboard = self._get_scoreboard()

            if scoreboard is not None:
                self.middle.handle_snapshot(("scoreboard", { "scores": scoreboard }))

            #if challs is not None:
            #    self.middle.handle_snapshot(("challenges", { "challenges": challs }))

            time.sleep(self.conf["poll-interval"])

    def stop(self):
        self.running = False


    def update(self):
        pass

    def _baseurl(self, url):
        url = re.sub("/dashboard.*", "", url)
        return url

    def _get_scoreboard(self):

        teams = []

        failed = False

        # Handy dandy matrix of everything
        # Sadly, we have to parse the table, but that's allright
        try:
            resp = self.session.get(self.URL + "/dashboard/scoreboard")
        except:
            failed = True

        if failed or resp.status_code != 200:
            self.log.warning("Scoreboard fetch failed")
            return None

        # BS filters to find the elements that we are interested in
        filt_team_row   = lambda tag: tag.name == "tr"

        # Accidentally detects ISO-8859 due to some german team names or something
        # The page is explicitly encoded as utf-8, though.
        resp.encoding = "utf-8"

        soup = BeautifulSoup(resp.text, "html.parser")
        rows = soup.findAll(filt_team_row, class_="ctf-tr")

        self.log.info(f"{len(rows)} rows in the scoreboard.")

        for r in rows:

            cells = r.find_all("td")

            if not r.has_attr("team_id"):
                self.log.warning(f"Unexpected table row {r.string}")
                continue

            t = {}
            url = r["team_id"]
            t["team_id"] = re.match("/dashboard/team/([0-9]+)", url)[1]
            t["name"] = str(cells[1].string).strip()
            t["score"] = int(cells[2].string)
            t["place"] = int(cells[0].string)

            teams.append(t)

        return teams

