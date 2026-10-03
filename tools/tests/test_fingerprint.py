import math

import pytest

from work.fingerprint import fusion, harmonic, header, lyric, melodic, minhash
from work.fingerprint.header import FingerprintError


def scale(count: int, *, step: float = 0.5, start: int = 60) -> list[melodic.Note]:
    """An ascending chromatic line with even inter-onset intervals.

    Deliberately degenerate: every window is the same token repeated, so the n-gram
    set has one element. Useful only for testing that collapse.
    """
    return [melodic.Note(i * step, start + i, step * 0.9) for i in range(count)]


_INTERVALS = [2, -1, 3, -2, 5, -4, 1, -3, 2, 7, -5, 2, -2, 4, -1, -6, 3, 1]
_STEPS = [0.5, 0.25, 0.5, 1.0, 0.25, 0.75, 0.5, 0.5, 0.25, 1.0]


def melody(
    count: int, *, transpose: int = 0, stretch: float = 1.0, start: int = 60
) -> list[melodic.Note]:
    """A non-degenerate line: varied intervals over varied inter-onset intervals."""
    notes, pitch, t = [], start + transpose, 0.0
    for i in range(count):
        step = _STEPS[i % len(_STEPS)] * stretch
        notes.append(melodic.Note(t, pitch, step * 0.8))
        t += step
        pitch += _INTERVALS[i % len(_INTERVALS)]
    return notes


# -- preprocessing ---------------------------------------------------------------


def test_overlap_keeps_the_higher_pitch_and_discards_the_other():
    notes = [melodic.Note(0.0, 60, 1.0), melodic.Note(0.5, 72, 1.0)]
    assert melodic.preprocess(notes) == [melodic.Note(0.5, 72, 1.0)]


def test_overlapping_lower_pitch_is_dropped_not_truncated():
    notes = [melodic.Note(0.0, 72, 1.0), melodic.Note(0.5, 60, 1.0)]
    assert melodic.preprocess(notes) == [melodic.Note(0.0, 72, 1.0)]


def test_repeated_pitch_merges_below_the_gap_and_not_above():
    close = [melodic.Note(0.0, 60, 0.5), melodic.Note(0.52, 60, 0.5)]
    assert melodic.preprocess(close) == [melodic.Note(0.0, 60, 1.02)]

    apart = [melodic.Note(0.0, 60, 0.5), melodic.Note(0.53, 60, 0.5)]
    assert len(melodic.preprocess(apart)) == 2


def test_short_notes_are_dropped_at_the_boundary():
    assert melodic.preprocess([melodic.Note(0.0, 60, 0.040)]) == [melodic.Note(0.0, 60, 0.040)]
    assert melodic.preprocess([melodic.Note(0.0, 60, 0.039)]) == []


# -- representation --------------------------------------------------------------


def test_intervals_clamp_at_both_ends():
    notes = [
        melodic.Note(0.0, 48, 0.4),
        melodic.Note(0.5, 90, 0.4),
        melodic.Note(1.0, 48, 0.4),
        melodic.Note(1.5, 60, 0.4),
    ]
    toks = melodic.tokens(notes)
    assert toks[0] // 7 == 24  # +42 semitones clamps to +12
    assert toks[1] // 7 == 0  # -42 clamps to -12


def test_duration_class_boundary_is_decided_by_threshold_not_rounding():
    # 2**0.25 is exactly a class boundary. Deciding it by round(2*log2(r)) is at the
    # mercy of floating-point error; the threshold comparison is not.
    assert melodic._duration_class(2**0.25) == 1
    assert melodic._duration_class(melodic.DURATION_THRESHOLDS[3] * (1 - 1e-12)) == 0
    assert melodic._duration_class(1.0) == 0
    assert melodic._duration_class(100.0) == 3
    assert melodic._duration_class(0.001) == -3


def test_token_alphabet_is_one_byte():
    toks = melodic.tokens(melody(40))
    assert toks and all(0 <= t <= 174 for t in toks)


def test_an_identically_repeated_figure_contributes_one_element():
    # §3.4. The set semantics are what stop a loop-based arrangement drowning out
    # everything else in it.
    toks = melodic.tokens(melodic.preprocess(scale(60)))
    assert len(set(toks)) == 1
    raw = bytes(toks)
    assert len({raw[i : i + melodic.N] for i in range(len(raw) - melodic.N + 1)}) == 1


# -- encoding --------------------------------------------------------------------


def test_melodic_blob_is_1040_bytes_with_the_right_header():
    blob = melodic.melodic_ngram(melody(40))
    assert len(blob) == 1040
    head, values = header.unpack(blob)
    assert (head.scheme, head.major, head.count, head.n) == (0x01, 1, 128, 12)
    assert head.algorithm == "invoke:fp/melodic-ngram@1.0"
    assert head.disclosure == "substantial"
    assert head.tokens == 38
    assert len(values) == 128


def test_lsh_blob_is_144_bytes_and_opaque():
    blob = melodic.melodic_lsh(melody(40))
    assert len(blob) == 144
    head, bands = header.unpack(blob)
    assert (head.scheme, head.count) == (0x02, 16)
    assert head.disclosure == "opaque"
    assert len(bands) == 16


