# zrc

A small configuration framework for **oh-my-ztty**. One warm palette, native application settings, and one reviewable [zdot](https://github.com/LIghtJUNction/zdot) deployment.

zrc gives Neovim a complete editing environment and applies the same Ink colors to terminals and command-line tools. Applications read their own configuration formats. There is no configuration daemon, startup download, or additional plugin manager.

## Modules

| Module | Configuration |
| --- | --- |
| Neovim 0.11+ | Ink colors, welcome page, native fuzzy picker, status line, search, LSP, local extensions |
| Kitty, Foot, Ghostty | Warm palette, spacing and cursor |
| tmux | Compact status line and low-contrast dividers |
| fzf | Matching native finder colors |
| bat | ANSI theme that inherits the terminal palette |
| ripgrep | Smart-case search and warm match colors |
| Git | Display-only include, with no identity or signing settings |
| Shell | Builtin environment assignments for editor and tool defaults |

`registry.json` is the module catalog. `profiles/ink/profile.zdot` is the complete static profile. Choose a subset by composing a new profile directory:

```sh
python3 scripts/compose.py --list
python3 scripts/compose.py --list --json
python3 scripts/compose.py --modules nvim,fzf,bat,ripgrep,git,shell \
  --output /path/to/new-profile

zdot plan --root /path/to/new-profile --target "$HOME" --json
zdot apply --root /path/to/new-profile --target "$HOME" --backup
```

Review the plan before deployment. `--backup` lets zdot preserve replaced settings. Use `zdot remove` with the same root to restore them. Compose into a new, stable directory: moving a deployed profile breaks its links.

Python is only used when composing or checking profiles. It is not part of shell or editor startup. zdot owns deployment, backup and rollback; zrc does not duplicate those mechanisms.

## Neovim

Open Neovim with no file to see the welcome page. Space is the leader key.

| Keys | Action |
| --- | --- |
| Space f f | Find files with a native floating fuzzy picker |
| Space f g | Search project text and open quickfix results |
| Space f r | Recent files |
| Space b b | Open buffers |
| Space e | Native file explorer |
| Space w | Save |
| Space c a / c r / c f | Code action / rename / format |
| Space d | Line diagnostics |
| Space a c | Show local editor context as JSON |
| Space a s | Start ssmcp explicitly in a terminal split |
| Space ? | Search the shortcut list |
| Ctrl-Space | Native completion |

The picker starts one ripgrep process when opened, then filters in memory. It does not run a new process for each keystroke. File results are bounded to 4,000 entries and 512 KiB; text search uses a 2 MiB output bound and 1,000 quickfix entries. Truncated results are labelled. Each search has a five-second deadline. Searches use the current project and respect ignore files; no indexer runs at startup. When started from the home or filesystem root, the finder asks for a project directory before scanning.

LSP starts when a matching file is opened in a recognized project and its language server is already installed. Rust, C/C++, Go, Python, Lua, shell, JavaScript and TypeScript have native adapters. Existing executables in Neovim's `stdpath("data")/mason/bin` are reused when absent from PATH. zrc does not install servers or launch one for a loose file without a project root. `:ZrcHealth` shows optional executables.

Files over 1 MiB enter large-file mode before reading: persistent undo, syntax highlighting, Treesitter and LSP are skipped for that buffer. Buffers over 20,000 lines also skip highlighting after reading. Swap-file recovery stays at Neovim's normal setting. These limits can be adjusted.

### Local extensions

Put local settings in `~/.config/zrc/nvim.lua`, outside the managed Neovim directory:

```lua
return {
  large_file_bytes = 2 * 1024 * 1024,
  max_files = 4000,
  lsp = true,
  extensions = {
    {
      event = "InsertEnter",
      setup = function()
        -- Use an already installed optional native package.
        -- vim.cmd.packadd("my-local-package")
      end,
    },
  },
}
```

An extension may specify `event`, `pattern`, `once` and `setup`. Its setup runs through `pcall`, so one failing extension does not abort editor startup. Use Neovim's native packages for local plugins; no registry or lockfile is downloaded.

`:ZrcContext` displays only the current file path, cursor, file type, working directory, modified flag and diagnostic counts. It does not send anything or read buffer contents. `:ZrcConnect` starts the already installed ssmcp only when invoked.

## Activating optional tools

The suite sources `~/.config/zrc/shell.zsh` for fzf, bat, ripgrep and editor defaults. Standalone users can source that file from their interactive zsh configuration.

Git's module is an include file. Add its path once after reviewing existing includes:

```sh
git config --global --add include.path ~/.config/zrc/git.inc
```

It changes color output only. Existing identity, credentials, signing, transport, hooks and repositories are not copied into zrc. The tmux profile is ready for tmux when installed; composition never installs packages.

## Extension contract

The [registry schema](schema/registry.schema.json) defines module IDs, required executables, optional activation guidance and source-to-destination mappings. Source paths are repository-relative; destinations are target-relative.

Modules must own disjoint destinations. Composition rejects unknown modules, source symlinks, special files, path traversal, overlapping destinations and existing output directories. It copies selected sources into one immutable profile root and emits one `profile.zdot`, avoiding competing deployments to the same home.

Add native configuration under `profiles/ink/files`, register disjoint destinations, update the static profile, and validate the application parser before publishing. No application binary, personal configuration, secret, or device identifier belongs in this repository.

## Local verification

```sh
python3 scripts/check.py
python3 scripts/benchmark.py --runs 30
```

Checks use isolated XDG directories. They exercise profile safety, Neovim's palette, picker, welcome page, large-file behavior and LSP selection, plus configuration parsers for installed applications. Missing optional application validators are separate from successful checks.

[Measurements](docs/performance.md) record commands, versions and limitations. They describe a particular machine and workload; zrc makes no unmeasured ranking claim against other configurations.

## References

- [Neovim LSP](https://neovim.io/doc/user/lsp/) and [Lua API](https://neovim.io/doc/user/lua/)
- [Kitty configuration](https://sw.kovidgoyal.net/kitty/conf/)
- [Ghostty configuration](https://ghostty.org/docs/config/reference)
- [zdot design and recovery](https://github.com/LIghtJUNction/zdot/blob/main/docs/design.md)

MIT license.

## Releasing

Run python3 scripts/bump.py patch to update version metadata. Add --publish to first run local checks, then commit, tag and push from main. A tag starts the archive-and-checksum release workflow; ordinary pushes do not start CI.
