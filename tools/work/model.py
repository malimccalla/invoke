"""The object model: vocabularies, the field table, and a document wrapper.

The wrapper deliberately does not destructure the document. SPEC.md §9.2 requires a
consumer to preserve unrecognised fields and `ext` namespaces on round trip, and the
only way to guarantee that is to keep the parsed JSON intact and read through it.
Destructuring into dataclasses drops anything the dataclass does not name, silently.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

from . import digest, jcs

__all__ = [
    "ACK_STATUSES",
    "CONTENT_ROLES",
    "DISCLOSURE_CLASSES",
    "DISPOSITIONS",
    "DISPUTE_CLAIMS",
    "DISPUTE_STATUSES",
    "Document",
    "EVIDENCE_ROLES",
    "FINGERPRINT_SUBROLES",
    "PUBLISHER_TYPES",
    "RIGHTS",
    "STATUSES",
    "TITLE_TYPES",
    "TOP_LEVEL",
    "USE_CLASSES",
    "WORK_RELATIONS",
    "WRITER_DESIGNATIONS",
    "attestor_kind",
    "parse_reference",
]

SPEC_VERSION = "1.0.0"
SCHEMA_URL = "https://invoke.works/schema/work/v1"

# §4.1
STATUSES = frozenset({"draft", "attested", "withdrawn"})

# §7.2–§7.5
WRITER_DESIGNATIONS = frozenset({"C", "A", "CA", "AR", "AD", "SA", "SR", "TR", "PA"})
PUBLISHER_TYPES = frozenset({"E", "AQ", "AM", "SE", "ES", "PA"})
TITLE_TYPES = frozenset({"AT", "TE", "FT", "IT", "OT", "TT", "PT", "RT", "ET", "OL", "AL"})
ACK_STATUSES = frozenset({"RA", "AS", "AC", "CO", "DU", "RJ", "NP"})

# §7.6
USE_CLASSES = frozenset(
    {
        "sync_film",
        "sync_tv",
        "sync_advertising",
        "sync_game",
        "micro_sync",
        "ai_training",
        "ai_rendering",
        "artist_voice_cloning",
    }
)

# §7.7
CONTENT_ROLES = frozenset(
    {"melody", "harmony", "bassline", "rhythm", "lyrics", "score", "structure", "fingerprint"}
)
FINGERPRINT_SUBROLES = frozenset({"melodic", "harmonic", "bassline", "rhythm", "lyric", "embedding"})

# §7.8, §7.9
DISPOSITIONS = frozenset(
    {
        "cleared",
        "clearance_sought",
        "clearance_refused",
        "de_minimis_asserted",
        "independent_creation_asserted",
        "not_sought",
        "disputed",
    }
)
DISPUTE_STATUSES = frozenset({"raised", "contested", "withdrawn", "settled", "adjudicated"})
TERMINAL_DISPUTE_STATUSES = frozenset({"withdrawn", "settled", "adjudicated"})
DISPUTE_CLAIMS = frozenset({"work_derives_from_work", "same_work", "ownership", "credit"})

# §7.10–§7.12
EVIDENCE_ROLES = frozenset(
    {
        "reference_recording",
        "demo",
        "live_recording",
        "cover_recording",
        "remix",
        "lead_sheet",
        "deposit_copy",
        "session_note",
        "correspondence",
    }
)
WORK_RELATIONS = frozenset(
    {"same_work", "candidate_same_work", "shares_material", "disputed_same_work"}
)
DISCLOSURE_CLASSES = frozenset({"opaque", "approximate", "substantial", "exact"})

# §6.16
ATTESTATION_CLAIMS = frozenset(
    {"recording_embodies_work", "work_derives_from_work", "work_is_same_work"}
)

RIGHTS = ("pr", "mr", "sr")

TOP_LEVEL = (
    "$schema",
    "spec_version",
    "work_id",
    "version",
    "parent",
    "created_at",
    "status",
    "identity",
    "content",
    "evidence",
    "renders",
    "rights",
    "derivation",
    "related_works",
    "clearances",
    "mandates",
    "clearability",
    "disputes",
    "registrations",
    "provenance_log",
    "provenance_recent",
    "timestamps",
    "signatures",
)

# Identifiers that must be unique within a document (WORK-030), by the array holding them.
ID_FIELDS = {
    "rights.parties": "party_id",
    "rights.credits": "credit_id",
    "rights.agreements": "agreement_id",
    "mandates": "mandate_id",
    "clearances": "clearance_id",
    "renders": "render_id",
    "disputes": "dispute_id",
}

_ULID_ALPHABET = frozenset("0123456789ABCDEFGHJKMNPQRSTVWXYZ")


def is_ulid(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 26 and set(value) <= _ULID_ALPHABET


def attestor_kind(attestor: str, party_ids: frozenset[str] | set[str]) -> str:
    """Resolve an attestor to 'party', 'producer' or 'unresolvable'. §6.16.

    The order matters and is normative: a value equal to a declared party_id is a
    party, whatever else it looks like. An earlier draft left this to the reader and
    made WORK-024 undecidable.
    """
    if attestor in party_ids:
        return "party"
    scheme, sep, rest = attestor.partition(":")
    if not sep or not scheme or ":" in scheme:
        return "unresolvable"
    path, sep, version = rest.rpartition("@")
    if not sep or not path or not version:
        return "unresolvable"
    return "producer"


def parse_reference(ref: str) -> tuple[str, str, str | None]:
    """Split a component reference into (container, role, subrole).

    Bare references resolve against `content`; the `evidence:` prefix resolves against
    `evidence`. Only `computed_over` accepts the prefixed form (§6.4).
    """
    container = "content"
    if ref.startswith("evidence:"):
        container, ref = "evidence", ref[len("evidence:") :]
    role, sep, subrole = ref.partition(".")
    return container, role, (subrole if sep else None)


class Document:
    """A parsed `.work` document, held as the raw mapping it was loaded from."""

    def __init__(self, raw: dict[str, Any]) -> None:
        self.raw = raw

    # -- construction ---------------------------------------------------------

    @classmethod
    def load(cls, path: str | Path) -> "Document":
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))

    @classmethod
    def loads(cls, text: str) -> "Document":
        return cls(json.loads(text))

    def dump(self, path: str | Path, *, indent: int = 2) -> None:
        Path(path).write_text(self.to_json(indent=indent), encoding="utf-8")

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.raw, indent=indent, ensure_ascii=False) + "\n"

    # -- identity -------------------------------------------------------------

    @property
    def work_id(self) -> str | None:
        return self.raw.get("work_id")

    @property
    def version(self) -> int | None:
        return self.raw.get("version")

    @property
    def status(self) -> str | None:
        return self.raw.get("status")

    def array(self, name: str) -> list[dict[str, Any]]:
        value = self.raw.get(name)
        return value if isinstance(value, list) else []

    @property
    def content(self) -> list[dict[str, Any]]:
        return self.array("content")

    @property
    def evidence(self) -> list[dict[str, Any]]:
        return self.array("evidence")

    @property
    def parties(self) -> list[dict[str, Any]]:
        rights = self.raw.get("rights")
        return rights.get("parties", []) if isinstance(rights, dict) else []

    @property
    def credits(self) -> list[dict[str, Any]]:
        rights = self.raw.get("rights")
        return rights.get("credits", []) if isinstance(rights, dict) else []

    @property
    def party_ids(self) -> frozenset[str]:
        return frozenset(p["party_id"] for p in self.parties if isinstance(p.get("party_id"), str))

    # -- references -----------------------------------------------------------

    def resolve(self, ref: str) -> list[dict[str, Any]]:
        """Entries matching a component reference.

        Several fingerprint entries may share a (role, subrole) under different
        algorithms, so a reference resolves to all of them (§7.7).
        """
        container, role, subrole = parse_reference(ref)
        entries = self.content if container == "content" else self.evidence
        return [
            e
            for e in entries
            if e.get("role") == role and (subrole is None or e.get("subrole") == subrole)
        ]

    def references(self, container: str = "content") -> set[str]:
        out: set[str] = set()
        for entry in self.array(container):
            role = entry.get("role")
            if not isinstance(role, str):
                continue
            out.add(role)
            if isinstance(entry.get("subrole"), str):
                out.add(f"{role}.{entry['subrole']}")
        return out

    def declared_ids(self) -> dict[str, list[str]]:
        """Every declared identifier, by field name, in document order."""
        out: dict[str, list[str]] = {}
        for path, field in ID_FIELDS.items():
            head, _, tail = path.partition(".")
            entries = self.array(head) if not tail else (self.raw.get(head) or {}).get(tail, [])
            for entry in entries or []:
                if isinstance(entry.get(field), str):
                    out.setdefault(field, []).append(entry[field])
        return out

    def attestation_holders(self) -> Iterator[tuple[str, dict[str, Any]]]:
        """Every object carrying an `attestations` array, with the array's location."""
        for name in ("evidence", "derivation", "related_works"):
            for entry in self.array(name):
                if isinstance(entry.get("attestations"), list):
                    yield name, entry

    # -- canonicalisation -----------------------------------------------------

    def canonical(self) -> bytes:
        return jcs.canonicalize(self.raw)

    def signing_input(self) -> bytes:
        return digest.signing_input(self.raw)

    def digest(self, algorithm: str = "sha256") -> str:
        """The digest a child document would carry as its `parent` (§5.5)."""
        return digest.parent_digest(self.raw, algorithm)

    def __repr__(self) -> str:
        return f"<Document {self.work_id} v{self.version} {self.status}>"
