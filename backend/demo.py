import random
import time

from copy import deepcopy as CP

# A backend which generates nonsense data for a sort of attractor mode

class BackEnd:

    @staticmethod
    def help():
        return [
            "url: none",
            "auth: none"
        ]

    @staticmethod
    def supports(conf, url):
        # This backend should never be autodetected
        return False

    def __init__(self, conf, middleend):
        self.conf = conf
        self.middle = middleend


        self.team_names = [ "LuftensHjaltar", "ElectroH3xe", "Pappas Pojkar", "SpionFromage",  "L33tF33t",
                            "Ned Spandex",    "True Pink",   "x3",            "haxKLOWN",      "Sventon",
                            "F-string",       "buttHEX",     "9neinNEIN",     "Hell's Shells", "Twenty7",
                            "constrict0r",    "Mr.Hacker",   "xXx420xXx",     "Overfl0w",      "_______"
                          ]

        # These teams are always there for you.
        self.team_names += [ u"ȟ̴͖͖̯̿̀̑a̵̙̥̬͆̀x̸̟͙͆͜h̸̼͚͙̫́͗͑͘ä̵̟́͌̈́̃x̸̧͑͂́̕", "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA" ,
                             r"{__globals__}", "\033[12;31mANSIholes", "$(/bin/sh)"
                           ]

        self.challenge_names = [ "Revvy's Revenge", "Wafflz",          "PLIMby",    "This isn't wha...", "Hanky",
                                 "NESbitt",         "Kreislauf",       "Schlumpf",  "Rundfunk Röhmen",   "0xROP",
                                 "SwitchBleyd",     "Discombobulator", "EXCELsior", "Rusty Trombone",    "strlen",
                                 "Vladimir Login",  "Snoopy Cache",    "Smeltdown", "Forky",             "Y0 h0 and a bottle of Tschunk"
                               ]

        self.categories = [ "pwn", "web", "rev", "misc", "baby", "troll", "crypto", "osint" ]

        self.tid = 1000
        self.cid = 8000

        # ID is the key for both of these
        self.teams = {}
        self.challenges = {}

        # Everyone is ready and signed up
        for t in range(2):
            self._add_new_team()

        for c in range(3):
            self._add_new_challenge()

        self.events = [ self._event_new_team,
                        self._event_new_challenge,
                        self._event_solve
                      ]

    def start(self):
        # The bootup data
        self._send_snapshot()

        while True:
            time.sleep(1)
            self._random_event()
            self._send_snapshot()

    def stop(self):
        pass

    def update(self):
        pass

    def _event_new_team(self):
        self._add_new_team()
        self._sort_scoreboard()

    def _event_new_challenge(self):
        self._add_new_challenge()

    def _event_solve(self):
        tid = self._random_team()
        cid = self._random_challenge()

        if tid in self.challenges[cid]["solves"]:
            # That team already solved that challenge.
            return

        self.teams[tid]["score"] += self.challenges[cid]["points"]
        self.challenges[cid]["solves"].append(tid)

        self._sort_scoreboard()


    def _random_event(self):
        random.choice(self.events)()

    def _random_team(self):
        return random.choice(list(self.teams.keys()))

    def _random_challenge(self):
        return random.choice(list(self.challenges.keys()))

    def _pop_random(self, l):
        # Pick a unique entry from the list and remove it from the hat
        return l.pop(random.randrange(len(l)))

    # Recalculate the place of all teams
    def _sort_scoreboard(self):
        # Need to preserve previous ordering if there is a tie,
        # so start by assembling a list with the existing ranking
        all_scores = [ (tid, t["place"], t["score"]) for tid,t in self.teams.items() ]

        old_ranking = reversed(sorted(all_scores, key=lambda x: x[1]))

        # With that order established, sort them by current score instead
        new_ranking = reversed(sorted(old_ranking, key=lambda x: x[2]))

        # Write the new ranking back into the saved scoreboard
        place = 1
        for tid,_,_ in new_ranking:
            self.teams[tid]["place"] = place
            place += 1

    def _add_new_team(self):
        if len(self.team_names) == 0: return

        name = self._pop_random(self.team_names)
        self.tid += 1
        entry = { "team_id": str(self.tid),
                  "name": name,
                  "place": len(self.teams) + 1,
                  "score": 0
                }
        self.teams[entry["team_id"]] = entry

        return entry["team_id"]

    def _add_new_challenge(self):
        if len(self.challenge_names) == 0: return

        name = self._pop_random(self.challenge_names)
        categories = random.choices(self.categories, k=random.randint(1,3))
        self.cid += 1
        entry = { "challenge_id": str(self.cid),
                  "name": name,
                  "categories": categories,
                  "solves": [],
                  "points": 100 * random.randint(1, 10)
                }
        self.challenges[entry["challenge_id"]] = entry

        return entry["challenge_id"]

    def _send_snapshot(self):
        scores = [ team for tid,team in self.teams.items() ]
        challenges = [ chall for cid,chall in self.challenges.items() ]
        self.middle.handle_snapshot(CP(("challenges", { "challenges": challenges })))
        self.middle.handle_snapshot(CP(("scoreboard", { "scores": scores })))
        #self._dump_ranking()

    def _dump_ranking(self):
        print("Ranking:")
        ranking = [ (t["place"], tid, t) for tid,t in self.teams.items() ]
        ranking = sorted(ranking, key=lambda x: x[0])

        for place,tid,t in ranking:
            print(f"  {place}: {t['score']}  {tid}  {t['name']}")

