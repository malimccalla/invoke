"""Audio to a draft `.work` document.

Nothing machine-produced leaves here without `derived: true`, a named producer and a
confidence (SPEC.md §6.18, §9.1). The source recording lands in `evidence[]` as a
`reference_recording`; it is never a `content` component, because a recording is
evidence that a work exists and is not the work.

What the pipeline cannot produce is the rights graph. Writers, IPI numbers, splits,
publishers and chain of title are not derivable from audio and never will be, so the
caller supplies a writer and gets a self-owned draft to correct.
"""

from __future__ import annotations

import json
import os
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .. import SPEC_VERSION, __version__
from ..blobs import BlobStore
from ..fingerprint import harmonic, lyric, melodic
from ..fingerprint.header import FingerprintError
from ..model import SCHEMA_URL, Document
from .analyser import Analyser, Analysis, SyntheticAnalyser

__all__ = ["IngestResult", "ingest", "ulid"]

_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def ulid(now_ms: int | None = None) -> str:
    """48-bit millisecond timestamp, 80 bits of randomness, Crockford base32."""
    value = ((now_ms if now_ms is not None else int(time.time() * 1000)) << 80) | secrets.randbits(80)
    return "".join(_CROCKFORD[(value >> shift) & 0x1F] for shift in range(125, -1, -5))


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class IngestResult:
    document: Document
    digests: list[str]
    skipped: dict[str, str]


class _Builder:
    def __init__(self, store: BlobStore, analysis: Analysis) -> None:
        self.store = store
        self.analysis = analysis
        self.content: list[dict[str, Any]] = []
        self.provenance: list[dict[str, Any]] = []
        self.digests: list[str] = []
        self.skipped: dict[str, str] = {}

    def _put(self, data: bytes) -> str:
        digest = self.store.put(data)
        self.digests.append(digest)
        return digest

    def component(
        self,
        *,
        role: str,
        data: bytes,
        media_type: str,
        stage_name: str,
        subrole: str | None = None,
        derived: bool = True,
        computed_over: str | None = None,
        algorithm: str | None = None,
        disclosure: str | None = None,
    ) -> None:
        digest = self._put(data)
        self.content.append(
            {
                "role": role,
                "subrole": subrole,
                "media_type": media_type,
                "digest": digest,
                "size": len(data),
                "derived": derived,
                "attested_by": None,
                "computed_over": computed_over,
                "algorithm": algorithm,
                "disclosure": disclosure,
                "locators": [],
            }
        )
        if derived:
            stage = self.analysis.stage(stage_name)
            self.provenance.append(
                {
                    "at": _now(),
                    "actor": algorithm or (stage.producer if stage else "unknown"),
                    "action": "derived",
                    "target": role if subrole is None else f"{role}.{subrole}",
                    "from": computed_over,
                    "confidence": stage.confidence if stage and algorithm is None else None,
                    "note": None,
                }
            )

    def fingerprint(self, *, subrole: str, over: str, stage: str, encode) -> None:
        try:
            blob = encode()
        except FingerprintError as exc:
            # Emitting no entry is correct. A sketch over an empty set is a
            # well-formed blob that matches everything.
            self.skipped[f"fingerprint.{subrole}"] = str(exc)
            return
        from ..fingerprint.header import unpack

        header, _ = unpack(blob)
        self.component(
            role="fingerprint",
            subrole=subrole,
            data=blob,
            media_type="application/octet-stream",
            stage_name=stage,
            computed_over=over,
            algorithm=header.algorithm,
            disclosure=header.disclosure,
        )


def _rights_stub(writer_party_id: str, writer: str) -> dict[str, Any]:
    """One uncontrolled writer owning the whole work.

    `OWR` rather than `SWR`: an unpublished writer has no agreement to reference
    (WORK-038) and no publisher-for-writer link to appear in (WORK-036). The shares
    total 10000 because WORK-032 admits no other answer, and a pipeline that emitted
    zeros would be emitting a document it knows is invalid.
    """
    last, _, first = writer.partition(",")
    return {
        "parties": [
            {
                "party_id": writer_party_id,
                "canonical_party_id": None,
                "type": "natural_person",
                "last_name": last.strip(),
                "first_name": first.strip() or None,
                "ipi_name_number": None,
                "ipi_base_number": None,
                "isni": None,
                "ddex_party_id": None,
                "societies": {"pr": None, "mr": None, "sr": None},
            }
        ],
        "credits": [
            {
                "credit_id": "c-001",
                "party_id": writer_party_id,
                "writer_designation": "CA",
                "controlled": False,
                "cwr_record": "OWR",
                "agreement_id": None,
                "ownership_bps": {"pr": 10000, "mr": 10000, "sr": 10000},
                "effective_from": None,
                "effective_to": None,
                "territory_claims": [],
            }
        ],
        "publisher_for_writer": [],
        "agreements": [],
        "totals_bps": {"ownership": {"pr": 10000, "mr": 10000, "sr": 10000}},
    }


