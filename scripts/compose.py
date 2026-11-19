#!/usr/bin/env python3
"""Compose one zdot profile. Python is a build/management tool, never shell startup."""
import argparse
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]

def relative_path(value):
    if not isinstance(value, str) or not value or any(c in value for c in "\t\r\n\0"):
        raise ValueError("profile paths must be nonempty single-line strings")
    path = PurePosixPath(value)
    if path.is_absolute() or any(p in ("", ".", "..") for p in value.split("/")):
        raise ValueError("profile paths must be normalized and relative")
    return path

def validated_registry(root=ROOT):
    data = json.loads((root / "registry.json").read_text())
    if data.get("schema") != "zrc.registry.v1":
        raise ValueError("unsupported registry schema")
    ids = set()
    destinations = []
    for module in data["modules"]:
        mid = module["id"]
        if not isinstance(mid, str) or not mid or mid in ids:
            raise ValueError("module identifiers must be unique")
        ids.add(mid)
        for mapping in module["mappings"]:
            src = root / relative_path(mapping["source"])
            dst = relative_path(mapping["destination"])
            current = root
            for part in src.relative_to(root).parts:
                current = current / part
                if current.is_symlink():
                    raise ValueError("source symlinks are not supported")
            if not src.exists():
                raise ValueError("missing source: " + str(src))
            if any(dst == other or dst in other.parents or other in dst.parents for other in destinations):
                raise ValueError("overlapping destination: " + str(dst))
            destinations.append(dst)
            if src.is_dir():
                for child in src.rglob("*"):
                    if child.is_symlink() or not (child.is_dir() or child.is_file()):
                        raise ValueError("source tree contains symlink or special file")
            elif not src.is_file():
                raise ValueError("source must be file or directory")
    return data

def compose(names, output, root=ROOT):
    data = validated_registry(root)
    available = {m["id"]: m for m in data["modules"]}
    names = list(available) if names == ["all"] else list(dict.fromkeys(names))
    if not names or any(name not in available for name in names):
        raise ValueError("select known modules; use --list")
    destination = Path(output).absolute()
    if destination.exists() or destination.is_symlink():
        raise ValueError("output already exists; compose into a new profile directory")
    # Do not create unexpected ancestors. Parent setup belongs to the caller.
    if not destination.parent.is_dir() or destination.parent.is_symlink():
        raise ValueError("output parent must be an existing regular directory")
    stage = Path(tempfile.mkdtemp(prefix=".zrc-compose-", dir=destination.parent))
    try:
        lines = ["# zrc.profile.v1 / Ink; generated from reviewed modules"]
        for name in names:
            for mapping in available[name]["mappings"]:
                dst = relative_path(mapping["destination"])
                source = root / mapping["source"]
                target = stage / "files" / str(dst)
                target.parent.mkdir(parents=True, exist_ok=True)
                if source.is_dir():
                    shutil.copytree(source, target)
                else:
                    shutil.copy2(source, target)
                lines.append("files/" + str(dst) + "\t" + str(dst))
        (stage / "profile.zdot").write_text("\n".join(lines) + "\n")
        (stage / "zrc-profile.json").write_text(json.dumps({
            "schema": "zrc.profile.v1", "version": data["version"],
            "palette": data["palette"], "modules": names,
        }, indent=2) + "\n")
        os.rename(stage, destination)
    except BaseException:
        shutil.rmtree(stage)
        raise
    return destination

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="list registered modules")
    parser.add_argument("--json", action="store_true", help="machine-readable list")
    parser.add_argument("--modules", default="all", help="comma-separated names, or all")
    parser.add_argument("--output", type=Path, help="new immutable profile directory")
    args = parser.parse_args()
    if args.list:
        data = validated_registry()
        print(json.dumps(data, indent=2) if args.json else "\n".join(m["id"] + "  " + m["description"] for m in data["modules"]))
        return
    if args.output is None:
        parser.error("--output is required unless --list")
    try:
        print(compose(args.modules.split(","), args.output))
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, "zrc: " + str(error) + "\n")

if __name__ == "__main__":
    main()
