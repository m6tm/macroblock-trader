# MacroBlock Trader — XAU/USD (Or)

Système automatisé d'analyse et de génération de signaux de trading sur l'Or (XAU/USD), basé sur la méthodologie **Smart Money Concepts (SMC)** et **Order Blocks**.

> **Paper Trading uniquement** — Le bot ne se connecte jamais à un compte de trading réel. Il analyse, génère des signaux fictifs, et trace leur performance théorique. L'utilisateur exécute manuellement les trades qu'il souhaite.

---

## Installation

### Avec Conda (recommandé — Linux/macOS/Windows)

```bash
# Methode 1 : script automatique
bash setup_conda.sh

# Methode 2 : manuel
conda env create -f environment.yml
conda activate macroblock
pip install -e ".[dev]"
```

### Avec venv + pip (Termux/Android, ou sans Conda)

```bash
# Methode 1 : script automatique
bash setup.sh

# Methode 2 : manuel
python -m venv venv --system-site-packages
source venv/bin/activate  # Windows : venv\Scripts\activate
pip install --upgrade pip
pip install -e ".[dev]"
```

> **Note Termux** : Conda n'est pas nativement supporté sur Android/Termux. Utilisez la méthode `venv` ci-dessus.

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

3. Ajuster `config/settings.yaml` selon vos préférences (risque, killzones...).

---

## Lancement

```bash
# Avec l'environnement active
python src/main.py
```

---

## Validation par phase

```bash
# Phase 0 — Fondation
python tests/test_phase0.py

# Phase 1 — Données
python tests/test_phase1.py

# Phase 2 — Technique SMC
python tests/modules/test_technical.py

# Phase 3 — Macro
python tests/modules/test_macro.py

# Phase 4 — Sentiment
python tests/modules/test_sentiment.py

# Phase 5 — Fusion
python tests/modules/test_fusion.py

# Tests d'intégration (e2e)
python tests/integration/test_event_bus.py
python tests/integration/test_data_pipeline.py
python tests/integration/test_modules_pipeline.py
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
│   │   ├── risk/        # Gestion du risque, sizing, locks (retourné par l'utilisateur)
│   │   ├── journal/     # SQLite, cycle de vie des trades
│   │   ├── vector_brain/# Mémoire vectorielle, retrieval, ajustement
│   │   └── notifications/ # Telegram, dashboard Streamlit
│   ├── storage/         # Repositories SQLite
│   └── main.py          # Point d'entrée unique
└── tests/               # Tests unitaires et d'intégration
    ├── integration/     # Tests e2e (Event Bus, Data, Modules Pipeline)
    ├── modules/         # Tests unitaires par module
    ├── test_phase0.py   # Validation Phase 0
    └── test_phase1.py   # Validation Phase 1
```

---

## 🧪 Tests

```bash
# Tous les tests
python tests/test_phase0.py
python tests/test_phase1.py
python tests/modules/test_technical.py
python tests/modules/test_macro.py
python tests/modules/test_sentiment.py
python tests/modules/test_fusion.py
python tests/integration/test_event_bus.py
python tests/integration/test_data_pipeline.py
python tests/integration/test_modules_pipeline.py
```

---

## License

MIT
