# 11 — Stack Technique Suggéré

> **Note** : Ce document présente les technologies recommandées. Le choix final revient à l'utilisateur après analyse de ses contraintes (hébergement, budget, compétences).

## 11.1 Critères de sélection

| Critère | Priorité | Justification |
|---------|----------|---------------|
| Gratuit / Open Source | Élevée | Pas de coûts récurrents pour un projet personnel |
| Local first | Élevée | Données de trading sensibles, pas de dépendance cloud |
| Temps réel | Élevée | M5/M15 nécessitent une latence faible |
| Extensible | Moyenne | Ajout futur de nouveaux modules ou paires |
| Facilité de déploiement | Moyenne | Doit tourner sur un laptop standard |

## 11.2 Architecture technique cible

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         COUCHE DONNÉES                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │
│  │  OANDA API   │  │   ForexFactory│  │   COT (CFTC) │  │  FRED/Quandl│ │
│  │  (prix temps │  │   (calendrier │  │   (hebdo)    │  │  (yields)   │ │
│  │   réel)      │  │   éco)        │  │              │  │             │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬──────┘ │
│         │                 │                 │                 │        │
│         └─────────────────┴─────────────────┴─────────────────┘        │
│                                     │                                  │
│                         ┌───────────▼───────────┐                     │
│                         │   Python (ingestion)   │                     │
│                         │   pandas, requests     │                     │
│                         └───────────┬───────────┘                     │
│                                     │                                  │
├─────────────────────────────────────┼──────────────────────────────────┤
│                         COUCHE MÉTIER                                  │
│                                     ▼                                  │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │              MOTEUR D'ANALYSE (Python)                           │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌───────────┐ │  │
│  │  │  Macro  │ │Sentiment│ │  Tech   │ │ Scoring │ │   Risk    │ │  │
│  │  │  Engine │ │ Engine  │ │ Engine  │ │ Engine  │ │  Engine   │ │  │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └───────────┘ │  │
│  │                                                                  │  │
│  │  Librairies: numpy, pandas_ta, scipy, talib (optionnel)         │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                     │                                  │
├─────────────────────────────────────┼──────────────────────────────────┤
│                      COUCHE PRÉSENTATION                               │
│                                     ▼                                  │
│  ┌─────────────────────────┐    ┌─────────────────────────────────┐   │
│  │   Dashboard (Streamlit) │    │   Alertes (python-telegram-bot) │   │
│  │   ou Dash (Plotly)      │    │                                 │   │
│  └─────────────────────────┘    └─────────────────────────────────┘   │
│                                     │                                  │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │   Stockage: SQLite (trades) + JSON (config) + CSV (exports)     │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

## 11.3 Composants détaillés

### 11.3.1 Language principal : Python

| Aspect | Recommandation |
|--------|----------------|
| Version | Python 3.11+ (performance, typing) |
| Gestion d'environnement | `venv` ou `uv` |
| Gestion de dépendances | `requirements.txt` ou `pyproject.toml` |

**Pourquoi Python ?**
- Écosystème data science mature (pandas, numpy, scipy)
- Librairies technique analysis (pandas_ta, ta-lib, finta)
- Facilité de prototypage rapide
- Grande communauté pour le support

### 11.3.2 Données de marché

| Source | Usage | Coût | Alternative |
|--------|-------|------|-------------|
| **OANDA API** | Prix temps réel Forex, exécution papier | Gratuit (compte démo) | FXCM, IG, Dukascopy |
| **yfinance** | Indices, yields, matières premières | Gratuit | FRED API, Quandl |
| **ForexFactory** | Calendrier économique | Gratuit (scraping) | Investing.com, Myfxbook |
| **CFTC.gov** | COT Report | Gratuit (CSV hebdo) | — |
| **Myfxbook** | Ratios retail | Gratuit (API limitée) | OANDA OrderBook |

### 11.3.3 Librairies Python recommandées

| Catégorie | Librairie | Usage |
|-----------|-----------|-------|
| Data manipulation | `pandas`, `numpy` | OHLCV, calculs, filtres |
| Technical analysis | `pandas_ta` | Indicateurs techniques, ATR |
| SMC personnalisé | Code custom | Détection OB, FVG, structure |
| Data fetch | `requests`, `websocket-client` | APIs REST et WebSocket |
| Async | `asyncio`, `aiohttp` | Traitement parallèle |
| Scheduling | `APScheduler` | Tâches cron (COT, récap) |
| Dashboard | `streamlit` | Interface web rapide |
| Charts | `plotly`, `lightweight-charts` | Visualisation des prix |
| Alertes | `python-telegram-bot` | Bot Telegram |
| Database | `sqlite3` (built-in) | Stockage des trades |
| **Vector DB** | **`chromadb`** | **Mémoire vectorielle, similarité trades** |
| **Embedding** | **`sentence-transformers`** | **Encodage trades en vecteurs** |
| **LLM rédacteur** | **`openai` compatible Moonshot AI** ou **`ollama`** | **Rédaction alertes via Kimi-k2.6 (optionnel)** |
| Config | `pydantic`, `python-dotenv` | Validation et gestion de config |
| Logging | `loguru` | Logs structurés et lisibles |

### 11.3.4 Dashboard Web

**Option A : Streamlit (Recommandé pour le début)**

| Avantage | Inconvénient |
|----------|--------------|
| Prototypage ultra-rapide | Moins flexible pour UI complexe |
| Python natif | Performance limitée pour gros volumes |
| Déploiement simple | Refresh automatique un peu lourd |
| Gratuit | — |

**Option B : Dash (Plotly)**

