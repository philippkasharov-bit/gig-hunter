from datetime import datetime, timezone
from pathlib import Path

import pytest

from gighunter.config import FilterConfig
from gighunter.models import Gig, Source

NOW = datetime(2026, 11, 18, 12, 0, tzinfo=timezone.utc)


def make_gig(external_id: str = "1", title: str = "Нужен логотип",
             description: str = "", source: Source = Source.FL_RU,
             budget: int | None = None, posted_at: datetime | None = NOW) -> Gig:
    return Gig(source=source, external_id=external_id, title=title,
               description=description, url=f"https://example.com/p/{external_id}",
               budget_max_rub=budget, posted_at=posted_at)


@pytest.fixture
def cfg(tmp_path: Path) -> FilterConfig:
    return FilterConfig(
        sources={Source.FL_RU: True},
        feeds={Source.FL_RU: "https://example.com/rss"},
        keywords=["логотип", "дизайн", "ui"],
        stoplist=["за идею"],
        max_age_hours=48,
        db_path=tmp_path / "seen.db",
        max_alerts_per_run=2,
        send_pause_s=0,
    )
