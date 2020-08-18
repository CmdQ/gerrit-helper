#!/usr/bin/python3

import argparse
import subprocess
import sys
from os import devnull, environ, getcwd, makedirs, path


def flatten(ll):
    re = []
    try:
        for l in ll:
            if isinstance(l, list):
                re.extend(l)
            else:
                re.append(l)
    finally:
        return re


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
    parser.add_argument(
        "-e",
        "--exclude",
        help="exclude (pseudo) projects",
        action="append",
        nargs="?",
        const=[
            "All-Projects",
            "All-Users",
            "AllowSelfApproval-Project",
            "NoReviews-Project",
        ],
    )
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
        absolute = path.abspath(getcwd())
        re.server = path.basename(absolute)
        if re.verbose >= 2:
            print("CWD:", absolute)
        if re.verbose >= 1:
            print(f"No server given, using '{re.server}' from containing path.")

    re.exclude = set(flatten(re.exclude))
    if re.verbose >= 2:
        print("Excluded repositories:", re.exclude)

    re.repository = set(re.repository)

    return parser, re


def run(*args, **kwargs):
    """Run a command while capturing output."""
    want_these = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "universal_newlines": True,
    }
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
        for r in args.repository - args.exclude:
            if args.verbose >= 1:
                print()

            directory = path.dirname(r)
            if directory != "":
                if not path.exists(directory):
                    if args.verbose >= 1:
                        print("Making directory", directory, "for repository", r)
                    makedirs(directory)

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
            if directory == "":
                del cmd[-1]

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