| Avantage | Inconvénient |
|----------|--------------|
| Plus flexible, plus pro | Courbe d'apprentissage plus élevée |
| Composants React intégrables | Nécessite plus de code |
| Performances meilleures | — |

### 11.3.5 Stockage

| Donnée | Format | Justification |
|--------|--------|---------------|
| **Trades historiques** | SQLite | Requêtes SQL, rapports, intégrité |
| **Mémoire vectorielle** | ChromaDB (fichier local) | `data/chroma_db/` — similarité, apprentissage |
| **Configuration** | JSON / YAML | Lisible, versionnable, modifiable à la main |
| **Logs** | Fichiers texte rotatifs | `logs/trades_2026-05.log` |
| **Exports utilisateur** | CSV | Compatible Excel, Google Sheets |
| **Screenshots** | PNG | `screenshots/SIG-xxx.png` |

## 11.4 Infrastructure

### 11.4.1 Hébergement local (Recommandé au départ)

| Composant | Spécification minimale |
|-----------|------------------------|
| Machine | Laptop / PC standard (Windows, Mac, Linux) |
| RAM | 4 GB (suffisant pour 10 paires en temps réel) |
| Disque | 1 GB (données historiques légères) |
| Connexion | Internet stable (pas besoin de fibre) |
| Uptime | Marchés ouverts uniquement (pas besoin 24/7 au début) |

### 11.4.2 Hébergement VPS (optionnel, phase 2)

Si tu veux que le bot tourne 24/5 sans laisser ton PC allumé :

| Fournisseur | Coût mensuel estimé | Spécification |
|-------------|---------------------|---------------|
| DigitalOcean | 4–6 € | 1 vCPU, 1 GB RAM |
| Hetzner | 4–5 € | 1 vCPU, 2 GB RAM |
| AWS Lightsail | 3–5 € | 1 vCPU, 512 MB RAM (juste) |

### 11.4.3 Sécurité

| Mesure | Application |
|--------|-------------|
| **Pas de clés API de trading réel** | Le bot n'a besoin que d'une API de données (OANDA démo) |
| **Fichier `.env`** | Clés API hors du code source |
| **`.gitignore`** | Pas de secrets dans Git |
| **Firewall local** | Pas de port exposé si pas de dashboard externe |

## 11.5 Architecture de fichiers suggérée (projet)

```
macroblock-trader/
├── config/
│   ├── settings.yaml          # Paramètres généraux
│   ├── pairs.yaml             # Liste des paires et leurs configs
│   └── secrets.env            # Clés API (non versionné)
├── src/
│   ├── __init__.py
│   ├── main.py                # Point d'entrée
│   ├── data/
│   │   ├── fetcher.py         # Récupération des données
│   │   ├── oanda_client.py    # Client API OANDA
│   │   └── calendar.py        # Calendrier économique
│   ├── analysis/
│   │   ├── macro.py           # Module Macro
│   │   ├── sentiment.py       # Module Sentiment
│   │   └── technical.py       # Module Technique (SMC)
│   ├── engine/
│   │   ├── scoring.py         # Moteur de fusion
│   │   ├── risk.py            # Gestion du risque
│   │   └── signal.py          # Génération des signaux
│   ├── memory/
│   │   ├── vector_store.py    # Interface ChromaDB
│   │   ├── embedding.py       # Encodage trades en vecteurs
│   │   └── retrieval.py       # Recherche de similarité
│   ├── notifications/
│   │   ├── telegram_bot.py    # Bot Telegram
│   │   ├── dashboard.py       # Streamlit/Dash
│   │   └── writer.py          # Agent Rédacteur Kimi-k2.6 (optionnel)
│   └── storage/
│       ├── database.py        # Interface SQLite
│       └── journal.py         # Gestion du journal
├── notebooks/
│   └── exploration.ipynb      # Tests et analyses
├── tests/
│   ├── test_macro.py
│   ├── test_technical.py
│   └── test_scoring.py
├── logs/
│   └── app.log
├── screenshots/
│   └── .gitkeep
├── data/
│   └── macroblock.db          # Base SQLite
├── docs/                      # Documentation de conception
├── requirements.txt
├── pyproject.toml
└── README.md
```

## 11.6 Plan de développement par phases

| Phase | Durée estimée | Livrable |
|-------|---------------|----------|
| **Phase 1** : Fondation | 1 semaine | Connexion API, récupération des prix, stockage SQLite |
| **Phase 2** : Module Technique | 1 semaine | Détection OB, FVG, structure, scoring technique |
| **Phase 3** : Module Macro | 3–4 jours | Calendrier éco, scoring macro basique |
| **Phase 4** : Moteur de fusion | 3–4 jours | Scoring global, génération des signaux |
| **Phase 5** : Gestion risque | 2–3 jours | Sizing, SL/TP, locks, corrélation |
| **Phase 6** : Notifications | 2–3 jours | Telegram bot, formatage des alertes |
| **Phase 7** : Dashboard | 3–4 jours | Streamlit avec charts et performance |
| **Phase 8** : Cerveau Vectoriel | 3–4 jours | ChromaDB, embeddings, retrieval, intégration scoring |
| **Phase 9** : Agent Rédacteur (optionnel) | 2–3 jours | Intégration Kimi-k2.6 (Moonshot AI) pour alertes et rapports |
| **Phase 10** : Polish | 1 semaine | Tests, bugfix, optimisation, documentation |

**Total estimé** : 6–7 semaines à temps partiel (5–6 sans le cerveau vectoriel et l'agent rédacteur).

---

*Document informatif — Le choix technologique final est à valider par l'utilisateur.*
