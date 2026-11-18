from datetime import timedelta
from pathlib import Path

from conftest import NOW, make_gig
from gighunter.health import BASE_DELAY, MAX_DELAY, SourceHealth
from gighunter.models import Source
from gighunter.store import SeenStore


def test_seen_gig_filtered_and_survives_reopen(tmp_path: Path) -> None:
    db = tmp_path / "sub" / "seen.db"
    store = SeenStore(db)
    a, b = make_gig("a"), make_gig("b")
    store.mark_seen(a)
    store.mark_seen(a)  # idempotent
    assert store.filter_new([a, b]) == [b]
    store.close()
    reopened = SeenStore(db)
    assert reopened.filter_new([a]) == []
    reopened.close()


def test_same_id_on_other_source_is_new(tmp_path: Path) -> None:
    store = SeenStore(tmp_path / "seen.db")
    store.mark_seen(make_gig("1", source=Source.FL_RU))
    assert len(store.filter_new([make_gig("1", source=Source.KWORK)])) == 1
    store.close()


def test_backoff_doubles_and_caps() -> None:
    health = SourceHealth()
    health.record_failure(Source.KWORK, NOW)
    assert not health.ready(Source.KWORK, NOW + BASE_DELAY - timedelta(seconds=1))
    assert health.ready(Source.KWORK, NOW + BASE_DELAY)
    for _ in range(20):
        health.record_failure(Source.KWORK, NOW)
    assert health.ready(Source.KWORK, NOW + MAX_DELAY)
    assert health.ready(Source.FL_RU, NOW)  # other sources unaffected


def test_success_resets_backoff() -> None:
    health = SourceHealth()
    health.record_failure(Source.KWORK, NOW)
    health.record_success(Source.KWORK)
    assert health.ready(Source.KWORK, NOW)
