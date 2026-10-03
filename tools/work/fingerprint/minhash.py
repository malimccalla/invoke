"""Shared MinHash machinery. fingerprints/melodic-ngram-v1.md §3.5 and §4.1.

SHA-256 rather than a permutation family over a prime field: every language has it,
nobody has to agree on a modulus, and the cost is irrelevant beside the transcription
that produced the input.
"""

from __future__ import annotations

import hashlib

from .header import FingerprintError, Header, pack, unpack

__all__ = [
    "DROPOUT_PERCENT",
    "K",
    "apply_dropout",
    "compare_blobs",
    "compare_signatures",
    "encode",
    "minhash",
]

K = 128
DROPOUT_PERCENT = 15
_MAX_U64 = (1 << 64) - 1
_PERM_PREFIX = [i.to_bytes(8, "little") for i in range(K)]


def _h64(data: bytes) -> int:
    return int.from_bytes(hashlib.sha256(data).digest()[:8], "big")


def apply_dropout(grams: set[bytes]) -> set[bytes]:
    """Discard elements where h(0x00 || g) mod 100 < 15.

    Keyed on the element, not on the producer, so two parties drop the same n-grams
    and the Jaccard estimator stays unbiased. A seeded-per-producer dropout would be
    unbiased too, and would have the two parties sketching different sets.
    """
    return {g for g in grams if _h64(b"\x00" + g) % 100 >= DROPOUT_PERCENT}


def minhash(grams: set[bytes], k: int = K) -> list[int]:
    if not grams:
        raise FingerprintError("cannot sketch an empty set")
    sig = [_MAX_U64] * k
    for g in grams:
        for j in range(k):
            v = _h64(_PERM_PREFIX[j] + g)
            if v < sig[j]:
                sig[j] = v
    return sig


def encode(grams: set[bytes], *, scheme: int, n: int, tokens: int) -> bytes:
    kept = apply_dropout(grams)
    if not kept:
        raise FingerprintError("every n-gram was dropped; emit no fingerprint instead")
    return pack(Header(scheme, 1, 0, K, n, tokens), minhash(kept))


def compare_signatures(a: list[int], b: list[int]) -> float:
    if len(a) != len(b):
        raise FingerprintError("signatures of differing length are not comparable")
    return sum(x == y for x, y in zip(a, b)) / len(a)


def compare_blobs(a: bytes, b: bytes) -> float:
    """Estimated Jaccard. Refuses rather than scoring zero when the two differ in kind.

    Returning zero for an incomparable pair would report two identical works as
    maximally dissimilar (fingerprints/README.md §2).
    """
    ha, sa = unpack(a)
    hb, sb = unpack(b)
    if (ha.scheme, ha.major, ha.count, ha.n) != (hb.scheme, hb.major, hb.count, hb.n):
        raise FingerprintError(
            f"{ha.algorithm} and {hb.algorithm} blobs are not comparable"
        )
    return compare_signatures(sa, sb)
