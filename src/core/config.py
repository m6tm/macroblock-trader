"""Gestion centralisée de la configuration avec Pydantic."""

from pathlib import Path
from typing import List, Optional

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class TradingConfig(BaseSettings):
    """Paramètres de trading spécifiques à l'Or."""

    capital_base: float = Field(default=10_000.0, ge=1_000)
    risk_pct_a_plus: float = Field(default=1.0, ge=0.1, le=5.0)
    risk_pct_b: float = Field(default=0.5, ge=0.1, le=5.0)
    sl_max_pct_price: float = Field(default=1.0, ge=0.1, le=5.0)
    sl_min_dollars: float = Field(default=0.15, ge=0.05)
    rr_minimum: float = Field(default=2.0, ge=1.0)
    max_trades_simultaneous: int = Field(default=1, ge=1, le=5)
    asset: str = Field(default="XAU/USD")


class KillzoneConfig(BaseSettings):
    """Killzones actives et leurs horaires (heures GMT)."""

    london_fix_am: bool = True
    london_fix_pm: bool = True
    ny_open_comex: bool = True
    london_open: bool = True
    asia: bool = False
    ny_close: bool = False


class TimeframeConfig(BaseSettings):
    """Timeframes de scan."""

    entry: str = "M15"
    refinement: str = "M5"
    trend_h1: str = "H1"
    trend_h4: str = "H4"


class NotificationConfig(BaseSettings):
    """Configuration des notifications."""

    telegram_enabled: bool = False
    telegram_chat_id: Optional[str] = None
    dashboard_enabled: bool = True
    dashboard_port: int = 8501


class Settings(BaseSettings):
    """Configuration globale de l'application."""

    model_config = SettingsConfigDict(
        env_file="config/secrets.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API keys (peuvent être surchargées par secrets.env)
    oanda_api_key: Optional[str] = None
    oanda_account_id: Optional[str] = None
    fred_api_key: Optional[str] = None
    moonshot_api_key: Optional[str] = None
    telegram_bot_token: Optional[str] = None

    # Modules
    trading: TradingConfig = Field(default_factory=TradingConfig)
    killzones: KillzoneConfig = Field(default_factory=KillzoneConfig)
    timeframes: TimeframeConfig = Field(default_factory=TimeframeConfig)
    notifications: NotificationConfig = Field(default_factory=NotificationConfig)

    # Chemins
    data_dir: Path = Path("data")
    log_dir: Path = Path("logs")
    screenshot_dir: Path = Path("screenshots")
    config_dir: Path = Path("config")
    chroma_db_dir: Path = Path("data/chroma_db")

    @field_validator("data_dir", "log_dir", "screenshot_dir", "config_dir", "chroma_db_dir")
    @classmethod
    def ensure_path(cls, v: Path) -> Path:
        v.mkdir(parents=True, exist_ok=True)
        return v


def load_settings(yaml_path: Path = Path("config/settings.yaml")) -> Settings:
    """Charge la configuration depuis YAML + variables d'environnement.

    Le fichier YAML est optionnel — les valeurs par défaut de Settings
    suffisent pour démarrer.
    """
    kwargs: dict = {}
    if yaml_path.exists():
        with yaml_path.open("r", encoding="utf-8") as fh:
            kwargs = yaml.safe_load(fh) or {}

    return Settings(**kwargs)


def validate_startup(settings: Settings) -> None:
    """Valide la configuration au démarrage. Lève ConfigValidationError si invalide.

    Vérifie :
      - Présence des clés API si les modules associés sont activés
      - Cohérence des paramètres de risque
      - Existence du répertoire de config
    """
    from core.exceptions import ConfigValidationError

    # 1. Risque cohérent
    if settings.trading.risk_pct_b > settings.trading.risk_pct_a_plus:
        raise ConfigValidationError(
            f"risk_pct_b ({settings.trading.risk_pct_b}) ne peut pas dépasser "
            f"risk_pct_a_plus ({settings.trading.risk_pct_a_plus})"
        )

    # 2. Clés API si notifications Telegram activées
    if settings.notifications.telegram_enabled:
        if not settings.telegram_bot_token:
            raise ConfigValidationError(
                "telegram_enabled=True mais TELEGRAM_BOT_TOKEN manquant"
            )
        if not settings.notifications.telegram_chat_id:
            raise ConfigValidationError(
                "telegram_enabled=True mais telegram_chat_id manquant"
            )

    # 3. Timeframes reconnus
    valid_tfs = {"M1", "M5", "M15", "M30", "H1", "H4", "D1"}
    for attr in ("entry", "refinement", "trend_h1", "trend_h4"):
        tf = getattr(settings.timeframes, attr)
        if tf not in valid_tfs:
            raise ConfigValidationError(
                f"Timeframe invalide pour '{attr}': {tf} (attendu {valid_tfs})"
            )

    # 4. Capital suffisant
    if settings.trading.capital_base < 100:
        raise ConfigValidationError(
            f"capital_base trop faible: {settings.trading.capital_base} (min 100)"
        )
