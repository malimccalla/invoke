# Conformance fixtures

Test documents for validators of the [`.work` format](../SPEC.md).

Rules are tiered by what is needed to decide them — **L1** structural, **L2** referential, **L3** external ([SPEC §8.1](../SPEC.md#81-levels)). A validator declares the highest level it implements, and an **L1 validator is conformant**.

A **conformant validator at level *n*** ([SPEC §9.3](../SPEC.md#93-conformant-validator)) MUST:

- accept every document under `valid/` reporting no `WORK-` violations
- reject every document under `invalid/` whose `level` is *n* or below, reporting **exactly** the rule identifiers listed against it in [manifest.json](manifest.json) — no more and no fewer
- report fixtures above its level as **unchecked**, never as passed

The "no more" half matters. A fixture is only useful if it isolates one defect. If a validator reports extra violations against `invalid/missing-pwr.work`, either the validator or the fixture is wrong. Where one mutation genuinely causes two violations — as in `shares-do-not-total.work` — the manifest lists both.

Valid fixtures carry a `max_level`. All of them are currently `2`: their signatures are illustrative and their blobs are not retrievable, so an L3 validator cannot check them and MUST NOT treat that as failure.

## Layout

```
manifest.json    every fixture, its level, and the rules each invalid one violates
valid/           documents that must pass
invalid/         documents that must fail, one defect each
```

Every invalid fixture names a `base` in the manifest and differs from it by a single mutation. Diff them to see the defect:

```
diff <(jq -S . valid/minimal.work) <(jq -S . invalid/missing-pwr.work)
```

## Coverage

`manifest.json` declares the intended corpus. The `todo` array names fixtures that are specified but not yet written, one per remaining validation rule, each tagged with its level.

**5 of 32 invalid fixtures written.** `cwr_profile_todo` covers the optional CWR projection profile ([SPEC §8.2](../SPEC.md#82-cwr-projection-profile)), which is reported under a `CWR-` prefix and is not required for `.work` conformance.

## Adding a fixture

1. Copy the nearest `valid/` document and introduce exactly one defect.
2. Add it to `manifest.json` under `invalid`, with its `base`, its `level`, the rule identifiers it violates, and a one-line description of the defect.
3. If it exercises a rule with no identifier in [SPEC §8](../SPEC.md#8-validation-rules), add the rule first. A fixture without a rule identifier is untestable.

Fixtures are published under Apache-2.0 and may be used freely to test any implementation.
