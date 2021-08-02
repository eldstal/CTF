import logging
import re
import time
import hashlib
import urllib.parse

from bs4 import BeautifulSoup
import requests
from requests.exceptions import ReadTimeout

class BackEnd:

    @staticmethod
    def help():
        return [
            "url: ex https://ctf.rars.win",
            "poll-interval: seconds",
        ]

    @staticmethod
    def supports(conf, url):

        url_base = BackEnd._baseurl(url)

        # Return True if the url seems like a system we support
        resp = requests.get(url)

        # This is a compiled hyperblob of reactJS code. Absolutely awful.
        # The best heuristic I've found is the RACTF credit embedded in one
        # of the javascript blobs.

        soup = BeautifulSoup(resp.text, "html.parser")

        filt_script = lambda tag: tag.name == "script" and tag.has_attr("src")

        for js in soup.findAll(filt_script):
            js_url = url_base + js["src"]
            js_resp = requests.get(js_url)
            if "RACTF" in js_resp.text:
                return True

        #lcase = resp.text.lower()
        return False

    @staticmethod
    def _baseurl(url):

        # XXX: This relies on the top-level site being the CTF system.

        url_parts = urllib.parse.urlparse(url)
        url_parts = url_parts._replace(path="", params="", query="", fragment="")
        url_base = url_parts.geturl()

        return url_base

    def _apiurl(self, url):
        # The API may be on a different host. We have to extract it from the javascript sources.

        resp = requests.get(BackEnd._baseurl(url))

        api_re = re.compile(".*apiDomain:'([^']+)'.*")
        match = api_re.match(resp.text)

        if match is None:
            raise RuntimeError("Unable to determine API URL. This may not be an RACTF system.")

        return match.groups(1)[0]


    def __init__(self, conf, middleend):
        self.conf = conf
        self.middle = middleend
        self.log = logging.getLogger(__name__)

        if conf["url"] == "":
            raise RuntimeError("This backend requires a URL")


        # Help the user out a little bit, they can specify some various links
        self.URL = self._apiurl(BackEnd._baseurl(conf["url"]))
        self.log.info(f"Attempting to use RACTF instance at {self.URL}")

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

    def _get_scoreboard(self):

        teams = []

        failed = False
        try:
            resp = self.session.get(self.URL + "/api/v2/leaderboard/team/?limit=1000")
        except:
            failed = True

        if failed or resp.status_code != 200:
            self.log.warning("scoreboard fetch failed:")
            #self.log.warning(resp.text)
            return None

        data = resp.json()

        if "d" not in data:
            self.log.warning("scoreboard format unexpected:")
            self.log.warning(resp.text)

        if "results" not in data["d"]:
            self.log.warning("scoreboard format unexpected:")
            self.log.warning(resp.text)

        for k,v in enumerate(data["d"]["results"]):
            t = {}
            t["name"]    = v["name"]
            t["team_id"] = v["id"]
            t["place"]   = k
            t["score"]   = v["leaderboard_points"]

            teams.append(t)

        return teams
