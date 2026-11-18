import json
from datetime import timedelta

import httpx
import pytest

from gighunter.adapters.common import AdapterError
from gighunter.adapters.kwork import KworkAdapter, parse_kwork


def _want(want_id: int, name: str = "Логотип &quot;Кафе&quot;",
          price: str | None = "1000.00") -> dict:
    return {"id": want_id, "name": name, "description": "Нужен логотип ",
            "priceLimit": price, "date_create": "2026-11-18 16:21:11"}


def _page(wants: list[dict], next_url: str | None = None) -> str:
    state = {"wantsListData": {"pagination": {"data": wants, "next_page_url": next_url}}}
    return f"<script>window.stateData = {json.dumps(state)};</script>"


def test_parses_want() -> None:
    gigs, has_next = parse_kwork(_page([_want(3274192)]))
    gig = gigs[0]
    assert not has_next
    assert gig.external_id == "3274192"
    assert str(gig.url) == "https://kwork.ru/projects/3274192"
    assert gig.title == 'Логотип "Кафе"'
    assert gig.description == "Нужен логотип"
    assert gig.budget_max_rub == 1000
    assert gig.posted_at is not None and gig.posted_at.utcoffset() == timedelta(hours=3)


def test_missing_price_and_bad_item() -> None:
    gigs, _ = parse_kwork(_page([_want(1, price=None), {"name": "no id"}]))
    assert [(g.external_id, g.budget_max_rub) for g in gigs] == [("1", None)]


@pytest.mark.parametrize("page", [
    "<html>no state</html>",
    "<script>window.stateData = {broken</script>",
    "<script>window.stateData = {\"other\": 1};</script>",
])
def test_layout_change_raises_adapter_error(page: str) -> None:
    with pytest.raises(AdapterError):
        parse_kwork(page)


def test_adapter_follows_pages_until_last() -> None:
    pages = {"1": _page([_want(1)], "next"), "2": _page([_want(2)])}
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["c"] == "15"
        requested.append(request.url.params["page"])
        return httpx.Response(200, text=pages[request.url.params["page"]])

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        gigs = KworkAdapter("https://kwork.ru/projects?c=15").fetch(client)
    assert requested == ["1", "2"]
    assert [g.external_id for g in gigs] == ["1", "2"]
