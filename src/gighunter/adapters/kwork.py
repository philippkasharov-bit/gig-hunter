"""Kwork: the project list is embedded as JSON in `window.stateData` on the page."""
import html
import json
import logging
from datetime import datetime

import httpx

from gighunter.adapters.common import MSK, AdapterError, get_page
from gighunter.models import Gig, Source

log = logging.getLogger(__name__)

PROJECT_URL = "https://kwork.ru/projects/"
# Default sort is not by date, so read every page. Design category holds
# ~45 open projects at 12 per page; the cap bounds requests per poll.
MAX_PAGES = 5
_STATE_MARKER = "window.stateData"
_DATE_FMT = "%Y-%m-%d %H:%M:%S"


def _extract_state(page_html: str) -> dict:
    marker = page_html.find(_STATE_MARKER)
    start = page_html.find("{", marker) if marker >= 0 else -1
    if start < 0:
        raise AdapterError("kwork: stateData not found, layout changed?")
    try:
        state, _ = json.JSONDecoder().raw_decode(page_html, start)
    except json.JSONDecodeError as exc:
        raise AdapterError(f"kwork: stateData is not valid JSON: {exc.msg}") from None
    return state


def _posted_at(raw: str) -> datetime | None:
    try:
        return datetime.strptime(raw, _DATE_FMT).replace(tzinfo=MSK)
    except (TypeError, ValueError):
        return None


def _want_to_gig(want: dict) -> Gig:
    price = want.get("priceLimit")  # buyer's desired upper limit, e.g. "1000.00"
    return Gig(
        source=Source.KWORK,
        external_id=str(want["id"]),
        title=html.unescape(want.get("name") or ""),
        description=html.unescape(want.get("description") or "").strip(),
        url=f"{PROJECT_URL}{want['id']}",
        budget_max_rub=int(float(price)) if price else None,
        posted_at=_posted_at(want.get("date_create")),
    )


def parse_kwork(page_html: str) -> tuple[list[Gig], bool]:
    """Pure parser. Returns (gigs, has_next_page); bad items are logged and skipped."""
    try:
        pagination = _extract_state(page_html)["wantsListData"]["pagination"]
    except (KeyError, TypeError):
        raise AdapterError("kwork: wantsListData.pagination missing") from None
    gigs: list[Gig] = []
    for want in pagination.get("data") or []:
        try:
            gigs.append(_want_to_gig(want))
        except (KeyError, TypeError, ValueError) as exc:
            log.warning("kwork: skipped malformed project: %s", exc)
    return gigs, bool(pagination.get("next_page_url"))


class KworkAdapter:
    source = Source.KWORK

    def __init__(self, url: str) -> None:
        self._url = url

    def fetch(self, client: httpx.Client) -> list[Gig]:
        gigs: list[Gig] = []
        for page in range(1, MAX_PAGES + 1):
            found, has_next = parse_kwork(get_page(client, self._url, {"page": page}).text)
            gigs.extend(found)
            if not has_next:
                break
        return gigs
