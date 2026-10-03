"""The IWFP container. fingerprints/melodic-ngram-v1.md §4.2.

Big-endian throughout. The header carries `count` and `n` so that a comparison can
refuse two blobs that are not comparable, and `tokens` because a sketch over 40
symbols and one over 4000 are not equally trustworthy and nothing else records it.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

__all__ = ["HEADER_SIZE", "Header", "MAGIC", "SCHEMES", "pack", "unpack"]

MAGIC = b"IWFP"
CONTAINER_VERSION = 1
HEADER_SIZE = 16
_STRUCT = struct.Struct(">4sBBBBHHI")

# scheme id -> (algorithm identifier, disclosure class)
SCHEMES = {
    0x01: ("invoke:fp/melodic-ngram@1.0", "substantial"),
    0x02: ("invoke:fp/melodic-lsh@1.0", "opaque"),
    0x03: ("invoke:fp/harmonic-ngram@1.0", "substantial"),
    0x04: ("invoke:fp/lyric-shingle@1.0", "substantial"),
    0x05: ("invoke:fp/cqt-embedding@1.0", "substantial"),
}
ALGORITHMS = {ident: scheme_id for scheme_id, (ident, _) in SCHEMES.items()}


class FingerprintError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class Header:
    scheme: int
    major: int
    minor: int
    count: int
    n: int
    tokens: int

    @property
    def algorithm(self) -> str:
        return SCHEMES[self.scheme][0]

    @property
    def disclosure(self) -> str:
        return SCHEMES[self.scheme][1]


def pack(header: Header, values: list[int]) -> bytes:
    if len(values) != header.count:
        raise FingerprintError(f"expected {header.count} values, got {len(values)}")
    head = _STRUCT.pack(
        MAGIC,
        CONTAINER_VERSION,
        header.scheme,
        header.major,
        header.minor,
        header.count,
        header.n,
        header.tokens,
    )
    return head + b"".join(v.to_bytes(8, "big") for v in values)


def unpack(blob: bytes) -> tuple[Header, list[int]]:
    if len(blob) < HEADER_SIZE:
        raise FingerprintError("blob is shorter than the container header")
    magic, container, scheme, major, minor, count, n, tokens = _STRUCT.unpack(
        blob[:HEADER_SIZE]
    )
    if magic != MAGIC:
        raise FingerprintError("not an IWFP fingerprint")
    if container != CONTAINER_VERSION:
        raise FingerprintError(f"unsupported container version {container}")
    if scheme not in SCHEMES:
        raise FingerprintError(f"unknown scheme id {scheme:#04x}")
    if len(blob) != HEADER_SIZE + 8 * count:
        raise FingerprintError(f"expected {HEADER_SIZE + 8 * count} bytes, got {len(blob)}")
    values = [
        int.from_bytes(blob[HEADER_SIZE + 8 * i : HEADER_SIZE + 8 * i + 8], "big")
        for i in range(count)
    ]
    return Header(scheme, major, minor, count, n, tokens), values
