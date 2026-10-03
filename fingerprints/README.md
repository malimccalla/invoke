# Fingerprint schemes

A fingerprint is a lossy perceptual encoding of one component of a work, published so that two parties can compute similarity without either holding the other's repertoire. [SPEC §6.4](../SPEC.md#64-content-component-object) defines where one lives in a document. This directory defines what the bytes mean.

**These documents are normative for the schemes they name, and are versioned independently of [SPEC.md](../SPEC.md).** A new scheme is a new file here, not a specification revision. A scheme already published is immutable: a change to its preprocessing, layout, comparison function or disclosure class is a new version with a new identifier, because two parties running `@1.0` must produce comparable output forever.

---

## Why this exists at all

Audio fingerprinting is a solved problem and solves a different one.

Chromaprint and its relatives hash pairs of spectral peaks into landmarks and match them by exact lookup with time-offset voting. That buys invariance to codec, bitrate, equalisation, noise and clipping — everything that happens to a file between a master and a listener. It buys no invariance whatsoever to a different performance. A live take by the same band on the same night shares close to nothing with the studio master. This is the design goal, not a defect: the scheme identifies a recording.

A work is not a recording. Two recordings of one song may share no spectral content at all, and the thing that persists between them is structural — a sequence of intervals, a progression, a lyric. So a work fingerprint must be invariant to:

| | |
| --- | --- |
| Key, transposition | yes |
| Tempo | yes |
| Instrumentation, production, timbre | yes |
| Singer, register | yes |
| Section order, added or dropped sections | partially — local matching, not global |
| Reharmonisation | partially |
| Lyrics | **no.** A shared lyric is among the strongest signals that two recordings are one work |

And it must discriminate, which is the harder half. Two unrelated twelve-bar blues share a progression entirely. Any scheme that matches on harmony alone will eventually assert that they are the same song, and the cost of that error is somebody's copyright.

No single channel is both invariant and discriminative. That is why there are several schemes here and a [fusion rule](fusion-v1.md) over them, rather than one fingerprint.

---

## The registry

