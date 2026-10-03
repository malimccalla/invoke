# `invoke:fp/cqt-embedding@1.0`

**Status: reserved — not yet implementable · Disclosure: `substantial` · Subrole: `embedding`**

> **This scheme is specified but cannot yet be implemented.** The weight digest in [§4](#4-the-model) is unpinned, and until it is, two implementations cannot produce comparable output. The identifier is reserved, the shape is fixed, and the document is published now so that the obligations it carries are visible before anyone depends on it. It appears in [example.work](../example.work) as an illustration of a fingerprint computed over a recording rather than a transcription.

A learned fixed-length embedding of a recording, compared by angle. The only scheme here that reaches the accuracy the published cover-identification literature reports, and the only one that is not implementable from its own specification.

---

## 1. Why this is awkward

Every other scheme in this directory is a procedure. You read it, you write it, you are interoperable. The cost of adoption is reading the document, which is the whole premise of the format ([README](../README.md#design-constraints), constraint 7).

This one is a procedure plus a 50 MB binary. The scheme is not the architecture — a differently-trained instance of the same architecture produces vectors in a different space that are not comparable at all. **The weights are the scheme.** Interoperating means every party resolving the identical file, which is a permanent dependency on an artefact remaining available, for the lifetime of every document that cites it. That is the objection [SPEC Appendix A question 6](../SPEC.md#appendix-a--open-questions) raises about the context IRI, with more force, because a context can be re-hosted from a copy in a repository and a lost weight file ends the scheme.

There are two further costs, and they should be stated rather than discovered.

**It is not explainable.** [melodic-ngram](melodic-ngram-v1.md) can say which twelve-note figures two works share. A cosine of `0.82` decomposes into nothing. In a dispute, the first is an exhibit and the second is an assertion, and the format exists to produce evidence.

**Its training corpus is a rights question.** A model trained on recordings to detect reuse of works is an `ai_training` use of every work in it ([SPEC §6.14](../SPEC.md#614-mandate-object)), and `ai_training` is separately grantable and separately refusable. A scheme in this format that was itself trained without consent would be a contradiction, and [§4](#4-the-model) requires the provenance to be stated.

It is specified anyway, because on reharmonised and heavily ornamented material it is the only thing that works, and refusing to name it would not stop people using one — it would only stop them agreeing on which.

## 2. Source

`computed_over` MUST name either a `content` component or, using the `evidence:` prefix from [SPEC §6.4](../SPEC.md#64-content-component-object), an `evidence` entry — typically `evidence:reference_recording`.

This is the reason that prefix exists. The scheme takes audio and emits a vector, producing no intermediate component to point at, so without a way to name the recording its provenance would be unstatable.

## 3. Preprocessing

1. Decode to mono by averaging channels.
2. Resample to `22050 Hz`, sinc interpolation, `−100 dB` stopband.
3. Constant-Q transform: `12` bins per octave, `84` bins, lowest centre `32.70 Hz` (C1), hop `512` samples.
4. Magnitude, then `log(1 + |X|)`.
5. Per-bin mean and variance normalisation across time.
6. Centre crop or zero-pad to `400` frames.

Step 3 is a CQT rather than a mel spectrogram because its bins are logarithmic in frequency, so transposition is a translation along the bin axis and a convolution can learn to be invariant to it. On a mel scale it is not, and the model would have to memorise every key separately.

## 4. The model

| | |
| --- | --- |
| Architecture | `TO BE PINNED` |
| Weight digest | `TO BE PINNED` — `sha256`, over the ONNX file |
| ONNX opset | `TO BE PINNED` |
| Output dimension | `256`, L2-normalised |
| Training corpus | `TO BE STATED`, with its consent basis |

A producer MUST NOT emit under this identifier until every row above is fixed, and MUST NOT emit under it using any other weights. A variant trained differently is a different scheme and takes a different identifier.

The weight digest is carried in the blob (§5) so that a mismatch is detectable at comparison time rather than appearing as an inexplicably poor score.

## 5. Layout

Big-endian throughout.

| Offset | Size | Field |
| --- | --- | --- |
| `0` | 4 | Magic, ASCII `IWFP` |
| `4` | 1 | Container version, `0x01` |
| `5` | 1 | Scheme id, `0x05` |
| `6` | 1 | Scheme major version, `0x01` |
| `7` | 1 | Scheme minor version, `0x00` |
| `8` | 2 | Dimension `D` — `0x0100` |
| `10` | 2 | Reserved, `0x0000` |
| `12` | 4 | Source duration in milliseconds |
| `16` | 32 | Weight digest, raw `sha256` bytes |
| `48` | `4D` | `v[0] … v[D-1]`, each a big-endian IEEE-754 binary32 |

Total `1072` bytes at `D = 256`.

## 6. Comparison

$$\mathrm{sim}(a, b) = \max\left(0,\ \sum_{i=0}^{D-1} a.v_i \cdot b.v_i\right)$$

Both vectors are L2-normalised, so the sum is the cosine. Range `0.0 … 1.0`, higher is more similar.

Negative cosines are clamped rather than rescaled. Mapping `[−1, 1]` onto `[0, 1]` would place unrelated pairs near `0.5`, and every threshold downstream would then have to know which convention produced the number.

A consumer MUST refuse the comparison when the magic, container version, scheme id, scheme major version, dimension or **weight digest** differ between the two blobs, or when either length is not `48 + 4D`. A differing weight digest is not a weak match; it is two incomparable spaces.

## 7. Undefined inputs

MUST NOT emit when the source is shorter than `10` seconds, when it decodes to digital silence, or when any weight-digest row in §4 is unfixed.

## 8. Disclosure

**`substantial`**, by the default in [SPEC §7.12](../SPEC.md#712-fingerprint-disclosure-classes).

Embeddings are often assumed opaque because they are not legible. They are not therefore one-way: inversion of audio embeddings is an active area, a published model gives an attacker both the encoder and the gradients, and a scheme that claimed `opaque` on the strength of the vector looking like noise would be claiming a property nobody has established. `256` floats is `8192` bits, which is not obviously too few to carry a recognisable likeness.

Downgrading requires an inversion study against the pinned weights, a new scheme version and a new identifier.

## 9. Known failure modes

| | |
| --- | --- |
| **Out-of-distribution material** | Accuracy outside the training distribution is unknown and may be poor without any signal that it is. A symbolic scheme degrades visibly; this one degrades silently. |
| **Unexplainable** | No decomposition. A score, and nothing to point at. |
| **Weight availability** | If the file becomes unresolvable, every document citing this identifier loses the ability to be compared. |
| **Learned shortcuts** | The model may key on production era or genre rather than on the work. Unfalsifiable from the output. |
| **Training provenance** | §4 requires the corpus and its consent basis to be stated. An unstated one is a reason not to adopt the scheme. |

## 10. Test vectors

Under `vectors/cqt-embedding-v1/` once §4 is fixed. Until then the directory holds only preprocessing vectors — CQT frames for a known input — which can be checked without the model and are where independent implementations diverge in practice.
