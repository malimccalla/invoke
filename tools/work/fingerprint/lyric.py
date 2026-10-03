"""`invoke:fp/lyric-shingle@1.0`. Normative document: fingerprints/lyric-shingle-v1.md.

The strongest single indicator that two recordings are one work, and zero across
translation. No stopword removal and no stemming: the function words are where a
lyric's rhythm lives, and stemming would merge tenses a writer chose between.
"""

from __future__ import annotations

import re
import unicodedata

from .header import FingerprintError
from .minhash import compare_blobs, encode

__all__ = ["W", "compare", "lyric_shingle", "normalise", "shingles"]

W = 5
_SCHEME = 0x04
_MARKER = re.compile(r"^\[.*\]$|^\(.*\)$", re.DOTALL)
_APOSTROPHES = {"\u0027", "\u2019"}


def _strip_token(token: str) -> str:
    """Remove P and S characters, keeping an apostrophe between two letters."""
    out = []
    for i, ch in enumerate(token):
        if ch in _APOSTROPHES:
            prev_ok = i > 0 and token[i - 1].isalpha()
            next_ok = i + 1 < len(token) and token[i + 1].isalpha()
            if prev_ok and next_ok:
                out.append("\u0027")
            continue
        if unicodedata.category(ch)[0] in "PS":
            continue
        out.append(ch)
    return "".join(out)


def normalise(text: str) -> list[str]:
    """§2. NFKC, full case folding, punctuation, structural markers."""
    folded = unicodedata.normalize("NFKC", text).casefold()
    words = []
    for token in folded.split():
        if _MARKER.match(token):
            continue
        stripped = _strip_token(token)
        if stripped:
            words.append(stripped)
    return words


def shingles(words: list[str]) -> set[bytes]:
    return {" ".join(words[i : i + W]).encode("utf-8") for i in range(len(words) - W + 1)}


def lyric_shingle(text: str) -> bytes:
    words = normalise(text)
    if len(words) < W:
        raise FingerprintError(
            f"{len(words)} words; {W} are needed. An instrumental has no lyric "
            "component and therefore no entry — an absent signal, not a low score."
        )
    return encode(shingles(words), scheme=_SCHEME, n=W, tokens=len(words))


compare = compare_blobs
