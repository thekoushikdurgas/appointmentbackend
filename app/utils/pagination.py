from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl


def build_pagination_link(base_url: str, *, limit: int, offset: int) -> str:
    url = urlparse(base_url)
    query = dict(parse_qsl(url.query))
    query["limit"] = str(limit)
    query["offset"] = str(offset)
    new_query = urlencode(query)
    new_url = url._replace(query=new_query)
    return urlunparse(new_url)


def build_cursor_link(base_url: str, cursor: str) -> str:
    url = urlparse(base_url)
    query = dict(parse_qsl(url.query))
    query["cursor"] = cursor
    query.pop("offset", None)
    query.pop("limit", None)
    new_query = urlencode(query)
    new_url = url._replace(query=new_query)
    return urlunparse(new_url)

