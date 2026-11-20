#![forbid(unsafe_code)]
//! Compose the bundled, reviewed configuration files into a new zdot profile.
//!
//! This library never deploys into a user's home or invokes an external program.
//! Use zdot separately to plan, apply, back up and remove a composed profile.

use std::collections::BTreeSet;
use std::fmt;
use std::fs;
use std::io;
use std::path::{Component, Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};
use zconv::json::{self, Kind, Limits, Token, Value, Writer};

/// Version shared by the executable, registry and profile metadata.
pub const VERSION: &str = env!("CARGO_PKG_VERSION");
/// The complete original module catalog, embedded in the installed program.
pub const REGISTRY_JSON: &str = include_str!("../registry.json");

struct Asset {
    path: &'static str,
    bytes: Option<&'static [u8]>,
    mode: u32,
}
include!(concat!(env!("OUT_DIR"), "/assets.rs"));

/// A source-to-destination mapping relative to the reviewed profile and target.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Mapping {
    pub source: String,
    pub destination: String,
}

/// One available native application configuration.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Module {
    pub id: String,
    pub description: String,
    pub binaries: Vec<String>,
    pub activation: Option<String>,
    pub mappings: Vec<Mapping>,
}

/// The validated module catalog. Editing this value does not alter bundled assets.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Registry {
    pub version: String,
    pub palette: String,
    pub modules: Vec<Module>,
}

/// Composition failures leave existing output and user configuration untouched.
#[derive(Debug)]
pub enum Error {
    Invalid(String),
    Io(io::Error),
}
impl fmt::Display for Error {
    fn fmt(&self, out: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Invalid(message) => out.write_str(message),
            Self::Io(error) => error.fmt(out),
        }
    }
}
impl std::error::Error for Error {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Self::Io(error) => Some(error),
            Self::Invalid(_) => None,
        }
    }
}
impl From<io::Error> for Error {
    fn from(error: io::Error) -> Self {
        Self::Io(error)
    }
}
fn invalid(message: impl Into<String>) -> Error {
    Error::Invalid(message.into())
}

fn text(value: Value<'_, '_>) -> Result<String, Error> {
    let string = value
        .as_string()
        .ok_or_else(|| invalid("registry field must be a string"))?;
    String::from_utf8(string.bytes().collect()).map_err(|_| invalid("invalid registry UTF-8"))
}
fn field<'a, 't>(value: Value<'a, 't>, name: &str) -> Result<Value<'a, 't>, Error> {
    value
        .get(name)
        .ok_or_else(|| invalid(format!("missing registry field: {name}")))
}
fn array<'a, 't>(value: Value<'a, 't>) -> Result<json::Array<'a, 't>, Error> {
    if value.kind() != Kind::Array {
        return Err(invalid("registry field must be an array"));
    }
    Ok(value.array())
}
fn normalized(value: &str) -> Result<(), Error> {
    if value.is_empty()
        || value
            .chars()
            .any(|c| matches!(c, '\t' | '\r' | '\n' | '\0' | '\\'))
        || value.split('/').any(|part| matches!(part, "" | "." | ".."))
        || Path::new(value)
            .components()
            .any(|part| !matches!(part, Component::Normal(_)))
        || value.as_bytes().get(1) == Some(&b':')
    {
        return Err(invalid(
            "profile paths must be normalized, relative and portable",
        ));
    }
    Ok(())
}
fn parse_registry(input: &[u8], assets: &[Asset]) -> Result<Registry, Error> {
    let limits = Limits {
        max_input: 64 * 1024,
        max_tokens: 8192,
        max_depth: 16,
        max_object_fields: 64,
    };
    let mut tokens = vec![Token::EMPTY; input.len().min(limits.max_tokens)];
    let document = json::parse(input, &mut tokens, limits)
        .map_err(|error| invalid(format!("invalid registry JSON: {error:?}")))?;
    let root = document.root();
    if text(field(root, "schema")?)? != "zrc.registry.v1" {
        return Err(invalid("unsupported registry schema"));
    }
    let version = text(field(root, "version")?)?;
    let palette = text(field(root, "palette")?)?;
    let mut ids = BTreeSet::new();
    let mut destinations: Vec<String> = Vec::new();
    let mut modules = Vec::new();
    for item in array(field(root, "modules")?)? {
        let id = text(field(item, "id")?)?;
        if id.is_empty() || !ids.insert(id.clone()) {
            return Err(invalid("module identifiers must be nonempty and unique"));
        }
        let mut mappings = Vec::new();
        for mapping in array(field(item, "mappings")?)? {
            let source = text(field(mapping, "source")?)?;
            let destination = text(field(mapping, "destination")?)?;
            normalized(&source)?;
            normalized(&destination)?;
            if !assets.iter().any(|asset| asset.path == source) {
                return Err(invalid(format!("missing embedded source: {source}")));
            }
            if destinations.iter().any(|other| {
                Path::new(&destination).starts_with(other)
                    || Path::new(other).starts_with(&destination)
            }) {
                return Err(invalid(format!("overlapping destination: {destination}")));
            }
            destinations.push(destination.clone());
            mappings.push(Mapping {
                source,
                destination,
            });
        }
        let binaries = array(field(item, "binaries")?)?
            .map(text)
            .collect::<Result<_, _>>()?;
        modules.push(Module {
            id,
            description: text(field(item, "description")?)?,
            binaries,
            activation: item.get("activation").map(text).transpose()?,
            mappings,
        });
    }
    Ok(Registry {
        version,
        palette,
        modules,
    })
}

