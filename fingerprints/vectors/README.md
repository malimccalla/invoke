# Test vectors

Vectors for the schemes in [../](../). Each scheme directory holds cases as

```
<case>.json   the input, in the form that scheme's §1 defines
<case>.hex    the expected blob, lowercase hexadecimal, no whitespace
```

A conformant implementation reproduces every `.hex` **byte for byte**. Partial agreement is not partial conformance: a scheme that differs in one quantisation boundary produces a signature that shares no minima with a correct one, so the failure presents as a weak match between two identical works rather than as an error. That is the failure these vectors exist to catch, and it is invisible without them.

## Status

Not yet written. [melodic-ngram-v1 §9](../melodic-ngram-v1.md#9-test-vectors), [harmonic-ngram-v1 §8](../harmonic-ngram-v1.md#8-test-vectors) and [lyric-shingle-v1 §8](../lyric-shingle-v1.md#8-test-vectors) each name the cases their directory must contain. [cqt-embedding-v1](../cqt-embedding-v1.md) can carry only preprocessing vectors until its weights are pinned.

Until these exist, the schemes are specified and unverified, and two implementations agreeing is a hope rather than a fact.
