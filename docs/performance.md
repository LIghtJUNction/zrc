# Local measurements

Measured on 2026-11-20 (Asia/Taipei), x86_64, Neovim 0.12.6. Source data:
[benchmark-2026-11-20.json](benchmark-2026-11-20.json).

| Case | Median | p95 |
| --- | ---: | ---: |
| Neovim without configuration | 5.863 ms | 16.707 ms |
| zrc welcome page | 11.600 ms | 34.912 ms |
| zrc opening a small Lua file | 22.402 ms | 78.471 ms |

Each case ran 30 times after two warmups, interleaved to reduce drift from other
development processes. Measurements are end-to-end process wall time in isolated
XDG directories, ending after the VimEnter handlers and welcome page completed.
Filesystem caches were warm. The source-file case had no language server.

The welcome page adds about 5.7 ms to the empty baseline on this machine. Lua file
startup also includes Neovim's native filetype and syntax work. Tail latency was
variable on the shared development machine. These data do not establish a
cross-machine ranking, cold-start performance or interactive rendering speed.
Peak RSS was not collected in this initial record because the system time
executable was absent.

## Validation

Six profile tests cover composition, existing-output preservation, invalid modules,
path validation, symlink rejection and overlapping destinations. Native Neovim
checks exercise Lua loading, palette, local-only context, lazy LSP, picker filtering
and selection, welcome-window lifecycle, large-file mode and reuse of installed
Mason language servers. Real asynchronous ripgrep is checked for filenames with spaces, ignored .git paths and exact match coordinates; a home-directory search is verified to request a project before starting any process.

Kitty, Foot 1.28, Ghostty, fzf, bat, ripgrep, Git and zsh configurations passed
their installed parsers or execution checks. tmux was not installed and is listed
as an unvalidated optional profile on this machine.

## Review of claims

- **Contribution:** native configurations share a palette and one zdot profile;
  registry and composition tests demonstrate this.
- **Clarity:** installation, activation and recovery are separate operations.
- **Evidence:** startup claims cite the command, raw results and workload.
- **Completeness:** LSP and tmux limitations are explicit; no editor plugin or
  server downloads are counted as startup.
- **Design:** there is no background updater or duplicate deployment engine.