def ingest(
    audio: str | Path,
    *,
    store: BlobStore,
    title: str,
    writer: str,
    analyser: Analyser | None = None,
    language: str = "eng",
    isrc: str | None = None,
    recorded_at: str | None = None,
) -> IngestResult:
    audio = Path(audio)
    analyser = analyser or SyntheticAnalyser()
    analysis = analyser.analyse(audio)

    work_id = ulid()
    writer_party_id = ulid()
    builder = _Builder(store, analysis)

    recording_digest = builder._put(audio.read_bytes())
    evidence = [
        {
            "role": "reference_recording",
            "subrole": None,
            "media_type": "audio/wav",
            "digest": recording_digest,
            "size": audio.stat().st_size,
            "derived": False,
            "attested_by": None,
            "isrc": isrc,
            "recorded_at": recorded_at,
            "attestations": [],
            "locators": [],
        }
    ]

    if analysis.notes:
        builder.component(
            role="melody",
            data=_notes_json(analysis.notes),
            media_type="application/json",
            stage_name="melody",
        )
    if analysis.chords:
        builder.component(
            role="harmony",
            data=_chords_json(analysis.chords),
            media_type="application/json",
            stage_name="harmony",
        )
    if analysis.lyrics:
        builder.component(
            role="lyrics",
            data=analysis.lyrics.encode("utf-8"),
            media_type="text/plain; charset=utf-8",
            stage_name="lyrics",
        )
    if analysis.structure:
        builder.component(
            role="structure",
            data=json.dumps(analysis.structure, indent=2).encode("utf-8"),
            media_type="application/json",
            stage_name="structure",
        )

    if analysis.notes:
        builder.fingerprint(
            subrole="melodic",
            over="melody",
            stage="melody",
            encode=lambda: melodic.melodic_ngram(analysis.notes),
        )
    if analysis.chords:
        builder.fingerprint(
            subrole="harmonic",
            over="harmony",
            stage="harmony",
            encode=lambda: harmonic.harmonic_ngram(analysis.chords),
        )
    if analysis.lyrics:
        builder.fingerprint(
            subrole="lyric",
            over="lyrics",
            stage="lyrics",
            encode=lambda: lyric.lyric_shingle(analysis.lyrics),
        )

    attributes_stage = analysis.stage("attributes")
    musical_attributes = {
        "key": analysis.key,
        "tempo_bpm": analysis.tempo_bpm,
        "metre": analysis.metre,
        "derived": True,
        "confidence": attributes_stage.confidence if attributes_stage else 0.5,
    }

    log = b"".join(json.dumps(e, sort_keys=True).encode("utf-8") + b"\n" for e in builder.provenance)
    log_digest = builder._put(log)

    raw: dict[str, Any] = {
        "$schema": SCHEMA_URL,
        "spec_version": SPEC_VERSION,
        "work_id": work_id,
        "version": 1,
        "parent": None,
        "created_at": _now(),
        "status": "draft",
        "identity": {
            "iswc": None,
            "submitter_work_number": f"INV{work_id[-10:]}",
            "title": title,
            "alternative_titles": [],
            "language": language,
            "duration_ms": analysis.duration_ms,
            "version_type": "ORI",
            "music_arrangement": None,
            "lyric_adaptation": None,
            "distribution_category": "POP",
            "text_music_relationship": "MTX" if analysis.lyrics else "MUS",
            "composite_type": None,
            "excerpt_type": None,
            "recorded_indicator": True,
            "grand_rights_ind": False,
            "created_year": datetime.now(timezone.utc).year,
        },
        "musical_attributes": musical_attributes,
        "content": builder.content,
        "evidence": evidence,
        "renders": [],
        "rights": _rights_stub(writer_party_id, writer),
        "derivation": [],
        "related_works": [],
        "clearances": [],
        "mandates": [],
        "clearability": None,
        "disputes": [],
        "registrations": [],
        "provenance_log": {
            "digest": log_digest,
            "media_type": "application/jsonl",
            "locators": [],
        },
        "provenance_recent": builder.provenance,
        "timestamps": [],
        "signatures": [],
    }
    raw["ext"] = {"invoke.works": {"ingested_by": f"invoke-work@{__version__}", "analyser": analyser.name}}

    return IngestResult(Document(raw), builder.digests, builder.skipped)


def _notes_json(notes) -> bytes:
    payload = [{"onset": n.onset, "pitch": n.pitch, "duration": n.duration} for n in notes]
    return json.dumps(payload, indent=2).encode("utf-8")


def _chords_json(chords) -> bytes:
    payload = [{"onset": c.onset, "root": c.root, "quality": c.quality} for c in chords]
    return json.dumps(payload, indent=2).encode("utf-8")
