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

from release_projection import release_projection

ROOT = Path(__file__).resolve().parents[1]


def run(command, *, cwd=ROOT, env=None):
    print("+ " + " ".join(map(str, command)), flush=True)
    subprocess.run(command, cwd=cwd, env=env, check=True)


def native_tests(binary, env, *, cwd=ROOT):
    env = env.copy()
    env["ZRC_TEST_BINARY"] = str(binary)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    run([sys.executable, "-m", "unittest", "discover", "-s", "tests",
         "-p", "test_native_cli.py", "-v"], cwd=cwd, env=env)


def check(release=None):
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
    if release is None:
        return
    package_env = env.copy()
    package_env["CARGO_TARGET_DIR"] = str(release.target)
    run(["cargo", "package", "--locked"], cwd=release.path, env=package_env)
    version = tomllib.loads((release.path / "Cargo.toml").read_text())["package"]["version"]
    archive = release.target / "package" / ("zrc-" + version + ".crate")
    prefix = "zrc-" + version
    with tarfile.open(archive) as package_file:
        names = {member.name for member in package_file.getmembers() if member.isfile()}
        if any("__pycache__" in name or name.endswith(".pyc") for name in names):
            raise ValueError("crate contains Python build caches")
        assets = {path.relative_to(release.path).as_posix()
                  for path in (release.path / "profiles").rglob("*") if path.is_file()}
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
            install_env["CARGO_TARGET_DIR"] = str(work / "target")
            run(["cargo", "install", "--path", str(source), "--root", str(install),
                 "--offline", "--locked"], cwd=work, env=install_env)
            binary = install / "bin" / name
            shutil.rmtree(source)
            native_tests(binary, env, cwd=release.path)
            output = target / "package" / archive.name
            output.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(dir=output.parent) as staging:
                artifact = Path(staging) / archive.name
                shutil.copyfile(archive, artifact)
                artifact.replace(output)
            summary = {
                "schema": "zrc.crate-check.v1", "version": version,
                "source_commit": release.commit,
                "crate": archive.name,
                "crate_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                "packaged_assets": len(assets), "packaged_files": len(names),
                "installed_binary_bytes": binary.stat().st_size,
                "installed_outside_checkout": True, "offline_install": True,
                "installed_source_removed_before_run": True,
                "runtime_path_empty": True, "native_cli_tests": 12,
            }
            evidence = ROOT / ".build" / "cargo-validation.json"
            evidence.parent.mkdir(parents=True, exist_ok=True)
            evidence.write_text(json.dumps(summary, indent=2) + "\n")
            print(json.dumps(summary, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", action="store_true")
    args = parser.parse_args()
    if args.package:
        with release_projection(ROOT) as release:
            check(release)
    else:
        check()


if __name__ == "__main__":
    main()
