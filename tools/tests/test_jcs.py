import math

import pytest

from work import jcs


@pytest.mark.parametrize(
    "value,expected",
    [
        (0, "0"),
        (0.0, "0"),
        (-0.0, "0"),
        (1, "1"),
        (1.0, "1"),
        (-1.0, "-1"),
        (1.5, "1.5"),
        (333333333.33333329, "333333333.3333333"),
        # k <= n <= 21: integral forms print without a point or an exponent.
        (1e15, "1000000000000000"),
        (1e16, "10000000000000000"),
        (1e20, "100000000000000000000"),
        (1e21, "1e+21"),
        # -6 < n <= 0: leading-zero form, which is where Python's repr diverges.
        (0.000001, "0.000001"),
        (1e-7, "1e-7"),
        (1e-100, "1e-100"),
        (5e-324, "5e-324"),
        (1.7976931348623157e308, "1.7976931348623157e+308"),
        (123.456, "123.456"),
        (-123.456, "-123.456"),
    ],
)
def test_es6_number_formatting(value, expected):
    assert jcs.serialize(value) == expected


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_non_finite_numbers_are_rejected(value):
    with pytest.raises(jcs.JCSError):
        jcs.serialize(value)


def test_keys_sort_by_utf16_code_unit():
    # By code point U+FFFD precedes U+10000; by UTF-16 code unit it follows the
    # surrogate pair. RFC 8785 §3.2.3 requires the latter.
    doc = {"\U0001f600": 1, "\ufffd": 2, "a": 3}
    assert jcs.serialize(doc) == '{"a":3,"\U0001f600":1,"\ufffd":2}'


def test_string_escaping():
    assert jcs.serialize("a\"b\\c\nd\te\x00f\x1f") == '"a\\"b\\\\c\\nd\\te\\u0000f\\u001f"'


def test_no_insignificant_whitespace():
    assert jcs.serialize({"b": [1, 2], "a": {"c": None}}) == '{"a":{"c":null},"b":[1,2]}'


def test_literals():
    assert jcs.serialize([True, False, None]) == "[true,false,null]"


def test_rfc8785_appendix_b_sample():
    # The worked example from RFC 8785 §3.2.4.
    doc = {
        "\u20ac": "Euro Sign",
        "\r": "Carriage Return",
        "\u000a": "Newline",
        "1": "One",
        "\u0080": "Control\u007f",
        "\u00f6": "Latin Small Letter O With Diaeresis",
        "\u20ac\ufb33": "Hebrew Letter Dalet With Dagesh",
        "": "Empty",
    }
    out = jcs.serialize(doc)
    assert out.startswith('{"":"Empty","\\n":"Newline","\\r":"Carriage Return","1":"One"')
    assert list(doc) != list(dict.fromkeys(out))  # keys were reordered


def test_canonicalize_returns_utf8_bytes():
    assert jcs.canonicalize({"k": "\u00e9"}) == '{"k":"\u00e9"}'.encode("utf-8")
