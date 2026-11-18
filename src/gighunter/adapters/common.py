"""Shared pieces for source adapters: protocol, errors, HTTP and parsing helpers."""
import re
from datetime import timedelta, timezone
from typing import Protocol

import httpx

from gighunter.models import Gig, Source

HTTP_TIMEOUT_S = 20.0
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)
# Sites print naive Moscow time. Russia has had no DST since 2014, so a fixed
# offset is exact and avoids needing the tzdata package on Windows.
MSK = timezone(timedelta(hours=3), "MSK")
_BUDGET_RE = re.compile(r"(\d[\d\s ]*)\s*(?:руб|₽|р\.)", re.IGNORECASE)


class AdapterError(Exception):
    """Page was fetched but its structure is not what the parser expects."""


class Adapter(Protocol):
    source: Source

    def fetch(self, client: httpx.Client) -> list[Gig]: ...


def parse_budget(text: str) -> int | None:
    match = _BUDGET_RE.search(text)
    if not match:
        return None
    return int(re.sub(r"\D", "", match.group(1)))


def get_page(client: httpx.Client, url: str,
             params: dict[str, int] | None = None) -> httpx.Response:
    # Merge, not pass `params=`: httpx 0.28 would drop the URL's own query (?c=15).
    full_url = httpx.URL(url).copy_merge_params(params or {})
    resp = client.get(full_url, headers={"User-Agent": USER_AGENT},
                      timeout=HTTP_TIMEOUT_S, follow_redirects=True)
    resp.raise_for_status()
    return resp
