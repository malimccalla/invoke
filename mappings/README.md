# Crosswalks

Field-level mappings from a `.work` document into other formats, and from other formats into it.

None of this is normative. [SPEC.md](../SPEC.md) is the specification; these files record how a document is expected to project, and where the projection loses information.

| | Direction | Status |
| --- | --- | --- |
| [cwr-2.1.md](cwr-2.1.md) | `.work` → CWR `NWR`/`REV`, and `ACK` → `.work` | drafted |
| [sourcelume.md](sourcelume.md) | `.work` → Apache Sourcelume `ProvenanceRecord` | drafted |
| DDEX `MWN` | `.work` → musical work right share notification | planned |
| DDEX `MWL` | `.work` → licence request and grant | planned |
| Lead sheet | `.work` → US Copyright Office deposit copy | planned |

## A projection is lossy in one direction only

Every recipient format below is narrower than the document. CWR can say who owns what and cannot say what the song is, who may licence it, what it was derived from, or who asserted any of it. Sourcelume can say a dataset has provenance and a licence and cannot say anything about shares.

So each file has a **what does not survive** section. That section is the interesting one: it is the list of things the `.work` document exists to carry, enumerated by the formats that cannot carry them.

## JSON-LD

[context/v1/work.jsonld](../context/v1/work.jsonld) maps every field name in [SPEC §6](../SPEC.md#6-object-model) to an IRI. Adding `"@context": "https://invoke.works/context/v1/work.jsonld"` to a document, and changing nothing else, makes it valid JSON-LD 1.1.

Three things about it are worth stating plainly, because they are the places where a reader is likely to assume more than is true.

**It does not change how signing works.** The signing input is the canonical JSON document under RFC 8785, with or without a context ([SPEC §5.7](../SPEC.md#57-json-ld)). RDF Dataset Canonicalization is not used anywhere in this format. A document that has been expanded or compacted by a JSON-LD processor will usually fail signature verification while being semantically unchanged, so consumers verify first and process second.

**Nodes mostly have no IRI identity.** `work_id` is a ULID and `party_id` is a document-scoped handle; neither is an IRI, and the context does not pretend otherwise by aliasing them to `@id`. The result is a term-resolvable graph of mostly blank nodes. That is enough for crosswalking and for querying a single document, and it is not enough to merge two documents by subject. Making it so would require minting IRIs for parties who already have an IPI, an ISNI and a DDEX Party ID, which is exactly the duplication the format exists to reduce.

**Ambiguous keys fall through to `@vocab`.** `type`, `status`, `role`, `claim` and `note` each mean different things in different objects, so they resolve to `work:type`, `work:status` and so on rather than to a borrowed external term. In particular `type` resolves to `work:type` and **not** to JSON-LD `@type` — a party's `type` of `natural_person` is a value, not a class assertion.

External vocabularies are used only where the correspondence is exact: schema.org for titles, names and recording identifiers, PROV-O for `provenance_recent`, ODRL for `mandates`, Dublin Core for dates and formats.
