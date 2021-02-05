from copy import deepcopy as CP

class MiddleEnd:
    def __init__(self, conf, frontends):
        self.conf = conf

        # If the user eats crayons and passes in a single frontend instead of a list,
        # that's fine. It's fine. We can clean up your mess for you. No problem.
        try:
            check = iter(frontends)
        except:
            frontends = [frontends]

        self.frontends = frontends
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


    def _compare_field(self, field, send_func, old_entry, new_entry, default_old=0):
        if field not in new_entry:
            return

        old_value = default_old
        if field in old_entry:
            old_value = old_entry[field]
            if new_entry[field] == old_value:
                return

        send_func(old_entry, new_entry, old_value)

    def _handle_scoreboard(self, in_data):
        # Diff against the old list and generate events
        for new_entry in in_data["scores"]:
            tid = new_entry["team_id"]
            old_entry = self._find_team(tid)
            if old_entry is None:
                self._send_event( ("new_team", new_entry) )
                self.ctfstate["scoreboard"]["scores"].append(new_entry)
                continue

            self._compare_field("score", self._send_team_score,
                                         old_entry, new_entry,
                                         0)

            self._compare_field("place", self._send_team_place,
                                         old_entry, new_entry,
                                         1000)

            # Copy all the new data into the scoreboard
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
                continue

            self._compare_field("solves", self._send_challenge_solves,
                                         old_entry, new_entry,
                                         [])
            for k,v in new_entry.items():
                old_entry[k] = v

        # Keep them sorted by challenge id, for simplicity
        self.ctfstate["challenges"]["challenges"] = list(sorted(self.ctfstate["challenges"]["challenges"], key=lambda x: x["challenge_id"]))

        pass


    def _send_boot(self):
        payload = {}
        payload["scoreboard"] = self.ctfstate["scoreboard"]
        if len(self.ctfstate["challenges"]["challenges"]) > 0:
            payload["challenges"] = self.ctfstate["challenges"]

        self._send_event( ("boot", payload) )

    def _send_team_score(self, old_entry, new_entry, old_value):
        self._send_event(
            ( "score", {
                       "team_id": new_entry["team_id"],
                       "old_score": old_value,
                       "score": new_entry["score"]
                       }
            )
        )

    def _send_team_place(self, old_entry, new_entry, old_value):
        self._send_event(
            ( "place", {
                       "team_id": new_entry["team_id"],
                       "old_place": old_value,
                       "place": new_entry["place"]
                       }
            )
        )


    def _send_challenge_solves(self, old_entry, new_entry, old_value):
        is_first = False
        for tid in new_entry["solves"]:
            if tid in old_value: continue

            is_first = (len(old_value) == 0) and not is_first

            self._send_event(
                ( "solve", {
                           "team_id": tid,
                           "challenge_id": new_entry["challenge_id"],
                           "first": is_first
                           }
                )
            )



    # Drop events before boot event has been sent out
    # This way, the diffing code is kept free from
    # boot checks.
    def _send_event(self, event):
        if not self.booted:
            if event[0] != "boot":
                return
            self.booted = True

        for front in self.frontends:
            # Prevent accidental leaks of internal object references
            front.handle_event(CP(event))



