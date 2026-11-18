import os

from dotenv import load_dotenv
from pydantic import BaseModel, Field, SecretStr


class TelegramSettings(BaseModel):
    bot_token: SecretStr = Field(min_length=1)
    chat_id: str = Field(min_length=1)

    @classmethod
    def from_env(cls) -> "TelegramSettings":
        load_dotenv()
        return cls(
            bot_token=os.environ.get("TELEGRAM_BOT_TOKEN", ""),
            chat_id=os.environ.get("TELEGRAM_CHAT_ID", ""),
        )
