from datetime import timedelta

import pytest

from gighunter.adapters.common import AdapterError
from gighunter.adapters.freelance_ru import parse_freelance_ru


def _card(task_id: str, title: str, budget_html: str,
          stamp: str = "18.11.2026 16:28") -> str:
    return f"""
<article class="task-card">
  <div class="task-card__main">
    <a class="task-card__title-link" href="/task/view/{task_id}">{title}</a>
    <p class="task-card__desc">Описание задачи</p>
    <div class="task-card__foot">
      <span class="task-card__foot-item" title="{stamp}">9 минут назад</span>
    </div>
  </div>
  <div class="task-card__side"><div class="task-card__budget">{budget_html}</div></div>
</article>"""


FIXED = '<span class="bold">3 000 &#8381;</span> <span class="cost-unit">/ заказ</span>'
HOURLY = '<span class="bold">800 &#8381;</span> <span class="cost-unit">/ час</span>'
NOT_SET = '<span class="bold cost-not-set">Обсуждается индивидуально</span>'


def test_parses_fixed_budget_card() -> None:
    gig = parse_freelance_ru(_card("15822", "Дизайн баннера", FIXED))[0]
    assert gig.external_id == "15822"
    assert str(gig.url) == "https://freelance.ru/task/view/15822"
    assert gig.title == "Дизайн баннера"
    assert gig.description == "Описание задачи"
    assert gig.budget_max_rub == 3000


def test_date_is_moscow_time() -> None:
    gig = parse_freelance_ru(_card("1", "x", FIXED))[0]
    assert gig.posted_at is not None
    assert gig.posted_at.utcoffset() == timedelta(hours=3)
    assert (gig.posted_at.hour, gig.posted_at.minute) == (16, 28)


@pytest.mark.parametrize("budget_html", [HOURLY, NOT_SET])
def test_hourly_or_unset_budget_is_none(budget_html: str) -> None:
    assert parse_freelance_ru(_card("1", "x", budget_html))[0].budget_max_rub is None


def test_bad_card_skipped_others_kept() -> None:
    page = _card("1", "ok", FIXED) + _card("abc", "bad link", FIXED)
    assert [g.external_id for g in parse_freelance_ru(page)] == ["1"]


def test_no_cards_raises_adapter_error() -> None:
    with pytest.raises(AdapterError):
        parse_freelance_ru("<html><body>Сайт на обслуживании</body></html>")
