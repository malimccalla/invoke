# `invoke:fp/lyric-shingle@1.0`

**Status: draft · Disclosure: `substantial` · Subrole: `lyric`**

A set sketch over word shingles. The strongest single indicator that two recordings are one work, and the one that fails completely on the cases the others handle.

---

## 1. Source

`computed_over` MUST name a component whose `role` is `lyrics`. The blob MUST be UTF-8 text. Timing, if the component carries it, is ignored.

## 2. Preprocessing

Applied in order.

1. **Normalise** to Unicode NFKC.
2. **Case-fold** using the full Unicode default case folding, not ASCII lowercasing. `İ` and `ß` are not special cases to be handled later.
3. **Strip** every character in the Unicode `P` (punctuation) and `S` (symbol) general categories, **except** `U+0027 APOSTROPHE` and `U+2019 RIGHT SINGLE QUOTATION MARK` where both neighbours are letters. `dont` and `don't` must not become different words, and `U+2019` must not survive where `U+0027` did not.
4. **Fold** `U+2019` to `U+0027` wherever it survives step 3.
5. **Split** on runs of Unicode whitespace. Discard empty tokens.
6. **Discard structural markers.** A token that, before step 3, matched `^\[.*\]$` or `^\(.*\)$` — `[Chorus]`, `(x2)` — is removed. These are an editor's annotations and are not in the work.

**No stopword removal and no stemming.** Both are standard in document retrieval and both are wrong here. The function words are where a lyric's rhythm lives, `"I"` and `"you"` carry more of a pop lyric's identity than its nouns do, and stemming would merge tenses that a writer chose between.

The result is `W` words `w₁ … W_W`.

## 3. Representation

Shingle width `w = 5`. The shingle set is

$$G = \{\, w_k \,\|\, \texttt{0x20} \,\|\, w_{k+1} \,\|\, \cdots \,\|\, w_{k+4}\ :\ k = 1 \ldots W-4 \,\}$$

each element the UTF-8 bytes of five consecutive words joined by single spaces, taken as a **set** — a chorus repeated eight times contributes its shingles once.

Five words rather than the twelve tokens used for melody, because natural language has far more entropy per symbol: a five-word English shingle is already close to unique, while a five-note figure is not. Five also survives a mis-transcribed word better than a longer window, which matters because the input is usually a machine transcript.

Dropout as [melodic-ngram-v1 §3.5](melodic-ngram-v1.md#35-deterministic-dropout): discard `g` where `h(0x00 ‖ g) mod 100 < 15`.

## 4. Layout and comparison

MinHash with `K = 128` exactly as [melodic-ngram-v1 §4.1](melodic-ngram-v1.md#41-minhash-signature). Byte layout as [§4.2](melodic-ngram-v1.md#42-bytes) with scheme id `0x04`, `n = 5`, `T = W`, total `1040` bytes.

Comparison as [§4.3](melodic-ngram-v1.md#43-comparison), with the same refusal conditions. A consumer SHOULD attach reduced weight where `T < 40`.

## 5. Undefined inputs

MUST NOT emit when `W < 5`, when `G′` is empty, or when the source component's `role` is not `lyrics`. An instrumental work has no lyrics component and therefore no entry — which is the absence of a signal, not a score of zero, and [fusion-v1](fusion-v1.md) treats it accordingly.

## 6. Disclosure

**`substantial`**, and here the default is not merely cautious. Five-word English shingles are drawn from a space with far less effective entropy than the alphabet size suggests, overlapping shingles chain back into running text trivially, and a language model is an extremely effective prior for an adversary reconstructing from partial recovery.

Treat a published lyric shingle sketch as approximately publishing the lyric. Where that is not acceptable, do not publish this channel — there is no parameter that makes it safe, and a scheme document that implied otherwise would be the more dangerous artefact.

## 7. Known failure modes

| | |
| --- | --- |
| **Translation** | A translated lyric shares no shingles. The clearest case where a correct same-work relationship scores zero here, and precisely the case [SPEC §6.5](../SPEC.md#65-evidence-object) treats as a *new* work carrying a derivation — so the two disagree only in appearance. |
| **Instrumentals** | No input. See §5. |
| **Transcription error** | Each mis-heard word destroys up to five shingles. Machine transcripts of dense or accented material degrade this channel badly. |
| **Common phrasing** | `"i don't want to be"` is in a great many songs. Low-count matches over idiomatic phrases are noise. |
| **Interpolated lyric** | A quoted line produces a handful of shared shingles against a very large union, so Jaccard stays near zero. This channel detects shared *works*, not shared *lines*; a lyric interpolation is a `derivation` question and `matched_components` on the lyrics component, not a high score here. |
| **Covers with altered lyrics** | Pronoun and gender swaps break every shingle they touch. |

## 8. Test vectors

Under `vectors/lyric-shingle-v1/`, covering NFKC normalisation, full case folding on `İ` and `ß`, apostrophe handling in both codepoints and at word boundaries, structural marker removal, and the minimum viable input at `W = 5`.
