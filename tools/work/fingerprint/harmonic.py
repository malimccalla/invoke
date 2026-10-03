"""`invoke:fp/harmonic-ngram@1.0`. Normative document: fingerprints/harmonic-ngram-v1.md.

Corroboration only. Two unrelated twelve-bar blues match completely on this channel,
so `fusion.route` will not act on it alone whatever it returns.
"""

from __future__ import annotations

from dataclasses import dataclass

from .header import FingerprintError
from .minhash import compare_blobs, encode

__all__ = ["N", "QUALITIES", "Chord", "chords_from_dicts", "compare", "harmonic_ngram", "tokens"]

N = 8
_SCHEME = 0x03

# §3.2. Extensions above the seventh are discarded: the difference between a
# thirteenth and a dominant seventh is an arranger's, not a writer's.
QUALITIES = {
    "maj": 0,
    "major": 0,
    "min": 1,
    "minor": 1,
    "dom7": 2,
    "7": 2,
    "9": 2,
    "11": 2,
    "13": 2,
    "maj7": 3,
    "maj9": 3,
    "min7": 4,
    "m7": 4,
    "min9": 4,
    "dim": 5,
    "dim7": 5,
    "hdim7": 5,
    "m7b5": 5,
    "aug": 6,
    "sus2": 7,
    "sus4": 7,
    "sus": 7,
}


@dataclass(frozen=True, slots=True)
class Chord:
    onset: float
    root: int
    quality: str


def chords_from_dicts(raw: list[dict]) -> list[Chord]:
    return [Chord(float(c["onset"]), int(c["root"]), str(c["quality"])) for c in raw]


def _quality_code(quality: str) -> int:
    key = quality.strip().lower()
    if key not in QUALITIES:
        raise FingerprintError(f"quality {quality!r} has no mapping and no underlying triad")
    return QUALITIES[key]


def preprocess(chords: list[Chord]) -> list[Chord]:
    """§2. A chord held for sixteen bars and one struck every beat are one progression."""
    ordered = sorted(chords, key=lambda c: c.onset)
    for a, b in zip(ordered, ordered[1:]):
        if a.onset == b.onset:
            raise FingerprintError("two chords share an onset; fail rather than choose")

    collapsed: list[Chord] = []
    for chord in ordered:
        prev = collapsed[-1] if collapsed else None
        if prev and prev.root == chord.root and _quality_code(prev.quality) == _quality_code(
            chord.quality
        ):
            continue
        collapsed.append(chord)
    return collapsed


def tokens(chords: list[Chord]) -> list[int]:
    """§3.3. Root motion rather than Roman numerals, so no key is ever detected."""
    return [
        ((chords[k + 1].root - chords[k].root) % 12) * 8 + _quality_code(chords[k + 1].quality)
        for k in range(len(chords) - 1)
    ]


def harmonic_ngram(chords: list[Chord]) -> bytes:
    toks = tokens(preprocess(chords))
    if len(toks) < N:
        raise FingerprintError(
            f"{len(toks)} tokens; {N} are needed. Emit no fingerprint rather than a degenerate one."
        )
    raw = bytes(toks)
    grams = {raw[i : i + N] for i in range(len(raw) - N + 1)}
    return encode(grams, scheme=_SCHEME, n=N, tokens=len(toks))


compare = compare_blobs
