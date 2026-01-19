from pathlib import Path
from datetime import datetime, timezone
import tarfile
import json

class ManifestError(Exception):
    pass

class UnsupportedManifestVersion(ManifestError):
    pass

def create_manifest(
    sources: list[Path],
    compression: str,
    level: int,
    tool_name: str,
    tool_version: str
) -> dict:
    return {
        "manifest_version": 1,
        "tool": {
            "name": tool_name,
            "version": tool_version
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
        "archive": {
            "format": "tar",
            "compression": compression,
            "compression_level": level
        },
        "sources": [
            {
                "path": str(p),
                "type": "directory" if p.is_dir() else "file",
            }
            for p in sources
        ],
        "checksum": {
            "algorithm": "sha256"
        }
    }
    
def write_manifest(manifest: dict, dest: Path) -> Path:
    manifest_path = dest / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    return manifest_path

def read_manifest_from_tar(tar_path: Path) -> dict:
    try:
        with tarfile.open(tar_path, "r") as tar:
            try:
                member = tar.getmember("manifest.json")
            except KeyError:
                raise ManifestError("manifest.json not found in archive")

            f = tar.extractfile(member)
            if f is None:
                raise ManifestError("Unable to read manifest.json")
            
            return json.load(f)
        
    except tarfile.TarError as e:
        raise ManifestError(f"Invalid tar archive: {e}")

SUPPORTED_MANIFEST_VERSION = 1

def validate_manifest(manifest: dict):
    if "manifest_version" not in manifest:
        raise ManifestError("Missing manifest_version")

    if manifest["manifest_version"] != SUPPORTED_MANIFEST_VERSION:
        raise UnsupportedManifestVersion(f"Unsupported manifest version")

    archive = manifest.get("archive", {})
    if archive.get("format") != "tar":
        raise ManifestError("Unsupported archive format")

    if archive.get("compression") != "zstd":
        raise ManifestError("Unsupported compression algorithm")
