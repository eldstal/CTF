from copy import deepcopy as CP

class MiddleEnd:
    def __init__(self, frontend):
        self.front = frontend
        self.booted = False

        # The internal CTF snapshot
        self.ctfstate = {
            "scoreboard": {
                "scores": []
            },

            "challenges": {
                "challenges": []
            }

        }


    # A snapshot of some data from the backend
    def handle_snapshot(self, snapshot):
        assert(type(snapshot) == tuple)
        assert(len(snapshot) == 2)
        msg, in_data = snapshot

        handlers = {
            "scoreboard" : self._handle_scoreboard,
            "challenges" : self._handle_challenges
        }

        if msg not in handlers:
            sys.stderr.write(f"ERROR: Unexpected message {msg} received from back-end")
            return

        handlers[msg](in_data)

        # Special case: The very first scoreboard data
        # triggers a "boot" message to the frontend
        # containing everything we know.
        if not self.booted:
            if msg == "scoreboard":
                self._send_boot()

    # Returns a team's existing entry on the scoreboard, or None if there is none
    def _find_team(self, team_id):
        for t in self.ctfstate["scoreboard"]["scores"]:
            if t["team_id"] == team_id: return t
        return None

    # Returns a team's existing entry on the scoreboard, or None if there is none
    def _find_challenge(self, challenge_id):
        for c in self.ctfstate["challenges"]["challenges"]:
            if c["challenge_id"] == challenge_id: return c
        return None

    def _handle_scoreboard(self, in_data):
        # Diff against the old list and generate events
        for new_entry in in_data["scores"]:
            tid = new_entry["team_id"]
            old_entry = self._find_team(tid)
            if old_entry is None:
                self._send_event( ("new_team", new_entry) )
                self.ctfstate["scoreboard"]["scores"].append(new_entry)
            else:
                if new_entry["score"] != old_entry["score"]:
                    self._send_event(
                        ( "score", {
                                   "team_id": tid,
                                   "old_score": old_entry["score"],
                                   "score": new_entry["score"]
                                   }
                        )
                    )

                if new_entry["place"] != old_entry["place"]:
                    self._send_event(
                        ( "place", {
                                   "team_id": tid,
                                   "old_place": old_entry["place"],
                                   "place": new_entry["place"]
                                   }
                        )
                    )
                for k,v in new_entry.items():
                    old_entry[k] = v

        # We've updated all the team entries, but they are still in the old order.
        self.ctfstate["scoreboard"]["scores"] = list(sorted(self.ctfstate["scoreboard"]["scores"], key=lambda x: x["place"]))

    def _handle_challenges(self, in_data):
        # Diff against the old list and generate events
        for new_entry in in_data["challenges"]:
            cid = new_entry["challenge_id"]
            old_entry = self._find_challenge(cid)
            if old_entry is None:
                self._send_event( ("new_challenge", new_entry) )
                self.ctfstate["challenges"]["challenges"].append(new_entry)
            else:
                if len(new_entry["solves"]) != len(old_entry["solves"]):
                    for tid in new_entry["solves"]:
                        if tid in old_entry["solves"]: continue

                        is_first = len(old_entry["solves"]) == 0

                        self._send_event(
                            ( "solve", {
                                       "team_id": tid,
                                       "challenge_id": cid,
                                       "first": is_first
                                       }
                            )
                        )

                        old_entry["solves"].append(tid)

                for k,v in new_entry.items():
                    old_entry[k] = v

        # Keep them sorted by challenge id, for simplicity
        self.ctfstate["challenges"]["challenges"] = list(sorted(self.ctfstate["challenges"]["challenges"], key=lambda x: x["challenge_id"]))

        pass


    def _send_boot(self):
        payload = {}
        payload["scoreboard"] = CP(self.ctfstate["scoreboard"])
        if len(self.ctfstate["challenges"]["challenges"]) > 0:
            payload["challenges"] = CP(self.ctfstate["challenges"])

        self._send_event( ("boot", payload) )


    # Drop events before boot event has been sent out
    # This way, the diffing code is kept free from
    # boot checks.
    def _send_event(self, event):
        if not self.booted:
            if event[0] != "boot":
                return
            self.booted = True

        # Prevent accidental leaks of internal object references
        self.front.handle_event(CP(event))



