import unittest

from middleend.basic import MiddleEnd
from copy import deepcopy as CP

dummy_chall_1 = {
    "challenge_id": "cha1",
    "solves": [],
    "categories": [ "pwn" ],
    "name": "dummy 1",
    "points": 11
}

dummy_chall_2 = {
    "challenge_id": "cha2",
    "solves": [],
    "categories": [ "re", "baby" ],
    "name": "dummy 2",
    "points": 12
}

dummy_team_1 = {
    "team_id": "T12345",
    "name": "Team 1",
    "place": 2,
    "score": 25
}

dummy_team_2 = {
    "team_id": "T55443",
    "name": "Team 2",
    "place": 1,
    "score": 12
}

dummy_team_3 = {
    "team_id": "T333",
    "name": "Team Drei",
    "place": 3,
    "score": 190
}

class LogFrontEnd:
    def __init__(self, skip_boot=False):
        self.skip_boot = skip_boot
        self.log = []

    def handle_event(self, event):
        if self.skip_boot and event[0] == "boot":
            return

        self.log.append(event)

    # If there are multiple that are expected at the same time,
    # maybe this way we can make them come out in a more predictable order
    # This sorts by message name, followed by input order
    def sort_events(self):
        self.log = list(sorted(self.log, key=lambda x: x[0]))

