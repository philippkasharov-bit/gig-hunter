import json

import httpx
import pytest
from pydantic import SecretStr

from conftest import make_gig
from gighunter.filtering import ScoredGig
from gighunter.notifier import NotifyError, TelegramNotifier, format_message
from gighunter.settings import TelegramSettings

TOKEN = "123:SECRET"
SETTINGS = TelegramSettings(bot_token=SecretStr(TOKEN), chat_id="42")


def _item(**kw) -> ScoredGig:
    return ScoredGig(make_gig(**kw), score=7)


def _notifier(handler) -> TelegramNotifier:
    return TelegramNotifier(SETTINGS, httpx.Client(transport=httpx.MockTransport(handler)))


def test_format_escapes_html_and_shows_budget() -> None:
    text = format_message(_item(title="<script> & Co", budget=15000))
    assert "&lt;script&gt; &amp; Co" in text
    assert "15 000 ₽" in text and "score 7" in text


def test_send_posts_chat_and_button() -> None:
    sent: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(json.loads(request.content))
        return httpx.Response(200, json={"ok": True})

    _notifier(handler).send(_item(external_id="9"))
    assert sent[0]["chat_id"] == "42"
    button = sent[0]["reply_markup"]["inline_keyboard"][0][0]
    assert button["url"] == "https://example.com/p/9"


def test_api_error_raises_without_token() -> None:
    body = {"ok": False, "error_code": 403, "description": "bot was blocked"}
    notifier = _notifier(lambda r: httpx.Response(403, json=body))
    with pytest.raises(NotifyError) as exc:
        notifier.send(_item())
    assert "403" in str(exc.value) and TOKEN not in str(exc.value)


def test_network_error_message_hides_token() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(f"cannot reach {request.url}")

    with pytest.raises(NotifyError) as exc:
        _notifier(handler).send(_item())
    assert TOKEN not in str(exc.value)
    assert exc.value.__cause__ is None and exc.value.__suppress_context__


def test_long_rate_limit_is_not_slept_through() -> None:
    body = {"ok": False, "error_code": 429, "parameters": {"retry_after": 600}}
    with pytest.raises(NotifyError, match="rate limited"):
        _notifier(lambda r: httpx.Response(429, json=body)).send(_item())
