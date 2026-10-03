"""`invoke:fp/fusion@1.0`. Normative document: fingerprints/fusion-v1.md.

Every constant here is provisional: reasoned, not measured. `MEASURED` stays False
until fingerprints/benchmark.md exists, and `fuse` reports it alongside every score.
"""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = ["FLOORS", "MEASURED", "OUTCOMES", "Result", "WEIGHTS", "fuse", "route"]

MEASURED = False

WEIGHTS = {"melodic": 0.40, "lyric": 0.35, "embedding": 0.20, "harmonic": 0.05}
FLOORS = {"melodic": 0.55, "lyric": 0.70, "embedding": 0.75, "harmonic": 0.80}
CANDIDATE_THRESHOLD = 0.85
MATERIAL_THRESHOLD = 0.60

OUTCOMES = ("candidate_same_work", "shares_material", "none")


@dataclass(frozen=True, slots=True)
class Result:
    score: float
    outcome: str
    channels: dict[str, float]
    absent: tuple[str, ...]
    cleared: tuple[str, ...]
    measured: bool = MEASURED
    notes: tuple[str, ...] = field(default=())

    def report(self) -> dict:
        """A bare fused score is not reportable (fusion-v1 §7)."""
        return {
            "score": round(self.score, 4),
            "outcome": self.outcome,
            "channels": {k: round(v, 4) for k, v in self.channels.items()},
            "absent": list(self.absent),
            "cleared_floor": list(self.cleared),
            "thresholds": "measured" if self.measured else "provisional",
            "notes": list(self.notes),
        }


def fuse(channels: dict[str, float]) -> float:
    """Weighted mean over the channels actually present.

    Normalising by the present weights is what keeps the number on one scale as
    channels drop out, so a threshold means the same for an instrumental as for a song.
    An absent channel leaves the sum; it does not score zero.
    """
    present = {k: v for k, v in channels.items() if v is not None and k in WEIGHTS}
    if not present:
        return 0.0
    total = sum(WEIGHTS[k] for k in present)
    return sum(WEIGHTS[k] * v for k, v in present.items()) / total


def route(channels: dict[str, float]) -> Result:
    present = {k: v for k, v in channels.items() if v is not None and k in WEIGHTS}
    absent = tuple(sorted(set(WEIGHTS) - set(present)))
    cleared = tuple(sorted(k for k, v in present.items() if v >= FLOORS[k]))
    score = fuse(present)
    notes: list[str] = []

    if set(present) == {"harmonic"}:
        # §3. Harmony alone matches two unrelated twelve-bar blues completely. The
        # weight makes it unable to carry a result arithmetically; this makes it
        # unable to as a matter of specification, so a reweighting cannot remove it.
        notes.append("harmonic channel alone; no outcome regardless of score")
        outcome = "none"
    elif score >= CANDIDATE_THRESHOLD and len(present) >= 2 and len(cleared) >= 2:
        outcome = "candidate_same_work"
    elif score >= MATERIAL_THRESHOLD and cleared:
        outcome = "shares_material"
    else:
        outcome = "none"

    if not MEASURED:
        notes.append("thresholds are provisional and unmeasured")
    if outcome == "candidate_same_work":
        notes.append("a machine may assert no relation stronger than this; promotion needs a party")

    return Result(score, outcome, dict(present), absent, cleared, MEASURED, tuple(notes))
