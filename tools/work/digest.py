"""Digests and the signing input. SPEC.md §5.2–§5.5."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from . import jcs

__all__ = [
    "ALGORITHMS",
    "DIGEST_RE",
    "blob_digest",
    "digest_of",
    "parent_digest",
    "parse_digest",
    "signing_input",
    "signing_input_digest",
]

ALGORITHMS = {"sha256": hashlib.sha256, "sha512": hashlib.sha512}
_HEX_LEN = {"sha256": 64, "sha512": 128}
DIGEST_RE = re.compile(r"^(?P<alg>[a-z0-9]+):(?P<hex>[0-9a-f]+)$")


class DigestError(ValueError):
    pass


def parse_digest(value: str) -> tuple[str, str]:
    """Split a digest, rejecting unrecognised algorithms rather than ignoring them."""
    m = DIGEST_RE.match(value)
    if not m:
        raise DigestError(f"{value!r} is not <algorithm>:<lowercase-hex>")
    alg, hexval = m.group("alg"), m.group("hex")
    if alg not in ALGORITHMS:
        raise DigestError(f"unsupported digest algorithm {alg!r}")
    if len(hexval) != _HEX_LEN[alg]:
        raise DigestError(f"{alg} digest must be {_HEX_LEN[alg]} hex characters")
    return alg, hexval


def digest_of(data: bytes, algorithm: str = "sha256") -> str:
    if algorithm not in ALGORITHMS:
        raise DigestError(f"unsupported digest algorithm {algorithm!r}")
    return f"{algorithm}:{ALGORITHMS[algorithm](data).hexdigest()}"


def blob_digest(data: bytes, algorithm: str = "sha256") -> str:
    """Computed over the raw bytes of a blob, never over a JSON view of it (§5.3)."""
    return digest_of(data, algorithm)


def signing_input(document: dict[str, Any]) -> bytes:
    """JCS(document \\ {"signatures"}). Everything else, including ext, is covered."""
    return jcs.canonicalize({k: v for k, v in document.items() if k != "signatures"})


def signing_input_digest(document: dict[str, Any], algorithm: str = "sha256") -> str:
    return digest_of(signing_input(document), algorithm)


def parent_digest(parent: dict[str, Any], algorithm: str = "sha256") -> str:
    """Over the parent's canonical form *including* its signatures (§5.5)."""
    return digest_of(jcs.canonicalize(parent), algorithm)
