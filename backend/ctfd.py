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
        try:
            resp = requests.get(url, timeout=2)
        except:
            return False

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
        self.base_URL = self._baseurl(conf["url"])
        print(f"Attempting to use CTFd instance at {self.base_URL}")


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

        # This sets up the URLs and functions based on
        # autodetection of various ctfd versions. Not sure why there's such fragmentation.
        self._detect_version()

        # Several smaller CTFs have had load problems,
        # and a client like ours isn't going to help the matter.
        # Maybe CTFd is inefficient in its backend?
        # The right thing to do is to fall back to fewer requests.
        # The scoreboard can be queried in a single request, so we can
        # Just turn off challenge queries (which are quite cumbersome)
        if not self._test_connection():
            print("Connection test failed. You may need to authenticate, or the CTF hasn't started yet.")


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

    # Some CTFs disable the JSON API, so we have to fall back to stupid scraping techniques.
    def _detect_version(self):
        api_resp = self.session.get(self.base_URL + "/api/v1/scoreboard")
        if api_resp.status_code == 200:
            print("Using CTFd REST API.")
            self.scoreboard_URL = self.base_URL + "/api/v1/scoreboard"
            self.solve_URL = lambda challenge_id: self.base_URL + f"/api/v1/challenges/{challenge_id}/solves"
            self.challenges_URL = self.base_URL + "/api/v1/challenges"

            self._get_scoreboard = self._get_scoreboard_api
            self._get_solves = self._get_solves_api
            self._get_challenges = self._get_challenges_api

            return True

        # aeroCTF 2021 had some other version, with the API disabled
        # but special JSON endpoints for the challenges and solves
        # It smells a bit like an older version, before the structured REST API
        try:
            api_chals = self.session.get(self.base_URL + "/chals")
            j = api_chals.json()
            if api_chals.status_code == 200:
                print("Using sneaky API")
                self.scoreboard_URL = self.base_URL + "/scoreboard"
                self.solve_URL = lambda challenge_id: self.base_URL + f"/chal/{challenge_id}/solves"
                self.challenges_URL = self.base_URL + "/chals"

                self._get_scoreboard = self._get_scoreboard_scrape
                self._get_solves = self._get_solves_sneaky_api
                self._get_challenges = self._get_challenges_sneaky_api

                return True
        except:
            pass


        print("Unable to identify CTFd API version. Falling back to scrape and parse.")
        self.scoreboard_URL = self.base_URL + "/scoreboard"
        self.solve_URL = lambda challenge_id: self.base_URL + "/404"
        self.challenges_URL = self.base_URL + "/challenges"

        self._get_scoreboard = self._get_scoreboard_scrape
        self._get_solves = lambda challenge_id: []
        self._get_challenges = lambda: []
        self.do_challenges = False
        self.do_solves = False
        return False

    def _login(self):
        # Extract a nonce
        failed = False
        try:
            loginpage = self.session.get(self.base_URL + "/login")
        except:
            failed = True

        # Can't even load the login form
        if failed or loginpage.status_code != 200:
            print("Failed to load login page")
            return False

        soup = BeautifulSoup(loginpage.text, "html.parser")
        nonce = soup.find([
                            # This site has the proper REST API
                            lambda tag: tag.name == "input" and (tag.has_attr("id") and tag["id"] == "nonce"),

                            # This has the sneaky API
                            lambda tag: tag.name == "input" and (tag.has_attr("name") and tag["name"] == "nonce")
                          ])["value"]
        print(f"Login nonce: {nonce}")

        try:
            resp = self.session.post(self.base_URL + "/login", allow_redirects=False,
                data={ "nonce": nonce,
                       "_submit": "Submit",
                       "name": self.conf["username"],
                       "password": self.conf["password"] })
        except:
            print("Login timed out")
            return False

        # A 200 is a failed login, actually.
        # A successful login gives a 302 and redirects you.
        if resp.status_code != 302:
            return False

        return True

    #
    # Older JSON API, available for some of the data
    #

    def _get_solves_sneaky_api(self, challenge_id):
        ret = []

        try:
            resp = self.session.get(self.solve_URL(challenge_id), timeout=15)
        except ReadTimeout:
            return None

        try:
            msg = resp.json()
        except:
            print("Solves fetch failed:")
            print(resp.text)
            return None

        if not ("teams" in msg):
            print("solves fetch failed out:")
            print(msg)
            return ret

        for solv in msg["teams"]:
            ret.append(solv["id"])

        return ret

    def _get_challenges_sneaky_api(self, do_solves=False):

        ret = []

        try:
            resp = self.session.get(self.challenges_URL, timeout = 30)
        except ReadTimeout:
            return None

        if resp.status_code != 200:
            print("chall fetch failed:")
            print(resp.text)
            return None

        try:
            msg = resp.json()
        except:
            print("Chall fetch failed:")
            print(resp.text)
            return None

        if not ("game" in msg):
            print("chall fetch failed:")
            print(msg)
            return None

        for row in msg["game"]:
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



    #
    # Scrape the webpages like some sort of animal
    # This is only used if API access fails (i.e. API is disabled serverside)
    #

    def _get_scoreboard_scrape(self):
        teams = []

        failed = False

        # Handy dandy matrix of everything
        # Sadly, we have to parse the table, but that's allright
        try:
            resp = self.session.get(self.scoreboard_URL)
        except:
            failed = True

        if failed or resp.status_code != 200:
            print("Chall fetch failed")
            return None

        # BS filters to find the elements that we are interested in
        #filt_chall_link = lambda tag: tag.name == "a" and tag.has_attr("href") and "/internal/challenge/" in tag["href"]
        filt_team_row   = lambda tag: tag.name == "tr" and tag.parent.name == "tbody"

        # Accidentally detects ISO-8859 due to some german team names or something
        # The page is explicitly encoded as utf-8, though.
        resp.encoding = "utf-8"

        soup = BeautifulSoup(resp.text, "html.parser")
        rows     = soup.findAll(filt_team_row)

        for r in rows:
            head = r.find("th")
            cells = r.find_all("td")

            t = {}
            a = cells[0].find("a")
            url = a["href"]
            t["place"] = int(head.string)
            t["team_id"] = re.match("/team(s?)/([0-9]+)", url)[2]
            t["name"] = str(a.string)
            t["score"] = str(cells[1].string)

            teams.append(t)

        return teams

    def _get_solves_scrape(self, challenge_id):
        return []

    def _get_challenges_scrape(self, do_solves=False):

        ret = []
        return ret


    #
    # Use API, if it's allowed
    #

    def _get_scoreboard_api(self):
        failed = False
        try:
            resp = self.session.get(self.scoreboard_URL)
        except:
            failed = True

        if failed or resp.status_code != 200:
            print("Scoreboard fetch failed")
            return None

        try:
            msg = resp.json()
        except:
            print("Leaderboard fetch failed")
            return None

        if not ("success" in msg and msg["success"] == True):
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


    def _get_solves_api(self, challenge_id):
        ret = []

        try:
            resp = self.session.get(self.solve_URL(challenge_id), timeout=15)
        except ReadTimeout:
            return None

        try:
            msg = resp.json()
        except:
            print("Solves fetch failed:")
            print(resp.text)
            return None

        if not ("success" in msg and msg["success"] == True):
            print("solves fetch failed out:")
            print(msg)
            return ret

        for solv in msg["data"]:
            ret.append(solv["account_id"])

        return ret

    def _get_challenges_api(self, do_solves=False):

        ret = []

        try:
            resp = self.session.get(self.challenges_URL, timeout = 30)
        except ReadTimeout:
            return None

        if resp.status_code != 200:
            print("chall fetch failed:")
            print(resp.text)
            return None

        try:
            msg = resp.json()
        except:
            print("Chall fetch failed:")
            print(resp.text)
            return None

        if not ("success" in msg and msg["success"] == True):
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
                solves = self._get_solves_api(c["challenge_id"])
                if solves is None:
                    # Give up on that, this time around
                    do_solves = False
                else:
                    c["solves"] = solves

            ret.append(c)

        return ret



    def _test_connection(self):
        if self.do_challenges and self.authenticated:
            print("Testing server latency...")

            t0 = time.time()
            challs = self._get_challenges(False)
            t1 = time.time()

            if challs is None:
                self.do_challenges = False
                self.do_solves = False
                return False

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

        return True
