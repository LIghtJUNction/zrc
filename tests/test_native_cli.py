"""Run against the actual native executable, including the installed crate."""
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("compose_native_reference", ROOT / "scripts/compose.py")
reference = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(reference)
BINARY = os.environ.get("ZRC_TEST_BINARY")


def tree(path):
    result = {}
    for child in sorted(path.rglob("*")):
        mode = stat.S_IMODE(child.stat().st_mode) if os.name == "posix" else None
        result[child.relative_to(path).as_posix()] = (
            "directory" if child.is_dir() else child.read_bytes(), mode
        )
    return result


@unittest.skipUnless(BINARY, "set ZRC_TEST_BINARY to a built or installed executable")
class NativeCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="zrc-native-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        (self.home / "keep").write_bytes(b"existing configuration")
        self.env = os.environ.copy()
        self.env.update(PATH="", HOME=str(self.home), XDG_CONFIG_HOME=str(self.home / ".config"))
        self.binary = str(Path(BINARY).resolve())
        self.home_before = tree(self.home)

    def tearDown(self):
        self.assertEqual(tree(self.home), self.home_before)
        self.assertEqual(list(self.root.glob(".zrc-compose-*")), [])

    def run_cli(self, *args):
        return subprocess.run([self.binary, *map(str, args)], cwd=self.root, env=self.env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)

    def compare(self, names, label):
        expected = reference.compose(names, self.root / ("python-" + label))
        actual = self.root / ("native-" + label)
        run = self.run_cli("--modules", ",".join(names), "--output", actual)
        self.assertEqual(run.returncode, 0, run.stderr.decode())
        self.assertEqual(tree(actual), tree(expected))
        self.assertEqual(run.stdout.decode().strip(), str(actual))
        return actual

    def test_all_assets_match_python_with_no_path_or_source_cwd(self):
        out = self.compare(["all"], "all")
        self.assertTrue((out / "files/.config/nvim/lua/zrc/context.lua").is_file())
        self.assertEqual(len(json.loads((out / "zrc-profile.json").read_text())["modules"]), 10)

    def test_each_module_matches_python(self):
        for module in reference.validated_registry()["modules"]:
            with self.subTest(module=module["id"]):
                self.compare([module["id"]], module["id"])

    def test_deduplication_preserves_requested_order(self):
        out = self.compare(["shell", "nvim", "shell", "git"], "ordered")
        self.assertEqual(json.loads((out / "zrc-profile.json").read_text())["modules"], ["shell", "nvim", "git"])

    def test_list_text_json_version_and_help(self):
        data = reference.validated_registry()
        plain = self.run_cli("--list")
        self.assertEqual(plain.returncode, 0, plain.stderr)
        self.assertEqual(plain.stdout.decode(), "".join(m["id"] + "  " + m["description"] + "\n" for m in data["modules"]))
        listed = self.run_cli("--list", "--json")
        self.assertEqual(listed.returncode, 0, listed.stderr)
        self.assertEqual(listed.stdout.decode(), json.dumps(data, indent=2) + "\n")
        self.assertEqual(self.run_cli("--version").stdout.decode(), "zrc " + data["version"] + "\n")
        self.assertIn(b"zdot plan", self.run_cli("--help").stdout)

    def test_unknown_empty_and_mixed_all_selections_do_not_write(self):
        for selection in ["unknown", "", "all,nvim", "nvim,", ",nvim", "nvim,unknown"]:
            with self.subTest(selection=selection):
                out = self.root / "rejected"
                run = self.run_cli("--modules=" + selection, "--output", out)
                self.assertNotEqual(run.returncode, 0)
                self.assertFalse(out.exists())

    def test_existing_file_directory_and_dangling_link_are_preserved(self):
        file = self.root / "file"
        file.write_bytes(b"keep")
        directory = self.root / "directory"
        directory.mkdir()
        (directory / "keep").write_bytes(b"keep")
        paths = [file, directory]
        if os.name == "posix":
            link = self.root / "dangling"
            link.symlink_to("missing")
            paths.append(link)
        for out in paths:
            with self.subTest(out=out.name):
                run = self.run_cli("--output", out)
                self.assertNotEqual(run.returncode, 0)
        self.assertEqual(file.read_bytes(), b"keep")
        self.assertEqual((directory / "keep").read_bytes(), b"keep")
        if os.name == "posix":
            self.assertEqual(os.readlink(self.root / "dangling"), "missing")

    def test_missing_parent_is_not_created(self):
        run = self.run_cli("--output", self.root / "missing" / "profile")
        self.assertNotEqual(run.returncode, 0)
        self.assertFalse((self.root / "missing").exists())

    @unittest.skipUnless(os.name == "posix", "Unix symlink contract")
    def test_symlink_parent_is_rejected(self):
        real = self.root / "real"
        real.mkdir()
        link = self.root / "parent"
        link.symlink_to(real, target_is_directory=True)
        run = self.run_cli("--output", link / "profile")
        self.assertNotEqual(run.returncode, 0)
        self.assertEqual(list(real.iterdir()), [])

    def test_usage_errors_do_not_create_output(self):
        for args in [[], ["--modules"], ["--output"], ["--output", "--list"],
                     ["--modules", "--output", "bad"], ["--wat"], ["extra"]]:
            with self.subTest(args=args):
                run = self.run_cli(*args)
                self.assertEqual(run.returncode, 2, run.stderr)
        self.assertEqual({path.name for path in self.root.iterdir()}, {"home"})

    def test_relative_output_and_equals_syntax(self):
        run = self.run_cli("--modules=git", "--output=relative")
        self.assertEqual(run.returncode, 0, run.stderr)
        expected = reference.compose(["git"], self.root / "reference")
        self.assertEqual(tree(self.root / "relative"), tree(expected))

    @unittest.skipUnless(os.name == "posix", "Unix non-UTF-8 filename contract")
    def test_non_utf8_output_name(self):
        name = os.fsdecode(b"profile-\xff")
        run = self.run_cli("--modules", "git", "--output", name)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertTrue((self.root / name / "profile.zdot").is_file())


if __name__ == "__main__":
    unittest.main()
