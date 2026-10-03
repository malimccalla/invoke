# `invoke:fp/fusion@1.0`

**Status: draft · All constants provisional**

How the channel scores combine into one number, and what each band of that number means. This document is not a fingerprint scheme — it produces no blob and appears in no `content` entry. It is the rule a matcher applies to the scores, and the place where a number becomes a decision about a person's copyright.

> **Every constant here is provisional.** The weights in §2 and the thresholds in §4 are reasoned, not measured, and reasoned thresholds on this problem are usually wrong. They are published so that two implementations behave identically and so that there is something specific to be falsified. A `benchmark.md` in this directory will replace them with values measured on Da-TACOS and SHS100K; until it exists, an implementation MUST report that its thresholds are unmeasured alongside any score it emits.

---

## 1. Inputs

A comparison between two works yields a score per channel, or no score where either side lacks the component. Channels are compared only within a scheme ([README §2](README.md#comparison-is-within-a-scheme-never-across)).

| Channel | Scheme | Present when |
| --- | --- | --- |
| `melodic` | [`melodic-ngram@1.0`](melodic-ngram-v1.md) | both works carry a melody fingerprint |
| `lyric` | [`lyric-shingle@1.0`](lyric-shingle-v1.md) | both carry a lyric fingerprint — never for instrumentals |
| `embedding` | [`cqt-embedding@1.0`](cqt-embedding-v1.md) | both carry an embedding under the same weight digest |
| `harmonic` | [`harmonic-ngram@1.0`](harmonic-ngram-v1.md) | both carry a harmony fingerprint |

**An absent channel is absent, not zero.** An instrumental has no lyric to match and has not failed to match one. Scoring absence as zero drags every instrumental's fused score down by the lyric weight and makes the threshold mean something different for instrumental repertoire than for vocal repertoire. Absent channels leave the sum.

Band scores from [`melodic-lsh@1.0`](melodic-ngram-v1.md#5-the-lsh-band-variant) MUST NOT be used as channel scores. They are a retrieval filter: they answer which pairs are worth comparing, and `s⁸` is not `s`.

## 2. Fusion

For the set `C` of present channels:

$$F = \frac{\sum_{c \in C} w_c \cdot s_c}{\sum_{c \in C} w_c}$$

| Channel | `w` |
| --- | --- |
| `melodic` | `0.40` |
| `lyric` | `0.35` |
| `embedding` | `0.20` |
| `harmonic` | `0.05` |

Normalising by the weights actually present is what keeps `F` on one scale as channels drop out, so that a threshold means the same thing for an instrumental as for a song.

Melody carries the most weight because melody plus lyric is what a musical work largely *is* as a matter of copyright, and because it is the channel a tribunal will recognise. Lyric is close behind and would be ahead on raw discriminative power, but it is zero across translation and absent across instrumentals, and a weighting that leaned on it would perform unevenly across repertoire. Embedding is capped at `0.20` despite being the most accurate channel in the literature, because it is unexplainable and provisional. Harmony is `0.05`, which is nearly nothing deliberately — see §3.

## 3. The harmonic rule

**A result MUST NOT clear any threshold in §4 on the harmonic channel alone.** Where `harmonic` is the only present channel, `F` is reported and the outcome is `none`, whatever the value.

Two unrelated twelve-bar blues match completely on harmony. So do two unrelated songs on `I–V–vi–IV`, which covers a great deal of everything released since 1960. A pipeline permitted to act on this channel alone will assert that two unrelated songs are one work, and will do it often. The weight of `0.05` makes harmony unable to carry a result on its own arithmetically; this rule makes it unable to as a matter of specification, so that no future reweighting quietly removes the protection.

## 4. Thresholds and outcomes

Apply in order; the first match wins.

| Condition | Outcome |
| --- | --- |
| `F ≥ 0.85` and at least two channels present, each at or above its floor in §5 | `candidate_same_work` |
| `F ≥ 0.60` and at least one channel at or above its floor | `shares_material` |
| otherwise | `none` |

`candidate_same_work` and `shares_material` are relations in [SPEC §7.11](../SPEC.md#711-work-relations) and are written into `related_works` with `method`, `score` and a producer attestation carrying `confidence`.

**The two-channel requirement is the load-bearing part.** A single channel at `0.90` is one transcription, one model and one set of failure modes agreeing with itself. Two independent channels agreeing is a much stronger statement than either of them alone, and the cost of the rule — missing works that carry only one usable component — is the right cost to pay.

### What a matcher MUST NOT do

- **Assert `same_work`.** The strongest relation a machine may assert is `candidate_same_work` ([SPEC §6.22](../SPEC.md#622-related-work-object), [WORK-075](../SPEC.md#8-validation-rules)). Promotion requires a party.
- **Append to `evidence`.** Deciding that a recording is evidence of an existing work is a judgement about which of two things is the work, and a similarity score does not contain it ([SPEC §6.5](../SPEC.md#65-evidence-object)).
- **Write a `derivation` entry.** `shares_material` records a resemblance. `derivation` carries a `disposition` — cleared, refused, de minimis, never asked — and every member of that vocabulary is a legal posture a person holds, not a measurement.
- **Modify a document it did not produce.** Including the one it matched against.
- **Suppress a result because it is inconvenient.** [SPEC §9.1](../SPEC.md#91-conformant-producer) forbids omitting a known dispute or an uncleared derivation to obtain a conformant file.

## 5. Channel floors

A channel at or below its floor is treated as not agreeing, whatever `F` says.

| Channel | Floor | Why there |
| --- | --- | --- |
| `melodic` | `0.55` | Jaccard over 12-grams falls off steeply with ornament; `0.55` is already a strong agreement on this channel, and the sketch's own standard error is `≈ 0.088`. |
| `lyric` | `0.70` | Shingles are near-unique, so genuine matches score high and anything middling is shared idiom. |
| `embedding` | `0.75` | Cosine in a trained space is compressed towards the top of its range; `0.75` is not a near-miss. |
| `harmonic` | `0.80` | High because the channel is cheap to satisfy by coincidence. Subject to §3 regardless. |

## 6. Routing the outcome

An outcome is a reason to ask a question. Which question depends on custody, which the matcher knows and the arithmetic does not.

```
                  outcome
                     │
        ┌────────────┼────────────┐
candidate_same_work  │      shares_material
        │            │            │
   same holder?      │      → related_works: shares_material
    │         │      │        → human review for a derivation posture
   yes        no     │
    │         │     none
    │         │      │
    │         │      └─ nothing is written
    │         │
    │         └─ related_works: candidate_same_work
    │            (one-sided; the other document is untouched)
    │
    └─ present to a party for confirmation.
       On confirmation, the second recording becomes
       an evidence entry on the existing work_id and
       the document gains a version. The matcher does
       not perform this; it asks.
```

The custody branch is the one that cannot be automated past. Where the same holder controls both, one work is one document and a second recording is an entry in `evidence` ([SPEC §6.5](../SPEC.md#65-evidence-object)) — but it is still a party who decides that the work did not change. Where the holders differ, nothing may be merged at all: the other document is somebody else's, and a `related_works` entry is an assertion about it and not a modification of it.

## 7. Reporting

A matcher emitting a result MUST carry, alongside `F`:

- every channel score, with its scheme identifier and version
- which channels were absent, distinguished from channels that scored low
- the `T` or duration value from each compared blob, so a short-sketch comparison is visible
- whether its thresholds are measured or provisional

A bare fused score is not reportable. `0.88` means one thing when melody and lyric both cleared their floors over full-length sketches and something else when it is a harmonic match on a forty-second fragment, and a reader given only the number cannot tell which — including the reader who is deciding whether to telephone somebody about their song.
