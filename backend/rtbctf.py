import logging
import re
import time
import hashlib

from bs4 import BeautifulSoup
import requests
from requests.exceptions import ReadTimeout

class BackEnd:

    @staticmethod
    def help():
        return [
            "url: ex https://rtblivedemo.herokuapp.com/scoreboard",
            "poll-interval: seconds",
        ]

    @staticmethod
    def supports(conf, url):
        # Return True if the url seems like a system we support
        resp = requests.get(url)

        lcase = resp.text.lower()
        return "abs0lut3pwn4g3" in lcase

    def __init__(self, conf, middleend):
        self.conf = conf
        self.middle = middleend
        self.log = logging.getLogger(__name__)

        if conf["url"] == "":
            raise RuntimeError("This backend requires a URL")


        # Help the user out a little bit, they can specify some various links
        self.URL = self._baseurl(conf["url"])
        self.log.info(f"Attempting to use RTB-CTF instance at {self.URL}")

        self.session = requests.Session()


    def run(self):
        self.running = True
        while self.running:

            scoreboard = self._get_scoreboard()

            if scoreboard is not None:
                self.middle.handle_snapshot(("scoreboard", { "scores": scoreboard }))

            time.sleep(self.conf["poll-interval"])

    def stop(self):
        self.running = False


    def update(self):
        pass

    def _baseurl(self, url):
        url = re.sub("/scoreboard.*", "", url)
        return url

    def _get_scoreboard(self):

        teams = []

        # Sadly, we have to parse the table, but that's allright
        failed = False
        try:
            resp = self.session.get(self.URL + "/scoreboard")
        except:
            failed = True

        if failed or resp.status_code != 200:
            self.log.warning("scoreboard fetch failed:")
            return None

        # BS filters to find the elements that we are interested in
        filt_team_row   = lambda tag: tag.name == "tr" and tag.parent.name == "tbody"

        # Accidentally detects ISO-8859 due to some german team names or something
        # The page is explicitly encoded as utf-8, though.
        resp.encoding = "utf-8"

        soup = BeautifulSoup(resp.text, "html.parser")
        rows     = soup.findAll(filt_team_row)

        # Important: BS4 objects have string representations, but they do not
        # belong in the data we pass to middle-end. 
        # Convert strings to proper strings or face the consequences!

        for r in rows:
            heads = r.find_all("th")
            cells = r.find_all("td")

            t = {}
            t["name"]    = str(cells[0].string)
            t["team_id"] = t["name"]
            t["place"]   = int(heads[0].string)
            t["score"]   = str(cells[1].string)

            teams.append(t)

        return teams

