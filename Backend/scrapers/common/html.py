def as_html(source) -> str:
    if source is None:
        return ""
    if isinstance(source, (bytes, bytearray)):
        return source.decode("utf-8", errors="replace")
    if isinstance(source, str):
        return source
    html = getattr(source, "html", None)
    if callable(html):
        try:
            html = html()
        except TypeError:
            html = None
    if isinstance(html, (str, bytes, bytearray)):
        return as_html(html)
    body = getattr(source, "body", None)
    if isinstance(body, (str, bytes, bytearray)):
        return as_html(body)
    return str(source)
