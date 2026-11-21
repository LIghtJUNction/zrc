from pathlib import Path
import sys
import tempfile
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from release_projection import ZCONV_CHECKSUM, ZCONV_GIT, ZCONV_REVISION, ZCONV_VERSION, project_zconv


class ReleaseProjectionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.source = Path(temporary.name)
        self.manifest = self.source / "Cargo.toml"
        self.lock = self.source / "Cargo.lock"
        self.manifest.write_text(f'[dependencies]\nzconv = {{ git = "{ZCONV_GIT}" }}\n')
        self.lock.write_text(
            f'[[package]]\nname = "zconv"\nversion = "{ZCONV_VERSION}"\n'
            f'source = "git+{ZCONV_GIT}#{ZCONV_REVISION}"\n'
        )

    def test_projects_the_reviewed_revision_to_the_exact_registry_crate(self):
        project_zconv(self.source)
        manifest = tomllib.loads(self.manifest.read_text())
        lock = tomllib.loads(self.lock.read_text())
        self.assertEqual(manifest["dependencies"]["zconv"], f"={ZCONV_VERSION}")
        [zconv] = [item for item in lock["package"] if item["name"] == "zconv"]
        self.assertEqual(zconv, {"name": "zconv", "version": ZCONV_VERSION,
                                 "source": "registry+https://github.com/rust-lang/crates.io-index",
                                 "checksum": ZCONV_CHECKSUM})

    def test_rejects_a_different_git_revision_with_the_same_version(self):
        manifest = self.manifest.read_text()
        changed_lock = self.lock.read_text().replace(ZCONV_REVISION, "1" * 40)
        self.lock.write_text(changed_lock)
        with self.assertRaisesRegex(ValueError, "does not match the reviewed crates.io release"):
            project_zconv(self.source)
        self.assertEqual(self.manifest.read_text(), manifest)
        self.assertEqual(self.lock.read_text(), changed_lock)
