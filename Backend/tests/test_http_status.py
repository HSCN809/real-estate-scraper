from scrapers.common.http_status import is_failed_http_response, response_http_status


class _Resp:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def test_prefers_status_code_when_status_missing():
    assert response_http_status(_Resp(status_code=403)) == 403


def test_403_html_is_failed_even_if_body_is_long():
    assert is_failed_http_response(_Resp(status=403, body=b"x" * 500))


def test_200_with_tiny_body_is_failed():
    assert is_failed_http_response(_Resp(status=200, body=b"no"))