def test_encoding_is_deterministic():
    assert melodic.melodic_ngram(melody(40)) == melodic.melodic_ngram(melody(40))


def test_too_few_notes_refuses_rather_than_emitting_a_degenerate_sketch():
    with pytest.raises(FingerprintError):
        melodic.melodic_ngram(melody(13))
    assert len(melodic.melodic_ngram(melody(14))) == 1040


# -- the invariances the scheme exists for ---------------------------------------


def test_transposition_leaves_the_sketch_identical():
    assert melodic.melodic_ngram(melody(60)) == melodic.melodic_ngram(melody(60, transpose=7))


def test_uniform_tempo_change_leaves_the_sketch_identical():
    assert melodic.melodic_ngram(melody(60)) == melodic.melodic_ngram(melody(60, stretch=1.5))


def test_an_unrelated_melody_does_not_match():
    a = melodic.melodic_ngram(melody(60))
    b = melodic.melodic_ngram(
        [melodic.Note(i * 0.4, 60 + (i * 7) % 13, 0.3) for i in range(60)]
    )
    assert minhash.compare_blobs(a, b) < 0.2


def test_a_shared_passage_scores_between_the_extremes():
    base = melody(60)
    head_notes = base[:40]
    t, p = head_notes[-1].onset, head_notes[-1].pitch
    tail = []
    for i in range(20):
        t += 0.3 + 0.1 * (i % 3)
        p += [4, -3, 6, -2][i % 4]
        tail.append(melodic.Note(t, p, 0.25))
    score = minhash.compare_blobs(
        melodic.melodic_ngram(base), melodic.melodic_ngram(head_notes + tail)
    )
    assert 0.2 < score < 0.95


def test_comparison_refuses_across_schemes():
    with pytest.raises(FingerprintError):
        minhash.compare_blobs(melodic.melodic_ngram(melody(40)), melodic.melodic_lsh(melody(40)))


def test_dropout_is_unbiased_and_shared():
    grams = {bytes([i, i, i]) for i in range(200)}
    kept = minhash.apply_dropout(grams)
    assert minhash.apply_dropout(grams) == kept
    assert 0.75 < len(kept) / len(grams) < 0.95


# -- harmonic --------------------------------------------------------------------


def progression(repeats: int, roots=(0, 7, 9, 5)) -> list[harmonic.Chord]:
    return [
        harmonic.Chord(float(i), roots[i % len(roots)], "maj")
        for i in range(repeats * len(roots))
    ]


def test_harmonic_collapses_repeats_and_is_transposition_invariant():
    a = harmonic.harmonic_ngram(progression(6))
    b = harmonic.harmonic_ngram([harmonic.Chord(c.onset, (c.root + 5) % 12, c.quality) for c in progression(6)])
    assert a == b


def test_harmonic_extensions_fold_to_the_seventh():
    assert harmonic.QUALITIES["13"] == harmonic.QUALITIES["dom7"]


def test_harmonic_rejects_shared_onsets():
    with pytest.raises(FingerprintError):
        harmonic.harmonic_ngram([harmonic.Chord(0.0, 0, "maj"), harmonic.Chord(0.0, 7, "maj")])


# -- lyric -----------------------------------------------------------------------


def test_lyric_normalisation():
    words = lyric.normalise("[Chorus]\nDon\u2019t \u2014 STOP! (x2) believin\u2019")
    assert words == ["don't", "stop", "believin"]


def test_lyric_case_folding_is_full():
    assert lyric.normalise("STRASSE stra\u00dfe") == ["strasse", "strasse"]


def test_identical_lyrics_match_exactly():
    text = "one two three four five six seven eight nine ten"
    assert minhash.compare_blobs(lyric.lyric_shingle(text), lyric.lyric_shingle(text)) == 1.0


def test_too_few_words_refuses():
    with pytest.raises(FingerprintError):
        lyric.lyric_shingle("one two three four")


# -- fusion ----------------------------------------------------------------------


def test_harmonic_alone_never_produces_an_outcome():
    result = fusion.route({"harmonic": 1.0})
    assert result.outcome == "none"
    assert "harmonic channel alone" in result.notes[0]


def test_two_cleared_channels_give_a_candidate_and_never_more():
    result = fusion.route({"melodic": 0.88, "lyric": 0.95})
    assert result.outcome == "candidate_same_work"
    assert "promotion needs a party" in result.notes[-1]


def test_one_strong_channel_is_not_enough():
    assert fusion.route({"melodic": 0.99}).outcome == "shares_material"


def test_absent_channels_do_not_drag_the_score_down():
    both = fusion.route({"melodic": 0.9, "lyric": 0.9})
    instrumental = fusion.route({"melodic": 0.9, "harmonic": 0.9})
    assert math.isclose(both.score, 0.9) and math.isclose(instrumental.score, 0.9)
    assert "lyric" in instrumental.absent


def test_report_declares_that_thresholds_are_unmeasured():
    assert fusion.route({"melodic": 0.9, "lyric": 0.9}).report()["thresholds"] == "provisional"
