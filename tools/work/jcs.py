"""RFC 8785 JSON Canonicalization Scheme.

The interoperability core: two implementations that disagree here produce documents
whose signatures do not verify. See SPEC.md §5.1.
"""

from __future__ import annotations

import math
from decimal import Decimal
from typing import Any

__all__ = ["canonicalize", "serialize", "JCSError"]


class JCSError(ValueError):
    pass


_ESCAPES = {
    0x08: "\\b",
    0x09: "\\t",
    0x0A: "\\n",
    0x0C: "\\f",
    0x0D: "\\r",
    0x22: '\\"',
    0x5C: "\\\\",
}


def _utf16_key(s: str) -> tuple[int, ...]:
    """Sort key over UTF-16 code units.

    Python orders strings by code point, which disagrees with UTF-16 order for any
    key containing a character above the BMP: U+FFFD precedes U+10000 by code point
    but follows it once surrogates are involved.
    """
    raw = s.encode("utf-16-be")
    return tuple(int.from_bytes(raw[i : i + 2], "big") for i in range(0, len(raw), 2))


def _string(s: str) -> str:
    out = ['"']
    for ch in s:
        cp = ord(ch)
        esc = _ESCAPES.get(cp)
        if esc is not None:
            out.append(esc)
        elif cp < 0x20:
            out.append(f"\\u{cp:04x}")
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def _number(value: float | int) -> str:
    """ECMAScript Number::toString, as RFC 8785 §3.2.2.3 requires.

    Python's repr is also shortest-round-trip but switches to exponential at
    different magnitudes, so the digits are taken from repr and reformatted here.
    """
    if isinstance(value, int):
        return str(value)
    if math.isnan(value) or math.isinf(value):
        raise JCSError(f"{value!r} is not representable in JSON")
    if value == 0:
        return "0"

    sign = "-" if value < 0 else ""
    digits, exp = Decimal(repr(abs(float(value)))).as_tuple()[1:]
    digits = list(digits)
    while len(digits) > 1 and digits[-1] == 0:
        digits.pop()
        exp += 1

    k = len(digits)
    n = exp + k
    ds = "".join(str(d) for d in digits)

    if k <= n <= 21:
        return sign + ds + "0" * (n - k)
    if 0 < n <= 21:
        return sign + ds[:n] + "." + ds[n:]
    if -6 < n <= 0:
        return sign + "0." + "0" * -n + ds
    e = n - 1
    mantissa = ds if k == 1 else ds[0] + "." + ds[1:]
    return f"{sign}{mantissa}e{'+' if e >= 0 else '-'}{abs(e)}"


def _value(v: Any, out: list[str]) -> None:
    if v is None:
        out.append("null")
    elif v is True:
        out.append("true")
    elif v is False:
        out.append("false")
    elif isinstance(v, str):
        out.append(_string(v))
    elif isinstance(v, (int, float)):
        out.append(_number(v))
    elif isinstance(v, (list, tuple)):
        out.append("[")
        for i, item in enumerate(v):
            if i:
                out.append(",")
            _value(item, out)
        out.append("]")
    elif isinstance(v, dict):
        out.append("{")
        for i, key in enumerate(sorted(v, key=_utf16_key)):
            if not isinstance(key, str):
                raise JCSError(f"object key {key!r} is not a string")
            if i:
                out.append(",")
            out.append(_string(key))
            out.append(":")
            _value(v[key], out)
        out.append("}")
    else:
        raise JCSError(f"{type(v).__name__} has no JSON serialisation")


def serialize(value: Any) -> str:
    out: list[str] = []
    _value(value, out)
    return "".join(out)


def canonicalize(value: Any) -> bytes:
    return serialize(value).encode("utf-8")
