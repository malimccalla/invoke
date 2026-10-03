import json
from pathlib import Path

import pytest

from work import jcs
from work.blobs import BlobStore, DigestMismatch
from work.cli import main
from work.fingerprint.minhash import compare_blobs
from work.ingest import SyntheticAnalyser, ingest, ulid
from work.model import Document

REPO = Path(__file__).resolve().parents[2]
FIXTURES = sorted((REPO / "conformance" / "valid").glob("*.work")) + [REPO / "example.work"]


@pytest.fixture
def audio(tmp_path: Path) -> Path:
    path = tmp_path / "recording.wav"
    path.write_bytes(b"RIFF" + bytes(range(256)) * 32)
    return path


@pytest.fixture
def store(tmp_path: Path) -> BlobStore:
    return BlobStore(tmp_path / "blobs")


# -- round trip ------------------------------------------------------------------


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.name)
def test_documents_round_trip_byte_identically_under_jcs(path: Path):
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert Document(raw).canonical() == jcs.canonicalize(json.loads(json.dumps(raw)))


def test_unknown_fields_and_ext_namespaces_survive_a_round_trip():
    # SPEC §9.2: an extension mechanism that silently drops data corrupts documents
    # while appearing to work.
    raw = json.loads((REPO / "conformance" / "valid" / "minimal.work").read_text())
    raw["ext"] = {"example.com": {"private": [1, 2, 3]}}
    raw["identity"]["some_future_field"] = "kept"
    doc = Document.loads(json.dumps(raw))
    reloaded = Document.loads(doc.to_json())
    assert reloaded.raw["ext"]["example.com"]["private"] == [1, 2, 3]
    assert reloaded.raw["identity"]["some_future_field"] == "kept"
    assert reloaded.canonical() == doc.canonical()


def test_signing_input_excludes_signatures_and_nothing_else():
    raw = json.loads((REPO / "example.work").read_text())
    doc = Document(raw)
    assert b'"signatures"' not in doc.signing_input()
    assert b'"ext"' in doc.signing_input()


def test_parent_digest_covers_the_parents_signatures():
    raw = json.loads((REPO / "conformance" / "valid" / "minimal.work").read_text())
    before = Document(raw).digest()
    raw["signatures"] = [{"party_id": "x"}]
    assert Document(raw).digest() != before


# -- references ------------------------------------------------------------------


def test_evidence_prefix_resolves_against_evidence():
    doc = Document.load(REPO / "example.work")
    assert doc.resolve("evidence:reference_recording")
    assert not doc.resolve("reference_recording")
    assert doc.resolve("fingerprint.melodic")


def test_a_reference_resolves_to_every_entry_sharing_role_and_subrole():
    doc = Document.load(REPO / "example.work")
    assert len(doc.resolve("melody")) == 1


# -- blob store ------------------------------------------------------------------


def test_blob_store_verifies_on_read(store: BlobStore):
    digest = store.put(b"hello")
    assert store.get(digest) == b"hello"
    store.path_for(digest).write_bytes(b"tampered")
    with pytest.raises(DigestMismatch):
        store.get(digest)


def test_workpkg_contains_the_manifest_and_every_blob(tmp_path: Path, store: BlobStore, audio: Path):
    result = ingest(audio, store=store, title="Low Tide", writer="Okafor, Ada")
    out = store.write_package(
        result.document.to_json().encode("utf-8"), result.digests, tmp_path / "out.workpkg"
    )
    import zipfile

    with zipfile.ZipFile(out) as zf:
        names = zf.namelist()
    assert "manifest.work" in names
    assert len(names) == 1 + len(set(result.digests))


# -- ingestion -------------------------------------------------------------------


def test_ulid_is_26_crockford_characters():
    value = ulid()
    assert len(value) == 26
    assert set(value) <= set("0123456789ABCDEFGHJKMNPQRSTVWXYZ")


def test_ingest_produces_a_draft_with_the_recording_as_evidence(store: BlobStore, audio: Path):
    doc = ingest(audio, store=store, title="Low Tide", writer="Okafor, Ada").document
    assert doc.status == "draft"
    assert doc.version == 1 and doc.raw["parent"] is None
    assert [e["role"] for e in doc.evidence] == ["reference_recording"]
    # The recording is evidence, never a content component.
    assert all(e["role"] != "reference_recording" for e in doc.content)


