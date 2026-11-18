from datetime import datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, Field, HttpUrl


class Source(StrEnum):
    KWORK = "kwork"
    FL_RU = "fl_ru"
    FREELANCE_RU = "freelance_ru"
    AVITO = "avito"
    PROFI_RU = "profi_ru"


class Gig(BaseModel):
    """Normalized gig; every source adapter must emit this."""

    source: Source
    external_id: str = Field(min_length=1)  # id on the source platform
    title: str
    description: str = ""
    url: HttpUrl
    budget_min_rub: int | None = None
    budget_max_rub: int | None = None
    posted_at: datetime | None = None
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def key(self) -> str:
        """Stable dedupe key across runs."""
        return f"{self.source.value}:{self.external_id}"
