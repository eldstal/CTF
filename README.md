# CTF
CTF Terminal Frontend

## Backend
Fetches scoreboard and team stats and stuff from a CTF server. Tailor one to whatever score system the event is using.

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
        "points": 500,
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
All the above.

## Backends
- CTFd
- rCTF
- ...

Auto-detection would be cool, so the user can provide a URL and a proper backend is selected automatically. This should be possible with some well-chosen fingerprints.

## Frontend
A simple print-a-table thing to begin with

After that, the [sky](https://blessed.readthedocs.io/en/latest/) is the limit!

Support is in place for multiple frontends active at the same time, so maybe one for sound, one for video, one for external lighting effects, etc.

## Nepotism
Support for "special" teams to always keep visible. My team is blue, the bad guys are gray. Boo, those guys!
