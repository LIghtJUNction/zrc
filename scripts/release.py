#!/usr/bin/env python3
"""Build a source/profile release from a verified committed version."""
import argparse
import hashlib
from pathlib import Path
import subprocess

from version import read_version

ROOT = Path(__file__).resolve().parents[1]

def build(tag, output):
    version = read_version(ROOT)
    if tag != "v" + version:
        raise ValueError("tag must exactly match VERSION")
    changed = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT)
    if changed:
        raise ValueError("commit tracked changes before building a release")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    archive = output / ("zrc-" + version + ".tar.gz")
    if archive.exists():
        raise ValueError("release archive already exists")
    subprocess.run(["git", "archive", "--format=tar.gz", "--prefix=zrc-" + version + "/",
                    "--output=" + str(archive.absolute()), "HEAD"], cwd=ROOT, check=True)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (output / "SHA256SUMS").write_text(digest + "  " + archive.name + "\n")
    return archive

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--out-dir", type=Path, default=ROOT / ".dist")
    args = parser.parse_args()
    try:
        print(build(args.tag, args.out_dir))
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, "zrc: " + str(error) + "\n")

if __name__ == "__main__":
    main()
