import base64


def encode_offset_cursor(offset: int) -> str:
    token = f"o={offset}"
    return base64.urlsafe_b64encode(token.encode("utf-8")).decode("utf-8")


def decode_offset_cursor(token: str) -> int:
    try:
        decoded = base64.urlsafe_b64decode(token.encode("utf-8")).decode("utf-8")
        if not decoded.startswith("o="):
            raise ValueError("Invalid cursor payload")
        return int(decoded.split("=", 1)[1])
    except Exception as exc:  # noqa: BLE001
        raise ValueError("Invalid cursor value") from exc

