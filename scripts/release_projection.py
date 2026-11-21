"""Project reviewed Git dependencies to their published crates for packaging."""
from contextlib import contextmanager
from pathlib import Path
import subprocess
import tarfile
import tempfile
import tomllib
from typing import NamedTuple

ZCONV_GIT = "https://github.com/LIghtJUNction/zconv.git"
ZCONV_REVISION = "f78b97b7065bbb7cf9ddfd0914d7f2296bbfe712"
ZCONV_VERSION = "0.4.1"
ZCONV_CHECKSUM = "dd6be639bafc8f7b710017c27935d88b0aba3705568067d16a6d2e774e27a022"


class ReleaseSource(NamedTuple):
    path: Path
    commit: str

    @property
    def target(self):
        return self.path.parent / "target"


def project_zconv(root):
    manifest_path = root / "Cargo.toml"
    lock_path = root / "Cargo.lock"
    manifest = manifest_path.read_text()
    lock = lock_path.read_text()
    git_source = f"git+{ZCONV_GIT}#{ZCONV_REVISION}"
    expected = {"name": "zconv", "version": ZCONV_VERSION, "source": git_source}
    packages = [item for item in tomllib.loads(lock)["package"] if item["name"] == "zconv"]
    dependency = tomllib.loads(manifest)["dependencies"].get("zconv")
    if dependency != {"git": ZCONV_GIT} or packages != [expected]:
        raise ValueError("zconv Git dependency does not match the reviewed crates.io release")

    git_dependency = f'zconv = {{ git = "{ZCONV_GIT}" }}'
    git_lock = f'source = "{git_source}"'
    if manifest.count(git_dependency) != 1 or lock.count(git_lock) != 1:
        raise ValueError("expected one zconv Git declaration in Cargo.toml and Cargo.lock")
    registry_lock = ('source = "registry+https://github.com/rust-lang/crates.io-index"\n'
                     f'checksum = "{ZCONV_CHECKSUM}"')
    manifest_path.write_text(manifest.replace(git_dependency, f'zconv = "={ZCONV_VERSION}"'))
    lock_path.write_text(lock.replace(git_lock, registry_lock))


@contextmanager
def release_projection(root, *, expected_commit=None):
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=root, text=True).strip()

    commit = git("rev-parse", "HEAD")
    if expected_commit is not None and commit != expected_commit:
        raise ValueError("HEAD changed from the reviewed commit")
    if git("status", "--porcelain"):
        raise ValueError("packaging requires a clean checkout of the reviewed commit")

    with tempfile.TemporaryDirectory(prefix="zrc-release-") as temporary:
        work = Path(temporary)
        archive = work / "source.tar"
        source = work / "source"
        source.mkdir()
        git("-c", "tar.umask=0022", "archive", "--format=tar", f"--output={archive}", commit)
        with tarfile.open(archive) as package:
            package.extractall(source, filter="data")
        project_zconv(source)
        yield ReleaseSource(source, commit)
