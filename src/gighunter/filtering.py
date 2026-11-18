import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache

from gighunter.config import FilterConfig
from gighunter.models import Gig

TITLE_HIT_POINTS = 10
DESC_HIT_POINTS = 3
BUDGET_STATED_BONUS = 2
FRESH_WINDOW = timedelta(hours=3)
FRESH_BONUS = 3
# Short ASCII keywords ("ui") need word boundaries or they hit "quiz", "build".
SHORT_ASCII_MAX_LEN = 3


@dataclass(frozen=True)
class ScoredGig:
    gig: Gig
    score: int


@lru_cache(maxsize=8)
def _compile(keywords: tuple[str, ...]) -> tuple[re.Pattern[str], ...]:
    patterns = []
    for kw in keywords:
        body = re.escape(kw)
        if kw.isascii() and len(kw) <= SHORT_ASCII_MAX_LEN:
            body = rf"\b{body}\b"
        patterns.append(re.compile(body, re.IGNORECASE))
    return tuple(patterns)


def _hits(text: str, keywords: list[str]) -> int:
    return sum(1 for p in _compile(tuple(keywords)) if p.search(text))


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _too_old(gig: Gig, cfg: FilterConfig, now: datetime) -> bool:
    if gig.posted_at is None:  # unknown age: keep, don't guess
        return False
    return now - _aware(gig.posted_at) > timedelta(hours=cfg.max_age_hours)


def _below_floor(gig: Gig, cfg: FilterConfig) -> bool:
    if cfg.min_budget_rub is None or gig.budget_max_rub is None:
        return False  # unknown budget passes
    return gig.budget_max_rub < cfg.min_budget_rub


def is_candidate(gig: Gig, cfg: FilterConfig, now: datetime) -> bool:
    text = f"{gig.title} {gig.description}"
    if _too_old(gig, cfg, now) or _below_floor(gig, cfg):
        return False
    if cfg.stoplist and _hits(text, cfg.stoplist):
        return False
    return _hits(text, cfg.keywords) > 0


def score(gig: Gig, cfg: FilterConfig, now: datetime) -> int:
    pts = TITLE_HIT_POINTS * _hits(gig.title, cfg.keywords)
    pts += DESC_HIT_POINTS * _hits(gig.description, cfg.keywords)
    if gig.budget_max_rub is not None:
        pts += BUDGET_STATED_BONUS
    if gig.posted_at and now - _aware(gig.posted_at) <= FRESH_WINDOW:
        pts += FRESH_BONUS
    return pts


def rank(
    gigs: list[Gig], cfg: FilterConfig, now: datetime | None = None
) -> list[ScoredGig]:
    """Filter then sort by score desc, newest first on ties."""
    now = now or datetime.now(timezone.utc)
    scored = [ScoredGig(g, score(g, cfg, now)) for g in gigs
              if is_candidate(g, cfg, now)]
    epoch = datetime.min.replace(tzinfo=timezone.utc)
    return sorted(
        scored,
        key=lambda s: (s.score, _aware(s.gig.posted_at) if s.gig.posted_at else epoch),
        reverse=True,
    )