/// Read and validate the catalog embedded in this crate.
pub fn registry() -> Result<Registry, Error> {
    let registry = parse_registry(REGISTRY_JSON.as_bytes(), ASSETS)?;
    if registry.version != VERSION {
        return Err(invalid("registry version differs from Cargo version"));
    }
    Ok(registry)
}

fn select<'a>(registry: &'a Registry, names: &[&str]) -> Result<Vec<&'a Module>, Error> {
    if names == ["all"] {
        return Ok(registry.modules.iter().collect());
    }
    let mut selected = Vec::new();
    let mut seen = BTreeSet::new();
    for name in names {
        let module = registry
            .modules
            .iter()
            .find(|module| module.id == *name)
            .ok_or_else(|| invalid(format!("unknown module {name:?}; use --list")))?;
        if seen.insert(*name) {
            selected.push(module);
        }
    }
    if selected.is_empty() {
        return Err(invalid("select known modules; use --list"));
    }
    Ok(selected)
}

fn profile_json(version: &str, palette: &str, names: &[&str]) -> Result<Vec<u8>, Error> {
    // Six bytes per input byte is enough for JSON's longest control escape.
    let capacity = 512
        + 6 * (version.len() + palette.len() + names.iter().map(|s| s.len()).sum::<usize>())
        + 16 * names.len();
    let mut output = vec![0; capacity];
    let mut writer = Writer::new(&mut output);
    writer.raw(b"{\n  \"schema\": \"zrc.profile.v1\",\n  \"version\": ");
    writer.string(version.as_bytes());
    writer.raw(b",\n  \"palette\": ");
    writer.string(palette.as_bytes());
    writer.raw(b",\n  \"modules\": [\n");
    for (index, name) in names.iter().enumerate() {
        writer.raw(b"    ");
        writer.string(name.as_bytes());
        if index + 1 != names.len() {
            writer.byte(b',');
        }
        writer.byte(b'\n');
    }
    writer.raw(b"  ]\n}\n");
    let written = writer
        .finish()
        .map_err(|error| invalid(format!("profile JSON: {error:?}")))?;
    output.truncate(written);
    Ok(output)
}

static NEXT_STAGE: AtomicU64 = AtomicU64::new(0);
struct Stage(Option<PathBuf>);
impl Stage {
    fn new(parent: &Path) -> Result<Self, Error> {
        for _ in 0..128 {
            let nonce = NEXT_STAGE.fetch_add(1, Ordering::Relaxed);
            let path = parent.join(format!(".zrc-compose-{}-{nonce}", std::process::id()));
            let mut builder = fs::DirBuilder::new();
            #[cfg(unix)]
            {
                use std::os::unix::fs::DirBuilderExt;
                builder.mode(0o700);
            }
            match builder.create(&path) {
                Ok(()) => return Ok(Self(Some(path))),
                Err(error) if error.kind() == io::ErrorKind::AlreadyExists => continue,
                Err(error) => return Err(error.into()),
            }
        }
        Err(invalid("could not reserve a fresh staging directory"))
    }
    fn path(&self) -> &Path {
        self.0.as_deref().expect("live staging directory")
    }
}
impl Drop for Stage {
    fn drop(&mut self) {
        if let Some(path) = self.0.take() {
            let _ = fs::remove_dir_all(path);
        }
    }
}
fn ensure_absent(path: &Path) -> Result<(), Error> {
    match fs::symlink_metadata(path) {
        Ok(_) => Err(invalid(
            "output already exists; compose into a new profile directory",
        )),
        Err(error) if error.kind() == io::ErrorKind::NotFound => Ok(()),
        Err(error) => Err(error.into()),
    }
}
fn write_asset(asset: &Asset, target: &Path) -> Result<(), Error> {
    match asset.bytes {
        Some(bytes) => {
            if let Some(parent) = target.parent() {
                fs::create_dir_all(parent)?;
            }
            fs::write(target, bytes)?;
            #[cfg(unix)]
            {
                use std::os::unix::fs::PermissionsExt;
                fs::set_permissions(target, fs::Permissions::from_mode(asset.mode))?;
            }
            #[cfg(not(unix))]
            let _ = asset.mode;
        }
        None => fs::create_dir_all(target)?,
    }
    Ok(())
}

