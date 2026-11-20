"""Release metadata changes must stay coherent and preserve unrelated packages."""
import importlib.util
import json
from pathlib import Path
import tempfile
import tomllib
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("zrc_version", ROOT / "scripts/version.py")
version = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(version)


class VersionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="zrc-version-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in version.VERSION_FILES:
            (self.root / name).write_bytes((ROOT / name).read_bytes())

    def test_bump_updates_all_four_files_and_preserves_dependency_lock(self):
        old = tomllib.loads((self.root / "Cargo.lock").read_text())
        version.update_version(self.root, "9.8.7")
        self.assertEqual(version.read_version(self.root), "9.8.7")
        new = tomllib.loads((self.root / "Cargo.lock").read_text())
        self.assertEqual([p for p in old["package"] if p["name"] != "zrc"],
                         [p for p in new["package"] if p["name"] != "zrc"])
        self.assertEqual(json.loads((self.root / "registry.json").read_text())["version"], "9.8.7")

    def test_mismatch_rejects_bump_without_any_write(self):
        (self.root / "VERSION").write_text("9.9.9\n")
        before = {name: (self.root / name).read_bytes() for name in version.VERSION_FILES}
        with self.assertRaises(ValueError):
            version.update_version(self.root, "1.2.3")
        self.assertEqual(before, {name: (self.root / name).read_bytes() for name in version.VERSION_FILES})

    def test_failed_write_restores_every_metadata_file(self):
        before = {name: (self.root / name).read_bytes() for name in version.VERSION_FILES}
        original = Path.write_text

        def fail_lock(path, *args, **kwargs):
            if path == self.root / "Cargo.lock":
                raise OSError("fixture write failure")
            return original(path, *args, **kwargs)

        with mock.patch.object(Path, "write_text", fail_lock), self.assertRaises(OSError):
            version.update_version(self.root, "1.2.3")
        self.assertEqual(before, {name: (self.root / name).read_bytes() for name in version.VERSION_FILES})


if __name__ == "__main__":
    unittest.main()
