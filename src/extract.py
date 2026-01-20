from pathlib import Path
import tarfile

def extract_tar(tar_path: Path, destination: Path) -> Path:
    with tarfile.open(tar_path, "r") as tar:
        members = [
            m for m in tar.getmembers()
            if m.name != "manifest.json"
        ]
        tar.extractall(destination, members)
