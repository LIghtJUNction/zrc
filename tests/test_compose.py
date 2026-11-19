import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("compose", ROOT / "scripts/compose.py")
compose = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(compose)

class ComposeTests(unittest.TestCase):
    def test_all_modules_materialize_one_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = compose.compose(["all"], Path(tmp) / "profile")
            mappings = [line.split("\t") for line in (out / "profile.zdot").read_text().splitlines() if not line.startswith("#")]
            self.assertEqual(len(mappings), 10)
            self.assertTrue((out / "files/.config/nvim/init.lua").is_file())
            self.assertEqual(json.loads((out / "zrc-profile.json").read_text())["modules"][0], "nvim")
            self.assertTrue(all((out / source).exists() and not (out / source).is_symlink() for source, _ in mappings))

    def test_existing_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "existing"
            out.mkdir()
            (out / "keep").write_text("user")
            with self.assertRaises(ValueError):
                compose.compose(["nvim"], out)
            self.assertEqual((out / "keep").read_text(), "user")

    def test_unknown_modules_do_not_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "profile"
            with self.assertRaises(ValueError):
                compose.compose(["unknown"], out)
            self.assertFalse(out.exists())

    def test_path_policy(self):
        for value in ["/home/a", "../a", "a/../b", "a//b", ".", "a\tb", "a\nb", "a\x00b"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                compose.relative_path(value)

    def test_source_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "source").symlink_to("/etc/passwd")
            (root / "registry.json").write_text(json.dumps({"schema": "zrc.registry.v1", "modules": [
                {"id": "test", "mappings": [{"source": "source", "destination": ".config/test"}]}]}))
            with self.assertRaises(ValueError):
                compose.validated_registry(root)

    def test_overlapping_destinations_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "source").write_text("safe")
            (root / "registry.json").write_text(json.dumps({"schema": "zrc.registry.v1", "modules": [
                {"id": "a", "mappings": [{"source": "source", "destination": ".config/test"}]},
                {"id": "b", "mappings": [{"source": "source", "destination": ".config/test/sub"}]},
            ]}))
            with self.assertRaises(ValueError):
                compose.validated_registry(root)

if __name__ == "__main__":
    unittest.main()
