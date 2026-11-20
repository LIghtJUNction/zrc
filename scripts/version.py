"""Keep the profile catalog and Cargo package on one release version."""
import json
from pathlib import Path
import re
import tomllib

VERSION_FILES = ("VERSION", "registry.json", "Cargo.toml", "Cargo.lock")


def read_version(root):
    root = Path(root)
    version = (root / "VERSION").read_text().strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("invalid VERSION")
    registry = json.loads((root / "registry.json").read_text())
    manifest = tomllib.loads((root / "Cargo.toml").read_text())
    lock = tomllib.loads((root / "Cargo.lock").read_text())
    packages = [package for package in lock["package"] if package["name"] == "zrc"]
    if len(packages) != 1:
        raise ValueError("Cargo.lock must contain one zrc package")
    versions = (registry["version"], manifest["package"]["version"], packages[0]["version"])
    if any(value != version for value in versions):
        raise ValueError("VERSION, registry.json, Cargo.toml and Cargo.lock must agree")
    return version


def _package_version(text, version):
    lines = text.splitlines(keepends=True)
    in_package = False
    count = 0
    for index, line in enumerate(lines):
        if line.startswith("["):
            in_package = line.strip() == "[package]"
        if in_package and re.match(r'^version\s*=', line):
            lines[index] = 'version = "' + version + '"\n'
            count += 1
    if count != 1:
        raise ValueError("expected exactly one Cargo package version")
    return "".join(lines)


def _lock_version(text, version):
    blocks = re.split(r"(?m)(?=^\[\[package\]\]\s*$)", text)
    count = 0
    for index, block in enumerate(blocks):
        data = tomllib.loads(block)
        packages = data.get("package", [])
        if packages and packages[0]["name"] == "zrc":
            blocks[index], replacements = re.subn(
                r'(?m)^version\s*=\s*"[^"]*"\s*$', 'version = "' + version + '"', block
            )
            count += replacements
    if count != 1:
        raise ValueError("expected exactly one zrc lockfile version")
    return "".join(blocks)


def update_version(root, version):
    root = Path(root)
    read_version(root)
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("invalid next version")
    originals = {name: (root / name).read_bytes() for name in VERSION_FILES}
    registry = json.loads(originals["registry.json"])
    registry["version"] = version
    replacements = {
        "VERSION": version + "\n",
        "registry.json": json.dumps(registry, indent=2) + "\n",
        "Cargo.toml": _package_version(originals["Cargo.toml"].decode(), version),
        "Cargo.lock": _lock_version(originals["Cargo.lock"].decode(), version),
    }
    try:
        for name, content in replacements.items():
            (root / name).write_text(content)
        read_version(root)
    except BaseException:
        for name, content in originals.items():
            (root / name).write_bytes(content)
        raise
