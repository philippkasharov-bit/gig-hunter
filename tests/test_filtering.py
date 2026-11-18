from datetime import timedelta

from conftest import NOW, make_gig
from gighunter.config import FilterConfig
import pytest
from pydantic import ValidationError

from gighunter.filtering import categorize, is_candidate, rank, tier
from gighunter.models import Source


def test_keyword_match_is_case_insensitive(cfg: FilterConfig) -> None:
    assert is_candidate(make_gig(title="ЛОГОТИП для кафе"), cfg, NOW)


def test_no_keyword_rejected(cfg: FilterConfig) -> None:
    assert not is_candidate(make_gig(title="Настроить сервер"), cfg, NOW)


def test_short_ascii_keyword_needs_word_boundary(cfg: FilterConfig) -> None:
    assert is_candidate(make_gig(title="UI для приложения"), cfg, NOW)
    assert not is_candidate(make_gig(title="Build a quiz bot"), cfg, NOW)


def test_keyword_free_source_skips_keywords_only(cfg: FilterConfig) -> None:
    cfg.keyword_free_sources = [Source.KWORK]
    assert is_candidate(make_gig(title="Этикетка для комбучи", source=Source.KWORK), cfg, NOW)
    assert not is_candidate(make_gig(title="Этикетка для комбучи"), cfg, NOW)
    assert not is_candidate(make_gig(title="Этикетка за идею", source=Source.KWORK), cfg, NOW)
    old = NOW - timedelta(hours=49)
    assert not is_candidate(make_gig(source=Source.KWORK, posted_at=old), cfg, NOW)


def test_stoplist_rejects(cfg: FilterConfig) -> None:
    assert not is_candidate(make_gig(title="Логотип за идею"), cfg, NOW)


def test_too_old_rejected_unknown_age_kept(cfg: FilterConfig) -> None:
    assert not is_candidate(make_gig(posted_at=NOW - timedelta(hours=49)), cfg, NOW)
    assert is_candidate(make_gig(posted_at=None), cfg, NOW)


def test_budget_floor(cfg: FilterConfig) -> None:
    cfg.min_budget_rub = 5000
    assert not is_candidate(make_gig(budget=1000), cfg, NOW)
    assert is_candidate(make_gig(budget=5000), cfg, NOW)
    assert is_candidate(make_gig(budget=None), cfg, NOW)


def test_rank_orders_by_score_then_newest(cfg: FilterConfig) -> None:
    weak = make_gig("weak", title="x", description="логотип")
    strong = make_gig("strong", title="Логотип и дизайн")
    old_tie = make_gig("old", title="x", description="логотип",
                       posted_at=NOW - timedelta(hours=10))
    ranked = rank([old_tie, weak, strong, make_gig("off", title="сервер")], cfg, NOW)
    assert [s.gig.external_id for s in ranked] == ["strong", "weak", "old"]


def test_all_hit_categories_best_first(cfg: FilterConfig) -> None:
    gig = make_gig(title="Логотип", description="и UI")
    assert categorize(gig, cfg) == ("логотип", "веб")
    assert categorize(make_gig(title="UI и логотип"), cfg) == ("логотип", "веб")  # tie -> order


def test_generic_category_only_when_no_specific_hit(cfg: FilterConfig) -> None:
    many_generic = make_gig(title="Дизайн дизайн", description="дизайн, и логотип")
    assert categorize(many_generic, cfg) == ("логотип",)
    assert categorize(make_gig(title="Дизайн коробки"), cfg) == ("дизайн",)
    assert categorize(make_gig(title="Афиша"), cfg) == ("дизайн",)  # keyword-free source


def test_short_cyrillic_keyword_needs_word_boundary(cfg: FilterConfig) -> None:
    assert categorize(make_gig(title="Карточки на ВБ"), cfg) == ("маркетплейс",)
    assert categorize(make_gig(title="Дизайн вблизи моря"), cfg) == ("дизайн",)


@pytest.mark.parametrize(("points", "expected"), [(25, "топ"), (20, "топ"), (19, "норм"), (3, "слабо")])
def test_tier_is_highest_reached(cfg: FilterConfig, points: int, expected: str) -> None:
    assert tier(points, cfg) == expected


def test_rank_attaches_categories_and_tier(cfg: FilterConfig) -> None:
    item = rank([make_gig(title="Логотип")], cfg, NOW)[0]
    assert (item.categories, item.tier) == (("логотип",), "норм")


@pytest.mark.parametrize(("field", "tags"), [
    ("categories", {"two words": ["x"]}),
    ("categories", {"веб-дизайн": ["x"]}),
    ("categories", {"пусто": []}),
    ("score_tiers", {"очень топ": 20}),
])
def test_bad_tag_rejected(cfg: FilterConfig, field: str, tags: dict) -> None:
    with pytest.raises(ValidationError):
        FilterConfig.model_validate({**cfg.model_dump(), field: tags})
