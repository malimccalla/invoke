"""Audio analysis, behind an interface.

The analysers are the slow, heavy, non-deterministic half of ingestion. Everything
downstream of them — digests, fingerprints, document assembly, provenance — is
deterministic logic, and it is where the errors that matter live: a fingerprint with
one quantisation boundary wrong is a well-formed blob that silently never matches.

So the interface comes first and the models arrive behind it. The fixture analysers
are also what the fingerprint test vectors are generated from, since a vector derived
from "whatever CREPE said today" cannot be frozen.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable

from ..fingerprint.harmonic import Chord
from ..fingerprint.melodic import Note

__all__ = ["Analyser", "Analysis", "FixtureAnalyser", "Stage", "SyntheticAnalyser"]


@dataclass(frozen=True, slots=True)
class Stage:
    """A producer and its confidence, for the provenance entry every derived value needs."""

    producer: str
    confidence: float


@dataclass
class Analysis:
    notes: list[Note] | None = None
    chords: list[Chord] | None = None
    lyrics: str | None = None
    structure: list[dict] | None = None
    key: str | None = None
    tempo_bpm: float | None = None
    metre: str | None = None
    duration_ms: int | None = None
    stages: dict[str, Stage] = field(default_factory=dict)

    def stage(self, name: str) -> Stage | None:
        return self.stages.get(name)


@runtime_checkable
class Analyser(Protocol):
    name: str

    def analyse(self, audio: Path) -> Analysis: ...


_INTERVALS = (2, -1, 3, -2, 5, -4, 1, -3, 2, 7, -5, 2, -2, 4, -1, -6, 3, 1)
_STEPS = (0.5, 0.25, 0.5, 1.0, 0.25, 0.75, 0.5, 0.5, 0.25, 1.0)
_QUALITIES = ("maj", "min", "maj7", "min7", "dom7", "sus4")
_WORDS = (
    "low tide the harbour empties out again and i am counting every stone you left "
    "behind me on the wall where we were young enough to think the water never "
    "turned around but it does and so do i and so do you"
).split()


class SyntheticAnalyser:
    """Deterministic pseudo-analysis derived from the audio bytes.

    Not an analysis of anything — it never looks at the waveform. It exists so the
    whole pipeline can be exercised without the model stack, and because two distinct
    files must yield distinct fingerprints for the matcher's tests to mean anything.
    Emits no confidences above 0.5: nothing here is a measurement.
    """

    name = "invoke:pipeline/synthetic@0.1.0"

    def analyse(self, audio: Path) -> Analysis:
        seed = hashlib.sha256(Path(audio).read_bytes()).digest()
        stream = [b for b in seed] * 8

        notes, pitch, t = [], 55 + seed[0] % 12, 0.0
        for i in range(64):
            step = _STEPS[(stream[i] + i) % len(_STEPS)]
            notes.append(Note(t, max(36, min(96, pitch)), step * 0.8))
            t += step
            pitch += _INTERVALS[stream[i + 1] % len(_INTERVALS)]

        chords = [
            Chord(float(i * 2), (stream[i + 64] * 5) % 12, _QUALITIES[stream[i + 96] % len(_QUALITIES)])
            for i in range(24)
        ]

        words = [_WORDS[(stream[i + 128] + i) % len(_WORDS)] for i in range(48)]

        stage = Stage(self.name, 0.5)
        return Analysis(
            notes=notes,
            chords=chords,
            lyrics=" ".join(words),
            structure=[{"label": "verse", "start_ms": 0}, {"label": "chorus", "start_ms": 30000}],
            key=f"{'CDEFGAB'[seed[1] % 7]} {'major' if seed[2] % 2 else 'minor'}",
            tempo_bpm=float(80 + seed[3] % 60),
            metre="4/4",
            duration_ms=int(t * 1000),
            stages={k: stage for k in ("melody", "harmony", "lyrics", "structure", "attributes")},
        )


class FixtureAnalyser:
    """Reads a hand-written analysis from JSON. The source of the test vectors."""

    name = "invoke:pipeline/fixture@0.1.0"

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def analyse(self, audio: Path) -> Analysis:  # noqa: ARG002 - fixture ignores the audio
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        stage = Stage(self.name, float(raw.get("confidence", 0.5)))
        return Analysis(
            notes=[Note(**n) for n in raw["notes"]] if raw.get("notes") else None,
            chords=[Chord(**c) for c in raw["chords"]] if raw.get("chords") else None,
            lyrics=raw.get("lyrics"),
            structure=raw.get("structure"),
            key=raw.get("key"),
            tempo_bpm=raw.get("tempo_bpm"),
            metre=raw.get("metre"),
            duration_ms=raw.get("duration_ms"),
            stages={k: stage for k in ("melody", "harmony", "lyrics", "structure", "attributes")},
        )
