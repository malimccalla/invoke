# `invoke-work`

Reference tooling for the [`.work`](../SPEC.md) format: ingestion, fingerprinting, validation and matching.

**None of this is required in order to use the format.** A `.work` file is a JSON document and any JSON library can read one. This package exists so that there is at least one implementation to disagree with, and so that the [conformance corpus](../conformance/) and the [fingerprint schemes](../fingerprints/) have something that runs them.

Versioned separately from the specification. `0.1.0` here implements `spec_version` `1.0.0`.

## Install

```sh
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

The base install has no dependencies. Extras are opt-in because the analysis stack is large:

| Extra | Pulls in | Needed for |
| --- | --- | --- |
| `dev` | pytest | tests |
| `sign` | cryptography | ed25519 signing and verification |
| `analyse` | librosa, numpy | key and tempo estimation |
| `models` | torch, demucs, basic-pitch, whisper | melody, harmony and lyric extraction |

Without `models`, ingestion runs against a fixture analyser that returns fixed musical data. That is enough to exercise everything downstream — digests, fingerprints, document assembly, provenance, canonicalisation — which is where the errors that matter are, because a fingerprint with one quantisation boundary wrong is a well-formed blob that silently never matches.

## Use

```sh
work ingest recording.wav --out draft.work   # audio → draft document
work fingerprint draft.work                  # recompute fingerprints
work validate draft.work --level 2           # check against SPEC §8
work sign draft.work --key ed25519.pem       # draft → attested
work match draft.work --index catalogue.db   # candidates, fused and routed
```

## Layout

| | |
| --- | --- |
| `work/jcs.py` | RFC 8785 canonicalisation. The interoperability core — see [SPEC §5.1](../SPEC.md#51-canonicalisation). |
| `work/digest.py` | Blob digests, the signing input, the parent digest. |
| `work/model.py` | The object model, and the field table everything else reads. |
| `work/fingerprint/` | The schemes in [fingerprints/](../fingerprints/), byte for byte. |
| `work/ingest/` | Analyser protocol, fixture and real analysers, the pipeline. |
| `work/validate/` | Rules `WORK-001`–`WORK-076`, tiered L1/L2/L3. |
| `work/match/` | Fingerprint index, candidate retrieval, fusion, routing. |

## Licence

[Apache-2.0](../LICENSE), as the schema and fixtures.
