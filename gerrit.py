#!/usr/bin/python3

import argparse
import subprocess
import sys
from os import devnull, environ, makedirs, path


def parse():
    """Parse command line arguments and get default values from the environment."""
    parser = argparse.ArgumentParser(
        description="List and checkout Gerrit repositories."
    )
    parser.add_argument("repository", nargs="*")
    parser.add_argument("-u", "--user", help="the username to use")
    parser.add_argument("-s", "--server", help="the server to connect to")
    parser.add_argument(
        "-l", "--list", help="list available repositories", action="store_true"
    )
    parser.add_argument("-p", "--port", help="server port to use", default="29418")
    q_or_v = parser.add_mutually_exclusive_group()
    q_or_v.add_argument(
        "-v", "--verbose", help="be more verbose", action="count", default=0
    )
    q_or_v.add_argument("-q", "--quiet", help="silent operation", action="store_true")
    re = parser.parse_args()

    if re.quiet:
        sys.stdout = open(devnull, "w")

    if re.user is None:
        re.user = environ["USER"]
        if re.verbose >= 1:
            print(f"No user giving, using '{re.user}' from environment.")

    if re.server is None:
        re.server = path.basename(path.dirname(path.abspath(__file__)))
        if re.verbose >= 1:
            print(f"No server given, using '{re.server}' from containing path.")

    return parser, re


def run(*args, **kwargs):
    """Run a command while capturing output."""
    want_these = {"capture_output": True, "universal_newlines": True}
    want_these.update(kwargs)
    return subprocess.run(*args, **want_these)


def main():
    try:
        parser, args = parse()
    except KeyError:
        print("Couldn't get user name, please provide one.", file=sys.stderr)
        return 1

    server = f"{args.user}@{args.server}"
    if args.list:
        cmd = ["ssh", "-p", args.port, server, "gerrit", "ls-projects"]
        return subprocess.run(cmd).returncode
    elif len(args.repository) == 0:
        parser.print_usage()
        return 1
    else:
        for r in args.repository:
            if args.verbose >= 1:
                print()
            if not path.exists(path.dirname(r)):
                makedirs(path.dirname(r))

            cmd = [
                "git",
                "clone",
                "--quiet" if args.quiet else "--progress",
                "--origin",
                "gerrit",
                "--branch",
                "master",
                f"ssh://{server}:{args.port}/{r}",
                r,
            ]
            # git tries to be smart about redirecting. That messes up the easy way.
            if args.quiet:
                output = run(cmd)
            else:
                output = subprocess.run(cmd)
            if output.returncode != 0:
                print(output.stderr, file=sys.stderr)
                return 1
            if args.verbose >= 1:
                print("Installing Gerrit hooks...")

            cmd = ["git", "review", "--setup"]
            output = run(cmd, cwd=r)
            if output.returncode != 0:
                print(output.stderr, file=sys.stderr)
                return 1


if __name__ == "__main__":
    sys.exit(main())
