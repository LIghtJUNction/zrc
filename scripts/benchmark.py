#!/usr/bin/env python3
"""Measure editor-ready wall time and peak RSS in isolated XDG directories."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=30)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not 3 <= args.runs <= 200:
        parser.error("--runs must be 3..200")
    with tempfile.TemporaryDirectory(prefix="zrc-bench-") as temp:
        env = os.environ.copy()
        for key in ["XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME", "XDG_CACHE_HOME"]:
            env[key] = str(Path(temp) / key)
        quit_ready = "+autocmd VimEnter * ++once lua vim.schedule(function() vim.cmd('qa!') end)"
        init = str(ROOT / "profiles/ink/files/.config/nvim/init.lua")
        cases = {
            "nvim-none": ["nvim", "--headless", "-i", "NONE", "-u", "NONE", quit_ready],
            "zrc-welcome": ["nvim", "--headless", "-i", "NONE", "-u", init, quit_ready],
        }
        sample = Path(temp) / "example.lua"
        sample.write_text("local message = 'hello'\nprint(message)\n")
        cases["zrc-file"] = ["nvim", "--headless", "-i", "NONE", "-u", init, str(sample), quit_ready]
        result = {"schema": "zrc.benchmark.v1", "date_utc": datetime.now(timezone.utc).isoformat(),
                  "runs": args.runs, "warmups": 2, "architecture": platform.machine(),
                  "neovim": subprocess.check_output(["nvim", "--version"], text=True).splitlines()[0],
                  "method": "warm filesystem, isolated XDG, headless VimEnter completed; no language server",
                  "cases": {}}
        # Interleave cases to reduce drift from other processes on the machine.
        samples = {name: [] for name in cases}
        for run in range(args.runs + 2):
            for name, command in cases.items():
                start = time.perf_counter_ns()
                process = subprocess.run(command, env=env, capture_output=True, timeout=20)
                elapsed = (time.perf_counter_ns() - start) / 1_000_000
                if process.returncode:
                    raise RuntimeError(process.stderr.decode(errors="replace"))
                if run >= 2:
                    samples[name].append(elapsed)
        for name, values in samples.items():
            ordered = sorted(values)
            result["cases"][name] = {"median_ms": round(statistics.median(values), 3),
                "p95_ms": round(ordered[min(len(ordered) - 1, int(len(ordered) * .95))], 3),
                "min_ms": round(ordered[0], 3), "max_ms": round(ordered[-1], 3)}
            if Path("/usr/bin/time").exists():
                rss = []
                for _ in range(5):
                    measurement = subprocess.run(["/usr/bin/time", "-f", "ZRC_RSS=%M", *cases[name]],
                                                 env=env, capture_output=True, text=True, timeout=20, check=True)
                    rss.extend(int(line.split("=")[1]) for line in measurement.stderr.splitlines()
                               if line.startswith("ZRC_RSS="))
                result["cases"][name]["peak_rss_kib_median_5"] = statistics.median(rss)
        rendered = json.dumps(result, indent=2) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered)
        print(rendered, end="")

if __name__ == "__main__":
    main()
