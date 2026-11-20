"""Download the confidential sample pack into ./data and verify every file's SHA-256.

The documents are not committed to git (the brief asks us not to share them), so a
fresh clone runs this once:

    uv run python scripts/fetch_data.py

Files that already exist with the right checksum are skipped, so re-running is cheap.
"""

from __future__ import annotations

import hashlib
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = Path(__file__).resolve().parent / "sample_pack_manifest.json"
DATA_DIR = ROOT / "data"
DOWNLOAD_URL = "https://drive.usercontent.google.com/download?id={id}&export=download"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch(file_id: str) -> bytes:
    request = urllib.request.Request(
        DOWNLOAD_URL.format(id=file_id), headers={"User-Agent": "invoice-extractor/1.0"}
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    failures: list[str] = []

    for entry in manifest["files"]:
        target = DATA_DIR / entry["path"]
        if target.exists() and sha256(target.read_bytes()) == entry["sha256"]:
            print(f"  ok      {entry['path']}")
            continue

        try:
            payload = fetch(entry["drive_id"])
        except OSError as exc:
            failures.append(f"{entry['path']}: download failed ({exc})")
            print(f"  FAILED  {entry['path']}")
            continue

        if sha256(payload) != entry["sha256"]:
            failures.append(f"{entry['path']}: checksum mismatch (got {len(payload)} bytes)")
            print(f"  BAD     {entry['path']}")
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        print(f"  fetched {entry['path']}")

    if failures:
        print("\nSome files could not be fetched:", *failures, sep="\n  ")
        print(f"\nDownload them by hand from {manifest['source']} into {DATA_DIR}.")
        return 1

    print(f"\nSample pack ready in {DATA_DIR} ({len(manifest['files'])} files verified).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
