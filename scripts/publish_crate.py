#!/usr/bin/env python3
"""Check an exact committed source and publish its crate using local Cargo login."""
import argparse
from pathlib import Path
import re
import subprocess
import sys

from version import read_version

ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", required=True, help="reviewed full 40-character commit SHA")
    parser.add_argument("--publish", action="store_true",
                        help="perform the crates.io publication; default is a dry run")
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.commit) or git("rev-parse", "HEAD") != args.commit:
        parser.error("--commit must identify the current reviewed commit exactly")
    if git("status", "--porcelain"):
        parser.error("commit changes before publishing")
    version = read_version(ROOT)
    if args.publish:
        remote_main = git("ls-remote", "origin", "refs/heads/main").split()
        if not remote_main or remote_main[0] != args.commit:
            parser.error("publish only the reviewed source already on origin/main")
    subprocess.run([sys.executable, str(ROOT / "scripts/check.py")], cwd=ROOT, check=True)
    subprocess.run([sys.executable, str(ROOT / "scripts/check_cargo.py"), "--package"], cwd=ROOT, check=True)
    command = ["cargo", "publish", "--locked"]
    if not args.publish:
        command.append("--dry-run")
    print(("Publishing " if args.publish else "Dry run for ") + "zrc " + version, flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