class TestMiddleEnd(unittest.TestCase):

    def conf(self):
        return {}

    # The very first scoreboard data from the backend
    # should trigger a "boot" message with all known info
    # to bootstrap the frontend and have an actual info display.
    def test_boot(self):
        front = LogFrontEnd()
        mid = MiddleEnd(self.conf(), front)

        self.assertEqual(front.log, [])

        # Only the scoreboard message should trigger the boot message
        mid.handle_snapshot(CP(("challenges", { "challenges" : [ dummy_chall_1 ] })))
        self.assertEqual(front.log, [])

        # Only the scoreboard message should trigger the boot message
        mid.handle_snapshot(CP(("scoreboard", { "scores" : [ dummy_team_2, dummy_team_1 ] })))

        # No additional events should be sent before the boot,
        # and the initial information is __only__ a boot message.
        self.assertEqual(len(front.log), 1)

        msg,data = front.log[0]
        self.assertEqual(msg, "boot")

        self.assertTrue("challenges" in data)
        self.assertEqual(data["challenges"], { "challenges" : [ dummy_chall_1 ] })

        self.assertTrue("scoreboard" in data)
        self.assertEqual(data["scoreboard"], { "scores" : [ dummy_team_2, dummy_team_1 ] })


    def test_firstblood(self):
        front = LogFrontEnd(skip_boot = True)
        mid = MiddleEnd(self.conf(), front)

        # Set up a CTF base state
        mid.handle_snapshot(CP(("challenges", { "challenges" : [ dummy_chall_1 ] })))
        mid.handle_snapshot(CP(("scoreboard", { "scores" : [ dummy_team_2, dummy_team_1, dummy_team_3 ] })))
        self.assertEqual(front.log, [])

        # Two teams solved challenge 1
        new_chall_1 = CP(dummy_chall_1)
        new_chall_1["solves"].append(dummy_team_1["team_id"])
        new_chall_1["solves"].append(dummy_team_2["team_id"])
        mid.handle_snapshot(CP(("challenges", { "challenges" : [ new_chall_1 ] })))

        # We expect two solves to come out of this.
        # First, team 1 with a first:True
        # Second, team 2 with first:False
        self.assertEqual(len(front.log), 2)

        msg,data = front.log[0]
        self.assertEqual(msg, "solve")

        self.assertEqual(data["challenge_id"], new_chall_1["challenge_id"])
        self.assertEqual(data["team_id"], dummy_team_1["team_id"])
        self.assertEqual(data["first"], True)

        msg,data = front.log[1]
        self.assertEqual(msg, "solve")

        self.assertEqual(data["challenge_id"], new_chall_1["challenge_id"])
        self.assertEqual(data["team_id"], dummy_team_2["team_id"])
        self.assertEqual(data["first"], False)


        # Straggler team 3 also don't get a first blood, obviously
        # Two teams solved challenge 1
        front.log = []
        new_chall_1 = CP(new_chall_1)
        new_chall_1["solves"].append(dummy_team_3["team_id"])
        mid.handle_snapshot(CP(("challenges", { "challenges" : [ new_chall_1 ] })))

        # We expect a solve notification, though
        self.assertEqual(len(front.log), 1)

        msg,data = front.log[0]
        self.assertEqual(msg, "solve")

        self.assertEqual(data["challenge_id"], new_chall_1["challenge_id"])
        self.assertEqual(data["team_id"], dummy_team_3["team_id"])
        self.assertEqual(data["first"], False)



    def test_challs(self):
        front = LogFrontEnd(skip_boot = True)
        mid = MiddleEnd(self.conf(), front)

        # Set up a CTF base state
        mid.handle_snapshot(CP(("challenges", { "challenges" : [ dummy_chall_1 ] })))
        mid.handle_snapshot(CP(("scoreboard", { "scores" : [ dummy_team_2, dummy_team_1 ] })))
        self.assertEqual(front.log, [])

        # Someone solved challenge 1
        new_chall_1 = CP(dummy_chall_1)
        new_chall_1["solves"].append(dummy_team_1["team_id"])
        mid.handle_snapshot(CP(("challenges", { "challenges" : [ new_chall_1 ] })))

        self.assertEqual(len(front.log), 1)

        msg,data = front.log[0]
        self.assertEqual(msg, "solve")

        self.assertEqual(data["challenge_id"], new_chall_1["challenge_id"])
        self.assertEqual(data["team_id"], dummy_team_1["team_id"])
        self.assertEqual(data["first"], True)

        front.log = []


        # Someone else solved challenge 1 also
        new_chall_1 = CP(new_chall_1)
        new_chall_1["solves"].append(dummy_team_2["team_id"])
        mid.handle_snapshot(CP(("challenges", { "challenges" : [ new_chall_1 ] })))

        self.assertEqual(len(front.log), 1)

        msg,data = front.log[0]
        self.assertEqual(msg, "solve")

        self.assertEqual(data["challenge_id"], new_chall_1["challenge_id"])
        self.assertEqual(data["team_id"], dummy_team_2["team_id"])
        self.assertEqual(data["first"], False)



    def test_teams(self):
        front = LogFrontEnd(skip_boot = True)
        mid = MiddleEnd(self.conf(), front)

        # Set up a CTF base state
        mid.handle_snapshot(CP(("challenges", { "challenges" : [ dummy_chall_1 ] })))
        mid.handle_snapshot(CP(("scoreboard", { "scores" : [ dummy_team_2, dummy_team_1 ] })))
        self.assertEqual(front.log, [])

        # A new team enters. Before we have time to notice, they also nab second place!

        t_1 = CP(dummy_team_1)
        t_2 = CP(dummy_team_2)
        t_3 = CP(dummy_team_1)

        t_3["team_id"] = "T33333"
        t_3["name"] = "Intruders"
        t_3["place"] = 2
        t_3["score"] = t_1["score"] + 2

        t_1["place"] = 3

        mid.handle_snapshot(CP(("scoreboard", { "scores" : [ t_2, t_3, t_1 ] })))

        # We expect two events. First, there's a new team in town
        front.sort_events()
        self.assertEqual(len(front.log), 2)

        msg,data = front.log[0]
        self.assertEqual(msg, "new_team")
        self.assertEqual(data, t_3)

        # Second event: team 1 had their place changed
        msg,data = front.log[1]
        self.assertEqual(msg, "place")
        self.assertEqual(data["team_id"], t_1["team_id"])
        self.assertEqual(data["old_place"], 2)
        self.assertEqual(data["place"], 3)

    # The backend can omit data if it wants to.
    def test_incomplete(self):
        front = LogFrontEnd(skip_boot = True)
        mid = MiddleEnd(self.conf(), front)

        # Set up a CTF base state
        mid.handle_snapshot(CP(("challenges", { "challenges" : [ dummy_chall_1 ] })))
        mid.handle_snapshot(CP(("scoreboard", { "scores" : [ dummy_team_2, dummy_team_1 ] })))
        self.assertEqual(front.log, [])

        # For some weird reason, the backend loses the ability to check scores. It only gets the order of teams.
        t_1 = CP(dummy_team_1)
        t_2 = CP(dummy_team_2)

        del(t_1["score"])
        del(t_2["score"])

        # The teams do change places, though
        t_1["place"] = 1
        t_2["place"] = 2

        mid.handle_snapshot(CP(("scoreboard", { "scores" : [ t_1, t_2 ] })))

        # We expect two events, one for each team's new place
        front.sort_events()
        self.assertEqual(len(front.log), 2)

        # First event, should come from team_1 since it was the first reported
        msg,data = front.log[0]
        self.assertEqual(msg, "place")
        self.assertEqual(data["team_id"], t_1["team_id"])
        self.assertEqual(data["old_place"], 2)
        self.assertEqual(data["place"], 1)

        # Second event, team_2 also changed place
        msg,data = front.log[1]
        self.assertEqual(msg, "place")
        self.assertEqual(data["team_id"], t_2["team_id"])
        self.assertEqual(data["old_place"], 1)
        self.assertEqual(data["place"], 2)

