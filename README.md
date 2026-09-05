# `.work`

An open format for musical works.

A `.work` file is a signed, content-addressed, versioned JSON document describing a musical work: who wrote it, who publishes and administers it, in which territory, for which right, at what share, under which agreement — plus the musical content that anchors it and the provenance of every assertion in it.

**The recording is no longer the barrier. The song is everything.** A sound recording has an artefact and a musical work does not. This is an attempt at giving it one.

---

## The documents

| | |
| --- | --- |
| **[SPEC.md](SPEC.md)** | The normative specification. Object model, canonicalisation, signing, validation rules, conformance. |
| **[RATIONALE.md](RATIONALE.md)** | Why the format exists and why it is shaped this way. Non-normative, and the part worth reading first. |
| **[example.work](example.work)** | A complete, valid document exercising every awkward case. |
| **[conformance/](conformance/)** | Fixtures a validator must pass — valid documents, invalid ones, and the rules each violates. |

---

## What it looks like

```json
{
  "$schema": "https://invoke.works/schema/work/v1",
  "spec_version": "1.0.0",
  "work_id": "01J8QK3M2N4P5R6S7T8V9WXYZA",
  "version": 3,
  "parent": "sha256:bb17c0f4…",
  "status": "attested",

  "identity": { "iswc": "T-034.524.680-1", "title": "Salt Water" },
  "content":  [ { "role": "melody", "digest": "sha256:9f2a4c7e…" } ],
  "rights":   { "parties": [], "credits": [], "agreements": [] },
  "signatures": [ { "algorithm": "ed25519" } ]
}
```

The manifest holds a **digest** and a list of **locators**, never the audio. The digest is the truth; the location is a hint. That is what lets the canonical copy stay with the rightsholder, and it means nothing in the audio pipeline has to change for the format to be useful.

---

## Design constraints

Learned from every previous attempt at this problem, all of which failed — [in detail here](RATIONALE.md#reading-the-graveyard).

1. Never require industry-wide adoption to be useful.
2. Speak the existing standards fluently — CWR, DDEX, ISWC, ISRC, IPI, ISNI, TIS. Interoperate, don't replace.
3. The canonical copy stays with the rightsholder.
4. Every assertion is attributable and reversible.
5. Derived data is never asserted as fact.
6. Whoever adopts it captures the value.
7. **The cost of adoption is reading the schema.** No patent, no licence, no membership, no consortium, no committee.

---

## Status

`1.0.0-draft`. The object model, canonicalisation rules and validation rules are drafted, and [example.work](example.work) is a complete conforming document. Unresolved questions are tracked in [SPEC Appendix A](SPEC.md#appendix-a--open-questions).

Roadmap:

1. Publish the JSON Schema at its `$schema` URL
2. Release the reference validator
3. Complete the conformance corpus — 3 of 23 fixtures written
4. CWR `NWR` projection

---

## Tooling

Tooling is developed and versioned separately from the specification. None of it is required in order to use the format — a `.work` file is a JSON document, and any JSON library can read one.

| | |
| --- | --- |
| **Reference validator** | Checks a document against [SPEC §8](SPEC.md#8-validation-rules) and the [conformance corpus](conformance/). In development. |
| **Projections** | `.work` → CWR, DDEX `MWL` / `MWN`, lead sheet. Planned. |
| **[invoke-works](https://github.com/malimccalla/invoke-works)** | Publishing administration platform built on the format. In development. |

---

## Maintenance

The specification is maintained by [INVOKE](https://invoke.works), an independent songwriting collective based in London.

`.work` is an open format. It is free to implement, requires no licence, membership or registration, and is covered by no patent. Implementations are neither certified nor endorsed, and none is privileged over another.

Three related names: **`.work`** is the format, **invoke-works** is a platform that implements it, and **INVOKE** maintains the format and operates the platform.

---

## Licence

Specification text under CC BY 4.0. Schema and fixtures under Apache-2.0. No patent has been or will be sought on this format. See [SPEC §13](SPEC.md#13-licence-and-patent-position).

Contact: `mali@invoke.works`
