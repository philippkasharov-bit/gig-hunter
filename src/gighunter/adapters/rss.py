import html
import logging
import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree

import httpx

from gighunter.adapters.common import get_page, parse_budget
from gighunter.models import Gig, Source

log = logging.getLogger(__name__)

_TAG_RE = re.compile(r"<[^>]+>")
_TRAILING_ID_RE = re.compile(r"(\d{4,})")


def _text(item: ElementTree.Element, tag: str) -> str:
    return (item.findtext(tag) or "").strip()


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
    # FL.ru double-encodes entities inside CDATA (e.g. "&#8381;" for the ruble sign).
    title, link = html.unescape(_text(item, "title")), _text(item, "link")
    desc = html.unescape(_TAG_RE.sub(" ", _text(item, "description"))).strip()
    budget = parse_budget(f"{title} {desc}")
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
        return parse_rss(get_page(client, self._url).content, self.source)
