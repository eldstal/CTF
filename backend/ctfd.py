import re
import time
from datetime import datetime

from copy import deepcopy as CP

from bs4 import BeautifulSoup
import requests
from requests.exceptions import ReadTimeout

class BackEnd:

    @staticmethod
    def help():
        return [
            "url: none",
            "username: (optional, needed for challenges and solves)",
            "password: (optional, needed for challenges and solves)",
            "poll-interval: seconds",
        ]

    @staticmethod
    def supports(conf, url):
        # Return True if the url seems like a system we support
        resp = requests.get(url)

        # This is in the footer of every page.
        if "Powered by CTFd" in resp.text:
            return True
        return False

    def __init__(self, conf, middleend):
        self.conf = conf
        self.middle = middleend

        if conf["url"] == "":
            raise RuntimeError("This backend requires a URL")


        # Help the user out a little bit, they can specify some various links
        self.URL = self._baseurl(conf["url"])
        print(f"Attempting to use CTFd instance at {self.URL}")


        self.session = requests.Session()
        self.authenticated = False
        self.authtoken = ""

        self.do_challenges = False
        self.do_solves = False

        if conf["username"] != "" and conf["password"] != "":
            if self._login():
                print("Logged in successfully.")
                self.authenticated = True
                self.do_challenges = True
                self.do_solves = True
            else:
                print("Login failed. Scores will still be available, but no challs/solves")


        # Several smaller CTFs have had load problems,
        # and a client like ours isn't going to help the matter.
        # Maybe CTFd is inefficient in its backend?
        # The right thing to do is to fall back to fewer requests.
        # The scoreboard can be queried in a single request, so we can
        # Just turn off challenge queries (which are quite cumbersome)
        self._test_latency()


    def run(self):
        self.running = True
        while self.running:
            if self.do_challenges and self.authenticated:
                challs = self._get_challenges(self.do_solves)
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
        url = re.sub("/scoreboard.*", "", url)
        url = re.sub("/login.*", "", url)
        return url

    def _login(self):
        # Extract a nonce
        loginpage = self.session.get(self.URL + "/login")

        soup = BeautifulSoup(loginpage.text, "html.parser")
        nonce = soup.find("input", id="nonce")["value"]
        print(f"Login nonce: {nonce}")

        resp = self.session.post(self.URL + "/login", allow_redirects=False,
            data={ "nonce": nonce,
                   "_submit": "Submit",
                   "name": self.conf["username"],
                   "password": self.conf["password"] })

        # A 200 is a failed login, actually.
        # A successful login gives a 302 and redirects you.
        if resp.status_code != 302:
            return False

        return True

    def _get_scoreboard(self):
        resp = self.session.get(self.URL + "/api/v1/scoreboard")

        if resp.status_code != 200:
            print("chall fetch failed:")
            print(resp.text)
            return None

        msg = resp.json()

        if msg["success"] != True:
            print("leaderboard fetch failed:")
            print(msg)
            return None


        # Convert into the format we expect
        scoreboard_snapshot = [
                                   { "name": t["name"],
                                     "team_id" : t["account_id"],
                                     "score": t["score"],
                                     "place": t["pos"] }
                                   for index,t in enumerate(msg["data"])
                              ]
        return scoreboard_snapshot

    def _get_solves(self, challenge_id):
        ret = []

        try:
            resp = self.session.get(self.URL + f"/api/v1/challenges/{challenge_id}/solves", timeout=15)
        except ReadTimeout:
            return None

        msg = resp.json()

        if msg["success"] != True:
            print("solves fetch failed out:")
            print(msg)
            return ret

        for solv in msg["data"]:
            ret.append(solv["account_id"])

        return ret

    def _get_challenges(self, do_solves=False):

        ret = []

        try:
            resp = self.session.get(self.URL + "/api/v1/challenges", timeout = 30)
        except ReadTimeout:
            return None

        if resp.status_code != 200:
            print("chall fetch failed:")
            print(resp.text)
            return None

        msg = resp.json()

        if msg["success"] != True:
            print("chall fetch failed:")
            print(msg)
            return None

        for row in msg["data"]:
            c = {
                    "name": row["name"],
                    "challenge_id": row["id"],
                    "points": row["value"],
                    "categories": [ row["category"] ]

                }

            if do_solves:
                solves = self._get_solves(c["challenge_id"])
                if solves is None:
                    # Give up on that, this time around
                    do_solves = False
                else:
                    c["solves"] = solves

            ret.append(c)

        return ret

    def _test_latency(self):
        if self.do_challenges and self.authenticated:
            print("Testing server latency...")

            t0 = time.time()
            challs = self._get_challenges(False)
            t1 = time.time()

            chall_duration = int(t1 - t0)
            if chall_duration > 10:
                print(f"Fetching challenges took {chall_duration} seconds! This host is probably slow or overloaded. Disabling challenges/solves.")
                self.do_challenges = False
                self.do_solves = False

            # Fetching solves is particularly slow on CTFd for some reason
            t1 = time.time()
            if self.do_solves:
                for c in challs[:5]:
                    self._get_solves(c["challenge_id"])
            t2 = time.time()

            solve_duration = int(t2 - t1)
            if solve_duration > 15:
                print(f"Fetching a few solves took {solve_duration} seconds! This host is probably slow or overloaded. Disabling solves.")
                self.do_solves = False
