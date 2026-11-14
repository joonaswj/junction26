"""Download the Junction 2026 S-Pankki dataset into backend/data/raw.

Run from the backend directory:

    uv run python -m junction26.data.download

The CSVs are not committed to our repo (the transactions file is ~350 MB).
Files that already exist with the right size are skipped. The large
transactions file is stored with Git LFS upstream, so it is fetched from
GitHub's LFS media endpoint and its sha256 is verified.
"""

from __future__ import annotations

import hashlib
import os
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

REPO = "hackjunction/Junction-2026-S-pankki"
# Pinned commit so everyone gets identical data.
COMMIT = "fbdecdedf1a1f49dd641c2e6b9f2b62d0dc0cc8f"

RAW_URL = f"https://raw.githubusercontent.com/{REPO}/{COMMIT}/{{name}}"
LFS_URL = f"https://media.githubusercontent.com/media/{REPO}/{COMMIT}/{{name}}"


@dataclass(frozen=True)
class DataFile:
    name: str
    lfs: bool = False
    size: int | None = None
    sha256: str | None = None

    @property
    def url(self) -> str:
        return (LFS_URL if self.lfs else RAW_URL).format(name=self.name)


FILES = [
    DataFile("tx_customers_junction.csv"),
    DataFile("mtg_negotiation_history.csv"),
    DataFile("mtg_tx_customer_link_and_final_mtg_infio.csv"),
    DataFile(
        "tx_junction_transactions.csv",
        lfs=True,
        size=362_796_501,
        sha256="49b3265d8e44e751de305a074dcffcda732bb79aa1e07b46fcca774ce76f1e63",
    ),
]


def data_dir() -> Path:
    """Directory holding the raw CSVs. Override with JUNCTION_DATA_DIR."""
    env = os.environ.get("JUNCTION_DATA_DIR")
    if env:
        return Path(env)
    # backend/src/junction26/data/download.py -> backend/data/raw
    return Path(__file__).resolve().parents[3] / "data" / "raw"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _is_lfs_pointer(path: Path) -> bool:
    with path.open("rb") as f:
        return f.read(40).startswith(b"version https://git-lfs")


def _download(file: DataFile, dest: Path) -> None:
    tmp = dest.with_suffix(dest.suffix + ".part")
    print(f"Downloading {file.name} ...", flush=True)
    with urllib.request.urlopen(file.url) as resp, tmp.open("wb") as out:
        total = int(resp.headers.get("Content-Length") or 0)
        done = 0
        while chunk := resp.read(1 << 20):
            out.write(chunk)
            done += len(chunk)
            if total > 10 << 20:
                print(f"\r  {done >> 20} / {total >> 20} MB", end="", flush=True)
        if total > 10 << 20:
            print()
    if _is_lfs_pointer(tmp):
        tmp.unlink()
        raise RuntimeError(f"{file.name}: got a Git LFS pointer instead of data")
    if file.sha256 and _sha256(tmp) != file.sha256:
        tmp.unlink()
        raise RuntimeError(f"{file.name}: sha256 mismatch, download corrupted")
    tmp.replace(dest)


def _is_complete(file: DataFile, path: Path) -> bool:
    if not path.exists() or _is_lfs_pointer(path):
        return False
    return file.size is None or path.stat().st_size == file.size


def download_all(force: bool = False) -> Path:
    target = data_dir()
    target.mkdir(parents=True, exist_ok=True)
    for file in FILES:
        dest = target / file.name
        if not force and _is_complete(file, dest):
            print(f"OK  {file.name} (already downloaded)")
            continue
        _download(file, dest)
        print(f"OK  {file.name}")
    print(f"Data is in {target}")
    return target


if __name__ == "__main__":
    download_all(force="--force" in sys.argv)
