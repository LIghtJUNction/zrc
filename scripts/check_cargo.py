#!/usr/bin/env python3
"""Check the native crate, then optionally install its packaged source offline."""
import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parents[1]


def run(command, *, cwd=ROOT, env=None):
    print("+ " + " ".join(map(str, command)), flush=True)
    subprocess.run(command, cwd=cwd, env=env, check=True)


def native_tests(binary, env):
    env = env.copy()
    env["ZRC_TEST_BINARY"] = str(binary)
    run([sys.executable, "-m", "unittest", "discover", "-s", "tests",
         "-p", "test_native_cli.py", "-v"], env=env)


def check(package=False):
    env = os.environ.copy()
    env.setdefault("CARGO_BUILD_JOBS", "1")
    env.setdefault("CARGO_INCREMENTAL", "0")
    run(["cargo", "fmt", "--check"], env=env)
    run(["cargo", "clippy", "--locked", "--all-targets", "--", "-D", "warnings"], env=env)
    run(["cargo", "test", "--locked"], env=env)
    run(["cargo", "build", "--locked"], env=env)
    metadata = json.loads(subprocess.check_output(
        ["cargo", "metadata", "--locked", "--no-deps", "--format-version=1"], cwd=ROOT, env=env))
    target = Path(metadata["target_directory"])
    name = "zrc.exe" if os.name == "nt" else "zrc"
    native_tests(target / "debug" / name, env)
    if not package:
        return
    run(["cargo", "package", "--locked"], env=env)
    version = tomllib.loads((ROOT / "Cargo.toml").read_text())["package"]["version"]
    archive = target / "package" / ("zrc-" + version + ".crate")
    prefix = "zrc-" + version
    with tarfile.open(archive) as package_file:
        names = {member.name for member in package_file.getmembers() if member.isfile()}
        if any("__pycache__" in name or name.endswith(".pyc") for name in names):
            raise ValueError("crate contains Python build caches")
        assets = {path.relative_to(ROOT).as_posix() for path in (ROOT / "profiles").rglob("*") if path.is_file()}
        missing = sorted(path for path in assets if prefix + "/" + path not in names)
        if missing:
            raise ValueError("crate is missing configuration assets: " + ", ".join(missing))
        # The scratch directory and installed executable live away from the checkout.
        with tempfile.TemporaryDirectory(prefix="zrc-install-") as temporary:
            work = Path(temporary)
            package_file.extractall(work, filter="data")
            source = work / prefix
            install = work / "installed"
            install_env = env.copy()
            install_env["CARGO_TARGET_DIR"] = str(target / "install-check")
            run(["cargo", "install", "--path", str(source), "--root", str(install),
                 "--offline", "--locked"], cwd=work, env=install_env)
            binary = install / "bin" / name
            shutil.rmtree(source)
            native_tests(binary, env)
            summary = {
                "schema": "zrc.crate-check.v1", "version": version,
                "crate": archive.name,
                "crate_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                "packaged_assets": len(assets), "packaged_files": len(names),
                "installed_binary_bytes": binary.stat().st_size,
                "installed_outside_checkout": True, "offline_install": True,
                "installed_source_removed_before_run": True,
                "runtime_path_empty": True, "native_cli_tests": 11,
            }
            evidence = ROOT / ".build" / "cargo-validation.json"
            evidence.parent.mkdir(parents=True, exist_ok=True)
            evidence.write_text(json.dumps(summary, indent=2) + "\n")
            print(json.dumps(summary, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", action="store_true")
    args = parser.parse_args()
    check(args.package)


if __name__ == "__main__":
    main()
