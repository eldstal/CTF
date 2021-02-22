import re
import time

from copy import deepcopy as CP
import requests

class BackEnd:

    @staticmethod
    def help():
        return [
            "url: none",
            "auth: team token (optional, needed for challenges and solves)",
            "poll-interval: seconds",
        ]

    @staticmethod
    def supports(conf, url):
        # Return True if the url seems like a system we support
        resp = requests.get(url)

        # The web interface is quite obfuscated. This meta tag is on several pages, though.
        if "rctf-config" in resp.text:
            return True
        return False

    def __init__(self, conf, middleend):
        self.conf = conf
        self.middle = middleend

        if conf["url"] == "":
            raise RuntimeError("This backend requires a URL")


        # Help the user out a little bit, they can specify some various links
        self.URL = self._baseurl(conf["url"])
        print(f"Attempting to use rCTF instance at {self.URL}")


        self.session = requests.Session()
        self.authenticated = False
        self.authtoken = ""

        self.do_challenges = False
        self.do_solves = False


        if "auth" in conf:
            if self._login():
                print("Logged in successfully.")
                self.authenticated = True
                self.do_challenges = True
                self.do_solves = True

            else:
                print("Login failed. Scores will still be available, but no challs/solves")


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
        url = re.sub("/scores.*", "", url)
        url = re.sub("/login.*", "", url)
        return url

    def _login(self):
        failed = False
        try:
            resp = self.session.post(self.URL + "/api/v1/auth/login", json={ "teamToken": self.conf["auth"] })
            msg = resp.json()
        except:
            failed = True

        if failed or resp.status_code != 200:
            print("Login failed.")
            return False

        if msg["kind"] == "goodLogin":
            self.authtoken = msg["data"]["authToken"]
            self.session.headers.update({ "Authorization": f"Bearer {self.authtoken}" }) 
            return True

        return False

    def _get_scoreboard(self):
        # We can only request 100 at a time, so we need to chain multiple requests.
        leader_data = []
        expected_length = 1
        while len(leader_data) < expected_length:
            failed = False
            try:
                resp = self.session.get(self.URL + "/api/v1/leaderboard/now", params={ "limit": 100, "offset": len(leader_data)})
                msg = resp.json()
            except:
                failed = True

            if failed or "kind" not in msg or msg["kind"] != "goodLeaderboard":
                print("leaderboard fetch failed")
                return None

            expected_length = msg["data"]["total"]

            leader_data += msg["data"]["leaderboard"]


        # Convert into the format we expect
        scoreboard_snapshot = [
                                   { "name": t["name"],
                                     "team_id" : t["id"],
                                     "score": t["score"],
                                     "place": index+1 }
                                   for index,t in enumerate(leader_data)
                              ]
        return scoreboard_snapshot

    def _get_solves(self, challenge_id, count=100):
        ret = []
        expected_length = count
        while len(ret) < expected_length:
            try:
                resp = self.session.get(self.URL + f"/api/v1/challs/{challenge_id}/solves",
                                        params={"limit": 10, "offset": len(ret)},
                                        timeout=15)

                msg = resp.json()
            except ReadTimeout:
                return None

            except:
                return None

            if msg["kind"] != "goodChallengeSolves":
                print("solves fetch failed out:")
                print(msg)
                return ret

            for s in msg["data"]["solves"]:
                ret.append(s["userId"])
        return ret

    def _get_challenges(self, do_solves=False):
        # We can only request 100 at a time, so we need to chain multiple requests.
        ret = []

        failed = False
        try:
            resp = self.session.get(self.URL + "/api/v1/challs", timeout=10)
            msg = resp.json()
        except ReadTimeout:
            failed = True
        except:
            failed = True

        if failed or not ("kind" in msg and msg["kind"] == "goodChallenges"):
            print("chall fetch failed")
            return None

        for row in msg["data"]:
            c = {
                    "name": row["name"],
                    "challenge_id": row["id"],
                    "points": row["points"],
                    "categories": [ row["category"] ]

                }

            if do_solves:
                solves = self._get_solves(c["challenge_id"], count=row["solves"])
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
            challs = self._get_challenges(True)
            t1 = time.time()

            chall_duration = int(t1 - t0)
            if chall_duration > 10:
                print(f"Fetching challenges/solves took {chall_duration} seconds! This host is probably slow or overloaded. Disabling challenges/solves.")
                self.do_challenges = False
                self.do_solves = False

