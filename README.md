# INVOKE

> **This repository is the static landing page and the thinking behind it.**
> A single `index.html` plus `robots.txt`, and this README — which is a working design document and brainstorm, not a spec. Nothing here is the product.
>
> **The publishing administration platform is a work in progress being built at [github.com/malimccalla/invoke-works](https://github.com/malimccalla/invoke-works)** as a separate Python / FastAPI project.

INVOKE is an independent songwriting collective based in London, and the front end of a publishing administration platform for musical works.

---

## Thesis

**The recording is no longer the barrier. The song is everything.**

Recording and distribution are commodities. Anyone can cut a master and put it on every DSP on earth for the price of a coffee. What is *not* solved is the layer underneath: the musical work — who wrote it, who publishes it, who administers it, in which territory, for which right, at what share, and under which agreement.

That layer runs on spreadsheets, PDFs, email threads and a fixed-width flat file format designed in the 1990s. It is where money goes unmatched, where clearance takes six weeks, and where writers have the least visibility and the least leverage.

The asymmetry is concrete: **a sound recording has an artefact and a musical work does not.**

---

## The manifestation problem

### A work is not a thing

An image is a file. A film is a file. Software is a file. A sound recording is a file — you can hash it, stream it, fingerprint it, sign it, put it in an object store and point a URL at it.

A musical work is none of these. It is an abstract legal object: a melody-and-lyric that exists across every performance of it and is identical to none of them. You cannot download a musical work. You can only download evidence that one exists.

Library science has the vocabulary for exactly this. **FRBR** (IFLA's Functional Requirements for Bibliographic Records, now the LRM) splits creative output into four tiers — **Work → Expression → Manifestation → Item**. Beethoven's Ninth is a *work*; the 1996 London Philharmonic performance is an *expression*; the CD release of that performance is a *manifestation*; your copy is an *item*.

The music industry has excellent infrastructure at the manifestation and item tiers — ISRC, DDEX ERN, audio files, delivery pipelines. At the work tier it has an identifier and a batch message. **The work tier was never given an artefact.**

### Isn't CWR that artefact?

No, and the distinction is the whole design.

**CWR (Common Works Registration)** is a CISAC-governed fixed-width flat file for bulk registration and revision of works between publishers, PROs and mechanical societies. It is real, it is the only game in town, and INVOKE has to speak it fluently. But it is a **message**, not a **document**:

| CWR is | A manifestation would be |
| --- | --- |
| A batch transmission to a named recipient | Addressable and dereferenceable by anyone permitted |
| A point-in-time *claim* by a submitter | A versioned, verifiable state with history |
| Write-mostly, acknowledged asynchronously via `ACK` | Readable, with a stable identity |
| Lossy — it carries rights data, not the music | Anchored to the musical content itself |
| Register-only; it cannot express a licence | Composable into licensing and settlement |

CWR is the **EDIFACT of music publishing**, not the PDF. It is a wire format for one transaction type. The MLC's own guidance makes the point bluntly: CWR is for submitting hundreds or thousands of registrations at once, and "if you do not have thousands of work registrations, CWR may not be the best choice for you." It also cannot express a partial claim — a CWR registration necessarily covers *all* mechanical usage types. A format that cannot say "I control this for these uses and not those" is structurally incapable of supporting granular licensing.

And ISWC (ISO 15707) is only an identifier: `T-`, nine sequential digits, a mod-10 check digit. It encodes nothing — not the writers, not the shares, not the music. It is a pointer with no referent you can fetch. Duplicate ISWCs for the same work exist and, by CISAC's own admission, cannot be retired — only linked.

### Has anyone built the artefact before?

Partially, in three traditions that have never been joined up.

**Notation and content encodings** — MusicXML, MEI, MNX, LilyPond, ABC, Standard MIDI Files. These genuinely encode the *musical* content of a composition; MIDI is the closest thing to a machine-readable composition that exists at scale. None carry a byte of rights data.

**Rights and registration formats** — CWR, DDEX (MWL/MWN for work licensing and notification, RDR-N for royalty reporting), MLC bulk registration, ICE, CIS-Net. These carry rights data and no music.

**Legal deposit** — the oldest answer and the most instructive. US copyright registration historically required a deposit copy, usually a lead sheet. The courts have already had to rule on what the actual artefact of a musical work is, and in *Skidmore v. Led Zeppelin* (9th Cir. 2020, en banc) the answer was: the scope of the copyright is the deposit copy, not the famous recording. The legal system's manifestation of a musical work is a piece of paper in an archive.

**Attempts to merge the three have a graveyard.** The International Music Joint Venture (1998–2001) dissolved without opening an office. WIPO's International Music Registry (2011) collapsed in industry infighting. The Global Repertoire Database (2008–2014) had thirteen CMOs, Google and Apple on board, and folded when committed investment was withdrawn. dotBlockchain Media tried to define a file format carrying rights alongside audio and became Verifi Media. Open Music Initiative, Mediachain and Ujo are gone. Blokur survives.

The pattern is unambiguous and worth stating plainly: **every attempt at a single global authoritative works database has failed, and they failed for governance reasons, not technical ones.** No rightsholder will cede the canonical copy. Any design that needs universal buy-in to be useful is dead before it starts.

### So what is INVOKE actually building?

Not a global database. A **work package**: a signed, content-addressed, versioned artefact that one party can produce, hold and hand to another, and which is useful on its own from day one.

```
work-package/
  manifest.json        # identity: ISWC, internal ID, canonical hash, version, signatures
  work.json            # titles, language, duration, version type, derivation
  content/
    score.musicxml     # or MEI — the notated composition
    melody.mid         # normalised melodic line + harmonic reduction
    lyrics.txt         # timestamped where available
  rights/
    parties.json       # interested parties, IPI, society affiliation
    splits.json        # ownership + collection shares, per right, per territory
    agreements/        # chain of title, term, retention, post-term collection
    clearances/        # samples, interpolations, derivations, evidence
  mandates/            # per-party licensing authority and terms
  evidence/
    reference.wav      # a recording, as evidence, not as the work
  provenance.jsonl     # append-only log of every assertion and who made it
```

The useful analogues are outside music. An **SBOM** (SPDX/CycloneDX) is a machine-readable bill of materials for an intangible composite. An **OCI image manifest** gives content-addressed identity to something assembled from layers. **C2PA content credentials** attach signed provenance to media. A **git commit** gives verifiable, replayable history of who changed what.

The honest caveat, stated in the design rather than papered over: **you cannot fully represent a musical work, because its legal boundary is deliberately undefined.** Substantial similarity is decided by a jury, not a schema. So the artefact is not the work. It is a *verifiable, versioned, attributable claim about* the work, with the musical content attached so the claim is anchored to something rather than floating free. That is exactly what a deposit copy does, and exactly what CWR does not.

---

## Scope

Deliberately narrow. Publishing only.

- Musical works, not masters
- Interested parties — writers, publishers, sub-publishers, administrators
- Splits and shares, separated by right and by territory
- Agreements and chain of title
- CWR generation, delivery and `ACK` reconciliation
- Rights clearance — samples, interpolations, derivatives, medleys
- Programmatic licensing against known mandates
- Royalty accounting and settlement

Sound recordings appear only as *evidence of* a work, never as the primary entity.

---

## Domain model

Modelled against CWR (v2.1 rev 8 / v2.2) so data can be delivered to societies without a translation layer bolted on at the end.

```
InterestedParty ──< WorkCredit >── MusicalWork ──< WorkRelation >── MusicalWork
       │                │  │                            (VER / COM)
       │                │  └──< TerritoryClaim          (SPT / OPT / SWT / OWT)
       │                └─────< PublisherForWriter      (PWR)
       ├──< Agreement                                   (AGR)
       └──< Mandate                                     (licensing authority)

MusicalWork ──< WorkRegistration >── Society            (NWR/REV → ACK)
MusicalWork ──< SoundRecording                          (REC — evidence)
```

### `MusicalWork`

The composition. ISWC, titles and alternative titles, language, lyrics, duration, version type (`ORI` / `MOD`), distribution category, and clearance state.

### `InterestedParty`

A globally unique creative or corporate identity — a writer or a publisher entity. Keyed on **IPI Name Number** (11 digits) and **IPI Base Number** (`I-000000229-7`), with society affiliation held per right.

Deliberately *not* tenant-scoped. The same writer is the same entity everywhere; membership is a separate relation.

### `WorkCredit`

The junction, and the most important table in the system: an interested party assigned to a work with a role, a control indicator, and shares.

**Shares are split by right, never combined.** The single most common modelling error in publishing software. Each party holds independent ownership and collection shares in:

- **PR** — performing rights (broadcast, live, streaming)
- **MR** — mechanical rights (sales, downloads, reproduction)
- **SR** — synchronisation rights (film, TV, advertising, games)

Stored as **integer basis points**, `10000` = 100.00% — which is exactly how CWR encodes them, five digits with two implied decimals. Never floats.

**Control indicator** determines which CWR record type a credit serialises to:

| Record | Meaning |
| --- | --- |
| `SWR` | Writer controlled by submitter |
| `OWR` | Other writer, not controlled |
| `SPU` | Publisher controlled by submitter |
| `OPU` | Other publisher, not controlled |

---

## Model corrections

The earlier draft of this schema had real defects. They are listed here because finding them is the work.

**1 — Writer roles and publisher roles were merged into one enum.** They are two distinct CWR controlled vocabularies. Writer designation codes are `C`, `A`, `CA`, `AR`, `AD`, `SA`, `SR`, `TR`, `PA`. Publisher type codes are `E`, `AQ`, `AM`, `SE`, `ES`, `PA`. Collapsing them permits a composer-publisher, which is not a thing.

**2 — `ES` is not sub-publisher.** In CWR, `SE` is Sub Publisher and `ES` is *Substituted* Publisher. The original had this backwards. A sub-publishing chain built on `ES` will be rejected.

**3 — `PWR` was missing entirely.** CWR requires a Publisher For Writer record linking each controlled writer to the publisher their share flows through. Without it there is no chain of title and files will not validate. A flat list of credits cannot represent publishing — the structure is a graph.

**4 — Territory was an ISO 3166 string array.** CWR uses **TIS** codes (CISAC's Territory Information System), which are hierarchical, and every territory claim carries an **inclusion/exclusion indicator**. "World except US and Canada" is `include 2136, exclude 840, exclude 124`. An array cannot express exclusion, and using one as part of a uniqueness constraint is a footgun.

**5 — Collection shares were on the wrong record.** In CWR, ownership share is global and sits on `SPU`/`SWR`; collection share is *per territory* and sits on `SPT`/`SWT`. Putting both on the credit makes territorial deals unrepresentable. Collection shares move down to `TerritoryClaim`.

**6 — Splits had no time dimension.** Rights revert, catalogues are sold, terms expire. Royalties must be computed against the split **as it stood when the usage occurred**, not as it stands today. Every credit needs `effective_from` / `effective_to`, plus retention and post-term collection periods. This is the expensive bug: it is silent, and it surfaces as a restatement.

**7 — There was no `Agreement` entity.** Deal terms were scattered across credits as loose columns. CWR has a whole `AGR` transaction: agreement type (`OG`/`OS`/`PG`/`PS`), start and end dates, retention end, prior royalty status, post-term collection end, sales/manufacture clause. The contract is a real object; credits should reference it, not duplicate it.

**8 — Derivation was a JSON blob.** `isDerivative` / `isMedley` booleans plus an untyped `originalWorks` field. CWR needs structured `VER` (version of an original work) and `COM` (medley component) records. Model it as a self-referencing `WorkRelation` with a typed relation. The booleans are derivable from the relations; the relations are not derivable from the booleans.

**9 — Registration status was a single field on the work.** Registration is per society, per submission, per transaction, each with its own `ACK` and message records. One work has many `WorkRegistration` rows carrying the society, the transaction sequence, the returned status (`RA`, `AS`, `AC`, `CO`, `DU`, `RJ`, `NP`…), any allocated ISWC and the society's own work code. Conflicts (`CO`) are the interesting state and need somewhere to live.

**10 — `iswc @unique` globally, on a tenant-scoped work.** The model correctly kept `InterestedParty` global, then applied a global constraint to a workspace-scoped `MusicalWork`. Two publishers can legitimately hold credits in the same work. This exposes the real distinction: there is **the work** (global, sparse, identity-only) and **our claim on the work** (tenant-scoped, opinionated, complete). Conflating them is the same mistake the GRD made at industry scale.

**11 — Money as `Float`.** `adminCommission Float?`, `totalWriterShare Float?`. Percentages that touch money are integer basis points or `Decimal`, never binary floating point.

**12 — Missing conditionally-mandatory CWR fields.** `grand_rights_ind` (required for UK societies), `music_arrangement` and `lyric_adaptation` (required when version type is `MOD`), `recorded_indicator`, `text_music_relationship`, `composite_type`, `excerpt_type`, `duration` (mandatory for `SER`). These do not degrade gracefully — the file rejects.

**13 — Society codes as free strings.** The three-digit CISAC society codes are a controlled vocabulary. Lookup table and foreign key, not `String?`.

**14 — No merge strategy for parties without an IPI.** A nullable unique IPI permits unlimited duplicates of unregistered writers. Needs a `canonical_party_id` and an explicit merge path — because most new writers do not have an IPI yet, and onboarding them is the actual product.

---

## Programmatic licensing

The reason to build the artefact. Everything above is plumbing; this is what it unlocks.

### Why sync clearance still takes six weeks

Licensing a song needs two independent grants — the master and the composition. The master side is usually one phone call, because one label controls it. The composition side is not: a song with four writers routinely has four publishers, two administrators and a sub-publisher in the relevant territory, and nobody holds a complete, current picture of who controls what.

There is also a jurisdictional trap that makes this a data problem rather than a paperwork problem. In the **US**, any joint owner can grant a non-exclusive licence unilaterally, subject to a duty to account to the others. In the **UK** (CDPA 1988) and most of Europe, a joint work requires the consent of *all* owners. Whether you can grant instantly is therefore a function of the split table and the territory — which means it is computable, if the split table is trustworthy.

### Mandates, and the clearability calculation

Attach a **`Mandate`** to each interested party's credit: the rights they authorise INVOKE to grant, the territories, the use classes, a rate card or floor, and exclusions (no political, no gambling, no tobacco, no AI training). A mandate is a standing offer, expressed as data.

A licence request then becomes an evaluation, not a negotiation:

```
POST /licence-requests
  work_id, use_class, territory, term, media, exclusivity

→ clearability: {
    pr: { covered_bps: 10000, grantable: true },
    mr: { covered_bps: 10000, grantable: true },
    sr: { covered_bps:  8750, grantable: false,
          gaps: [{ party: "…", bps: 1250, reason: "no_mandate" }] },
    exclusions_triggered: [],
    one_stop: false,
    quote: { … }
  }
```

**100% mandated coverage in the requested right and territory, no exclusion triggered, a rate on file → bind the licence, take payment, emit the ledger entries.** Anything less → a quote plus an escalation naming the *specific* residual, which already beats "we'll get back to you."

That `one_stop` boolean is the product. Production music libraries have dominated commercial sync for decades on exactly one advantage: pre-cleared, one-stop rights. Not better songs — lower transaction cost. A works catalogue with complete mandates has the same property without giving up the copyright.

### Design notes

- **The licence is itself an artefact.** Signed, addressable, versioned, carrying the exact split state it was granted against. When a dispute arrives three years later, the licence carries its own evidence.
- **Most-favoured-nations clauses get modelled, not handled by email.** If one writer's rate is raised in a sync, MFN co-writers match automatically. It is a rule on the deal, and the most common source of after-the-fact adjustments.
- **AI training is a use class, not an edge case.** Enumerable and separately excludable per party, per territory, from the start.
- **Adopt DDEX MWL/MWN rather than inventing messages.** Musical Work Licensing and Notification already exist and are better than anything worth designing from scratch.
- **Settlement runs against the split as at usage date.** See correction 6. Every payout references an immutable snapshot.

---

## Architecture

Python, **FastAPI**, PostgreSQL. Pydantic models as the domain boundary; share and chain-of-title invariants enforced in the domain layer, not in route handlers.

```
GET    /works/{id}
POST   /works
GET    /works/{id}/credits
GET    /works/{id}/package            # the signed work package
GET    /works/{id}/clearability
GET    /interested-parties/{id}
POST   /agreements
POST   /registrations                 # generate + deliver CWR
POST   /registrations/ack             # ingest ACK, reconcile, surface conflicts
POST   /licence-requests
GET    /licences/{id}
GET    /royalties/statements/{id}
GET    /payouts/{id}
```

**Works registry** — canonical store for works, parties, agreements and splits, with per-right totals and chain-of-title completeness enforced as domain invariants.

**Work package builder** — assembles, hashes and signs the artefact described above.

**CWR engine** — generate conformant `NWR`/`REV` transactions from the internal model; parse and reconcile `ACK` files; surface `CO` conflicts as first-class objects rather than log lines.

**Licensing engine** — mandate evaluation, clearability, quoting, licence issuance.

**Settlement** — usage ingestion, matching, split application per right and territory, commission netting, auditable ledger, payouts.

---

## Design constraints

Learned from the graveyard above, and non-negotiable:

1. **Never require industry-wide adoption to be useful.** The artefact has to be valuable to one writer holding one song on day one.
2. **Speak the existing standards fluently — CWR, DDEX, ISWC, IPI, TIS.** Interoperate, don't replace. The replacements are the ones that died.
3. **The canonical copy stays with the rightsholder.** No central authority. Federate, verify, reconcile.
4. **Every assertion is attributable and reversible.** Provenance is append-only; conflicts are data, not errors.

---

## Status

Early. Public page live, data model in its second iteration, API in progress at [invoke-works](https://github.com/malimccalla/invoke-works). This repository stays the landing page and the design notes.

Contact: `mali@invoke.works`

---
