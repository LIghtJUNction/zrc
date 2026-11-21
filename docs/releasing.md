# Releasing zrc

zrc has two distribution channels: the GitHub source/profile archive and the crates.io command/library package. Publishing one does not publish the other.

## Check a candidate

Use Python 3.11 or newer and Rust 1.100 or newer. Start with a clean checkout and the intended version already committed.

```sh
python3 scripts/check.py
python3 scripts/check_cargo.py --package
python3 scripts/release.py --tag "v$(cat VERSION)" --out-dir .dist/review
```

The first command validates the Python composer and available application parsers in isolated XDG directories. The second checks Rust, compares native output to Python, checks that all profile assets are in the crate, installs the extracted crate offline into a temporary prefix and runs the installed executable outside the checkout with an empty PATH. It records a checksum and install evidence in `.build/cargo-validation.json`. The third builds the committed Git archive and its checksum. No command in this section modifies the user's application configuration.

Development builds resolve `zconv` from Git. For the crate gate, a temporary archive of the reviewed commit switches the dependency to the exact published crates.io version and checksum recorded in `scripts/release_projection.py`. The script checks that the development lock points to the corresponding Git revision before it calls `cargo package --locked`. When updating the projection, verify the published crate's `.cargo_vcs_info.json` against the development lock and use the checksum from the crates.io index. The validation record identifies the source commit.

Choose a task-specific `CARGO_TARGET_DIR` when build space should live on another filesystem. `TMPDIR` controls temporary install and test directories. The Cargo checker defaults to one build job.

## Synchronize versions and publish the archive

`python3 scripts/bump.py patch` updates all four version sources together and preserves unrelated dependency lock entries. A failed metadata write restores the original files. Choose `minor` or `major` when appropriate.

`python3 scripts/bump.py patch --publish` requires a clean main branch, checks the new version locally, commits it, creates an annotated version tag and pushes main and the tag atomically. The tag-only GitHub workflow runs its verification and builds the source archive and SHA256SUMS. A failed push leaves the local commit and tag for review; it does not silently retag or force-push.

For an already committed version, a maintainer can tag that reviewed commit through the normal release process. Do not run the bump command merely to publish an existing version.

## Publish the Cargo package

First review the exact commit and merge it to origin/main. The command below defaults to a dry run and uses the same complete local check/package/install gate:

```sh
python3 scripts/publish_crate.py --commit FULL_40_CHARACTER_SHA
```

After that result is reviewed, publish the same commit:

```sh
python3 scripts/publish_crate.py --commit FULL_40_CHARACTER_SHA --publish
```

The command requires a clean checkout and four matching versions. Its final Cargo command runs in the same projected source directory that passed the package and offline-install gate. Actual publication also verifies that origin/main is still the requested commit. Cargo uses the maintainer's existing credential provider; no token is read, copied into the repository or passed on a command line. This repository does not require a GitHub Cargo secret.

Verify the version through the official crates.io registry, then install that published version into a fresh temporary prefix and run `zrc --version`, `zrc --list --json` and a profile composition outside the checkout. Record the registry version/checksum and the reviewed Git commit in the release report. Until that registry check passes, describe a candidate as source-validated, not published.

## Deployment stays explicit

Installing zrc only installs its executable. Composition writes a new profile directory. Review `zdot plan` before `zdot apply --backup`; use zdot's existing remove/restore flow for recovery. Release checks do not apply profiles to a real home directory.
