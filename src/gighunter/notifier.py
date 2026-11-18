import html
import time

import httpx

from gighunter.filtering import ScoredGig
from gighunter.settings import TelegramSettings

API_BASE = "https://api.telegram.org"
SEND_TIMEOUT_S = 15.0
DESC_PREVIEW_CHARS = 300
OPEN_BUTTON_TEXT = "Открыть"
MAX_RETRY_AFTER_S = 30  # longer 429 waits are surfaced, not slept through


class NotifyError(RuntimeError):
    """Delivery failed. Message never contains the bot token."""


def _budget(gig_budget: int | None) -> str:
    return "бюджет не указан" if gig_budget is None else f"{gig_budget:,} ₽".replace(",", " ")


def format_message(item: ScoredGig) -> str:
    g = item.gig
    desc = g.description[:DESC_PREVIEW_CHARS].strip()
    parts = [
        f"<b>{html.escape(g.title)}</b>",
        f"#{html.escape(item.category)} · {g.source.value} · "
        f"{_budget(g.budget_max_rub)} · score {item.score}",
    ]
    if desc:
        parts.append(html.escape(desc))
    return "\n".join(parts)


def _payload(item: ScoredGig, chat_id: str) -> dict:
    return {
        "chat_id": chat_id,
        "text": format_message(item),
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
        "reply_markup": {
            "inline_keyboard": [[{"text": OPEN_BUTTON_TEXT, "url": str(item.gig.url)}]]
        },
    }


class TelegramNotifier:
    def __init__(self, settings: TelegramSettings, client: httpx.Client) -> None:
        self._settings, self._client = settings, client
        token = settings.bot_token.get_secret_value()
        self._url = f"{API_BASE}/bot{token}/sendMessage"

    def send(self, item: ScoredGig) -> None:
        body = self._post(item)
        if body.get("error_code") == 429:
            wait = body.get("parameters", {}).get("retry_after", MAX_RETRY_AFTER_S + 1)
            if wait > MAX_RETRY_AFTER_S:
                raise NotifyError(f"rate limited, retry after {wait}s")
            time.sleep(wait)
            body = self._post(item)
        if not body.get("ok"):
            raise NotifyError(f"telegram error {body.get('error_code')}: {body.get('description')}")

    def _post(self, item: ScoredGig) -> dict:
        try:
            resp = self._client.post(
                self._url, json=_payload(item, self._settings.chat_id),
                timeout=SEND_TIMEOUT_S,
            )
            return resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            # from None: httpx messages can embed the URL, which holds the token.
            raise NotifyError(f"request failed: {type(exc).__name__}") from None
