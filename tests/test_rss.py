from gighunter.adapters.rss import parse_rss
from gighunter.models import Source

FEED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
<item>
  <title><![CDATA[Логотип для кафе (Бюджет: 15 000 &#8381;)]]></title>
  <link>https://www.fl.ru/projects/5529733/logotip-kafe.html</link>
  <description><![CDATA[<p>Нужен <b>логотип</b> &amp; стиль</p>]]></description>
  <guid>https://www.fl.ru/projects/5529733/</guid>
  <pubDate>Wed, 18 Nov 2026 11:38:00 GMT</pubDate>
</item>
<item>
  <title>Без ссылки</title>
  <link>not a url</link>
</item>
</channel></rss>""".encode()


def test_parses_item_and_unescapes_entities() -> None:
    gig = parse_rss(FEED, Source.FL_RU)[0]
    assert gig.title == "Логотип для кафе (Бюджет: 15 000 ₽)"
    assert gig.budget_max_rub == 15000
    assert gig.external_id == "5529733"
    assert "<b>" not in gig.description and "& стиль" in gig.description
    assert gig.posted_at is not None and gig.posted_at.hour == 11


def test_malformed_item_is_skipped_not_fatal() -> None:
    assert len(parse_rss(FEED, Source.FL_RU)) == 1
