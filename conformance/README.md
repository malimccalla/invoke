# Conformance fixtures

Test documents for validators of the [`.work` format](../SPEC.md).

A **conformant validator** ([SPEC §9.3](../SPEC.md#9-conformance)) MUST:

- accept every document under `valid/` reporting no `WORK-` violations
- reject every document under `invalid/` reporting **exactly** the rule identifiers listed against it in [manifest.json](manifest.json) — no more and no fewer

The "no more" half matters. A fixture is only useful if it isolates one defect. If a validator reports extra violations against `invalid/missing-pwr.work`, either the validator or the fixture is wrong.

## Layout

```
manifest.json    every fixture, and the rules each invalid one violates
valid/           documents that must pass
invalid/         documents that must fail, one defect each
```

Each invalid fixture is `valid/minimal.work` with a single mutation. Diff them against it to see the defect:

```
diff <(jq -S . valid/minimal.work) <(jq -S . invalid/missing-pwr.work)
```

## Coverage

`manifest.json` declares the intended corpus. The `todo` array names fixtures that are specified but not yet written, one per remaining validation rule.

**3 of 23 invalid fixtures written.**

## Adding a fixture

1. Copy `valid/minimal.work` and introduce exactly one defect.
2. Add it to `manifest.json` under `invalid`, with the rule identifiers it violates and a one-line description of the defect.
3. If it exercises a rule with no identifier in [SPEC §8](../SPEC.md#8-validation-rules), add the rule first. A fixture without a rule identifier is untestable.

Fixtures are published under Apache-2.0 and may be used freely to test any implementation.
