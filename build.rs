mod build_support;

use std::env;
use std::fs;
use std::path::PathBuf;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let root =
        PathBuf::from(env::var_os("CARGO_MANIFEST_DIR").ok_or("missing manifest directory")?);
    let version = fs::read_to_string(root.join("VERSION"))?;
    if version.trim() != env::var("CARGO_PKG_VERSION")? {
        return Err("VERSION and Cargo.toml must agree".into());
    }
    println!("cargo:rerun-if-changed=profiles/ink/files");
    println!("cargo:rerun-if-changed=registry.json");
    println!("cargo:rerun-if-changed=VERSION");
    println!("cargo:rerun-if-changed=build_support.rs");
    let mut generated = String::from("static ASSETS: &[Asset] = &[\n");
    for asset in build_support::collect_assets(&root)? {
        let bytes = if asset.directory {
            "None".to_owned()
        } else {
            format!(
                "Some(include_bytes!(concat!(env!(\"CARGO_MANIFEST_DIR\"), \"/\", {:?})))",
                asset.path
            )
        };
        generated.push_str(&format!(
            "Asset {{ path: {:?}, bytes: {}, mode: {} }},\n",
            asset.path, bytes, asset.mode
        ));
    }
    generated.push_str("];\n");
    let output = PathBuf::from(env::var_os("OUT_DIR").ok_or("missing build output directory")?);
    fs::write(output.join("assets.rs"), generated)?;
    Ok(())
}
