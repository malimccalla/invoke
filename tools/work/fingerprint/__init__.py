"""Fingerprint schemes. See ../../fingerprints/ for the normative documents."""

from .fusion import OUTCOMES, fuse, route
from .harmonic import Chord, harmonic_ngram
from .header import Header, pack, unpack
from .lyric import lyric_shingle
from .melodic import Note, melodic_lsh, melodic_ngram
from .minhash import compare_blobs, compare_signatures

__all__ = [
    "Chord",
    "Header",
    "Note",
    "OUTCOMES",
    "compare_blobs",
    "compare_signatures",
    "fuse",
    "harmonic_ngram",
    "lyric_shingle",
    "melodic_lsh",
    "melodic_ngram",
    "pack",
    "route",
    "unpack",
]
