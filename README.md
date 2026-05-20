# MacroBlock Trader — XAU/USD (Or)

Système automatisé d'analyse et de génération de signaux de trading sur l'Or (XAU/USD), basé sur la méthodologie **Smart Money Concepts (SMC)** et **Order Blocks**.

> **Paper Trading uniquement** — Le bot ne se connecte jamais à un compte de trading réel. Il analyse, génère des signaux fictifs, et trace leur performance théorique. L'utilisateur exécute manuellement les trades qu'il souhaite.

---

## Installation

### Avec Conda (recommandé)

```bash
conda env create -f environment.yml
conda activate macroblock
```

### Avec venv + pip

```bash
python -m venv venv
source venv/bin/activate  # Windows : venv\Scripts\activate
pip install -e ".[dev]"
```

---

## Configuration

1. Copier le template de secrets :
   ```bash
   cp config/secrets.env.template config/secrets.env
   ```

2. Éditer `config/secrets.env` avec vos clés API :
   - `OANDA_API_KEY` — Clé API OANDA (pratique)
   - `OANDA_ACCOUNT_ID` — ID de compte OANDA
   - `TELEGRAM_BOT_TOKEN` — Token du bot Telegram (optionnel)
   - `TELEGRAM_CHAT_ID` — ID du chat Telegram (optionnel)
   - `FRED_API_KEY` — Clé API FRED (optionnel)
   - `MOONSHOT_API_KEY` — Clé API Moonshot AI (optionnel)

3. Ajuster `config/settings.yaml` selon vos préférences (capital, risque, killzones...).

---

## Lancement

```bash
python src/main.py
```

---

## Structure du projet

```
├── config/              # Configuration (YAML + secrets)
├── data/                # Données brutes et cache
├── logs/                # Logs structurés (loguru)
├── notebooks/           # Notebooks d'analyse & backtest
├── screenshots/         # Captures d'écran au moment des signaux
├── src/
│   ├── core/            # Event Bus, config, exceptions, logging
│   ├── data/            # Fetchers, normaliseur, cache temps réel
│   ├── engine/          # Orchestration (si besoin)
│   ├── memory/          # ChromaDB, embeddings
│   ├── modules/         # 8 modules métiers découplés
│   │   ├── macro/       # Analyse macroéconomique (DXY, yields, inflation)
│   │   ├── sentiment/   # COT, retail ratios, fear/greed
│   │   ├── technical/   # Détection OB, FVG, BOS, liquidité
│   │   ├── fusion/      # Moteur de scoring et génération de signaux
│   │   ├── risk/        # Gestion du risque, sizing, locks
│   │   ├── journal/     # SQLite, cycle de vie des trades
│   │   ├── vector_brain/# Mémoire vectorielle, retrieval, ajustement
│   │   └── notifications/ # Telegram, dashboard Streamlit
│   ├── storage/         # Repositories SQLite
│   └── main.py          # Point d'entrée unique
└── tests/               # Tests unitaires et d'intégration
```

---

## 🧪 Tests

```bash
pytest tests/
```

---

## License

MIT
