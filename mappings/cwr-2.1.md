# `.work` → CWR 2.1 rev 8 / 2.2

Registration is the projection that has to work, so this is the one specified first.

Not normative. See [SPEC §8.2](../SPEC.md#82-cwr-projection-profile) for the `CWR-` rules a document must satisfy before it will project, and [RATIONALE](../RATIONALE.md#cwr) for a worked `NWR` transaction.

## Transaction shape

```
HDR                                   sender credentials, account config
GRH  NWR
  NWR   ← identity
    SPU ← credits where cwr_record = SPU
      SPT ← that credit's territory_claims
    SWR ← credits where cwr_record = SWR
      SWT ← that credit's territory_claims
      PWR ← rights.publisher_for_writer
    OPU ← credits where cwr_record = OPU
    OWR ← credits where cwr_record = OWR
    ALT ← identity.alternative_titles
    VER ← derivation where relation_type = VER
    COM ← derivation where relation_type = COM
    REC ← evidence where isrc is non-null
GRT
TRL
```

## Field map

| CWR | `.work` | Note |
| --- | --- | --- |
| `NWR` Work Title | `identity.title` | 60 chars, `CWR-001` |
| `NWR` Submitter Work # | `identity.submitter_work_number` | 14 chars, `CWR-002`. **Not** `work_id` |
| `NWR` ISWC | `identity.iswc` | strip `T-`, dots and hyphen |
| `NWR` Language Code | `identity.language` | ISO 639-2/T → 639-1, `CWR-003` |
| `NWR` Duration | `identity.duration_ms` | truncate to `HHMMSS` |
| `NWR` Version Type | `identity.version_type` | |
| `NWR` Music Arrangement | `identity.music_arrangement` | `MOD` only |
| `NWR` Lyric Adaptation | `identity.lyric_adaptation` | `MOD` only |
| `NWR` Musical Work Distribution Category | `identity.distribution_category` | |
| `NWR` Text Music Relationship | `identity.text_music_relationship` | |
| `NWR` Composite Type | `identity.composite_type` | |
| `NWR` Excerpt Type | `identity.excerpt_type` | |
| `NWR` Recorded Indicator | `identity.recorded_indicator` | `Y`/`N` |
| `NWR` Grand Rights Ind | `identity.grand_rights_ind` | `Y`/`N`, required by UK societies |
| `SPU`/`OPU` Interested Party # | `rights.parties[].ipi_name_number` | `CWR-005` |
| `SPU`/`OPU` Publisher Type | `credits[].publisher_type` | `SE` is sub-publisher, `ES` is *substituted* |
| `SPU` Publisher Sequence # | `credits[].publisher_sequence` | |
| `SPU`/`SWR` PR/MR/SR Ownership Share | `credits[].ownership_bps` | `2500` → `02500`, no conversion |
| `SPU`/`SWR` PR/MR/SR Affiliation Society | `parties[].societies` | |
| `SPT`/`SWT` TIS Numeric Code | `territory_claims[].tis_code` | |
| `SPT`/`SWT` Inclusion/Exclusion Indicator | `territory_claims[].indicator` | |
| `SPT`/`SWT` PR/MR/SR Collection Share | `territory_claims[].collection_bps` | precedes the indicator in the record layout |
| `SWR`/`OWR` Writer Last/First Name | `parties[].last_name`, `.first_name` | natural persons only |
| `SWR`/`OWR` Writer Designation | `credits[].writer_designation` | |
| `PWR` Publisher IP # | the publisher credit named in `publisher_for_writer` | |
| `PWR` Writer IP # | the writer credit named in `publisher_for_writer` | |
| `PWR` Submitter Agreement # | `credits[].agreement_id` | |
| `ALT` Alternate Title | `alternative_titles[].title` | 60 chars, `CWR-004` |
| `ALT` Title Type | `alternative_titles[].cwr_title_type` | `TT` is translated; `TE` is first line of text |
| `VER` Original Work Title | `derivation[].parent_title` | |
| `VER` ISWC of Original Work | `derivation[].parent_iswc` | |
| `REC` ISRC | `evidence[].isrc` | |

## Header arithmetic

`HDR` Sender ID is nine characters; an IPI Name Number is eleven. A sender whose IPI exceeds nine digits puts the leading two digits in **Sender Type** and the remaining nine in **Sender ID**. So `00555000111` serialises as type `00`, id `555000111` — not as `PB` plus the whole number.

`HDR` also needs sender credentials and a transmission date, which are account configuration rather than work data. Each society gets its own file with its own recipient code, named `CWyynnnnsss_rrr.Vxx` and recorded in `registrations[].file`.

## `ACK` → `.work`

Acknowledgements reconcile on `identity.submitter_work_number`, which is why `work_id` cannot serve as the submitter work number.

| `ACK` | `.work` |
| --- | --- |
| Transaction Status | `registrations[].ack_status` |
| Creation Date/Time | `registrations[].ack_received_at` |
| Recipient Work # | `registrations[].society_work_code` |
| ISWC of Work | `registrations[].allocated_iswc` |
| `MSG` records | `registrations[].messages[]` |

A `CO` conflict is data. It is written into `registrations` and does not invalidate the document ([SPEC §6.17](../SPEC.md#617-registration-object)).

## What does not survive

Everything CWR needs is in a `.work` document. Much of a `.work` document has nowhere to go.

| | Home in CWR |
| --- | --- |
| `clearances` — a licence and its consideration | none. `CWR-006` reports it as lossy, not as an error |
| `derivation.disposition` — cleared vs refused vs never asked | none. `VER` records the link and not the posture |
| `derivation.affected_components` — *which* component derives | none |
| `disputes` — an infringement claim against the work | none |
| `mandates` — who has authorised what licensing | none |
| `clearability` — coverage in bps and the named gaps | none |
| `content` — melody, harmony, bassline, lyrics, score, fingerprints | none |
| `renders` and their consent coverage | none |
| `signatures`, `timestamps`, `provenance_log` | none |
| the version chain and per-component digest continuity | none |

The interpolation case is the sharpest of these. CWR offers `ORI`, which discards the derivation entirely, or `MOD` with a `VER` record, which tells every society that the work *is a version of* its parent and invites the parent's publisher to claim all of it. There is no third option, and the clearance that was actually paid for has nowhere to go at all.
