# CTF
CTF Terminal Formatting


## Backend
Fetches scoreboard and team stats and stuff from a CTF server. Tailor one to whatever score system the event is using.

## Middle-end
Keeps a running copy of the CTF state and identifies changes. Sends events to the front-end

## Front-end
Receives specific updates from the Middle-end and renders it. 


# Protocols

## Back -> Middle
Backend sends a message periodically (poll the server or whatever).

A message is a tuple of `("message_type", { "data" : 1234 })` as specified below:



```python
(
    "scoreboard",
    {
        "scores": [
                     {
                        "id": "team_id_1",
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
                               "id" : "chall_id_1",
                               "solves": [ "team_id_1", ... ],
                               "name": "S4n1ty Ch3ck",
                               "points": 25
                            },
                            ...
                       ]
    }
)
```


# TODO
All the above.

## Backends
- A demo backend that just exercises the various features
- CTFd
- rCTF
- ...

## Middle-end
Probably only need one, which is nice.

## Front-end
A simple print-a-table thing to begin with

After that, the [sky](https://blessed.readthedocs.io/en/latest/) is the limit!

## Nepotism
Support for "special" teams to always keep visible. My team is blue, the bad guys are gray. Boo, those guys!
