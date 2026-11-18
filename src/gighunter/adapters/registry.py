import logging
from collections.abc import Callable
from functools import partial

from gighunter.adapters.common import Adapter
from gighunter.adapters.freelance_ru import FreelanceRuAdapter
from gighunter.adapters.kwork import KworkAdapter
from gighunter.adapters.rss import RssAdapter
from gighunter.config import FilterConfig
from gighunter.models import Source

log = logging.getLogger(__name__)

# Source -> factory taking the source URL from config `feeds`.
_FACTORIES: dict[Source, Callable[[str], Adapter]] = {
    Source.FL_RU: partial(RssAdapter, Source.FL_RU),
    Source.FREELANCE_RU: FreelanceRuAdapter,
    Source.KWORK: KworkAdapter,
}


def build_adapters(cfg: FilterConfig) -> list[Adapter]:
    """Adapters for enabled sources; enabled-but-unusable sources are logged."""
    adapters: list[Adapter] = []
    for source in cfg.enabled_sources:
        factory, url = _FACTORIES.get(source), cfg.feeds.get(source)
        if factory is None or url is None:
            log.warning("%s enabled but has no adapter or URL; skipped", source.value)
            continue
        adapters.append(factory(url))
    return adapters
