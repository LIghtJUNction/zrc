use std::fs;
use std::io;
use std::path::Path;

#[derive(Debug)]
pub struct AssetSource {
    pub path: String,
    pub directory: bool,
    pub mode: u32,
}

fn invalid(message: impl Into<String>) -> io::Error {
    io::Error::new(io::ErrorKind::InvalidData, message.into())
}

/// Collect all configuration assets, including hidden directories, without following links.
pub fn collect_assets(root: &Path) -> io::Result<Vec<AssetSource>> {
    let mut current = root.to_path_buf();
    for part in ["profiles", "ink", "files"] {
        current.push(part);
        let metadata = fs::symlink_metadata(&current)?;
        if !metadata.is_dir() || metadata.file_type().is_symlink() {
            return Err(invalid("asset ancestors must be regular directories"));
        }
    }
    let mut assets = Vec::new();
    walk(root, &current, &mut assets)?;
    Ok(assets)
}

fn walk(root: &Path, path: &Path, assets: &mut Vec<AssetSource>) -> io::Result<()> {
    let metadata = fs::symlink_metadata(path)?;
    let kind = metadata.file_type();
    if kind.is_symlink() || !(kind.is_dir() || kind.is_file()) {
        return Err(invalid(format!(
            "asset is a symlink or special file: {}",
            path.display()
        )));
    }
    let relative = path
        .strip_prefix(root)
        .map_err(|error| invalid(error.to_string()))?;
    let components: Option<Vec<_>> = relative.iter().map(|part| part.to_str()).collect();
    let name = components
        .ok_or_else(|| invalid("asset paths must be UTF-8"))?
        .join("/");
    #[cfg(unix)]
    let mode = {
        use std::os::unix::fs::PermissionsExt;
        metadata.permissions().mode() & 0o777
    };
    #[cfg(not(unix))]
    let mode = if kind.is_dir() { 0o755 } else { 0o644 };
    assets.push(AssetSource {
        path: name,
        directory: kind.is_dir(),
        mode,
    });
    if kind.is_dir() {
        let mut children = fs::read_dir(path)?.collect::<Result<Vec<_>, _>>()?;
        children.sort_by_key(|entry| entry.file_name());
        for child in children {
            walk(root, &child.path(), assets)?;
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicU64, Ordering};
    static NEXT: AtomicU64 = AtomicU64::new(0);
    struct Temp(std::path::PathBuf);
    impl Temp {
        fn new() -> Self {
            let path = std::env::temp_dir().join(format!(
                "zrc-asset-test-{}-{}",
                std::process::id(),
                NEXT.fetch_add(1, Ordering::Relaxed)
            ));
            fs::create_dir(&path).unwrap();
            fs::create_dir_all(path.join("profiles/ink/files/.config/test")).unwrap();
            Self(path)
        }
    }
    impl Drop for Temp {
        fn drop(&mut self) {
            let _ = fs::remove_dir_all(&self.0);
        }
    }
    #[test]
    fn hidden_assets_and_empty_directories_are_collected() {
        let temp = Temp::new();
        fs::write(
            temp.0.join("profiles/ink/files/.config/test/value"),
            b"reviewed",
        )
        .unwrap();
        let assets = collect_assets(&temp.0).unwrap();
        assert!(
            assets
                .iter()
                .any(|asset| asset.path.ends_with("/.config/test") && asset.directory)
        );
        assert!(assets.iter().any(|asset| asset.path.ends_with("/value")
            && !asset.directory
            && asset.mode & 0o444 != 0));
    }
    #[cfg(unix)]
    #[test]
    fn source_symlinks_and_special_files_are_rejected() {
        let temp = Temp::new();
        let link = temp.0.join("profiles/ink/files/.config/test/link");
        std::os::unix::fs::symlink("missing", &link).unwrap();
        assert!(collect_assets(&temp.0).is_err());
        fs::remove_file(link).unwrap();
        let socket_path = temp.0.join("profiles/ink/files/.config/test/socket");
        let _socket = std::os::unix::net::UnixListener::bind(socket_path).unwrap();
        assert!(collect_assets(&temp.0).is_err());
    }
    #[cfg(unix)]
    #[test]
    fn a_symlinked_asset_ancestor_is_rejected() {
        let temp = Temp::new();
        fs::rename(temp.0.join("profiles"), temp.0.join("saved")).unwrap();
        std::os::unix::fs::symlink("saved", temp.0.join("profiles")).unwrap();
        assert!(collect_assets(&temp.0).is_err());
    }
}
