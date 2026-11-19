#!/usr/bin/env python3
"""Run local checks without touching the user's live configuration."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]

def run(command, env, stdin=None):
    completed = subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True, timeout=30, input=stdin)
    print(json.dumps({"command": command[0:3], "exit": completed.returncode,
                      "stdout": completed.stdout[-3000:], "stderr": completed.stderr[-3000:]}))
    if completed.returncode:
        raise SystemExit(completed.returncode)

def main():
    with tempfile.TemporaryDirectory(prefix="zrc-check-") as temp:
        env = os.environ.copy()
        for key in ["XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME", "XDG_CACHE_HOME"]:
            env[key] = str(Path(temp) / key)
        env["ZRC_TEST_ROOT"] = str(ROOT)
        large = Path(temp) / "large.txt"
        large.write_text("a" * (1024 * 1024 + 1) + "\n")
        env["ZRC_TEST_LARGE_FILE"] = str(large)
        run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], env)
        run([sys.executable, "scripts/compose.py", "--modules", "all", "--output", str(Path(temp) / "composed")], env)
        config = ROOT / "profiles/ink/files/.config"
        if shutil.which("nvim"):
            run(["nvim", "--headless", "-i", "NONE", "-u", str(config / "nvim/init.lua"),
                 "+lua local ok,err=pcall(dofile,'tests/nvim.lua'); if not ok then io.stderr:write(tostring(err)); vim.cmd('cquit 1') end"], env)
        if shutil.which("foot"):
            run(["foot", "--check-config", "--config=" + str(config / "foot/foot.ini")], env)
        if shutil.which("ghostty"):
            run(["ghostty", "+validate-config",
                 "--config-file=" + str(config / "ghostty/config")], env)
        if shutil.which("kitty"):
            script = "from kitty.config import load_config; errors=[]; load_config(" + repr(str(config / "kitty/kitty.conf")) + ", accumulate_bad_lines=errors); assert not errors, errors; print('kitty parsed')"
            run(["kitty", "+runpy", script], env)
        if shutil.which("zsh"):
            run(["zsh", "-n", str(config / "zrc/shell.zsh")], env)
        if shutil.which("git"):
            run(["git", "config", "--file", str(config / "zrc/git.inc"), "--list"], env)
        if shutil.which("fzf"):
            env["FZF_DEFAULT_OPTS_FILE"] = str(config / "fzf/fzfrc")
            run(["fzf", "--filter", "zrc"], env, stdin="zrc\n")
        if shutil.which("bat"):
            env["BAT_CONFIG_PATH"] = str(config / "bat/config")
            run(["bat", "--paging=never", "VERSION"], env)
        if shutil.which("rg"):
            env["RIPGREP_CONFIG_PATH"] = str(config / "ripgrep/config")
            run(["rg", "zrc", "registry.json"], env)

if __name__ == "__main__":
    main()
