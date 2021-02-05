#!/usr/bin/env python3

import argparse
import os
import json


from frontend import FRONTENDS
import middleend.basic
from backend import BACKENDS


def list_frontends():
    print("Frontends:")
    for name,cls in FRONTENDS.items():
        print(f"  {name}")
        try:
            for line in cls.help():
                print(f"    {line}")
        except:
            pass

def list_backends():
    print("Backends:")
    for name,cls in BACKENDS.items():
        print(f"  {name}")
        try:
            for line in cls.help():
                print(f"    {line}")
        except:
            pass


# Returns None if an exit is needed
def load_config():
    conf = {}

    parser = argparse.ArgumentParser(description="Fetch and display a live CTF scoreboard")

    parser.add_argument("--frontend", "-f", type=str, nargs="*",
                        help="Add a frontend")

    parser.add_argument("--list-frontends", "-F", action="store_true",
                        help="List known frontends")

    parser.add_argument("--backend", "-b", type=str,
                        help="Specify a CTF backend")

    parser.add_argument("--list-backends", "-B", action="store_true",
                        help="List known frontends")

    parser.add_argument("--poll-interval", "-i", type=int,
                        help="Seconds between server polling. Don't set this too low!")

    parser.add_argument("--config", "-c", type=str, default="~/.ctfront/config.json",
                        help="Load a configuration file.")

    parser.add_argument("--url", "-u", type=str, default=None,
                        help="URL to scoreboard. See backend list for specifics.")

    parser.add_argument("--auth", "-a", type=str, default=None,
                        help="Auth token for scoreboard. See backend list for specifics.")


    args = parser.parse_args()

    if args.list_backends:
        list_backends()
        return None

    if args.list_frontends:
        list_frontends()
        return None

    # Try to load the user's config file first
    try:
        configpath = os.path.expanduser(args.config)
        with open(configpath, "r") as f:
            conf = json.load(f)
        conf["config"] = args.config
    except:
        print(f"Unable to load configuration {args.config}")
        pass


    def override(conf, conf_key, value, default=None):
        if value is not None:
            conf[conf_key] = value
        if default is not None:
            if conf_key not in conf:
                conf[conf_key] = default

    # Override the loaded config with command line options
    override(conf, "frontend", args.frontend, [])
    override(conf, "backend", args.backend, "auto")
    override(conf, "url", args.url, "")
    override(conf, "auth", args.auth, "")
    override(conf, "poll-interval", args.poll_interval, 60)


    return conf

def main():

    conf = load_config()
    if conf is None:
        return 1

    if len(conf["frontend"]) == 0:
        print("No frontend specified. Look at --list-frontends")
        return 1

    front = [ FRONTENDS[name](conf) for name in conf["frontend"] ]

    middle = middleend.basic.MiddleEnd(conf, front)

    back = BACKENDS[conf["backend"]](conf, middle)

    if back is None:
        return 1

    for f in front:
        f.start()

    middle.start()

    back.start()


if __name__ == "__main__":
    main()
