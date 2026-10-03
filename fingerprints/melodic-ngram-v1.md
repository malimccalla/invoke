# `invoke:fp/melodic-ngram@1.0`

**Status: draft · Disclosure: `substantial` · Subrole: `melodic`**

A set sketch over short melodic figures, transposition-invariant and tempo-invariant by construction. This is the baseline scheme: it is specified so that it can be implemented from this document alone, and it is the one an implementation supporting exactly one scheme should support.

The companion band scheme [`invoke:fp/melodic-lsh@1.0`](#5-the-lsh-band-variant) is defined in §5 and shares every step up to §4.

---

## 1. Source

`computed_over` MUST name a component whose `role` is `melody`, resolved per [SPEC §6.4](../SPEC.md#64-content-component-object). The blob MUST be a MIDI file or any representation from which an ordered sequence of `(onset, pitch, duration)` triples can be recovered without inference.

The scheme operates on note events, not audio. Where the melody was transcribed from a recording, the transcription is a separate component with its own digest, its own `derived: true` and its own provenance entry. The fingerprint is computed over the transcription and inherits the transcription's errors — see [§8](#8-known-failure-modes).

## 2. Preprocessing

Applied in order. Every constant is fixed by this document.

1. **Collect note events.** Each is `(onset, pitch, duration)` with `onset` and `duration` in seconds as IEEE-754 doubles and `pitch` an integer MIDI note number in `0..127`.
2. **Reduce to monophony.** Sort by `onset` ascending, then `pitch` descending. Walk the sequence; where a note's onset falls before the previous retained note's offset, retain whichever has the higher pitch and discard the other outright. Do not truncate — a truncated note has a duration the source never contained.
3. **Merge repeated pitches.** Where two consecutive retained notes have equal `pitch` and the gap between the first's offset and the second's onset is below `25 ms`, merge them into one note spanning both. This removes articulation artefacts that transcription introduces and performance does not.
4. **Drop notes shorter than `40 ms`.** Below this, transcribers emit spurious events at a rate that swamps the signal.
5. **Order and index.** The result is `N` notes `n₁ … n_N` ordered by onset. Ties cannot remain after step 2.

No key detection, no beat tracking and no tempo estimation is performed at any point. Both invariances fall out of the representation in §3, and a scheme that does not estimate key cannot estimate it wrongly.

## 3. Representation

### 3.1 Interval class

For `k` in `1 … N-1`:

$$i_k = \mathrm{clamp}(\mathrm{pitch}(n_{k+1}) - \mathrm{pitch}(n_k),\ -12,\ +12)$$

Twenty-five values. Intervals are differences, so transposing the melody by any number of semitones leaves every `iₖ` unchanged — transposition invariance costs nothing and requires no key to be detected. Clamping folds octave-and-larger leaps together, which loses the distinction between a tenth and a seventeenth and keeps the sketch from being dominated by octave displacement choices made by an arranger.

### 3.2 Duration class

Let `IOIₖ = onset(n_{k+1}) − onset(n_k)`. For `k` in `1 … N-2`:

$$r_k = \frac{\mathrm{IOI}_{k+1}}{\mathrm{IOI}_k}$$

Classify `rₖ` into seven values by strict comparison against six fixed thresholds, in order:

| `dₖ` | Condition |
| --- | --- |
| `-3` | `r < 0.42044820762685725` |
| `-2` | `r < 0.59460355750136053` |
| `-1` | `r < 0.84089641525371454` |
| `0` | `r < 1.18920711500272107` |
| `1` | `r < 1.68179283050742909` |
| `2` | `r < 2.37841423000544171` |
| `3` | otherwise |

The thresholds are the midpoints of a half-octave grid in log space — `2^((2c+1)/4)` for `c = -3 … 2` — and they are written out rather than computed deliberately. An earlier draft specified `clamp(round(2 log₂ r), -3, 3)`, which partitions the line identically and decides the partition by a rounding operation whose behaviour at exactly `.5` differs between languages, applied to a value carrying the accumulated error of `log₂`. A ratio of `2^0.25` is a boundary case that two correct implementations can straddle. Explicit constants and strict `<` are decidable identically everywhere, and an implementation MUST NOT substitute the logarithmic form.

A ratio is scale-free, so doubling the tempo of the whole melody leaves every `dₖ` unchanged, and no beat grid is needed to obtain that. Quantising to seven classes at half-octave resolution absorbs the expressive timing that would otherwise make two performances of one phrase disagree on every token.

Where `IOIₖ` is zero the ratio is undefined; step 2 of §2 makes this unreachable, and an implementation encountering it MUST fail rather than substitute a value.

### 3.3 Token

For `k` in `1 … N-2`:

$$t_k = (i_k + 12) \times 7 + (d_k + 3)$$

A token is an integer in `0 … 174`, encoded as a single unsigned byte. The alphabet is 175 symbols and the sequence has `T = N − 2` of them.

### 3.4 n-gram

`n = 12`. The n-gram set is

$$G = \{\, t_k \,\|\, t_{k+1} \,\|\, \cdots \,\|\, t_{k+11} \ :\ k = 1 \ldots T-11 \,\}$$

each element a 12-byte string. `G` is a **set**: a figure repeated identically throughout a song contributes one element, not one per repetition, which is what keeps a loop-based arrangement from drowning out everything else in it.

Twelve is chosen against disclosure rather than against accuracy. The space of 12-grams is `175¹² ≈ 2.4 × 10²⁶`, which is not enumerable; at `n = 5` it is `175⁵ ≈ 1.6 × 10¹¹`, which is a table an adversary builds once. Overlapping n-grams chain back into the contour they were taken from in the manner of a de Bruijn graph, so a short `n` publishes the melody. Twelve costs recall on short figures — see [§8](#8-known-failure-modes) — and that is the trade this scheme makes deliberately.

### 3.5 Deterministic dropout

Let `h(x)` be the first 8 bytes of `SHA-256(x)` read big-endian as an unsigned 64-bit integer. Discard every element `g ∈ G` for which

$$h(\texttt{0x00} \,\|\, g) \bmod 100 < 15$$

Call the survivors `G′`.

**Dropout is a function of the element, not of the producer, so two parties drop the same n-grams.** Writing `K` for the kept universe, `G′ = G ∩ K` on both sides, and the estimator is unbiased:

$$\mathbb{E}\left[\frac{|A \cap B \cap K|}{|(A \cup B) \cap K|}\right] = \frac{|A \cap B|}{|A \cup B|}$$

Variance rises by roughly `1/0.85`, which at `K = 128` permutations is immaterial. The 15% that never enters the sketch is 15% that no attack against the sketch can recover, bought at almost no cost to matching. An implementation MUST NOT use a random or seeded-per-producer dropout: it would be unbiased too, and the two parties would be sketching different sets.

## 4. Layout

### 4.1 MinHash signature

`K = 128` permutations. For `j` in `0 … 127`, with `LE64(j)` the little-endian encoding of `j` as eight bytes:

$$h_j(g) = \text{first 8 bytes of } \mathrm{SHA\text{-}256}\big(\mathrm{LE64}(j) \,\|\, g\big) \text{ as a big-endian } \mathrm{u}64$$

$$\mathrm{sig}[j] = \min_{g \in G'} h_j(g)$$

SHA-256 rather than a permutation family over a prime field, because every language has it, nobody has to agree on a modulus, and the cost is irrelevant beside the transcription that produced the input.

### 4.2 Bytes

All multi-byte fields are big-endian.

| Offset | Size | Field |
| --- | --- | --- |
| `0` | 4 | Magic, ASCII `IWFP` |
| `4` | 1 | Container version, `0x01` |
| `5` | 1 | Scheme id, `0x01` |
| `6` | 1 | Scheme major version, `0x01` |
| `7` | 1 | Scheme minor version, `0x00` |
| `8` | 2 | `K`, permutation count — `0x0080` |
| `10` | 2 | `n`, n-gram length — `0x000C` |
| `12` | 4 | `T`, token count before n-gramming |
| `16` | `8K` | `sig[0] … sig[K-1]`, each a big-endian u64 |

Total `1040` bytes at `K = 128`. The blob is stored at its own digest like any other component and referenced from `content[]`.

`T` is carried because it is the one piece of context a comparison needs and cannot recover: a sketch over 40 tokens and a sketch over 4000 are not equally trustworthy, and §4.3 uses it.

### 4.3 Comparison

For two blobs `a` and `b` of this scheme and version:

$$\mathrm{sim}(a, b) = \frac{1}{K}\left|\{\, j : a.\mathrm{sig}[j] = b.\mathrm{sig}[j] \,\}\right|$$

Range `0.0 … 1.0`, higher is more similar. This estimates the Jaccard coefficient of `G′ₐ` and `G′_b` with standard error `≈ 1/√K ≈ 0.088`, which is the resolution of the scheme and the reason [fusion-v1](fusion-v1.md) does not distinguish between scores two hundredths apart.

A consumer MUST refuse the comparison, rather than returning a number, when:

- the magic, container version, scheme id or scheme major version differ between the two blobs, or from this document
- either `K` or `n` differs between the two blobs
- either blob's length is not `16 + 8K`

A consumer SHOULD attach reduced weight where either `T` is below `60`, and MUST NOT report a bare similarity figure over a short sketch as though it were comparable to one over a full song.

## 5. The LSH band variant

`invoke:fp/melodic-lsh@1.0` — **disclosure `opaque`** — exists to make candidate retrieval possible without publishing §4.

Everything through §4.1 is identical. Partition `sig` into `B = 16` bands of `R = 8` consecutive values. For band `b`:

$$\mathrm{band}[b] = \text{first 8 bytes of } \mathrm{SHA\text{-}256}\big(\texttt{0x01} \,\|\, \mathrm{LE64}(b) \,\|\, \mathrm{sig}[8b] \,\|\, \cdots \,\|\, \mathrm{sig}[8b{+}7]\big)$$

Layout as §4.2 with scheme id `0x02` and `16` big-endian u64 band digests in place of the signature — `144` bytes.

Comparison is collision counting: the number of positions `b` where `band_a[b] = band_b[b]`, divided by `B`. Two sketches with Jaccard `s` collide in a given band with probability `s⁸`, so the expected band score is `s⁸`. This is a retrieval filter and not a similarity measure: it is near-useless at distinguishing `0.4` from `0.6` and very good at discarding the ninety-nine per cent of a catalogue that is nowhere near. A consumer MUST NOT substitute a band score for §4.3 in [fusion-v1](fusion-v1.md).

**Disclosure analysis.** The published artefact is `16 × 64 = 1024` bits, and it is the image of a 128-element signature over an n-gram set of typically `10³`–`10⁴` elements drawn from a space of `175¹²`. Each band digest is a one-way function of eight u64 values and is published without them. No melody is recoverable because no melody is encoded: the argument is from information content and does not depend on the strength of any attack, which is why this scheme can claim `opaque` without an inversion study while §4 cannot.

## 6. Undefined inputs

A producer MUST NOT emit a fingerprint under this scheme when:

- `N < 14` after §2, so that `T < 12` and `G` is empty
- `G′` is empty after dropout
- any `IOIₖ` is zero
- the source component's `role` is not `melody`

In each case the correct behaviour is to emit no fingerprint entry at all. A sketch over an empty set is a well-formed blob that matches everything, and is worse than its absence.

## 7. Disclosure

**`substantial`, by the default in [SPEC §7.12](../SPEC.md#712-fingerprint-disclosure-classes).**

No inversion study has been performed against §4, so the honest class is the pessimistic one. The structural facts are these, and they are an argument for expecting better rather than a substitute for measuring it: `n = 12` puts exhaustive enumeration out of reach; the 15% dropout removes chain links an adversary reassembling overlapping n-grams would need; and the MinHash is a 128-element summary of a set of thousands, so most of what entered it is not present in the output.

Against that, an adversary holding a *candidate* melody can test it cheaply by sketching it and comparing. Confirmation is far easier than reconstruction, and `substantial` is the right class until somebody has tried to invert it and published how far they got. Lowering this class requires that study, a new scheme version and a new identifier.

`invoke:fp/melodic-lsh@1.0` is `opaque` on the counting argument in §5 and does not depend on this.

## 8. Known failure modes

| | |
| --- | --- |
| **Transcription error** | The scheme inherits every error in the melody component. A dense mix yields a noisy `f0`, and this is the dominant source of false negatives — not the sketch. |
| **Melisma and ornament** | A soul or gospel vocal fragments one notional note into many. Intervals and inter-onset ratios both change, and a correct match can fall below any threshold. The most common false negative on real repertoire. |
| **Short figures** | `n = 12` means a hook shorter than fourteen notes contributes nothing. A work whose melody is a four-note motif repeated is invisible to this scheme. |
| **Octave displacement** | Clamping at `±12` folds a tenth into an octave. Two arrangements differing only by register mostly agree; they do not agree exactly. |
| **Shared idiom** | Scalar and arpeggiated figures are common property. High similarity over a handful of n-grams within one idiom is not evidence of anything, which is why [fusion-v1](fusion-v1.md) will not act on this channel alone. |
| **Instrumentals and non-melodic works** | No melody component, no fingerprint. Silence, not a low score. |

## 9. Test vectors

Under `vectors/melodic-ngram-v1/`. Each case gives an input note sequence as JSON and the expected blob as hexadecimal, and the set is chosen to separate a correct implementation from a plausible one: monophonic reduction with overlaps, the `25 ms` merge boundary, the `40 ms` floor, `round` at exactly `±0.5`, clamping at both ends of both ranges, an n-gram landing on the dropout boundary, and the minimum viable input at `N = 14`.

An implementation that reproduces every vector byte for byte interoperates. One that reproduces most of them does not, and will fail in a way that looks like a weak match rather than like a bug.
