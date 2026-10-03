"""Content-addressed blob store. SPEC.md §5.3, §3.3.

`digest` is authoritative and `locators` are advisory, so every read verifies.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from .digest import blob_digest, parse_digest

__all__ = ["BlobStore", "DigestMismatch"]


class DigestMismatch(ValueError):
    pass


class BlobStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def path_for(self, digest: str) -> Path:
        algorithm, hexval = parse_digest(digest)
        return self.root / algorithm / hexval

    def put(self, data: bytes, *, algorithm: str = "sha256") -> str:
        digest = blob_digest(data, algorithm)
        path = self.path_for(digest)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_bytes(data)
        return digest

    def get(self, digest: str) -> bytes:
        data = self.path_for(digest).read_bytes()
        actual = blob_digest(data, parse_digest(digest)[0])
        if actual != digest:
            raise DigestMismatch(f"stored blob hashes to {actual}, not {digest}")
        return data

    def has(self, digest: str) -> bool:
        return self.path_for(digest).exists()

    def write_package(self, document_bytes: bytes, digests: list[str], out: str | Path) -> Path:
        """A `.workpkg`: the manifest plus every blob it references (§3.3)."""
        out = Path(out)
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("manifest.work", document_bytes)
            for digest in sorted(set(digests)):
                algorithm, hexval = parse_digest(digest)
                zf.writestr(f"blobs/{algorithm}/{hexval}", self.get(digest))
        return out
