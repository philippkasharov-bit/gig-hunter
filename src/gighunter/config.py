import re
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator

from gighunter.models import Source

_HASHTAG_RE = re.compile(r"\w+")  # Telegram hashtag: one word, no spaces/hyphens


class FilterConfig(BaseModel):
    sources: dict[Source, bool]
    feeds: dict[Source, str] = {}
    # Category tag -> keywords; order = tie-break priority (generic last).
    categories: dict[str, list[str]] = Field(min_length=1)
    stoplist: list[str] = []
    # Sources whose feed is already design-only: keyword match is skipped.
    keyword_free_sources: list[Source] = []
    min_budget_rub: int | None = None
    max_age_hours: int = Field(gt=0)
    db_path: Path
    poll_interval_s: int = Field(default=300, gt=0)
    max_alerts_per_run: int = Field(default=5, gt=0)
    send_pause_s: float = Field(default=1.0, ge=0)

    @field_validator("categories")
    @classmethod
    def _tags_are_hashtags(cls, value: dict[str, list[str]]) -> dict[str, list[str]]:
        bad = [tag for tag, kws in value.items() if not kws or not _HASHTAG_RE.fullmatch(tag)]
        if bad:
            raise ValueError(f"category tags must be one word with >=1 keyword: {bad}")
        return value

    @property
    def keywords(self) -> list[str]:
        return [kw for kws in self.categories.values() for kw in kws]

    @property
    def enabled_sources(self) -> list[Source]:
        return [s for s, on in self.sources.items() if on]


def load_config(path: Path) -> FilterConfig:
    with path.open(encoding="utf-8") as fh:
        return FilterConfig.model_validate(yaml.safe_load(fh))
