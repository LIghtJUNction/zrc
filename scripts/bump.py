#!/usr/bin/env python3
"""Bump all release metadata; --publish validates, commits, tags and pushes."""
import argparse
from pathlib import Path
import subprocess
import sys

from version import VERSION_FILES, read_version, update_version

ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("part", choices=["patch", "minor", "major"], default="patch", nargs="?")
    parser.add_argument("--publish", action="store_true",
                        help="publish the Git tag/archive; crates.io uses publish_crate.py")
    args = parser.parse_args()
    if git("status", "--porcelain"):
        parser.error("start from a clean working tree")
    old = read_version(ROOT)
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
        if git("tag", "--list", tag):
            parser.error("release tag already exists")
    originals = {name: (ROOT / name).read_bytes() for name in VERSION_FILES}
    update_version(ROOT, version)
    if args.publish:
        try:
            subprocess.run([sys.executable, str(ROOT / "scripts/check.py")], cwd=ROOT, check=True)
            subprocess.run([sys.executable, str(ROOT / "scripts/check_cargo.py")], cwd=ROOT, check=True)
        except BaseException:
            for name, content in originals.items():
                (ROOT / name).write_bytes(content)
            raise
        subprocess.run(["git", "add", *VERSION_FILES], cwd=ROOT, check=True)
        subprocess.run(["git", "commit", "-m", "release: " + tag], cwd=ROOT, check=True)
        subprocess.run(["git", "tag", "-a", tag, "-m", "zrc " + version], cwd=ROOT, check=True)
        subprocess.run(["git", "push", "--atomic", "origin", "main", tag], cwd=ROOT, check=True)
    print(old + " -> " + version)


if __name__ == "__main__":
    main()
