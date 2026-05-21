"""Accès rapide aux secrets critiques du projet.

Charge config/secrets.env automatiquement via pydantic_settings.
"""

from core.config import load_settings

_settings = load_settings()

OANDA_API_KEY: str = _settings.oanda_api_key or ""
OANDA_ACCOUNT_ID: str = _settings.oanda_account_id or ""

FRED_API_KEY: str = _settings.fred_api_key or ""
MOONSHOT_API_KEY: str = _settings.moonshot_api_key or ""

TELEGRAM_BOT_TOKEN: str = _settings.telegram_bot_token or ""
TELEGRAM_CHAT_ID: str = _settings.notifications.telegram_chat_id or ""

__all__ = [
    "OANDA_API_KEY",
    "OANDA_ACCOUNT_ID",
    "FRED_API_KEY",
    "MOONSHOT_API_KEY",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
]
