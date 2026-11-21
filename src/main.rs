use std::env;
use std::ffi::{OsStr, OsString};
use std::io::{self, Write};
use std::path::PathBuf;

const HELP: &str = "\
zrc — compose reviewed native application profiles

Usage:
  zrc --list [--json]
  zrc --modules all|name,name --output NEW_DIRECTORY
  zrc --version

Use --output=NEW_DIRECTORY when the path starts with a dash.
The output parent must already exist. Composition does not deploy settings.
Review with zdot plan, then use zdot apply --backup to deploy explicitly.
";

#[derive(Debug)]
enum Failure {
    Usage(String),
    Core(zrc::Error),
    Io(io::Error),
}
impl From<io::Error> for Failure {
    fn from(value: io::Error) -> Self {
        Self::Io(value)
    }
}
impl From<zrc::Error> for Failure {
    fn from(value: zrc::Error) -> Self {
        Self::Core(value)
    }
}
fn value(args: &mut impl Iterator<Item = OsString>, option: &str) -> Result<OsString, Failure> {
    let value = args
        .next()
        .ok_or_else(|| Failure::Usage(format!("{option} requires a value")))?;
    if value.as_encoded_bytes().starts_with(b"-") {
        return Err(Failure::Usage(format!(
            "{option} requires a value; use {option}=VALUE for a leading dash"
        )));
    }
    Ok(value)
}
fn attached_output(argument: &OsStr) -> Option<PathBuf> {
    const PREFIX: &str = "--output=";
    #[cfg(unix)]
    {
        use std::os::unix::ffi::OsStrExt;

        let path = argument.as_bytes().strip_prefix(PREFIX.as_bytes())?;
        Some(PathBuf::from(OsStr::from_bytes(path)))
    }
    #[cfg(not(unix))]
    {
        argument.to_str()?.strip_prefix(PREFIX).map(PathBuf::from)
    }
}
fn run() -> Result<(), Failure> {
    let mut args = env::args_os().skip(1);
    let mut list = false;
    let mut json = false;
    let mut modules = String::from("all");
    let mut output = None;
    let mut stdout = io::stdout().lock();
    while let Some(argument) = args.next() {
        match argument.to_str() {
            Some("--help" | "-h") => {
                stdout.write_all(HELP.as_bytes())?;
                return Ok(());
            }
            Some("--version" | "-V") => {
                writeln!(stdout, "zrc {}", zrc::VERSION)?;
                return Ok(());
            }
            Some("--list") => list = true,
            Some("--json") => json = true,
            Some("--modules") => {
                modules = value(&mut args, "--modules")?
                    .into_string()
                    .map_err(|_| Failure::Usage("module names must be UTF-8".into()))?;
            }
            Some("--output") => output = Some(PathBuf::from(value(&mut args, "--output")?)),
            Some(arg) if arg.starts_with("--modules=") => {
                modules = arg["--modules=".len()..].to_owned()
            }
            _ => {
                output = Some(attached_output(&argument).ok_or_else(|| {
                    Failure::Usage(format!("unknown argument: {}", argument.to_string_lossy()))
                })?);
            }
        }
    }
    if list {
        let registry = zrc::registry()?;
        if json {
            writeln!(stdout, "{}", zrc::REGISTRY_JSON.trim_end())?;
        } else {
            for module in registry.modules {
                writeln!(stdout, "{}  {}", module.id, module.description)?;
            }
        }
    } else {
        let output =
            output.ok_or_else(|| Failure::Usage("--output is required unless --list".into()))?;
        let path = zrc::compose(&modules.split(',').collect::<Vec<_>>(), output)?;
        writeln!(stdout, "{}", path.display())?;
    }
    Ok(())
}

fn main() -> std::process::ExitCode {
    match run() {
        Ok(()) => std::process::ExitCode::SUCCESS,
        Err(Failure::Io(error)) if error.kind() == io::ErrorKind::BrokenPipe => {
            std::process::ExitCode::SUCCESS
        }
        Err(Failure::Usage(message)) => {
            eprintln!("zrc: {message}\nUse zrc --help for usage.");
            std::process::ExitCode::from(2)
        }
        Err(Failure::Core(error)) => {
            eprintln!("zrc: {error}");
            std::process::ExitCode::FAILURE
        }
        Err(Failure::Io(error)) => {
            eprintln!("zrc: {error}");
            std::process::ExitCode::FAILURE
        }
    }
}

#[cfg(all(test, unix))]
mod tests {
    use super::*;
    use std::os::unix::ffi::OsStrExt;
    use std::path::Path;

    #[test]
    fn attached_output_preserves_non_utf8_path() {
        let argument = OsStr::from_bytes(b"--output=-profile-\xff");
        let path = Path::new(OsStr::from_bytes(b"-profile-\xff"));
        assert_eq!(attached_output(argument).as_deref(), Some(path));
    }
}
