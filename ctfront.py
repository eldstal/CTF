#!/usr/bin/env python3

import argparse
import os
import json
import threading


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

    # These are the myriad drawing options, etc.
    parser.add_argument("--focus-teams", "-t", type=str, nargs="*",
                        help="One or more team names (regex) to always show")

    parser.add_argument("--max-length", type=int,
                        help="Max length of shown scoreboard")


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

    def force_list(conf, conf_key):
        if conf_key in conf:
            if type(conf[conf_key]) == list:
                return
            conf[conf_key] = [ conf[conf_key] ]

    # Override the loaded config with command line options
    override(conf, "frontend", args.frontend, ["fancy"])
    override(conf, "backend", args.backend, "auto")

    # Backend options
    override(conf, "url", args.url, "")
    override(conf, "auth", args.auth, "")
    override(conf, "poll-interval", args.poll_interval, 60)

    # Frontend options
    override(conf, "focus-teams", args.focus_teams, [])
    override(conf, "max-length", args.max_length, 20)

    force_list(conf, "focus-teams")

    return conf

def boot_thread(func):
    t = threading.Thread(target=func)
    t.daemon = True
    t.start()
    return t


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

    threaded_frontends = []
    modal_frontends = []
    for f in front:
        if f.needs_main_thread():
            modal_frontends.append(f)
        else:
            threaded_frontends.append(f)

    if len(modal_frontends) > 1:
        print("Multiple incompatible frontends configured.")
        return 1

    # Parallel frontends run in their own threads
    frontend_threads = []
    for f in threaded_frontends:
        frontend_threads.append(boot_thread(f.run))

    # Backend also runs in its own thread
    middle.start()
    backend_thread = boot_thread(back.run)

    # This is a special child, which cannot tolerate being anywhere except
    # the main main main thread. Fine.
    for f in modal_frontends:
        f.run()

    for t in frontend_threads:
        t.join()

    backend_thread.join()

if __name__ == "__main__":
    main()
