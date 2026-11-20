## 0.1.2

zrc now has a native Rust command and library. `cargo install zrc --version 0.1.2 --locked` installs a binary with all ten modules and hidden configuration assets embedded. `--list`, `--list --json`, `--modules` and `--output` use the existing profile format and module ordering. Composition works outside the source checkout without Python or a network connection.

The Python entry remains supported. Both entries create a new profile root for zdot to review and deploy; neither changes HOME. The Neovim terminal-buffer preservation fix from 0.1.1 is retained without changing configuration assets.

The Cargo package gate checks every module against Python, validates rejection boundaries, extracts the crate, installs it offline and runs the installed executable with an empty PATH. Version metadata now stays synchronized across VERSION, registry.json, Cargo.toml and Cargo.lock. The GitHub archive workflow remains in place, with a separate exact-commit local crates.io publication command.

## 0.1.1

The explicit Neovim connection opens ssmcp in its own terminal buffer. Unsaved text, the original editing buffer and its window remain intact. Failed starts close the empty split and return focus to the editor with an error message.

Regression coverage exercises a real terminal job with a local fixture, plus invalid, failed and thrown job starts.

Native Ink profiles for Neovim, Kitty, Foot, Ghostty, tmux, fzf, bat, ripgrep, Git and zsh.

The archive contains source configuration, the module registry, composition tools and one complete zdot profile. Applications load their own native formats; no configuration daemon or startup downloader is added.

Preview changes with zdot before applying. The Git profile is a display-only include; it does not change identity or signing. Existing language-server executables may be reused, including installed Mason binaries.

See README.md for activation, recovery and the local extension API. docs/performance.md records the measured workload and its limits.
