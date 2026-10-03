"""`work` — the command line entry point."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .blobs import BlobStore
from .fingerprint import fusion
from .fingerprint.header import FingerprintError, unpack
from .fingerprint.minhash import compare_blobs
from .ingest import FixtureAnalyser, SyntheticAnalyser, ingest
from .model import Document


def _cmd_ingest(args: argparse.Namespace) -> int:
    analyser = FixtureAnalyser(args.analysis) if args.analysis else SyntheticAnalyser()
    result = ingest(
        args.audio,
        store=BlobStore(args.blobs),
        title=args.title,
        writer=args.writer,
        analyser=analyser,
        isrc=args.isrc,
    )
    result.document.dump(args.out)

    doc = result.document
    print(f"{args.out}  {doc.work_id} v{doc.version} {doc.status}")
    print(f"  {len(doc.content)} components, {len(doc.evidence)} evidence, {len(result.digests)} blobs")
    for ref, reason in result.skipped.items():
        print(f"  skipped {ref}: {reason}", file=sys.stderr)
    print(
        "  rights are a stub: one uncontrolled writer at 10000 bps. Splits, IPI numbers,\n"
        "  publishers and chain of title are not derivable from audio.",
        file=sys.stderr,
    )
    return 0


def _cmd_fingerprint(args: argparse.Namespace) -> int:
    doc = Document.load(args.document)
    store = BlobStore(args.blobs)
    for entry in doc.content:
        if entry.get("role") != "fingerprint":
            continue
        header, _ = unpack(store.get(entry["digest"]))
        print(
            f"{entry['role']}.{entry['subrole']:<10} {header.algorithm:<32} "
            f"{header.disclosure:<12} {header.tokens} tokens"
        )
    return 0


def _cmd_compare(args: argparse.Namespace) -> int:
    store = BlobStore(args.blobs)
    a, b = Document.load(args.a), Document.load(args.b)
    by_subrole = {
        side: {e["subrole"]: e["digest"] for e in doc.content if e.get("role") == "fingerprint"}
        for side, doc in (("a", a), ("b", b))
    }
    channels: dict[str, float] = {}
    for subrole in sorted(set(by_subrole["a"]) & set(by_subrole["b"])):
        try:
            channels[subrole] = compare_blobs(
                store.get(by_subrole["a"][subrole]), store.get(by_subrole["b"][subrole])
            )
        except FingerprintError as exc:
            print(f"  {subrole}: not comparable — {exc}", file=sys.stderr)
    result = fusion.route(channels)
    print(json.dumps(result.report(), indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="work", description="Reference tooling for .work")
    parser.add_argument("--version", action="version", version=f"invoke-work {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("ingest", help="audio -> draft document")
    p.add_argument("audio", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--writer", required=True, help='"Last, First"')
    p.add_argument("--blobs", type=Path, default=Path("blobs"))
    p.add_argument("--analysis", type=Path, help="JSON analysis fixture; synthetic if omitted")
    p.add_argument("--isrc")
    p.set_defaults(func=_cmd_ingest)

    p = sub.add_parser("fingerprint", help="list a document's fingerprints")
    p.add_argument("document", type=Path)
    p.add_argument("--blobs", type=Path, default=Path("blobs"))
    p.set_defaults(func=_cmd_fingerprint)

    p = sub.add_parser("compare", help="compare two documents channel by channel")
    p.add_argument("a", type=Path)
    p.add_argument("b", type=Path)
    p.add_argument("--blobs", type=Path, default=Path("blobs"))
    p.set_defaults(func=_cmd_compare)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