def test_every_derived_component_carries_provenance(store: BlobStore, audio: Path):
    doc = ingest(audio, store=store, title="Low Tide", writer="Okafor, Ada").document
    targets = {e["target"] for e in doc.raw["provenance_recent"]}
    for entry in doc.content:
        if entry["derived"]:
            ref = entry["role"] if entry["subrole"] is None else f"{entry['role']}.{entry['subrole']}"
            assert ref in targets


def test_fingerprints_carry_an_algorithm_and_a_disclosure_class(store: BlobStore, audio: Path):
    doc = ingest(audio, store=store, title="Low Tide", writer="Okafor, Ada").document
    prints = [e for e in doc.content if e["role"] == "fingerprint"]
    assert {e["subrole"] for e in prints} == {"melodic", "harmonic", "lyric"}
    for entry in prints:
        assert entry["algorithm"].startswith("invoke:fp/")
        assert entry["disclosure"] in {"opaque", "approximate", "substantial"}
        assert entry["computed_over"] in {"melody", "harmony", "lyrics"}


def test_non_fingerprint_components_carry_a_null_disclosure(store: BlobStore, audio: Path):
    doc = ingest(audio, store=store, title="Low Tide", writer="Okafor, Ada").document
    for entry in doc.content:
        if entry["role"] != "fingerprint":
            assert entry["disclosure"] is None


def test_rights_stub_totals_ten_thousand_and_needs_no_agreement(store: BlobStore, audio: Path):
    doc = ingest(audio, store=store, title="Low Tide", writer="Okafor, Ada").document
    credit = doc.credits[0]
    assert credit["ownership_bps"] == {"pr": 10000, "mr": 10000, "sr": 10000}
    assert credit["cwr_record"] == "OWR" and credit["controlled"] is False
    assert credit["agreement_id"] is None
    assert doc.raw["rights"]["totals_bps"]["ownership"]["pr"] == 10000


def test_the_same_audio_yields_the_same_fingerprints(store: BlobStore, audio: Path):
    def prints(doc):
        return {e["subrole"]: e["digest"] for e in doc.content if e["role"] == "fingerprint"}

    a = ingest(audio, store=store, title="A", writer="Okafor, Ada").document
    b = ingest(audio, store=store, title="B", writer="Okafor, Ada").document
    assert prints(a) == prints(b)


def test_different_audio_yields_different_fingerprints(tmp_path: Path, store: BlobStore, audio: Path):
    other = tmp_path / "other.wav"
    other.write_bytes(b"RIFF" + bytes(reversed(range(256))) * 32)
    a = ingest(audio, store=store, title="A", writer="Okafor, Ada").document
    b = ingest(other, store=store, title="B", writer="Okafor, Ada").document
    melodic_a = next(e for e in a.content if e["subrole"] == "melodic")
    melodic_b = next(e for e in b.content if e["subrole"] == "melodic")
    assert melodic_a["digest"] != melodic_b["digest"]
    assert compare_blobs(store.get(melodic_a["digest"]), store.get(melodic_b["digest"])) < 0.5


def test_ingested_document_is_canonicalisable(store: BlobStore, audio: Path):
    doc = ingest(audio, store=store, title="Low Tide", writer="Okafor, Ada").document
    assert Document.loads(doc.to_json()).canonical() == doc.canonical()


# -- cli -------------------------------------------------------------------------


def test_cli_ingest_and_compare(tmp_path: Path, audio: Path, capsys):
    blobs = tmp_path / "blobs"
    out = tmp_path / "draft.work"
    assert main(
        ["ingest", str(audio), "--out", str(out), "--title", "Low Tide",
         "--writer", "Okafor, Ada", "--blobs", str(blobs)]
    ) == 0
    assert Document.load(out).status == "draft"

    capsys.readouterr()
    assert main(["compare", str(out), str(out), "--blobs", str(blobs)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["score"] == 1.0
    assert report["outcome"] == "candidate_same_work"
    assert report["thresholds"] == "provisional"
    assert "promotion needs a party" in report["notes"][-1]
