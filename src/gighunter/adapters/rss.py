import logging
import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree

import httpx

from gighunter.models import Gig, Source

log = logging.getLogger(__name__)

HTTP_TIMEOUT_S = 20.0
USER_AGENT = "Mozilla/5.0 (compatible; gighunter/0.1)"
_TAG_RE = re.compile(r"<[^>]+>")
_BUDGET_RE = re.compile(r"(\d[\d\s ]*)\s*(?:руб|₽|р\.)", re.IGNORECASE)
_TRAILING_ID_RE = re.compile(r"(\d{4,})")


def _text(item: ElementTree.Element, tag: str) -> str:
    return (item.findtext(tag) or "").strip()


def _parse_budget(text: str) -> int | None:
    match = _BUDGET_RE.search(text)
    if not match:
        return None
    return int(re.sub(r"\D", "", match.group(1)))


def _parse_date(raw: str) -> datetime | None:
    try:
        return parsedate_to_datetime(raw) if raw else None
    except (TypeError, ValueError):
        return None


def _external_id(link: str, guid: str) -> str:
    # Prefer the longest digit run in the link (platform project id).
    ids = _TRAILING_ID_RE.findall(link)
    return max(ids, key=len) if ids else guid or link


def _item_to_gig(item: ElementTree.Element, source: Source) -> Gig:
    title, link = _text(item, "title"), _text(item, "link")
    desc = _TAG_RE.sub(" ", _text(item, "description")).strip()
    budget = _parse_budget(f"{title} {desc}")
    return Gig(
        source=source,
        external_id=_external_id(link, _text(item, "guid")),
        title=title,
        description=desc,
        url=link,
        budget_min_rub=budget,
        budget_max_rub=budget,
        posted_at=_parse_date(_text(item, "pubDate")),
    )


def parse_rss(xml: bytes, source: Source) -> list[Gig]:
    """Pure parser: bad items are logged and skipped, never fatal."""
    gigs: list[Gig] = []
    for item in ElementTree.fromstring(xml).iter("item"):
        try:
            gigs.append(_item_to_gig(item, source))
        except ValueError as exc:
            log.warning("%s: skipped malformed item: %s", source.value, exc)
    return gigs


class RssAdapter:
    def __init__(self, source: Source, url: str) -> None:
        self.source, self._url = source, url

    def fetch(self, client: httpx.Client) -> list[Gig]:
        resp = client.get(
            self._url, headers={"User-Agent": USER_AGENT}, timeout=HTTP_TIMEOUT_S
        )
        resp.raise_for_status()
        return parse_rss(resp.content, self.source)
