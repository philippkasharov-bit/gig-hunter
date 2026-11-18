from gighunter.adapters.rss import RssAdapter
from gighunter.config import FilterConfig
from gighunter.models import Source

_RSS_SOURCES = (Source.FL_RU, Source.FREELANCE_RU)


def build_adapters(cfg: FilterConfig) -> list[RssAdapter]:
    """Adapters for enabled sources that have a feed URL (batch 2 scope)."""
    return [
        RssAdapter(s, cfg.feeds[s])
        for s in cfg.enabled_sources
        if s in _RSS_SOURCES and s in cfg.feeds
    ]
