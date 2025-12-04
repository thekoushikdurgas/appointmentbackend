import base64

import pytest

from app.utils.cursor import decode_offset_cursor, encode_offset_cursor


def test_decode_offset_cursor_round_trip_current_format():
    token = encode_offset_cursor(12)
    assert decode_offset_cursor(token) == 12


def test_decode_offset_cursor_accepts_legacy_base64_plain_integer():
    legacy_token = base64.urlsafe_b64encode(b"7").decode("utf-8")
    assert decode_offset_cursor(legacy_token) == 7


def test_decode_offset_cursor_accepts_raw_integer_string():
    assert decode_offset_cursor("5") == 5


@pytest.mark.parametrize(
    "invalid_token",
    ["", " ", base64.urlsafe_b64encode(b"-1").decode("utf-8"), "not-an-int", "bz1=", "--"],
)
def test_decode_offset_cursor_rejects_invalid_tokens(invalid_token):
    with pytest.raises(ValueError):
        decode_offset_cursor(invalid_token)

