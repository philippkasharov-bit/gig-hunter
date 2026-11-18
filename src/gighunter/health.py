from datetime import datetime, timedelta

from gighunter.models import Source

BASE_DELAY = timedelta(minutes=5)
MAX_DELAY = timedelta(hours=1)


class SourceHealth:
    """Exponential backoff per source so one dead site doesn't get hammered."""

    def __init__(self) -> None:
        self._failures: dict[Source, int] = {}
        self._retry_at: dict[Source, datetime] = {}

    def ready(self, source: Source, now: datetime) -> bool:
        return now >= self._retry_at.get(source, now)

    def record_success(self, source: Source) -> None:
        self._failures.pop(source, None)
        self._retry_at.pop(source, None)

    def record_failure(self, source: Source, now: datetime) -> None:
        n = self._failures.get(source, 0) + 1
        self._failures[source] = n
        self._retry_at[source] = now + min(BASE_DELAY * 2 ** (n - 1), MAX_DELAY)
