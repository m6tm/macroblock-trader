"""Hiérarchie d'exceptions custom du projet MacroBlock."""


class MacroBlockError(Exception):
    """Exception de base pour tous les erreurs du système."""
    pass


class DataFetchError(MacroBlockError):
    """Échec de récupération de données externe (API, scraper...)."""
    pass


class ConfigValidationError(MacroBlockError):
    """Configuration invalide ou incomplète."""
    pass


class RiskLockError(MacroBlockError):
    """Un lock de risque bloque la génération ou l'exécution d'un trade."""
    pass


class SignalValidationError(MacroBlockError):
    """Un signal ne passe pas les validations (score, R:R, etc.)."""
    pass


class TradeLifecycleError(MacroBlockError):
    """Transition d'état impossible dans le cycle de vie d'un trade."""
    pass


class VectorStoreError(MacroBlockError):
    """Erreur liée au cerveau vectoriel (ChromaDB, embeddings...)."""
    pass
