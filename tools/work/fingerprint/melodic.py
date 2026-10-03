"""`invoke:fp/melodic-ngram@1.0` and `invoke:fp/melodic-lsh@1.0`.

Normative document: fingerprints/melodic-ngram-v1.md.

Transposition invariance comes from using intervals rather than pitches, and tempo
invariance from using inter-onset ratios rather than durations. Neither requires a key
to be detected or a beat to be tracked, and a scheme that never estimates the key
cannot estimate it wrongly.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

from .header import FingerprintError, Header, pack, unpack
from .minhash import K, apply_dropout, compare_blobs, encode, minhash

__all__ = [
    "BANDS",
    "N",
    "Note",
    "compare",
    "melodic_lsh",
    "melodic_ngram",
    "notes_from_dicts",
    "preprocess",
    "tokens",
]

N = 12
BANDS = 16
ROWS = K // BANDS
MERGE_GAP = 0.025
MIN_DURATION = 0.040
_SCHEME_NGRAM = 0x01
_SCHEME_LSH = 0x02

# §3.2. Midpoints of a half-octave grid in log space, given explicitly rather than
# computed, so that no implementation's log2 or rounding mode can shift a boundary.
DURATION_THRESHOLDS = (
    0.42044820762685725,
    0.59460355750136053,
    0.84089641525371454,
    1.18920711500272107,
    1.68179283050742909,
    2.37841423000544171,
)


@dataclass(frozen=True, slots=True)
class Note:
    onset: float
    pitch: int
    duration: float

    @property
    def offset(self) -> float:
        return self.onset + self.duration


def notes_from_dicts(raw: list[dict]) -> list[Note]:
    return [Note(float(n["onset"]), int(n["pitch"]), float(n["duration"])) for n in raw]


def _duration_class(ratio: float) -> int:
    for i, threshold in enumerate(DURATION_THRESHOLDS):
        if ratio < threshold:
            return i - 3
    return 3


def preprocess(notes: list[Note]) -> list[Note]:
    """§2. Monophonic reduction, articulation merge, minimum duration."""
    ordered = sorted(notes, key=lambda n: (n.onset, -n.pitch))

    mono: list[Note] = []
    for note in ordered:
        if mono and note.onset < mono[-1].offset:
            # Overlap: keep the higher pitch and discard the other outright. Not
            # truncated — a truncated note has a duration the source never contained.
            if note.pitch > mono[-1].pitch:
                mono[-1] = note
            continue
        mono.append(note)

    merged: list[Note] = []
    for note in mono:
        prev = merged[-1] if merged else None
        if prev and prev.pitch == note.pitch and note.onset - prev.offset < MERGE_GAP:
            merged[-1] = Note(prev.onset, prev.pitch, note.offset - prev.onset)
            continue
        merged.append(note)

    return [n for n in merged if n.duration >= MIN_DURATION]


def tokens(notes: list[Note]) -> list[int]:
    """§3.3. One byte per token over a 175-symbol alphabet."""
    if len(notes) < 3:
        return []
    out: list[int] = []
    for k in range(len(notes) - 2):
        interval = max(-12, min(12, notes[k + 1].pitch - notes[k].pitch))
        ioi_a = notes[k + 1].onset - notes[k].onset
        ioi_b = notes[k + 2].onset - notes[k + 1].onset
        if ioi_a <= 0 or ioi_b <= 0:
            raise FingerprintError("zero inter-onset interval; preprocessing is wrong")
        duration = _duration_class(ioi_b / ioi_a)
        out.append((interval + 12) * 7 + (duration + 3))
    return out


def _grams(toks: list[int]) -> set[bytes]:
    raw = bytes(toks)
    return {raw[i : i + N] for i in range(len(raw) - N + 1)}


def _prepare(notes: list[Note]) -> tuple[set[bytes], int]:
    processed = preprocess(notes)
    toks = tokens(processed)
    if len(toks) < N:
        raise FingerprintError(
            f"{len(processed)} notes yield {len(toks)} tokens; {N} are needed. "
            "Emit no fingerprint rather than a degenerate one."
        )
    return _grams(toks), len(toks)


def melodic_ngram(notes: list[Note]) -> bytes:
    grams, count = _prepare(notes)
    return encode(grams, scheme=_SCHEME_NGRAM, n=N, tokens=count)


def melodic_lsh(notes: list[Note]) -> bytes:
    """§5. Band digests only — a retrieval filter, not a similarity measure."""
    grams, count = _prepare(notes)
    kept = apply_dropout(grams)
    if not kept:
        raise FingerprintError("every n-gram was dropped; emit no fingerprint instead")
    signature = minhash(kept)
    bands = []
    for b in range(BANDS):
        payload = b"\x01" + b.to_bytes(8, "little")
        for value in signature[b * ROWS : (b + 1) * ROWS]:
            payload += value.to_bytes(8, "big")
        bands.append(int.from_bytes(hashlib.sha256(payload).digest()[:8], "big"))
    return pack(Header(_SCHEME_LSH, 1, 0, BANDS, N, count), bands)


def bands_of(blob: bytes) -> list[int]:
    header, values = unpack(blob)
    if header.scheme != _SCHEME_LSH:
        raise FingerprintError(f"{header.algorithm} is not a band blob")
    return values


compare = compare_blobs
