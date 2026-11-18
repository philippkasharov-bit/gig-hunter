from pathlib import Path

import httpx

from conftest import NOW, make_gig
from gighunter.adapters.common import AdapterError
from gighunter.adapters.registry import build_adapters
from gighunter.config import FilterConfig
from gighunter.filtering import ScoredGig
from gighunter.health import SourceHealth
from gighunter.models import Gig, Source
from gighunter.notifier import NotifyError
from gighunter.runner import run_once
from gighunter.store import SeenStore


class FakeAdapter:
    def __init__(self, source: Source, gigs: list[Gig] | None = None,
                 error: Exception | None = None) -> None:
        self.source, self._gigs, self._error = source, gigs or [], error

    def fetch(self, client: httpx.Client) -> list[Gig]:
        if self._error:
            raise self._error
        return self._gigs


class FakeNotifier:
    def __init__(self, fail_after: int | None = None) -> None:
        self.sent: list[str] = []
        self._fail_after = fail_after

    def send(self, item: ScoredGig) -> None:
        if self._fail_after is not None and len(self.sent) >= self._fail_after:
            raise NotifyError("down")
        self.sent.append(item.gig.external_id)


def _run(cfg: FilterConfig, adapters, notifier, store: SeenStore,
         health: SourceHealth | None = None):
    return run_once(cfg, adapters, notifier, store, httpx.Client(),
                    health or SourceHealth(), now=NOW, sleep=lambda s: None)


def _logo_gigs(n: int) -> list[Gig]:
    return [make_gig(str(i), title="Логотип") for i in range(n)]


def test_sends_up_to_cap_and_rest_go_next_run(cfg: FilterConfig) -> None:
    store, notifier = SeenStore(cfg.db_path), FakeNotifier()
    adapters = [FakeAdapter(Source.FL_RU, _logo_gigs(3))]
    first = _run(cfg, adapters, notifier, store)
    second = _run(cfg, adapters, notifier, store)
    assert (first.candidates, first.sent) == (3, 2)
    assert (second.candidates, second.sent) == (1, 1)
    assert sorted(notifier.sent) == ["0", "1", "2"]
    store.close()


def test_failing_source_isolated_and_backed_off(cfg: FilterConfig) -> None:
    store, health = SeenStore(cfg.db_path), SourceHealth()
    adapters = [FakeAdapter(Source.KWORK, error=AdapterError("layout")),
                FakeAdapter(Source.FL_RU, _logo_gigs(1))]
    stats = _run(cfg, adapters, FakeNotifier(), store, health)
    assert stats.failed_sources == ["kwork"] and stats.sent == 1
    assert not health.ready(Source.KWORK, NOW)
    store.close()


def test_send_failure_keeps_gig_unseen(cfg: FilterConfig) -> None:
    store = SeenStore(cfg.db_path)
    adapters = [FakeAdapter(Source.FL_RU, _logo_gigs(2))]
    stats = _run(cfg, adapters, FakeNotifier(fail_after=0), store)
    assert stats.sent == 0
    assert len(store.filter_new(_logo_gigs(2))) == 2
    store.close()


def test_registry_skips_enabled_source_without_adapter(tmp_path: Path) -> None:
    cfg = FilterConfig(
        sources={Source.FL_RU: True, Source.AVITO: True, Source.KWORK: False},
        feeds={Source.FL_RU: "https://example.com/rss",
               Source.KWORK: "https://kwork.ru/projects?c=15"},
        categories={"x": ["x"]}, score_tiers={"t": 0}, max_age_hours=1, db_path=tmp_path / "db")
    assert [a.source for a in build_adapters(cfg)] == [Source.FL_RU]