| Identifier | Channel | `subrole` | Comparison | Disclosure |
| --- | --- | --- | --- | --- |
| [`invoke:fp/melodic-ngram@1.0`](melodic-ngram-v1.md) | melody | `melodic` | estimated Jaccard | `substantial` |
| [`invoke:fp/melodic-lsh@1.0`](melodic-ngram-v1.md#5-the-lsh-band-variant) | melody | `melodic` | band collision | `opaque` |
| [`invoke:fp/harmonic-ngram@1.0`](harmonic-ngram-v1.md) | harmony | `harmonic` | estimated Jaccard | `substantial` |
| [`invoke:fp/lyric-shingle@1.0`](lyric-shingle-v1.md) | lyrics | `lyric` | estimated Jaccard | `substantial` |
| [`invoke:fp/cqt-embedding@1.0`](cqt-embedding-v1.md) | audio | `embedding` | cosine | `substantial` |

`invoke:fp/melodic-ngram@1.0` is the **baseline**. It is specified so that it can be implemented from this directory and nothing else — no model weights, no training corpus, no network. An implementation that supports exactly one scheme SHOULD support that one, because a scheme nobody else runs is a scheme that matches nothing.

The same channel MAY carry several schemes in one document. [WORK-020](../SPEC.md#8-validation-rules) keys fingerprint uniqueness on `algorithm` for exactly that reason.

---

## 1. The identifier grammar

An `algorithm` value MUST match the producer grammar in [SPEC §6.16](../SPEC.md#616-attestation-object):

```
identifier  = scheme ":" path "@" version
scheme      = 1*( ALPHA / DIGIT / "-" )          ; no colon
path        = 1*( ALPHA / DIGIT / "-" / "/" / "." )
version     = 1*( ALPHA / DIGIT / "-" / "." )
```

Schemes published here use the `invoke` scheme and an `fp/` path prefix. **Anyone may publish a scheme under their own scheme name without asking.** There is no registry to join and no identifier to reserve; `scheme` is expected to be a name its publisher controls, in the same spirit as `ext` namespaces ([SPEC §6.20](../SPEC.md#620-extension-object)).

`version` is the scheme's version, not the implementation's. Two implementations of `@1.0` MUST agree byte for byte on the test vectors.

---

## 2. The comparison contract

Every scheme document in this directory MUST specify all nine of the following. A document missing any of them does not name a scheme; it describes one, which is not the same thing and is not enough to interoperate.

1. **Source** — the component the fingerprint is computed over, as a reference resolvable by `computed_over`.
2. **Preprocessing** — every transformation from the source bytes to the symbolic representation, in order, with all constants fixed.
3. **Representation** — the exact symbolic form, with its alphabet and its encoding to integers.
4. **Layout** — the byte layout of the emitted blob, including endianness and every header field.
5. **Comparison** — a function over two blobs of this scheme returning a number, with its range and its orientation (whether higher means more similar).
6. **Undefined inputs** — the conditions under which the scheme MUST NOT emit a fingerprint, rather than emitting a degenerate one.
7. **Disclosure** — a class from [SPEC §7.12](../SPEC.md#712-fingerprint-disclosure-classes), *and the analysis supporting it*.
8. **Known failure modes** — the cases where the scheme is known to be wrong, named explicitly.
9. **Test vectors** — under [`vectors/`](vectors/), sufficient to distinguish a correct implementation from a plausible one.

Points 5 and 6 are the ones previous attempts at this have left out, and they are the ones that decide whether two implementations agree.

### Comparison is within a scheme, never across

There is no defined comparison between a `melodic-ngram` sketch and a `cqt-embedding` vector, and there will not be one. They are not the same kind of object: one is a set sketch compared by Jaccard, the other a point in a learned space compared by angle. A consumer MUST NOT compare blobs whose `algorithm` values differ, including across versions of the same scheme, and MUST treat a differing `algorithm` as "not comparable" rather than as a score of zero. Scoring it zero would report two identical works as maximally dissimilar.

This is the standing limitation of the whole approach, and it is recorded as [open question 7](../SPEC.md#appendix-a--open-questions).

---

## 3. Disclosure is a claim, and it needs an argument

[SPEC §7.12](../SPEC.md#712-fingerprint-disclosure-classes) grades what someone holding only the fingerprint can recover. A scheme document MUST state its class and MUST state the analysis behind it. Two kinds of analysis count:

- **An argument from information content.** `melodic-lsh` emits 64 bits per band. The thing behind it is a 128-element signature over a set of thousands of n-grams. The map is not injective by an enormous margin, and no attack recovers what was never encoded. This kind of argument is available on the day a scheme is written.
- **An attempted inversion.** Build the best reconstruction you can from the published artefact, measure how close it gets, publish both the method and the result. This is the only way to justify anything better than `substantial` for a scheme that does encode its input richly.

**A scheme published without either MUST declare `substantial`.** Three of the five schemes above do, which is not a failure of the schemes — it is what has actually been established about them so far. Lowering a class later requires the inversion study, a new scheme version and a new identifier. Documents already published keep the class they were published under, because their holders agreed to that class and cannot be made to agree to another one retroactively.

> The earlier draft of [SPEC §6.4](../SPEC.md#64-content-component-object) required that the source "cannot be reconstructed" from a fingerprint. Nothing in this directory satisfies that, and nothing in this class of scheme can. It is replaced by a graded claim because a requirement every implementation violates teaches implementers that the normative language is ornamental, and they are then right to ignore the requirements that matter.

---

## 4. What a score is

A comparison function returns a number. The number is evidence that two things resemble each other.

It is not a finding of substantial similarity, it is not a legal conclusion, and it is not authority to merge two works. [SPEC §6.22](../SPEC.md#622-related-work-object) holds the line in the object model: a machine may assert `candidate_same_work` and nothing stronger, and promotion requires a party. This directory holds the same line in the arithmetic. Every threshold in [fusion-v1](fusion-v1.md) is a threshold for *raising a question with a person*, and none of them is a threshold for acting.

---

## 5. Files

| | |
| --- | --- |
| [melodic-ngram-v1.md](melodic-ngram-v1.md) | The baseline. Interval and inter-onset-ratio n-grams, MinHash, LSH bands. |
| [harmonic-ngram-v1.md](harmonic-ngram-v1.md) | Key-relative chord n-grams. Corroboration only. |
| [lyric-shingle-v1.md](lyric-shingle-v1.md) | Normalised word shingles. |
| [cqt-embedding-v1.md](cqt-embedding-v1.md) | Learned embedding over constant-Q. Optional; carries a binary dependency. |
| [fusion-v1.md](fusion-v1.md) | How channels combine, and what each band of the result means. |
| [vectors/](vectors/) | Test vectors. Two implementations that disagree here are not interoperable. |

## Licence

As the specification: text under [CC BY 4.0](../LICENSE-DOCS), vectors under [Apache-2.0](../LICENSE). No patent has been or will be sought on any scheme described here.
