# `invoke:fp/harmonic-ngram@1.0`

**Status: draft · Disclosure: `substantial` · Subrole: `harmonic`**

A set sketch over short chord progressions, transposition-invariant by construction. **This channel is corroboration and never evidence on its own** — see [§7](#7-known-failure-modes) and the hard rule in [fusion-v1](fusion-v1.md#3-the-harmonic-rule).

---

## 1. Source

`computed_over` MUST name a component whose `role` is `harmony`. The blob MUST be a JSON array of chord events, each an object with `onset` (seconds, number), `root` (integer pitch class `0..11`, where `0` is C) and `quality` (string).

## 2. Preprocessing

1. Sort by `onset` ascending. Two chords with equal onset is an error; fail rather than choose.
2. Collapse consecutive runs of identical `(root, quality)` into one event. A chord held for sixteen bars and a chord struck on every beat for sixteen bars are the same progression.
3. Map each `quality` onto the eight-member alphabet in §3.2. An unmappable quality maps to its underlying triad; a quality with no triad is an error.

The result is `M` chord events.

## 3. Representation

### 3.1 Root interval

For `k` in `1 … M-1`:

$$\rho_k = \big(\mathrm{root}(c_{k+1}) - \mathrm{root}(c_k)\big) \bmod 12$$

Twelve values. **No key is detected at any point.** An earlier design expressed chords as Roman numerals relative to a detected key, which is transposition-invariant only when the key detector is right, and key detection on modal or chromatic material is wrong often enough to matter. Root intervals are invariant whether or not anyone knows the key, and a scheme that never estimates the key cannot estimate it wrongly.

### 3.2 Quality

| Code | Quality |
| --- | --- |
| `0` | major triad |
| `1` | minor triad |
| `2` | dominant seventh |
| `3` | major seventh |
| `4` | minor seventh |
| `5` | diminished, including half-diminished |
| `6` | augmented |
| `7` | suspended, second or fourth |

Extensions above the seventh are discarded. A thirteenth and a dominant seventh are one symbol here, because the difference between them is an arranger's and not a writer's.

### 3.3 Token and n-gram

$$\tau_k = \rho_k \times 8 + \mathrm{quality}(c_{k+1})$$

An integer in `0 … 95`, one unsigned byte. With `T = M − 1` tokens and `n = 8`, the n-gram set `G` is every window of eight consecutive tokens, taken as a set.

`n = 8` rather than the twelve used for melody, because progressions are short and repetitive and a twelve-window matches almost nothing. The cost is paid in disclosure: `96⁸ ≈ 7.2 × 10¹⁵` is large but not comfortably beyond a determined adversary, and progressions are drawn from a far smaller effective space than the alphabet suggests. This is one reason the channel is capped in fusion.

### 3.4 Dropout

As [melodic-ngram-v1 §3.5](melodic-ngram-v1.md#35-deterministic-dropout): discard `g` where `h(0x00 ‖ g) mod 100 < 15`, with `h` the first eight bytes of SHA-256 read big-endian.

## 4. Layout and comparison

MinHash with `K = 128` exactly as [melodic-ngram-v1 §4.1](melodic-ngram-v1.md#41-minhash-signature). Byte layout as [§4.2](melodic-ngram-v1.md#42-bytes) with scheme id `0x03`, `n = 8`, total `1040` bytes.

Comparison as [§4.3](melodic-ngram-v1.md#43-comparison): the fraction of the `128` positions at which the signatures agree, range `0.0 … 1.0`, higher more similar, with the same refusal conditions.

## 5. Undefined inputs

MUST NOT emit when `M < 9`, when `G′` is empty, when two chords share an onset, or when the source component's `role` is not `harmony`.

## 6. Disclosure

**`substantial`**, by the default in [SPEC §7.12](../SPEC.md#712-fingerprint-disclosure-classes). No inversion study has been performed, and the small effective alphabet makes this channel a worse candidate for a later downgrade than the melodic one.

## 7. Known failure modes

**The channel is not discriminative, and this is a property of music rather than of the scheme.** Two unrelated twelve-bar blues share a progression completely and will score near `1.0`. So will two unrelated songs on `I–V–vi–IV`, which is a substantial fraction of everything released since 1960. A high harmonic score between two works is the expected outcome for a great many pairs that have nothing to do with each other.

It is kept because the converse is informative. Where a melodic or lyric match is already present, agreement here raises confidence that the match is structural rather than coincidental; disagreement is a reason to look harder at a match that otherwise looked clean. A signal that is weak alone and useful in combination is worth carrying, provided nothing is ever allowed to act on it alone.

| | |
| --- | --- |
| **Reharmonisation** | A jazz reading of a pop tune shares a melody and almost no root motion. False negative. |
| **Chord-detection error** | Inherited wholesale from the harmony component, which is less reliable than melody transcription on dense material. |
| **Modal and static harmony** | A drone or a one-chord vamp produces almost no tokens and falls under §5. |
| **Substitution** | Tritone and relative-minor substitutions change `ρ` and are invisible as relationships. |

## 8. Test vectors

Under `vectors/harmonic-ngram-v1/`, covering the collapse in §2.2, quality mapping including the extension-discard and diminished-folding cases, the `mod 12` wrap at the octave, and the minimum viable input at `M = 9`.
