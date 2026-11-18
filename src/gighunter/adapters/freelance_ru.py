"""Freelance.ru: no RSS, so parse the public task feed (https://freelance.ru/task)."""
import logging
import re
from datetime import datetime
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup, Tag

from gighunter.adapters.common import MSK, AdapterError, get_page, parse_budget
from gighunter.models import Gig, Source

log = logging.getLogger(__name__)

BASE_URL = "https://freelance.ru"
_DATE_FMT = "%d.%m.%Y %H:%M"  # from the card's clock tooltip, e.g. "18.11.2026 16:28"
_HOURLY_UNIT = "/ час"  # hourly rate is not a project budget
_ID_RE = re.compile(r"/task/view/(\d+)")


def _text(card: Tag, selector: str) -> str:
    node = card.select_one(selector)
    return node.get_text(" ", strip=True) if node else ""


def _budget(card: Tag) -> int | None:
    if _HOURLY_UNIT in _text(card, ".task-card__budget .cost-unit"):
        return None
    return parse_budget(_text(card, ".task-card__budget .bold"))


def _posted_at(card: Tag) -> datetime | None:
    node = card.select_one(".task-card__foot-item[title]")
    if node is None:
        return None
    try:
        return datetime.strptime(str(node["title"]), _DATE_FMT).replace(tzinfo=MSK)
    except ValueError:
        return None


def _card_to_gig(card: Tag) -> Gig:
    link = card.select_one("a.task-card__title-link")
    href = str(link.get("href", "")) if link else ""
    match = _ID_RE.search(href)
    if link is None or match is None:
        raise ValueError(f"no task link in card (href={href!r})")
    budget = _budget(card)
    return Gig(
        source=Source.FREELANCE_RU,
        external_id=match.group(1),
        title=link.get_text(" ", strip=True),
        description=_text(card, ".task-card__desc"),
        url=urljoin(BASE_URL, href),
        budget_max_rub=budget,
        posted_at=_posted_at(card),
    )


def parse_freelance_ru(html: str) -> list[Gig]:
    """Pure parser: bad cards are logged and skipped; zero cards means layout changed."""
    cards = BeautifulSoup(html, "html.parser").select("article.task-card")
    if not cards:
        raise AdapterError("freelance_ru: no task cards found, layout changed?")
    gigs: list[Gig] = []
    for card in cards:
        try:
            gigs.append(_card_to_gig(card))
        except ValueError as exc:
            log.warning("freelance_ru: skipped malformed card: %s", exc)
    return gigs


class FreelanceRuAdapter:
    source = Source.FREELANCE_RU

    def __init__(self, url: str) -> None:
        self._url = url

    def fetch(self, client: httpx.Client) -> list[Gig]:
        return parse_freelance_ru(get_page(client, self._url).text)
