import httpx
import pytest

from gighunter.adapters.common import get_page, parse_budget


@pytest.mark.parametrize(("text", "expected"), [
    ("Бюджет: 15 000 ₽", 15000),
    ("до 5 000 руб.", 5000),
    ("3000 р.", 3000),
    ("бюджет не указан", None),
    ("", None),
])
def test_parse_budget(text: str, expected: int | None) -> None:
    assert parse_budget(text) == expected


def test_get_page_keeps_url_query_when_adding_params() -> None:
    seen: list[httpx.URL] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url)
        return httpx.Response(200, text="ok")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        get_page(client, "https://kwork.ru/projects?c=15", {"page": 2})
    assert seen[0].params["c"] == "15"
    assert seen[0].params["page"] == "2"


def test_get_page_raises_on_http_error() -> None:
    transport = httpx.MockTransport(lambda r: httpx.Response(503))
    with httpx.Client(transport=transport) as client, pytest.raises(httpx.HTTPStatusError):
        get_page(client, "https://example.com/")
