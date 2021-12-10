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

        # This is in the footer of every page
        return "Milkdrop/CTFx" in resp.text

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
        url = re.sub("/user.*", "", url)
        url = re.sub("/home.*", "", url)
        url = re.sub("/challenges.*", "", url)
        return url

    def _get_scoreboard(self):

        teams = []

        failed = False

        # Handy dandy matrix of everything
        # Sadly, we have to parse the table, but that's allright
        try:
            resp = self.session.get(self.URL + "/scoreboard")
        except:
            failed = True

        if failed or resp.status_code != 200:
            self.log.warning("Chall fetch failed")
            return None

        # BS filters to find the elements that we are interested in
        filt_scoreboard_row = lambda tag: tag.name == "div" and tag.has_attr("class") and "scoreboard-entry" in tag["class"]
        filt_team_link      = lambda tag: tag.name == "a" and tag.has_attr("class") and "scoreboard-team-name" in tag["class"]
        filt_team_score     = lambda tag: tag.name == "div" and tag.has_attr("class") and "scoreboard-fill" in tag["class"]
        filt_team_place     = lambda tag: tag.name == "div" and not tag.has_attr("class") and re.match("[0-9]+\.", tag.string)

        # Accidentally detects ISO-8859 due to some german team names or something
        # The page is explicitly encoded as utf-8, though.
        resp.encoding = "utf-8"

        soup = BeautifulSoup(resp.text, "html.parser")
        rows = soup.findAll(filt_scoreboard_row)

        # The order in this list is important!
        # Each team's row has the challenges in this exact order.
        # We will index this to fill in solves below.

        #print(challs)

        for r in rows:
            link = r.find(filt_team_link)
            score_box = r.find(filt_team_score)
            place_box = r.find(filt_team_place)

            url = str(link["href"])

            self.log.info(url + "  " + place_box.string)

            t = {}
            t["team_id"] = re.match("user\?id=([0-9]+)", url)[1]
            t["name"] = str(link.string)
            t["score"] = str(score_box.string)
            t["place"] = int(re.match("([0-9]+)\.", place_box.string)[1])

            teams.append(t)

        return teams

