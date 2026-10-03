# The `.work` Format

**Version 1.0.0-draft · Status: draft · 2026-10-03**

A `.work` file is a signed, content-addressed, versioned JSON document describing a musical work: its identity, the musical content that anchors it, the rights graph that makes it commercial, and the provenance of every assertion in it.

This document is the normative specification. The reasoning behind it — why the format exists, why it is shaped this way, and what previous attempts at this problem got wrong — is in [RATIONALE.md](RATIONALE.md) and is **not** normative. [example.work](example.work) is a complete, valid document conforming to this version.

---

## 1. Introduction

### 1.1 Scope

This specification defines:

- the serialisation, media type and file extension of a work package
- the object model, field by field
- canonicalisation, digest and signature construction
- controlled vocabularies and their bindings to CWR, DDEX and ISO identifiers
- validation rules, each individually testable
- conformance requirements for producers, consumers and validators

### 1.2 Non-goals

This specification does **not** define an API, a registry, a database schema, a transport protocol, a discovery mechanism or a governance body. A `.work` file is a document. Implementations are free to store, index, transmit and serve it however they wish.

It also does not define the *truth* of any claim in the document. A `.work` file records who asserted what, when, and with what confidence. It does not adjudicate.

### 1.3 Relationship to existing standards

`.work` is designed to project losslessly *into* existing formats and to reuse their controlled vocabularies rather than invent new ones. It is not a replacement for CWR, DDEX or ISWC. See [§7](#7-controlled-vocabularies).

An OPTIONAL JSON-LD context ([§5.7](#57-json-ld)) maps the object model onto schema.org, PROV-O and ODRL, so that a document can be consumed as a graph by adjacent provenance infrastructure. It is a compatibility layer: the format is JSON, and remains readable by any JSON library.

---

## 2. Conventions

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD NOT**, **RECOMMENDED**, **MAY** and **OPTIONAL** are to be interpreted as described in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119) and [RFC 8174](https://www.rfc-editor.org/rfc/rfc8174) when, and only when, they appear in all capitals.

In field tables, **R** marks a required field. A required field MUST be present. A field whose value is not known MUST be present with a value of `null` where the type permits it, rather than omitted, unless stated otherwise.

---

## 3. File format

### 3.1 Serialisation

A work package MUST be a single JSON document as defined by [RFC 8259](https://www.rfc-editor.org/rfc/rfc8259), encoded as UTF-8 without a byte order mark.

The document MUST NOT contain comments, trailing commas, or any other extension to strict JSON. Producers MUST NOT emit YAML, JSON5, JSONC or any other superset.

> This is a hard constraint rather than a stylistic one. Signatures are computed over a canonical serialisation ([§5](#5-canonicalisation-digests-and-signatures)), and any syntax admitting two byte representations of the same document breaks signature stability.

### 3.2 File extension and media type

| | |
| --- | --- |
| Extension | `.work` |
| Media type | `application/vnd.invoke.work+json` |
| Container extension | `.workpkg` |
| Container media type | `application/vnd.invoke.workpkg+zip` |

Implementations MUST accept `application/json` where the media type is not negotiable, and SHOULD send `application/vnd.invoke.work+json` where it is. See [§12](#12-iana-considerations).

### 3.3 The `.workpkg` container

A `.workpkg` is a ZIP archive containing a manifest and every blob it references, for archival or offline handoff. Its layout MUST be:

```
manifest.work                    the work package document
blobs/sha256/<full-hex-digest>   one file per referenced blob
```

A `.workpkg` MUST contain a blob for every `digest` appearing in `content`, `evidence` and `renders`. It MAY contain blobs for digests appearing in `agreements`, `clearances`, `disputes` and `provenance_log`.

`.work` is the pointer; `.workpkg` is the payload. Producers SHOULD default to `.work`.

---

## 4. Identity and versioning

### 4.1 Document identity

| Field | Type | R | Description |
| --- | --- | --- | --- |
| `$schema` | string (URI) | ✓ | The JSON Schema for the `spec_version` in use. |
| `spec_version` | string | ✓ | The version of this specification the document conforms to. Semantic version. |
| `work_id` | string | ✓ | Stable identifier for the work across all versions. MUST be a [ULID](https://github.com/ulid/spec) — 26 characters, Crockford base32. |
| `version` | integer | ✓ | Monotonically increasing state counter, starting at `1`. |
| `parent` | string (digest) \| null | ✓ | Digest of the immediately preceding version. `null` if and only if `version` is `1`. |
| `created_at` | string (date-time) | ✓ | RFC 3339 UTC instant at which this version was created. |
| `status` | string | ✓ | `draft` \| `attested` \| `withdrawn`. Supersession is **not** a status — see [§4.2](#42-version-chain). |
| `@context` | string (IRI) \| array | | OPTIONAL JSON-LD context. See [§5.7](#57-json-ld). |
| `ext` | object | | Extension namespaces. See [§6.20](#620-extension-object). |

`work_id` identifies the work. It MUST NOT change between versions. It is **not** the CWR Submitter Work Number — see `identity.submitter_work_number` and [WORK-013](#8-validation-rules).

### 4.2 Version chain

Work packages are append-only. A producer MUST NOT mutate a published version; it MUST emit a new document with `version` incremented and `parent` set to the digest of the version it supersedes.

A consumer given two documents with the same `work_id` MUST treat the one with the higher `version` as current, and MUST NOT discard the earlier one if it is relied upon as evidence of prior state.

**Supersession is a property of the chain, not of a document.** A version is superseded when, and only when, a document exists whose `parent` is its digest. `status` therefore has no `superseded` member: a document could only declare itself superseded by being mutated after publication, which this section forbids.

### 4.3 Component-level continuity

Each entry in `content` is digested independently. An unchanged component therefore keeps a byte-identical `digest` across versions, which is what allows a single component's date of existence to be established without reference to the rest of the document.

Producers MUST NOT re-encode an unchanged component in a way that alters its digest. Consumers MAY rely on digest equality across versions as evidence that a component is unchanged.

### 4.4 Specification versioning

`spec_version` follows semantic versioning:

- **patch** — editorial only; no document that was valid becomes invalid
- **minor** — additive; new optional fields or vocabulary members. A consumer of `1.0` MUST accept a `1.1` document, ignoring fields it does not recognise, and MUST preserve them on round trip
- **major** — may remove or repurpose fields. Consumers MUST reject a document whose major version they do not implement

---

## 5. Canonicalisation, digests and signatures

This section is the interoperability core. Two independent implementations that disagree here will produce documents whose signatures do not verify.

### 5.1 Canonicalisation

The canonical form of a JSON value is its serialisation under [RFC 8785 (JCS)](https://www.rfc-editor.org/rfc/rfc8785): object keys sorted by UTF-16 code unit, no insignificant whitespace, and the number and string serialisation rules given in that document.

Implementations MUST use JCS. They MUST NOT define their own key ordering or number formatting.

### 5.2 Digest form

A digest is the string `<algorithm>:<value>`, where `<value>` is lowercase hexadecimal.

`sha256` MUST be supported. `sha512` MAY be supported. Implementations MUST reject a digest whose algorithm they do not recognise rather than ignoring it.

### 5.3 Blob digests

The `digest` of a `content`, `evidence` or `render` entry is computed over the **raw bytes of the referenced blob**, not over any JSON representation of it.

### 5.4 The signing input

The signing input is the canonical form ([§5.1](#51-canonicalisation)) of the document with the top-level `signatures` member **removed**. All other members, including `ext` and `timestamps`, are included.

```
signing_input = JCS(document \ {"signatures"})
```

Producers MUST compute signatures over exactly this input. Consumers MUST verify against exactly this input.

> `ext` is deliberately inside the signature. An extension namespace that can be altered without invalidating the signature is an unsigned side channel.

### 5.5 The parent digest

`parent` is the digest of the canonical form of the parent document **including** its `signatures`:

```
parent = "sha256:" + hex(SHA-256(JCS(parent_document)))
```

The parent's signatures are part of the state being referenced, so they are covered.

### 5.6 Timestamps

A `timestamps` entry records a token binding the document to a point in time. Its `digest` field MUST be the digest of the signing input ([§5.4](#54-the-signing-input)) that was submitted to the timestamping authority.

The `qualified` field asserts whether the authority is a qualified trust service provider under eIDAS. A producer MUST NOT set `qualified` to `true` unless the authority appears on an EU member state Trusted List. See [§10](#10-security-considerations).

### 5.7 JSON-LD

A document MAY carry an `@context` member. A context is published at `context/v1/work.jsonld` mapping every field name in [§6](#6-object-model) to an IRI, so that adding that one member — and changing nothing else — makes an otherwise unmodified document valid JSON-LD 1.1.

The context is a **compatibility layer, not a second object model.** This specification does not define `.work` in terms of RDF, no field is named for the convenience of a triplestore, and no conformance class requires an RDF toolchain.

**Signing is unaffected, and this is the part that must not be got wrong.** The signing input remains the canonical form of the JSON document under JCS ([§5.4](#54-the-signing-input)), including `@context` where present. Implementations MUST NOT use RDF Dataset Canonicalization to produce or verify a `.work` signature.

Consumers MUST NOT expand, compact, flatten or frame a document before verifying its signatures. JSON-LD processing is meaning-preserving and byte-destructive: a document round-tripped through a JSON-LD processor will generally fail [WORK-060](#8-validation-rules) while remaining semantically identical. Verify first, then process.

Producers SHOULD reference the context by IRI rather than inlining it, so that editing the context does not alter the signed bytes of every document that uses it.

---

## 6. Object model

### 6.1 Identity Object

`identity` — the work's own description. Every field maps to a CWR `NWR`/`REV` field.

| Field | Type | R | Description |
| --- | --- | --- | --- |
| `iswc` | string \| null | ✓ | ISO 15707, formatted `T-nnn.nnn.nnn-c`. MUST pass the check digit test ([WORK-011](#8-validation-rules)). |
| `submitter_work_number` | string | ✓ | Submitter-scoped key, non-empty. Maps to the CWR Submitter Work # field, which bounds it at 14 characters ([CWR-002](#82-cwr-projection-profile)). |
| `title` | string | ✓ | Non-empty. CWR bounds it at 60 characters ([CWR-001](#82-cwr-projection-profile)). |
| `alternative_titles` | array | ✓ | See [§6.2](#62-alternative-title-object). MAY be empty. |
| `language` | string \| null | ✓ | ISO 639-2/T three-letter code. |
| `duration_ms` | integer \| null | ✓ | REQUIRED (non-null) when `distribution_category` is `SER`. |
| `version_type` | string | ✓ | `ORI` \| `MOD`. |
| `music_arrangement` | string \| null | ✓ | REQUIRED (non-null) when `version_type` is `MOD`, otherwise MUST be `null`. |
| `lyric_adaptation` | string \| null | ✓ | REQUIRED (non-null) when `version_type` is `MOD`, otherwise MUST be `null`. |
| `distribution_category` | string | ✓ | `POP` \| `JAZ` \| `SER` \| `UNC`. |
| `text_music_relationship` | string \| null | ✓ | `MTX` \| `MUS` \| `TXT`. |
| `composite_type` | string \| null | ✓ | `COS` \| `MED` \| `POT` \| `UCO`. |
| `excerpt_type` | string \| null | ✓ | `MOV` \| `UEX`. |
| `recorded_indicator` | boolean | ✓ | |
| `grand_rights_ind` | boolean | ✓ | REQUIRED by UK societies. |
| `created_year` | integer \| null | ✓ | Four-digit year. |

### 6.2 Alternative Title Object

| Field | Type | R | Description |
| --- | --- | --- | --- |
| `title` | string | ✓ | |
| `type` | string | ✓ | Human-facing label. |
| `cwr_title_type` | string | ✓ | CWR Title Type code. See [§7.4](#74-title-types). |
| `language` | string \| null | | ISO 639-2/T. SHOULD be present when `cwr_title_type` is `TT`. |

### 6.3 Musical Attributes Object

`musical_attributes` — OPTIONAL. Scalar musical facts, usually machine-derived.

| Field | Type | R | Description |
| --- | --- | --- | --- |
| `key` | string \| null | | |
| `tempo_bpm` | number \| null | | |
| `metre` | string \| null | | |
| `derived` | boolean | ✓ | |
| `confidence` | number \| null | | `0.0`–`1.0`. MUST be present if `derived` is `true`. |

### 6.4 Content Component Object

`content` — an array of the musical content that anchors the work. This is what makes the document a deposit copy rather than a registration message.

| Field | Type | R | Description |
| --- | --- | --- | --- |
| `role` | string | ✓ | See [§7.7](#77-content-roles). |
| `subrole` | string \| null | ✓ | Discriminator where one role carries more than one component. The pair (`role`, `subrole`) MUST be unique within the array. |
| `media_type` | string | ✓ | |
| `digest` | string | ✓ | See [§5.2](#52-digest-form). |
| `size` | integer | ✓ | Bytes. |
| `derived` | boolean | ✓ | `true` if machine-produced. |
| `attested_by` | string \| null | | `party_id` of a party who has confirmed the component. |
| `computed_over` | string \| null | ✓ | REQUIRED (non-null) when `role` is `fingerprint`: the `role` or `role.subrole` of the component it was computed from. MUST resolve. |
| `algorithm` | string \| null | ✓ | REQUIRED (non-null) when `role` is `fingerprint`. Named and versioned, e.g. `invoke:fp/melodic-ngram@1.0`. |
| `locators` | array of string (URI) | ✓ | Advisory. MAY be empty. |

Components are addressed by `role`, or by `role.subrole` where a subrole is present. `content.melody` and `content.fingerprint.melodic` are stable references; an array index is not.

**`fingerprint` is the only role intended to be published.** Every other component discloses the work. A fingerprint is a one-way perceptual encoding — a melodic n-gram hash, an embedding — from which the component it was computed over cannot be reconstructed, and a producer MUST NOT emit one from which it can.

It exists for a specific reason. Detecting that two works share material requires comparing them, which has always required somebody to hold both. No rightsholder will surrender a catalogue to a central index, and every attempt to build one has failed. Publishable fingerprints make the comparison federated: parties publish fingerprints, keep the works, and compute similarity against each other without any of them holding the other's repertoire. This specification defines the field, not the matching — `algorithm` names the scheme, and interoperability between schemes is out of scope for `1.0`.

### 6.5 Evidence Object

`evidence` — recordings and documents evidencing that the work exists. A sound recording appears here only as evidence, never as a primary entity.

Fields as [§6.4](#64-content-component-object), except that the (`role`, `subrole`) pair need not be unique and `computed_over` and `algorithm` do not apply, plus:

| Field | Type | R | Description |
| --- | --- | --- | --- |
| `isrc` | string \| null | | 12 characters, no hyphens. |
| `recorded_at` | string (date) \| null | | |
| `attestations` | array | ✓ | See [§6.16](#616-attestation-object). MAY be empty. |

### 6.6 Render Object

`renders` — recordings generated *from* the work. See [RATIONALE.md](RATIONALE.md#rendering).

| Field | Type | R | Description |
| --- | --- | --- | --- |
| `render_id` | string | ✓ | Unique within the document. |
| `purpose` | string | ✓ | |
| `style_prompt` | string \| null | ✓ | |
| `engine` | string | ✓ | Producer and version, e.g. `invoke:pipeline/render@0.2.0`. |
| `rendered_at` | string (date-time) | ✓ | |
| `mandate_id` | string | ✓ | The mandate permitting the render. MUST resolve ([WORK-031](#8-validation-rules)). |
| `use_class` | string | ✓ | MUST appear in the referenced mandate's `use_classes`. |
| `isrc` | string \| null | ✓ | |
| `media_type`, `digest`, `size`, `locators` | | ✓ | As [§6.4](#64-content-component-object). |
| `melody_similarity` | number \| null | | Round-trip check against `content.melody`. |
| `human_in_loop` | boolean | ✓ | Bears on whether the master is protectable. |
| `copyright_note` | string \| null | | |
| `consent_coverage_bps` | object | ✓ | Keys `pr`, `mr`, `sr`. Ownership bps in each right whose holders have mandated this `use_class`. |
| `consent_note` | string \| null | | |
| `distribution_restriction` | string \| null | ✓ | `null` only when every `consent_coverage_bps` value is `10000`. |

Consent is measured per right because mandates are granted per right ([§6.14](#614-mandate-object)) and every other share in this document is split per right. A single scalar would be the one place the format contradicted itself, and it would do so at the point where the question is whether a party consented.

### The `rights` container

`rights` holds the whole rights graph. Its members are `parties` ([§6.7](#67-party-object)), `credits` ([§6.8](#68-credit-object)), `publisher_for_writer` ([§6.10](#610-publisher-for-writer-object)), `agreements` ([§6.11](#611-agreement-object)) — all REQUIRED, each MAY be empty — and:

| Field | Type | R | Description |
| --- | --- | --- | --- |
| `totals_bps` | object | ✓ | `ownership`, with keys `pr`, `mr`, `sr`. |

`totals_bps` is a **declared** summary, not an authority. A consumer MUST recompute it from `credits` ([WORK-032](#8-validation-rules)), and a mismatch between the declared and the computed total is itself a violation ([WORK-043](#8-validation-rules)). It exists so that a producer's own belief about the total is visible and can be contradicted — which is only useful for as long as it stays a belief.

An earlier draft carried a sibling `valid` boolean. It has been removed. A self-declared verdict on a document's own correctness is not evidence of anything, and a consumer that reads it has stopped validating. The document asserts; adjudication belongs to the reader.

### 6.7 Party Object

`rights.parties` — a globally unique creative or corporate identity. Not tenant-scoped.

| Field | Type | R | Description |
| --- | --- | --- | --- |
| `party_id` | string | ✓ | Document-scoped reference handle. MUST be unique within the document and stable across versions of the same work. SHOULD be a ULID. |
| `canonical_party_id` | string \| null | ✓ | Merge target where this party is a known duplicate. |
| `type` | string | ✓ | `natural_person` \| `legal_entity`. |
| `name` | string | — | REQUIRED for `legal_entity`; MUST be absent for `natural_person`. |
| `last_name` | string | — | REQUIRED for `natural_person`; MUST be absent for `legal_entity`. |
| `first_name` | string \| null | — | Permitted only for `natural_person`. |
| `ipi_name_number` | string \| null | ✓ | 11 digits, zero-padded. |
| `ipi_base_number` | string \| null | ✓ | `I-nnnnnnnnn-c`. |
| `isni` | string \| null | ✓ | ISO 27729, 16 characters. |
| `ddex_party_id` | string \| null | ✓ | DPID. |
| `societies` | object | ✓ | Keys `pr`, `mr`, `sr`; values are three-digit CISAC society codes or `null`. |

> Natural persons carry structured names because CWR has separate Last Name and First Name fields, and splitting a display string on a comma fails on mononyms, on suffixes, and on every name where the family name is not positionally obvious.

> `party_id` is a **handle, not an identity.** It exists so that credits, agreements, mandates and signatures within one document can refer to the same party. A party's identity across documents and organisations is carried by `ipi_name_number`, `ipi_base_number`, `isni` and `ddex_party_id`. Requiring a minted ULID here would oblige every implementation to invent a new identifier for a party that already has three, which is the duplication the format exists to reduce. `work_id` is different and MUST be a ULID ([§4.1](#41-document-identity)), because the work's identity across versions is the document's own to assert.

### 6.8 Credit Object

`rights.credits` — a party assigned to the work with a role, a control indicator and shares.

| Field | Type | R | Description |
| --- | --- | --- | --- |
| `credit_id` | string | ✓ | Unique within the document. |
| `party_id` | string | ✓ | MUST resolve to a party. |
| `writer_designation` | string | — | REQUIRED when `cwr_record` is `SWR`/`OWR`; MUST be absent otherwise. See [§7.2](#72-writer-designation-codes). |
| `publisher_type` | string | — | REQUIRED when `cwr_record` is `SPU`/`OPU`; MUST be absent otherwise. See [§7.3](#73-publisher-type-codes). |
| `controlled` | boolean | ✓ | |
| `cwr_record` | string | ✓ | `SWR` \| `OWR` \| `SPU` \| `OPU`. MUST agree with `controlled`. |
| `agreement_id` | string \| null | ✓ | MUST be non-null when `controlled` is `true`. |
| `publisher_sequence` | integer | — | REQUIRED for publisher credits. Position in its own chain of title, starting at `1`. |
| `ownership_bps` | object | ✓ | Keys `pr`, `mr`, `sr`; integers `0`–`10000`. |
| `effective_from` | string (date) | ✓ | |
| `effective_to` | string (date) \| null | ✓ | |
| `territory_claims` | array | ✓ | See [§6.9](#69-territory-claim-object). MAY be empty for non-controlled parties. |

**Writer and publisher role vocabularies are distinct and MUST NOT be merged.** A single `role` field admitting both permits a composer-publisher, which does not exist.

**Shares are integer basis points, split by right, never combined.** `10000` = 100.00%. This is exactly how CWR encodes them — five digits, two implied decimals — so `2500` serialises as `02500` with no scaling or rounding. Floating point MUST NOT be used for any share or monetary value.

### 6.9 Territory Claim Object

Ownership share is global and lives on the credit. **Collection** share is per territory and lives here.

| Field | Type | R | Description |
| --- | --- | --- | --- |
| `tis_code` | integer | ✓ | CISAC TIS code. Hierarchical; `2136` is World. |
| `tis_name` | string \| null | | Advisory. |
| `indicator` | string | ✓ | `I` (include) \| `E` (exclude). |
| `collection_bps` | object | ✓ | Keys `pr`, `mr`, `sr`. MUST be all-zero when `indicator` is `E`. |

An ISO 3166 country array cannot express exclusion. "World except Germany" is `include 2136, exclude 276`, and there is no array equivalent.

### 6.10 Publisher For Writer Object

`rights.publisher_for_writer` — the chain of title link. Projects to the CWR `PWR` record.

| Field | Type | R | Description |
| --- | --- | --- | --- |
| `writer_credit_id` | string | ✓ | MUST resolve to a credit whose `cwr_record` is `SWR`. |
| `publisher_credit_id` | string | ✓ | MUST resolve to a credit whose `cwr_record` is `SPU`. |

Without this, there is no chain of title and CWR files will not validate. A flat list of credits cannot represent publishing; the structure is a graph.

### 6.11 Agreement Object

`rights.agreements`. Deal terms are an object, not columns scattered across credits.

| Field | Type | R | Description |
| --- | --- | --- | --- |
| `agreement_id` | string | ✓ | Unique within the document. |
| `agreement_type` | string | ✓ | `OG` \| `OS` \| `PG` \| `PS`. |
| `assignor_party_id` | string | ✓ | MUST resolve. |
| `assignee_party_id` | string | ✓ | MUST resolve. |
| `start_date` | string (date) | ✓ | |
| `end_date` | string (date) \| null | ✓ | |
| `retention_end_date` | string (date) \| null | ✓ | MUST NOT precede `end_date`. |
| `post_term_collection_end_date` | string (date) \| null | ✓ | MUST NOT precede `retention_end_date`. |
| `prior_royalty_status` | string | ✓ | `N` \| `A` \| `D`. |
| `sales_manufacture_clause` | string \| null | ✓ | `S` \| `M`. |
| `admin_commission_bps` | integer \| null | ✓ | |
| `document_digest` | string \| null | ✓ | Digest of the executed contract. |

Retention and post-term collection are distinct from `end_date`. Royalties are computed against the split **as it stood when the usage occurred**, which requires all three.

### 6.12 Derivation Object

`derivation` — typed relations to other works. Replaces untyped `isDerivative` / `isMedley` booleans, which are derivable from relations while relations are not derivable from booleans.

| Field | Type | R | Description |
| --- | --- | --- | --- |
| `relation_type` | string | ✓ | `VER` (version of an original work) \| `COM` (medley component). |
| `role` | string | ✓ | Finer-grained label, e.g. `interpolation`, `sample`, `arrangement`. |
| `parent_work_id` | string \| null | ✓ | |
| `parent_iswc` | string \| null | ✓ | |
| `parent_title` | string | ✓ | |
| `parent_locators` | array of string (URI) | ✓ | Where the parent's own `.work` document may be retrieved. Advisory. MAY be empty. |
| `affected_components` | array of string | ✓ | `role` or `role.subrole` references into `content`, naming what is said to derive. MUST resolve. MAY be empty. |
| `description` | string \| null | | |
| `attestations` | array | ✓ | See [§6.16](#616-attestation-object). |
| `disposition` | string | ✓ | See [§7.8](#78-derivation-dispositions). |
| `clearance_id` | string \| null | ✓ | MUST be non-null when `disposition` is `cleared`, and `null` otherwise. |
| `dispute_id` | string \| null | ✓ | MUST be non-null when `disposition` is `disputed`. MUST resolve to a [§6.21](#621-dispute-object) entry. |

**A parent is referenced, never embedded.** The parent's own rights graph, content and provenance are not copied in; a consumer tracing further back resolves `parent_locators` to a separately signed document. Embedding would leave it unclear whose signature covered the embedded claims, and would freeze a copy that can never receive the parent's later corrections.

**`disposition` replaces a `cleared` boolean, and the reason is the whole point of the field.** A boolean collapses *"we licensed it"*, *"they refused and we released anyway"*, *"we judged it de minimis"* and *"we never asked"* into a single `false`. Those are four different legal postures with four different consequences, and which one applies is the most consequential thing this document records about a derivation. A format that cannot tell them apart is of no use as evidence to either side of a dispute.

`affected_components` exists so that a derivation claim names *what* is said to derive. A claim against a two-bar melodic phrase and a claim against an entire lyric are not the same claim, and a document that records only *that* a work derives, without recording *which component*, cannot be reasoned about.

### 6.13 Clearance Object

`clearances`.

| Field | Type | R | Description |
| --- | --- | --- | --- |
| `clearance_id` | string | ✓ | Unique within the document. |
| `type` | string | ✓ | |
| `status` | string | ✓ | `cleared` \| `pending` \| `refused`. |
| `granted_by` | string | ✓ | |
| `granted_on` | string (date) \| null | ✓ | |
| `terms` | string | ✓ | Human-readable. |
| `consideration` | object \| null | ✓ | Structured terms. See below. |
| `affects_ownership` | boolean | ✓ | |
| `document_digest` | string \| null | ✓ | |

`consideration` carries `type`, `basis`, `bps`, `beneficiary_party_id`, `territory` and `term`. `beneficiary_party_id` is the `party_id` of the party to whom the consideration is owed where that party is declared in `rights.parties`, and `null` where it is not.

**A clearance whose `affects_ownership` is `false` MUST NOT be reflected in `ownership_bps`.** A participation in receipts is not an assignment of copyright; conflating them corrupts the split. This distinction has no representation in CWR at all.

[WORK-051](#8-validation-rules) enforces the checkable half of that: a non-ownership beneficiary declared in `rights.parties` MUST NOT also hold a credit. It cannot catch a beneficiary who was never declared, and a validator MUST NOT report the absence of a violation here as confirmation that the split is clean.

### 6.14 Mandate Object

`mandates` — a standing offer expressed as data: what a party authorises to be granted on their behalf.

| Field | Type | R | Description |
| --- | --- | --- | --- |
| `mandate_id` | string | ✓ | Unique within the document. |
| `party_id` | string | ✓ | MUST resolve. |
| `granted_to` | string \| null | ✓ | |
| `rights` | array of string | ✓ | Members of `pr`, `mr`, `sr`. |
| `territories` | array | ✓ | Objects with `tis_code` and `indicator`. |
| `use_classes` | array of string | ✓ | See [§7.6](#76-use-classes). |
| `rate_floor` | object \| null | | `currency` (ISO 4217) and `minor_units` (integer). |
| `exclusions` | array of string | | |
| `effective_from` | string (date) \| null | | |
| `effective_to` | string (date) \| null | | |
| `note` | string \| null | | |

`ai_training` and `ai_rendering` are **distinct use classes**. Training a model on a work is not the same act as synthesising a performance of it, and a party may permit one and refuse the other. An implementation MUST NOT treat consent to one as consent to the other.

> A mandate is a policy — permissions, prohibitions, territorial and temporal constraints, and a price floor — and [ODRL](https://www.w3.org/TR/odrl-model/) is a W3C Recommendation for exactly that shape. The JSON-LD context ([§5.7](#57-json-ld)) maps this object onto ODRL where the correspondence is exact. Adopting ODRL as the normative model is deferred: its vocabulary has no term for a right split by `pr`/`mr`/`sr`, and nothing in it is cheaper to implement than the table above.

### 6.15 Clearability Object

`clearability` — a computed summary, valid as at `computed_at`. Consumers MUST NOT treat it as authoritative if the document has changed since.

| Field | Type | R | Description |
| --- | --- | --- | --- |
| `computed_at` | string (date-time) | ✓ | |
| `request` | object | ✓ | The question being answered: `use_class`, `territories` (as [§6.14](#614-mandate-object)) and `term`. |
| `one_stop` | boolean | ✓ | `true` only if coverage is `10000` in every right. |
| `coverage_bps` | object | ✓ | Keys `pr`, `mr`, `sr`. |
| `gaps` | array | ✓ | Objects with `party_id`, `bps`, `reason`. |

A mandate is scoped by right, territory and use class ([§6.14](#614-mandate-object)), so a coverage figure computed without naming all three is an answer to a question nobody asked. `request` records the question. Two `clearability` objects with different `request` values are not comparable, and a consumer MUST NOT apply one to a different request.

### 6.16 Attestation Object

An attestation records who asserted a claim about a **relationship**, when, and how confident they were. It appears on `evidence` and `derivation` entries as an ordered array.

| Field | Type | R | Description |
| --- | --- | --- | --- |
| `claim` | string | ✓ | `recording_embodies_work` \| `work_derives_from_work`. |
| `attestor` | string | ✓ | A `party_id`, or a producer identifier such as `invoke:pipeline/cover-id@0.3.1`. |
| `created` | string (date-time) | ✓ | |
| `confidence` | number | — | `0.0`–`1.0`. **MUST be present when the attestor is a producer. MUST be absent when the attestor is a party.** |
| `note` | string \| null | | |

**Telling the two apart is mechanical, not a matter of judgement.** A consumer MUST resolve `attestor` as follows, in order:

1. If the value equals a `party_id` declared in `rights.parties`, the attestor is a **party**.
2. Otherwise the value MUST match the producer identifier grammar `scheme ":" path "@" version`, where `scheme` contains no colon, `path` is non-empty, and `version` is non-empty — for example `invoke:pipeline/cover-id@0.3.1`. The attestor is a **producer**.
3. A value matching neither is a violation ([WORK-027](#8-validation-rules)).

A `party_id` SHOULD be a ULID ([§6.7](#67-party-object)) and a producer identifier MUST contain both a colon and an `@`, so the two cannot collide. An earlier draft left the discriminator to the reader, which made [WORK-024](#8-validation-rules) impossible to implement deterministically — two validators could disagree about whether the same document was conformant.

The absence of `confidence` means a party asserted the claim. This is a different statement from a measurement of `1.0` and MUST NOT be normalised to one.

Corroboration is a subsequent entry in the array, not a field. Entries MUST be ordered by `created`, ascending.

### 6.17 Registration Object

`registrations` — one entry per society, per submission. Registration state is not a single field on the work.

| Field | Type | R | Description |
| --- | --- | --- | --- |
| `society_code` | string \| null | ✓ | Three-digit CISAC code, or `null` for a non-CISAC recipient. |
| `recipient_code` | string | ✓ | Recipient identifier as used in the filename. |
| `society_name` | string | ✓ | |
| `transaction_type` | string | ✓ | `NWR` \| `REV`. |
| `submitted_at` | string (date-time) | ✓ | |
| `file` | string | ✓ | CWR filename, `CWyynnnnsss_rrr.Vxx`. |
| `ack_status` | string \| null | ✓ | See [§7.5](#75-acknowledgement-statuses). |
| `ack_received_at` | string (date-time) \| null | ✓ | |
| `society_work_code` | string \| null | ✓ | |
| `allocated_iswc` | string \| null | ✓ | |
| `messages` | array | ✓ | CWR `MSG` records: `type`, `level`, `code`, `record_type`, `original_record_sequence`, `text`. |

A conflict (`CO`) is data, not an error. Consumers MUST NOT discard a document because a registration conflicts.

### 6.18 Provenance

| Field | Type | R | Description |
| --- | --- | --- | --- |
| `provenance_log` | object | ✓ | `digest`, `media_type`, `locators` — the full append-only log. |
| `provenance_recent` | array | ✓ | Recent entries inline: `at`, `actor`, `action`, `target`, `from`, `confidence`, `note`. |

`provenance_recent` is a convenience view. `provenance_log` is authoritative. Every machine-derived value in the document MUST have a corresponding provenance entry naming the producer and its version.

### 6.19 Timestamp and Signature Objects

`timestamps[]`:

| Field | Type | R | Description |
| --- | --- | --- | --- |
| `type` | string | ✓ | `rfc3161`. |
| `authority` | string (URI) | ✓ | |
| `qualified` | boolean | ✓ | See [§5.6](#56-timestamps). |
| `qualification_note` | string \| null | | |
| `digest` | string | ✓ | Digest of the signing input submitted. |
| `stamped_at` | string (date-time) | ✓ | |
| `token` | string (base64) | ✓ | |

`signatures[]`:

| Field | Type | R | Description |
| --- | --- | --- | --- |
| `party_id` | string | ✓ | MUST resolve to a party. |
| `algorithm` | string | ✓ | `ed25519`. `ed25519` MUST be supported. |
| `key_id` | string | ✓ | A `did:key` or other resolvable key identifier. |
| `canonicalisation` | string | ✓ | `RFC8785`. |
| `signed_at` | string (date-time) | ✓ | |
| `value` | string | ✓ | Multibase-encoded signature over the signing input ([§5.4](#54-the-signing-input)). |

### 6.20 Extension Object

`ext` is an object whose keys are namespaces and whose values are arbitrary JSON.

Namespaces MUST be reverse-DNS or DNS names controlled by the extending implementation, e.g. `invoke.works`. Implementations MUST NOT write to a namespace they do not control.

**Consumers MUST preserve unrecognised `ext` namespaces on round trip.** An extension mechanism that silently drops data is worse than none, because it corrupts documents while appearing to work.

`ext` is covered by signatures ([§5.4](#54-the-signing-input)).

### 6.21 Dispute Object

`disputes` — claims made **against** the work by someone else. Every other object in this document records what the producer asserts; this one records what is asserted about them.

| Field | Type | R | Description |
| --- | --- | --- | --- |
| `dispute_id` | string | ✓ | Unique within the document. |
| `claim` | string | ✓ | `work_derives_from_work` \| `ownership` \| `credit`. |
| `raised_at` | string (date) | ✓ | |
| `claimant` | object | ✓ | `name` (string), plus nullable `party_id` and `ipi_name_number`. |
| `claimed_parent_title` | string \| null | ✓ | Non-null where `claim` is `work_derives_from_work`. |
| `claimed_parent_iswc` | string \| null | ✓ | |
| `disputed_components` | array of string | ✓ | `role` or `role.subrole` references into `content`, naming what is said to infringe. MUST resolve. MAY be empty. |
| `forum` | string \| null | ✓ | Where it is being pursued — a named court, a society, or correspondence. `null` where unstated. |
| `status` | string | ✓ | See [§7.9](#79-dispute-statuses). |
| `response` | string \| null | ✓ | The document holder's position, in their own words. |
| `resolved_at` | string (date) \| null | ✓ | |
| `resolution` | string \| null | ✓ | REQUIRED (non-null) when `status` is terminal. |
| `document_digests` | array of string | ✓ | Digests of pleadings, correspondence or settlement terms. MAY be empty. |

Design constraint 4 holds that conflicts are data rather than errors, but before this object the only conflict with anywhere to live was a society's `CO` acknowledgement ([§6.17](#617-registration-object)). An infringement allegation — the conflict that actually costs money — had no representation at all, which meant the format could describe a work that had been cleared and a work that had not, but not a work that someone was suing over.

A dispute is **recorded, not adjudicated.** The presence of an entry says that a claim was made and by whom; it says nothing about whether the claim is good. `status` tracks the claim's procedural state and `resolution` records the outcome in plain words. There is deliberately no field asserting that a dispute was meritless, and a consumer MUST NOT infer from a `withdrawn` or `settled` status that the underlying allegation was false.

**A document carrying an open dispute is still a valid document.** Rejecting it would destroy the only record of the dispute, and a producer who can only emit a conformant file by omitting an inconvenient fact will omit it.

---

## 7. Controlled vocabularies

Every vocabulary below is drawn from an existing standard. Where a code is defined externally, that definition governs; this specification does not fork it.

### 7.1 External bindings

| Concept | Standard |
| --- | --- |
| Work identifier | ISWC, ISO 15707 |
| Recording identifier | ISRC, ISO 3901 |
| Party identifier | IPI Name Number, IPI Base Number, ISNI (ISO 27729), DDEX Party ID |
| Territory | CISAC TIS |
| Society code | CISAC three-digit society codes |
| Language | ISO 639-2/T |
| Currency | ISO 4217 |
| Record and status codes | CWR 2.1 rev 8 / 2.2 |

### 7.2 Writer designation codes

`C` `A` `CA` `AR` `AD` `SA` `SR` `TR` `PA`

### 7.3 Publisher type codes

`E` `AQ` `AM` `SE` `ES` `PA`

`SE` is Sub Publisher. `ES` is *Substituted* Publisher. They are not interchangeable, and a sub-publishing chain built on `ES` will be rejected by societies.

### 7.4 Title types

`AT` `TE` `FT` `IT` `OT` `TT` `PT` `RT` `ET` `OL` `AL`

`TT` is Translated Title. `TE` is First Line of Text and is **not** a translation.

### 7.5 Acknowledgement statuses

`RA` `AS` `AC` `CO` `DU` `RJ` `NP`

### 7.6 Use classes

`sync_film` `sync_tv` `sync_advertising` `sync_game` `micro_sync` `ai_training` `ai_rendering` `artist_voice_cloning`

This list is extensible via a minor version. Implementations MUST reject an unrecognised use class rather than defaulting to permitted.

### 7.7 Content roles

`melody` `harmony` `bassline` `rhythm` `lyrics` `score` `structure` `fingerprint`

The set is open to additions by minor version and closed to a producer. `bassline` and `rhythm` are present because the material most often alleged to be copied is a bassline over a chord loop, and a vocabulary that could not name it could not describe the claim.

### 7.8 Derivation dispositions

| Code | Meaning |
| --- | --- |
| `cleared` | A licence was sought and granted. REQUIRES `clearance_id`. |
| `clearance_sought` | Requested, not yet answered. |
| `clearance_refused` | Requested and refused. The work is exploited, or not, at the holder's risk. |
| `de_minimis_asserted` | The holder's position is that the taking is too slight to require a licence. |
| `independent_creation_asserted` | The holder's position is that the similarity is coincidental. |
| `not_sought` | The similarity is acknowledged and no licence was requested. |
| `disputed` | A third party has made a claim. REQUIRES `dispute_id`. |

The last four are not failures of the format. They are real and common postures, and recording which one applies — with a date, an attestor and a signature — is more use than a boolean that calls all of them `false`.

### 7.9 Dispute statuses

`raised` `contested` `withdrawn` `settled` `adjudicated`

`withdrawn`, `settled` and `adjudicated` are **terminal** and REQUIRE a non-null `resolution`.

---

## 8. Validation rules

Each rule has a stable identifier and a level. Conformance fixtures in [conformance/](conformance/) reference these identifiers, and a validator MUST report the identifier of every rule violated.

### 8.1 Levels

A rule's level is the **lowest** at which it can be decided.

| Level | Decidable from | Example |
| --- | --- | --- |
| **L1** structural | the document's own bytes, a field at a time | a date format, an enum member, a share bound |
| **L2** referential | the document as a whole — references resolved, aggregates recomputed | a `party_id` that resolves, ownership totalling `10000` |
| **L3** external | the document **plus data outside it** | a signature, a blob's contents, the TIS hierarchy, an EU Trusted List |

This tiering exists because an earlier draft required every validator to implement every rule, while several rules cannot be decided from the document at all. `WORK-063` checks against a provenance log that is an external blob behind a digest; `WORK-060` needs a resolvable public key; `WORK-062` needs a Trusted List. A conformance class nobody can satisfy is not a conformance class. See [§9.3](#93-conformant-validator).

**Structure**

| ID | L | Rule |
| --- | --- | --- |
| `WORK-001` | 1 | The document MUST be strict, well-formed JSON, UTF-8, no BOM. |
| `WORK-002` | 1 | `spec_version` MUST be present and its major version supported. |
| `WORK-003` | 1 | `work_id` MUST be a valid 26-character ULID. |
| `WORK-004` | 1 | `parent` MUST be `null` if and only if `version` is `1`. |
| `WORK-005` | 1 | `version` MUST be a positive integer. |
| `WORK-006` | 1 | Every `ext` key MUST be a DNS or reverse-DNS name. |
| `WORK-007` | 1 | `status` MUST be `draft`, `attested` or `withdrawn`. `superseded` is not a status ([§4.2](#42-version-chain)). |
| `WORK-008` | 1 | `@context`, where present, MUST be a string IRI or an array of string IRIs and objects. |

**Identity**

| ID | L | Rule |
| --- | --- | --- |
| `WORK-010` | 1 | `identity.title` MUST be a non-empty string. |
| `WORK-011` | 1 | `identity.iswc`, when non-null, MUST match `T-nnn.nnn.nnn-c` and satisfy the ISO 15707 check digit. |
| `WORK-012` | 1 | `music_arrangement` and `lyric_adaptation` MUST be non-null when `version_type` is `MOD`, and `null` otherwise. |
| `WORK-013` | 1 | `submitter_work_number` MUST be a non-empty string. |
| `WORK-014` | 1 | `duration_ms` MUST be non-null when `distribution_category` is `SER`. |
| `WORK-015` | 1 | Every `cwr_title_type` MUST be a member of [§7.4](#74-title-types). |

**Content and evidence**

| ID | L | Rule |
| --- | --- | --- |
| `WORK-020` | 1 | The pair (`role`, `subrole`) MUST be unique within `content`. |
| `WORK-021` | 1 | Every `digest` MUST match `<algorithm>:<lowercase-hex>` with a supported algorithm and correct length. |
| `WORK-022` | 1 | `size` MUST be a non-negative integer. |
| `WORK-023` | 1 | `confidence`, where present, MUST be within `0.0`–`1.0` inclusive. |
| `WORK-024` | 2 | An attestation MUST include `confidence` when its attestor is a producer, and MUST omit it when its attestor is a `party_id`. |
| `WORK-025` | 1 | `attestations` MUST be ordered by `created`, ascending. |
| `WORK-026` | 1 | Every `isrc`, where non-null, MUST be 12 alphanumeric characters. |
| `WORK-027` | 2 | Every `attestor` MUST either equal a declared `party_id` or match the producer identifier grammar in [§6.16](#616-attestation-object). |
| `WORK-028` | 2 | A component whose `role` is `fingerprint` MUST carry non-null `computed_over` and `algorithm`, and `computed_over` MUST resolve to another component. |
| `WORK-029` | 1 | Every `content` `role` MUST be a member of [§7.7](#77-content-roles). |

**Rights**

| ID | L | Rule |
| --- | --- | --- |
| `WORK-030` | 1 | Every `party_id`, `credit_id`, `agreement_id`, `mandate_id`, `clearance_id`, `render_id` and `dispute_id` MUST be unique within the document. |
| `WORK-031` | 2 | Every reference to an identifier MUST resolve to an object declared in the same document. |
| `WORK-032` | 2 | `ownership_bps` MUST total exactly `10000` for each of `pr`, `mr` and `sr`, taken independently across all credits. |
| `WORK-033` | 1 | Every share value MUST be an integer in `0`–`10000`. No share or monetary value may be a JSON number with a fractional part. |
| `WORK-034` | 1 | A credit MUST carry `writer_designation` xor `publisher_type`, matching its `cwr_record`. |
| `WORK-035` | 1 | `cwr_record` MUST agree with `controlled`: `SWR`/`SPU` when `true`, `OWR`/`OPU` when `false`. |
| `WORK-036` | 2 | Every credit with `cwr_record` of `SWR` MUST appear as a `writer_credit_id` in `publisher_for_writer`. |
| `WORK-037` | 1 | A `territory_claim` with `indicator` of `E` MUST have all `collection_bps` set to `0`. |
| `WORK-038` | 1 | A credit with `controlled` of `true` MUST have a non-null `agreement_id`. |
| `WORK-039` | 2 | Publisher credits MUST have a `publisher_sequence` of `1` or greater, unique within their chain. |
| `WORK-040` | 1 | `effective_to`, where non-null, MUST NOT precede `effective_from`. |
| `WORK-041` | 1 | `retention_end_date` MUST NOT precede `end_date`; `post_term_collection_end_date` MUST NOT precede `retention_end_date`. |
| `WORK-042` | 3 | For every TIS territory referenced, collection shares MUST total `10000` per right across all controlled parties collecting there, after resolving the TIS hierarchy and all include/exclude claims. |
| `WORK-043` | 2 | `rights.totals_bps.ownership` MUST equal the total recomputed from `credits`, per right. |

**Derivation, clearance, consent and dispute**

| ID | L | Rule |
| --- | --- | --- |
| `WORK-050` | 1 | `clearance_id` MUST be non-null when `disposition` is `cleared`, and `null` otherwise. |
| `WORK-051` | 2 | Where a clearance has `affects_ownership` of `false`, its `consideration.beneficiary_party_id`, when non-null, MUST NOT hold a credit in `rights.credits`. |
| `WORK-052` | 2 | A render's `use_class` MUST appear in the `use_classes` of its referenced mandate. |
| `WORK-053` | 2 | A render's `use_class` MUST NOT appear in that mandate's `exclusions`. |
| `WORK-054` | 1 | `distribution_restriction` MUST be non-null when any `consent_coverage_bps` value is less than `10000`. |
| `WORK-055` | 1 | `clearability.one_stop` MUST be `true` only when every `coverage_bps` value is `10000`. |
| `WORK-056` | 1 | `disposition` MUST be a member of [§7.8](#78-derivation-dispositions); `disputes[].status` MUST be a member of [§7.9](#79-dispute-statuses). |
| `WORK-057` | 2 | Every `affected_components` and `disputed_components` entry MUST resolve to a component in `content`. |
| `WORK-058` | 2 | `dispute_id` MUST be non-null when `disposition` is `disputed`, and every `dispute_id` reference MUST resolve. |
| `WORK-059` | 1 | `resolution` MUST be non-null when a dispute's `status` is terminal, and `resolved_at` MUST NOT precede `raised_at`. |

**Signatures and status**

| ID | L | Rule |
| --- | --- | --- |
| `WORK-060` | 3 | Every signature MUST verify against the signing input defined in [§5.4](#54-the-signing-input). |
| `WORK-061` | 3 | A document with `status` of `attested` MUST carry at least one valid signature from a party declared in `rights.parties`. |
| `WORK-062` | 3 | A `timestamps` entry with `qualified` of `true` MUST name an authority on an EU member state Trusted List. |
| `WORK-063` | 3 | Every value marked `derived: true` MUST have a corresponding entry in the resolved provenance log. |
| `WORK-064` | 3 | Every retrieved blob MUST hash to the `digest` of the entry that referenced it. |

### 8.2 CWR projection profile

These rules constrain a document's ability to **project into CWR**. They are not properties of the format, and a document that violates them is a valid `.work` document that will be rejected by a society. They are published under a distinct prefix so that a validator can report them without implying that the document is malformed.

Implementing this profile is OPTIONAL and is not required for `.work` conformance ([§9.3](#93-conformant-validator)).

| ID | L | Rule |
| --- | --- | --- |
| `CWR-001` | 1 | `identity.title` MUST be 1–60 characters. |
| `CWR-002` | 1 | `identity.submitter_work_number` MUST be 1–14 characters. `work_id` is a ULID and cannot serve as one. |
| `CWR-003` | 1 | `identity.language`, where non-null, MUST have an ISO 639-1 two-letter equivalent. |
| `CWR-004` | 1 | Every `alternative_titles` entry MUST be 1–60 characters. |
| `CWR-005` | 2 | Every controlled credit MUST reference a party with a non-null `ipi_name_number`. |
| `CWR-006` | 2 | Every `clearance` whose `affects_ownership` is `false` is unrepresentable in CWR and MUST be reported as a lossy projection, not an error. |

---

## 9. Conformance

### 9.1 Conformant producer

MUST emit documents satisfying every rule in [§8.1](#81-levels); MUST use JCS for canonicalisation; MUST NOT emit a `status` of `attested` without a valid signature; MUST NOT assert machine-derived values without provenance and confidence; MUST NOT omit a known dispute or an uncleared derivation in order to produce a conformant file, neither of which this specification treats as a defect.

### 9.2 Conformant consumer

MUST verify every signature before relying on any claim; MUST treat `digest` as authoritative and `locators` as advisory, verifying every retrieved blob against its digest; MUST preserve unrecognised fields and `ext` namespaces on round trip; MUST reject unrecognised digest algorithms and use classes rather than ignoring them; MUST NOT treat `clearability` as current without recomputing, or as applicable to a request other than its own `request`; MUST NOT reject a document for carrying an open `dispute` or an uncleared `derivation`; and, where a document carries `@context`, MUST verify signatures before any JSON-LD processing ([§5.7](#57-json-ld)).

### 9.3 Conformant validator

Validation rules are tiered by what is needed to decide them ([§8.1](#81-levels)). A validator declares the highest level it implements.

| Level | Must implement |
| --- | --- |
| **L1** | every L1 rule |
| **L2** | every L1 and L2 rule |
| **L3** | every rule |

**An L1 validator is conformant.** This is deliberate. A document-only validator is the one that can be a dependency-free library, a CI check or a page that validates a pasted file, and requiring key resolution and blob retrieval of every implementation would put the cost of adoption well above "read the schema".

Every validator MUST:

- report violations by rule identifier
- declare the level it implements
- report a rule above its level as **unchecked**, never as passed

The third is the one that matters. Silently passing a rule you did not implement is indistinguishable, to the reader of the output, from the document being correct — and it is the failure this tiering exists to prevent.

A conformant validator at level *n* MUST accept every document under [conformance/](conformance/)`valid/` reporting no violations, and MUST reject every document under `invalid/` whose declared rules are at level *n* or below, reporting exactly those identifiers. Fixtures turning on rules above its level are out of scope and MUST be reported as unchecked rather than passed or failed.

A validator MAY implement rules beyond [§8.1](#81-levels) but MUST report them under a distinct, non-`WORK-` prefix. The CWR projection profile ([§8.2](#82-cwr-projection-profile)) is published under `CWR-` and is OPTIONAL: a `CWR-` violation means the document will not register at a society, not that it is malformed.

---

## 10. Security considerations

**Locators are untrusted.** A locator is a hint. A consumer MUST verify every retrieved blob against its `digest` and MUST discard any mismatch. A locator pointing at an attacker-controlled host is not a vulnerability provided the digest is checked; failing to check it is.

**Signature scope.** A signature covers the signing input, which excludes `signatures` and includes everything else. Consumers MUST NOT infer that a signer endorses claims added after their `signed_at`; a later version is a separate document requiring separate signatures.

**Timestamps prove bytes, not authorship.** An RFC 3161 token proves a set of bytes existed at a time. It does not prove authorship or originality. It is useful for rebutting a claim of prior creation and useless for proving independent creation.

**"Qualified" is a term of art.** Under eIDAS Article 41 a *qualified* timestamp carries a presumption of date accuracy and data integrity. A free RFC 3161 service runs the same protocol and is cryptographically equivalent, but carries no such presumption. Misreporting `qualified` misrepresents the legal weight of the document.

**Key compromise.** This version defines no revocation mechanism. Consumers relying on signatures for anything consequential SHOULD corroborate with a timestamp from an independent authority.

**Fetching blobs may leak interest.** Retrieving a locator discloses to its host that a party is examining a particular work. Consumers handling confidential deal data SHOULD mirror rather than hot-link.

---

## 11. Privacy considerations

A work package contains personal data: legal names, IPI numbers, society affiliations, and by implication professional relationships. Under UK GDPR and GDPR this makes any party distributing `.work` files a controller or processor.

**Distribution is not revocable.** Once handed to a counterparty, a document cannot be recalled. Producers SHOULD emit the minimum party data the recipient needs, and SHOULD NOT include contact details, addresses or bank details in a `.work` file. This specification defines no field for any of them, deliberately.

**Erasure.** Because the format is append-only and content-addressed, erasing a party from the historical chain is not possible without breaking every dependent digest. Implementations subject to erasure requests SHOULD hold party records by reference and resolve them at read time, rather than embedding, and MUST NOT publish work packages to an immutable public ledger. This is the principal reason this specification does not anchor to a blockchain.

**Locators may embed identity.** `s3://mali-mccalla-archive/…` discloses a person's name to anyone holding the file. Producers SHOULD prefer digest-addressed locator paths.

---

## 12. IANA considerations

Registration in the vendor tree is a form submission, not a standards process. This section is the intended template.

```
Type name:               application
Subtype name:            vnd.invoke.work+json
Required parameters:     none
Optional parameters:     none
Encoding considerations: binary (UTF-8 JSON)
Security considerations: see §10
Interoperability:        see §5
Published specification: this document
Applications:            music publishing administration, rights clearance,
                         copyright deposit
Fragment identifier:     as per application/json
File extension:          .work
```

A parallel registration for `application/vnd.invoke.workpkg+zip` with extension `.workpkg` applies.

---

## 13. Licence and patent position

This specification and the accompanying JSON Schema are published under **[CC BY 4.0](LICENSE-DOCS)** (text) and **[Apache-2.0](LICENSE)** (schema and fixtures).

**No patent has been or will be sought on this format, its schema, or any mechanism described in this document.** Implementing it requires no licence, no membership, no registration and no agreement of any kind.

Implementations are neither certified nor endorsed. Conformance is a property a document either has or does not, testable against [§8](#8-validation-rules) and the [conformance corpus](conformance/).

---

## Appendix A — Open questions

Unresolved in `1.0.0-draft`:

1. **`WORK-042` is correct but expensive.** It is now scoped to controlled parties and classified L3, because resolving overlapping include/exclude claims requires the TIS hierarchy, which is not a public dataset. In practice only an L3 validator with a TIS licence can check it.
2. **`attestations` overlaps `provenance_log`.** An attestation is current state on a relationship; provenance is the chronological log. Both carry attribution and confidence, and one should be derived from the other. The JSON-LD context ([§5.7](#57-json-ld)) maps both onto PROV-O, which may be where the duplication resolves.
3. **No revocation or key rotation.** [§10](#10-security-considerations) states the gap.
4. **`version_type` cannot express "original work containing a cleared interpolation".** CWR requires a choice between `ORI`, which discards the derivation, and `MOD`, which asserts the whole work is a version of the parent. `derivation.disposition` ([§6.12](#612-derivation-object)) now records the real posture, but it still cannot be projected.
5. **No canonical form for `.workpkg` ZIP entries**, so a `.workpkg` is not itself reproducibly digestible.
6. **The `$schema` host, the JSON-LD context IRI, the `vnd.invoke` media type and the `invoke.works` extension namespace are organisation-specific.** The `vnd.` tree denotes a vendor format. Publishing a context sharpens this: a context IRI is a permanent dependency on a host resolving, for the lifetime of every document that references it. Whether to move to a neutral host is open, and is better settled before the context ships than after.
7. **Fingerprint interoperability is undefined.** [§6.4](#64-content-component-object) defines where a fingerprint lives and what it must not disclose, and says nothing about how two of them are compared. Without at least one named scheme, federated matching is a field rather than a capability.
8. **`disputes` and `registrations` both record conflict.** A society's `CO` acknowledgement is an overclaim dispute by another name. They are kept separate because one is a protocol state and the other is not, but the boundary is not obviously in the right place.

---

## Appendix B — Change log

| Version | Date | Change |
| --- | --- | --- |
| `1.0.0-draft` | 2026-10-03 | Validation levels L1/L2/L3 and a conformant L1 validator class. CWR width limits moved to a `CWR-` projection profile. `derivation.cleared` replaced by `disposition`; `disputes[]` added; `content` roles opened with `bassline`, `rhythm` and `fingerprint`; render consent split per right; `clearability.request` added; `totals_bps.valid` removed; attestor grammar made decidable; optional JSON-LD context defined. |
| `1.0.0-draft` | 2026-09-05 | Initial draft, extracted from the design notes. |
