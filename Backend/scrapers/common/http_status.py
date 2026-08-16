def response_http_status(response: object, default: int = 200) -> int:
    for attr in ("status", "status_code"):
        value = getattr(response, attr, None)
        if isinstance(value, int):
            return value
    return default


def is_failed_http_response(response: object) -> bool:
    status = response_http_status(response)
    body = getattr(response, "body", b"")
    return status >= 400 or not body or len(body) <= 100
