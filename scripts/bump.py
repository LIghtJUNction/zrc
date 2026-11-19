#!/usr/bin/env python3
"""Bump metadata; --publish validates, commits, tags and pushes the release."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("part", choices=["patch", "minor", "major"], default="patch", nargs="?")
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    if git("status", "--porcelain"):
        parser.error("start from a clean working tree")
    old = (ROOT / "VERSION").read_text().strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", old):
        parser.error("invalid current version")
    bits = list(map(int, old.split(".")))
    index = {"major": 0, "minor": 1, "patch": 2}[args.part]
    bits[index] += 1
    for i in range(index + 1, 3):
        bits[i] = 0
    version = ".".join(map(str, bits))
    tag = "v" + version
    if args.publish:
        if git("branch", "--show-current") != "main":
            parser.error("--publish requires main")
        subprocess.run([sys.executable, str(ROOT / "scripts/check.py")], cwd=ROOT, check=True)
        if git("tag", "--list", tag):
            parser.error("release tag already exists")
    (ROOT / "VERSION").write_text(version + "\n")
    path = ROOT / "registry.json"
    data = json.loads(path.read_text())
    data["version"] = version
    path.write_text(json.dumps(data, indent=2) + "\n")
    if args.publish:
        subprocess.run(["git", "add", "VERSION", "registry.json"], cwd=ROOT, check=True)
        subprocess.run(["git", "commit", "-m", "release: " + tag], cwd=ROOT, check=True)
        subprocess.run(["git", "tag", "-a", tag, "-m", "zrc " + version], cwd=ROOT, check=True)
        subprocess.run(["git", "push", "origin", "main", tag], cwd=ROOT, check=True)
    print(old + " -> " + version)

if __name__ == "__main__":
    main()