/// Compose a new immutable profile. Selection is deduplicated in caller order.
///
/// A single "all" selects registry order. The output must not exist, its parent
/// must already be a regular directory, and staging stays in that same parent.
/// This function does not apply the profile or modify application settings.
pub fn compose(names: &[&str], output: impl AsRef<Path>) -> Result<PathBuf, Error> {
    let registry = registry()?;
    let selected = select(&registry, names)?;
    let names: Vec<_> = selected.iter().map(|module| module.id.as_str()).collect();
    let metadata = profile_json(&registry.version, &registry.palette, &names)?;
    let output = output.as_ref();
    let destination = if output.is_absolute() {
        output.to_path_buf()
    } else {
        std::env::current_dir()?.join(output)
    };
    ensure_absent(&destination)?;
    let parent = destination
        .parent()
        .ok_or_else(|| invalid("output requires a parent directory"))?;
    let parent_metadata = fs::symlink_metadata(parent)?;
    if !parent_metadata.is_dir() || parent_metadata.file_type().is_symlink() {
        return Err(invalid(
            "output parent must be an existing regular directory",
        ));
    }
    let mut stage = Stage::new(parent)?;
    let mut profile = String::from("# zrc.profile.v1 / Ink; generated from reviewed modules\n");
    for module in selected {
        for mapping in &module.mappings {
            let target = stage.path().join("files").join(&mapping.destination);
            let source = ASSETS
                .iter()
                .find(|asset| asset.path == mapping.source)
                .ok_or_else(|| invalid("embedded source disappeared"))?;
            if source.bytes.is_some() {
                write_asset(source, &target)?;
            } else {
                let prefix = mapping.source.clone() + "/";
                for asset in ASSETS {
                    if asset.path == mapping.source {
                        write_asset(asset, &target)?;
                    } else if let Some(suffix) = asset.path.strip_prefix(&prefix) {
                        write_asset(asset, &target.join(suffix))?;
                    }
                }
            }
            profile.push_str(&format!(
                "files/{}\t{}\n",
                mapping.destination, mapping.destination
            ));
        }
    }
    fs::write(stage.path().join("profile.zdot"), profile)?;
    fs::write(stage.path().join("zrc-profile.json"), metadata)?;
    ensure_absent(&destination)?;
    fs::rename(stage.path(), &destination)?;
    stage.0 = None;
    Ok(destination)
}

#[cfg(test)]
#[path = "../build_support.rs"]
mod build_support;
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn catalog_and_selection_preserve_order() {
        let data = registry().unwrap();
        assert_eq!(data.modules.len(), 10);
        let chosen = select(&data, &["shell", "nvim", "shell"]).unwrap();
        assert_eq!(
            chosen.iter().map(|m| m.id.as_str()).collect::<Vec<_>>(),
            ["shell", "nvim"]
        );
        assert!(select(&data, &[]).is_err());
        assert!(select(&data, &["all", "nvim"]).is_err());
    }
    #[test]
    fn normalized_paths_reject_traversal_and_platform_prefixes() {
        for path in [
            "", "/root", "../x", "x/../y", "x//y", ".", "x\ty", "x\ny", "x\0y", "C:/x", r"x\..\y",
        ] {
            assert!(normalized(path).is_err(), "{path:?}");
        }
        assert!(normalized("profiles/ink/files/.config/nvim").is_ok());
    }
    #[test]
    fn escaped_metadata_round_trips_through_the_shared_json_parser() {
        let encoded = profile_json("quote\"\\\n", "色🙂", &["x\t", "a\\b"]).unwrap();
        let mut tokens = [Token::EMPTY; 32];
        let parsed = json::parse(&encoded, &mut tokens, Limits::default()).unwrap();
        assert_eq!(
            text(parsed.root().get("version").unwrap()).unwrap(),
            "quote\"\\\n"
        );
        assert_eq!(text(parsed.root().get("palette").unwrap()).unwrap(), "色🙂");
        let names = parsed
            .root()
            .get("modules")
            .unwrap()
            .array()
            .map(text)
            .collect::<Result<Vec<_>, _>>()
            .unwrap();
        assert_eq!(names, ["x\t", "a\\b"]);
    }
    #[test]
    fn registry_rejects_duplicate_keys_and_overlapping_destinations() {
        assert!(
            parse_registry(
                br#"{"schema":"zrc.registry.v1","schema":"zrc.registry.v1"}"#,
                ASSETS
            )
            .is_err()
        );
        let data = REGISTRY_JSON.replace("\".config/kitty\"", "\".config/nvim/sub\"");
        assert!(parse_registry(data.as_bytes(), ASSETS).is_err());
        let data = REGISTRY_JSON.replace("\"id\": \"kitty\"", "\"id\": \"nvim\"");
        assert!(parse_registry(data.as_bytes(), ASSETS).is_err());
        let data = REGISTRY_JSON.replace("profiles/ink/files/.config/kitty", "../outside");
        assert!(parse_registry(data.as_bytes(), ASSETS).is_err());
    }
}
