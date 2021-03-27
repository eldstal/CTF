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
        # Return True if the url seems like a system we support
        resp = requests.get(url)

        soup = BeautifulSoup(resp.text, "html.parser")

        # This is on every page
        filt_meta = lambda tag: tag.name == "meta" and tag.has_attr("content") and "hxp CTF" in tag["content"]
        meta_tags = soup.findAll(filt_meta)

        if len(meta_tags) > 0:
            return True

        return False

    def __init__(self, conf, middleend):
        self.conf = conf
        self.middle = middleend
        self.log = logging.getLogger(__name__)

        if conf["url"] == "":
            raise RuntimeError("This backend requires a URL")


        # Help the user out a little bit, they can specify some various links
        self.URL = self._baseurl(conf["url"])
        self.log.info(f"Attempting to use hxp instance at {self.URL}")

        self.session = requests.Session()


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

    def _baseurl(self, url):
        url = re.sub("/public.*", "", url)
        url = re.sub("/internal.*", "", url)
        return url

    def _get_scoreboard_and_challenges(self):

        teams = []
        challs = []

        failed = False

        # Handy dandy matrix of everything
        # Sadly, we have to parse the table, but that's allright
        try:
            resp = self.session.get(self.URL + "/public/scoreboard/max/")
        except:
            failed = True

        if failed or resp.status_code != 200:
            self.log.warning("Chall fetch failed")
            return None

        # BS filters to find the elements that we are interested in
        filt_chall_link = lambda tag: tag.name == "a" and tag.has_attr("href") and "/internal/challenge/" in tag["href"]
        filt_team_row   = lambda tag: tag.name == "tr" and tag.parent.name == "tbody"

        # Accidentally detects ISO-8859 due to some german team names or something
        # The page is explicitly encoded as utf-8, though.
        resp.encoding = "utf-8"

        soup = BeautifulSoup(resp.text, "html.parser")
        headings = soup.findAll(filt_chall_link)
        rows     = soup.findAll(filt_team_row)

        # The order in this list is important!
        # Each team's row has the challenges in this exact order.
        # We will index this to fill in solves below.

        # Important: BS4 objects have string representations, but they do not
        # belong in the data we pass to middle-end. 
        # Convert strings to proper strings or face the consequences!
        for h in headings:
            c = {}
            c["challenge_id"] = re.match("/internal/challenge/([0-9a-fA-F-]+)/", h["href"])[1]
            c["name"] = str(h.string)
            c["categories"] = []    # Not part of the data
            c["points"] = 0         # Not part of the data
            c["solves"] = []
            challs.append(c)

        #print(challs)

        for r in rows:
            cells = r.find_all("td")

            t = {}
            a = cells[1].find("a")
            url = a["href"]
            t["team_id"] = re.match("/internal/team/([0-9]+)/", url)[1]
            t["name"] = str(a.string)
            t["score"] = str(cells[2].string)
            t["place"] = int(cells[0].string)

            teams.append(t)

            team_solves = cells[3:]

            # If this doesn't hold, the page format has changed.
            # This backend isn't compatible anymore.
            if len(team_solves) != len(challs):
                self.log.error("Backend has no idea how to parse this table. CTF website has probably changed.")
                assert(False)

            for c_index in range(len(team_solves)):
                s = team_solves[c_index]

                icon = s.string
                # Not solved by this team
                if icon is None: continue

                icon = icon.strip()

                # The table uses emoji to show first/second/third solve and all others.
                first = "\N{FIRST PLACE MEDAL}"
                second = "\N{SECOND PLACE MEDAL}"
                third = "\N{THIRD PLACE MEDAL}"
                flag = "\N{TRIANGULAR FLAG ON POST}"

                if icon == first:
                    # First solve!!
                    challs[c_index]["solves"] = [ t["team_id"] ] + challs[c_index]["solves"]
                elif icon in [ second, third, flag ]:
                    challs[c_index]["solves"].append(t["team_id"])

        return teams,challs

