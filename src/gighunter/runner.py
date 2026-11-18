import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from xml.etree import ElementTree

import httpx

from gighunter.adapters.common import Adapter, AdapterError
from gighunter.config import FilterConfig
from gighunter.filtering import ScoredGig, rank
from gighunter.health import SourceHealth
from gighunter.models import Gig
from gighunter.notifier import NotifyError, TelegramNotifier
from gighunter.store import SeenStore

log = logging.getLogger(__name__)


@dataclass
class RunStats:
    fetched: int = 0
    candidates: int = 0
    sent: int = 0
    failed_sources: list[str] = field(default_factory=list)


def _fetch_all(adapters: list[Adapter], client: httpx.Client,
               health: SourceHealth, now: datetime, stats: RunStats) -> list[Gig]:
    gigs: list[Gig] = []
    for adapter in adapters:
        if not health.ready(adapter.source, now):
            continue
        try:
            found = adapter.fetch(client)
        except (httpx.HTTPError, ElementTree.ParseError, AdapterError) as exc:
            health.record_failure(adapter.source, now)
            stats.failed_sources.append(adapter.source.value)
            log.warning("%s failed: %s", adapter.source.value, type(exc).__name__)
            continue
        health.record_success(adapter.source)
        gigs.extend(found)
    return gigs


def _send_ranked(ranked: list[ScoredGig], cfg: FilterConfig,
                 notifier: TelegramNotifier, store: SeenStore,
                 stats: RunStats, sleep: Callable[[float], None]) -> None:
    for item in ranked[: cfg.max_alerts_per_run]:
        try:
            notifier.send(item)
        except NotifyError as exc:
            log.error("send failed, stopping this run: %s", exc)
            return  # unsent gigs stay unseen and retry next run
        store.mark_seen(item.gig)
        stats.sent += 1
        sleep(cfg.send_pause_s)


def run_once(cfg: FilterConfig, adapters: list[Adapter],
             notifier: TelegramNotifier, store: SeenStore,
             client: httpx.Client, health: SourceHealth,
             now: datetime | None = None,
             sleep: Callable[[float], None] = time.sleep) -> RunStats:
    now = now or datetime.now(timezone.utc)
    stats = RunStats()
    gigs = _fetch_all(adapters, client, health, now, stats)
    stats.fetched = len(gigs)
    ranked = rank(store.filter_new(gigs), cfg, now)
    stats.candidates = len(ranked)
    _send_ranked(ranked, cfg, notifier, store, stats, sleep)
    return stats
