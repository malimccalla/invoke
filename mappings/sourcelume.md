# `.work` → Apache Sourcelume `ProvenanceRecord`

Sourcelume is an Apache Software Foundation project under the ASF's Responsible AI initiative, defining a JSON-LD record for AI **training-data** provenance: dataset identity, role-tagged creators, a licence claim, and an ordered chain of custody.

Not normative. Written against Sourcelume `0.0.1`.

## Why the two meet

They operate at different tiers and the join is `ai_training`.

A `ProvenanceRecord` describes a **dataset**: where a corpus came from, who handled it, and under what licence it is claimed to be distributed. It is explicitly dataset-centric and carries nothing per item.

A `.work` document describes **one musical work**, and carries `mandates` — a standing, signed, per-party statement of what may be licensed, scoped by right, territory and use class, with `ai_training` and `ai_rendering` as separately grantable classes ([SPEC §6.14](../SPEC.md#614-mandate-object)).

So a dataset of musical works has a provenance record that can assert a licence over the corpus, and no way to evidence that any individual writer consented. The `.work` documents are that evidence. The crosswalk below produces the dataset record; the works it points at are what make the record checkable.

## Dataset record, built from a corpus of `.work` documents

| `ProvenanceRecord` | Source | Note |
| --- | --- | --- |
| `id` | minted by the curator | an IRI for the record itself |
| `type` | `"ProvenanceRecord"` | fixed |
| `identifier` | the dataset's own DOI or persistent URL | not derivable from the works |
| `name` | the dataset's name | |
| `version` | the dataset's version | not `work.version` |
| `license` | see below | |
| `licenseCategory` | `agreement-supplied` | each work is included under a bilateral mandate, not a public licence |
| `creator[]` | union of `rights.parties` across the corpus, deduplicated on `ipi_name_number` | writers are `schema:Person` with `role: originator`; publishers are `schema:Organization` with `role: distributor` |
| `created` | when the record was authored | |
| `added` | when the works were incorporated | |
| `contentCreated` | earliest `identity.created_year` in the corpus | Sourcelume asks for the start of the range |
| `origin` | free text naming the catalogue | |
| `custodyChain[]` | one entry per handling step | `agent` is an IRI; `action` is `collected` / `ingested` / `transformed` |

### `license`

There is no SPDX term for "licensed per work by writer mandate". Use Sourcelume's own agreement-supplied IRI:

```
https://sourcelume.apache.org/ns#agreement-supplied
```

with `licenseNote` naming the mandate basis, and `licenseScope` where the mandates are territorially bounded — a corpus assembled from `territories: [{ tis_code: 2136, indicator: "I" }]` is worldwide; one assembled under a `276`-only mandate is not.

### Eligibility — the filter that produces the corpus

A work belongs in an `ai_training` dataset only if, for every credit:

1. a mandate exists for that party, and
2. `ai_training` appears in its `use_classes`, and
3. `ai_training` does **not** appear in its `exclusions`, and
4. the requested territory falls inside its `territories`, and
5. `effective_from`/`effective_to` cover the date of ingestion.

Anything less is a gap, and `clearability` ([SPEC §6.15](../SPEC.md#615-clearability-object)) computes it with the gaps named by party. The worked example in [example.work](../example.work) fails at step 3: `ai_training` is in `exclusions`, so the work is ineligible even though `ai_rendering` is permitted. **Consent to one is not consent to the other and an implementation must not infer it.**

## Patterns worth borrowing in the other direction

Three things Sourcelume does that this format has adopted or should.

**References, never embeddings.** A `custodyChain.agent` IRI may point to another `ProvenanceRecord`, and that record is not nested inside the current one — because a record is signed as one unit, because an embedded copy cannot receive the original's corrections, and because a graph of linked records is what graph storage actually wants. `derivation.parent_locators` ([SPEC §6.12](../SPEC.md#612-derivation-object)) follows the same reasoning.

**No adjudication fields.** Sourcelume's non-goals are explicit: there is no `verified: true/false`, because the record publishes a claim and verification is somebody else's job. `rights.totals_bps.valid` was exactly that anti-pattern and has been removed.

**Non-goals stated as non-goals.** `0.0.1` says what it deliberately left out, why, and which of those are settled versus open for argument. That is a better instrument than a bare list of open questions, because it distinguishes a decision from an omission.

## What does not survive

| `.work` | Home in `ProvenanceRecord` |
| --- | --- |
| shares, credits, agreements, chain of title | none — it has no rights graph |
| `clearability`, `clearances`, `disputes` | none |
| `content` digests and fingerprints | none |
| `registrations` | none |
| per-work consent | none, which is the gap the join above exists to fill |

And in the other direction, `0.0.1` carries no signature block at all: signing is deferred to a separate Sourcelume Attest project. A `.work` document is signed in the document ([SPEC §5.4](../SPEC.md#54-the-signing-input)), so a record generated from a corpus of signed works is better evidenced than the record format can currently express.
