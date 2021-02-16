# CTF
CTF Terminal Frontend

```
usage: ctfront.py [-h] [--frontend [FRONTEND [FRONTEND ...]]] [--list-frontends] [--backend BACKEND] [--list-backends] [--focus-team [FOCUS_TEAM [FOCUS_TEAM ...]]] [--poll-interval POLL_INTERVAL] [--config CONFIG] [--url URL] [--auth AUTH]

Fetch and display a live CTF scoreboard

optional arguments:
  -h, --help            show this help message and exit
  --frontend [FRONTEND [FRONTEND ...]], -f [FRONTEND [FRONTEND ...]]
                        Add a frontend
  --list-frontends, -F  List known frontends
  --backend BACKEND, -b BACKEND
                        Specify a CTF backend
  --list-backends, -B   List known frontends
  --focus-team [FOCUS_TEAM [FOCUS_TEAM ...]], -t [FOCUS_TEAM [FOCUS_TEAM ...]]
                        One or more team names (regex) to always show
  --poll-interval POLL_INTERVAL, -i POLL_INTERVAL
                        Seconds between server polling. Don't set this too low!
  --config CONFIG, -c CONFIG
                        Load a configuration file.
  --url URL, -u URL     URL to scoreboard. See backend list for specifics.
  --auth AUTH, -a AUTH  Auth token for scoreboard. See backend list for specifics.

```

## Backend
Fetches scoreboard and team stats and stuff from a CTF server. Tailor one to whatever score system the event is using.

Optionally implements autodetection ("Does this URL point to a CTF system I can handle?").

## Middle-end
Keeps a running copy of the CTF state and identifies changes. Sends events to the front-end when something interesting changes.

## Front-end
Receives specific updates from the Middle-end and renders it.

Obviously, the front-end is free to ignore events as needed. You could make a front-end which only flashes your keyboard LEDs when `p4` scores points!


# Protocols

## Back -> Middle
Backend sends a snapshot message periodically (poll the server or whatever).

A message is a tuple of `("message_type", { "data" : 1234 })` as specified below:
Most fields may be omitted if unknown. Middle-end will treat this as "No change".
The top-level list (`scores` and `challenges`) must be a complete listing.

`team_id` and `challenge_id` are *mandatory* and decided by the backend. These must remain stable throughout the tournament. If the server doesn't provide something suitable, hash the team name or something.


```python
(
    "scoreboard",
    {
        "scores": [
                     {
                        "team_id": "team_id_1",
                        "name": "LuftensHjaltar",
                        "place": 69,
                        "score": 31337
                     },
                     ...
                  ]
    }
)
```


```python
(
    "challenges",
    {
        "challenges" = [
                           {
                               "challenge_id" : "challenge_x",
                               "solves": [ "team_1", ... ],
                               "name": "S4n1ty Ch3ck",
                               "points": 25,
                               "categories": [ "pwn", "re" ]
                           },
                            ...
                       ]
    }
)
```


## Middle -> Front

Middle-end sends individual events to the frontend when something changes.

Omitted fields indicate that data is not available, so frontend should format accordingly (i.e. if no team has a "score" field, don't show a score column).

```python
(
    "boot",
    {
        "scoreboard": {  same format as scoreboard snapshot  }
        "challenges": {  same format as challenges snapshot  }
    }
)
```

```python
(
    "solve",
    {
        "team_id": "team_1",
        "challenge_id": "challenge_x",
        "first": True
    }
)
```

```python
(
    "place",
    {
        "team_id": "team_1",
        "old_place": 69,
        "place": 65
    }
)
```

```python
(
    "score",
    {
        "team_id": "team_1",
        "old_score": 1335,
        "score": 2001
    }
)
```

```python
(
    "new_challenge",
    {
        "challenge_id": "challenge_x",
        "name": "Grognar's Revenge",
        "points": 500,
        "solves": [ "team_id_a", "team_id_b" ],
        "categories": [ "pwn", "re" ]
    }
)

```

```python
(
    "new_team", { Same format as a team on the scoreboard }
)
```

# TODO

## Backends
- CTFd
- ...

A global (persistent) cookie jar to keep from having to authenticate new sessions on every restart

## Frontend
A simple print-a-table thing to begin with, this is already implemented as `--frontend basic`

After that, the [sky](https://blessed.readthedocs.io/en/latest/) is the limit!

Support is in place for multiple frontends active at the same time, so maybe one for sound, one for video, one for external lighting effects, etc.

