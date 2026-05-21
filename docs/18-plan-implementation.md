# 18 — Plan d'Implémentation Atomique


---

## Choix Architectural

Avant de découper les tâches, le plan repose sur une décision structurelle explicite :

**Architecture retenue : Monolithe Modulaire Event-Driven (In-Process)**

Un seul processus Python, 8 modules fonctionnels découplés, communication via un bus d'événements en mémoire. Pas de microservices, pas d'architecture hexagonale stricte, pas de serveur.

### Pourquoi pas l'Hexagonale (Ports & Adapters) ?
Trop de boilerplate pour un projet solo. On garde l'esprit (isoler le métier), sans la cérémonie des interfaces et injections.

### Pourquoi pas les Microservices ?
Latence réseau incompatible avec le temps réel (M5/M15), complexité opérationnelle inutile pour 1 développeur.

### Pourquoi pas un Monolithe Classique (Big Ball of Mud) ?
8 modules avec imports circulaires = spaghetti. Le bus d'événements garantit que le module Macro ignore l'existence du module Scoring.

### Pourquoi pas Serverless ?
Cold start, limite de durée, coût imprévisible. Le bot tourne 24/5 en continu avec un état en mémoire.

### Structure de fichiers reflétant ce choix
```
src/
├── core/                    # Event Bus, config, exceptions, logging
│   ├── event_bus.py
│   ├── config.py
│   ├── exceptions.py
│   └── logger.py
├── modules/                 # 8 modules métiers (découplés)
│   ├── macro/
│   ├── sentiment/
│   ├── technical/
│   ├── fusion/
│   ├── risk/
│   ├── journal/
│   ├── vector_brain/
│   └── notifications/
├── data/                    # Fetchers, normaliseur, cache
├── engine/                  # Orchestration (si besoin, mais priorité au bus)
├── storage/                 # SQLite, repositories
├── memory/                  # ChromaDB, embeddings
├── main.py                  # Point d'entrée unique
└── __init__.py
```

---

## Sommaire

| Phase | Nom | Dépend de | Objectif |
|-------|-----|-----------|----------|
| 0 | Fondation | — | Structure, config, event bus interne |
| 1 | Couche Données | 0 | Ingestion, normalisation, cache temps réel |
| 2 | Module Technique SMC | 1 | Détection OB, FVG, structure, liquidité, scoring tech |
| 3 | Module Macro | 1 | DXY, yields, inflation, scoring macro Or |
| 4 | Module Sentiment | 1 | COT, retail ratios, scoring sentiment |
| 5 | Moteur Fusion & Scoring | 2, 3, 4 | Agrégation, plan de trade, invalidation |
| 6 | Gestion du Risque | 5 | Sizing, SL/TP, locks, validation risque |
| 7 | Journal de Trading | 6 | SQLite, Trade ID, cycle de vie, feedback |
| 8 | Cerveau Vectoriel | 7 | ChromaDB, embeddings, retrieval, ajustement |
| 9 | Notifications | 6 | Telegram, dashboard, commandes utilisateur |
| 10 | Agent Rédacteur Kimi | 9 | Moonshot AI, prompts, fallback templates |
| 11 | Tests & Qualité | 0–10 | Unit, intégration, backtest, validation vectorielle |
| 12 | Déploiement & Docs | 11 | Packaging, doc technique, CI/CD |

---

## Phase 0 — Fondation

**Objectif** : Le squelette du projet est opérationnel. On peut lancer le programme, charger la config, émettre un événement, et logger.

### 0.1 Environnement Python
- [x] Créer le virtualenv (`uv venv` ou `python -m venv`)
- [x] Initialiser `pyproject.toml` avec métadonnées, dépendances de base
- [x] Créer `.gitignore` adapté (Python, secrets, data, chroma_db)
- [x] Créer `README.md` technique (installation, lancement, structure)

### 0.2 Architecture de fichiers (Monolithe Modulaire)
- [x] Créer `src/core/` avec `__init__.py` (event bus, config, exceptions, logging)
- [x] Créer `src/modules/` avec un sous-dossier par module (`macro/`, `sentiment/`, `technical/`, `fusion/`, `risk/`, `journal/`, `vector_brain/`, `notifications/`)
- [x] Créer `src/data/`, `src/storage/`, `src/memory/`
- [x] Créer `src/main.py` (point d'entrée unique, un seul processus)
- [x] Créer les dossiers `config/`, `data/`, `logs/`, `screenshots/`, `tests/`, `notebooks/`
- [x] Règle d'or : aucun module sous `src/modules/` ne fait d'import direct d'un autre module du même niveau. Toute communication passe par le bus.

### 0.3 Gestion de configuration
- [x] Créer `config/settings.yaml` avec tous les paramètres par défaut
- [x] Créer `config/secrets.env` (template, non versionné)
- [x] Implémenter le loader de config (`src/core/config.py`) avec Pydantic
- [x] Valider la config au démarrage (types, bornes, valeurs obligatoires)

### 0.4 Event Bus interne (In-Process, pas de réseau)
- [x] Définir la classe de base `Event` (timestamp, type, payload, source_module)
- [x] Implémenter `EventBus` (pub/sub en mémoire, single-threaded ou async selon besoin)
- [x] Spécifier : pas de broker externe (Redis, RabbitMQ), pas de sérialisation JSON inutile — appels Python directs
- [x] Créer les classes d'événements typés :
  - `MarketDataEvent`
  - `MacroUpdateEvent`
  - `TechnicalSetupEvent`
  - `SignalGeneratedEvent`
  - `TradeExecutedEvent`
  - `TradeClosedEvent`
  - `UserFeedbackEvent`
  - `VectorMemoryEvent`
  - `SimilarTradesFoundEvent`
- [x] Implémenter le logger structuré (`loguru`) avec rotation
- [x] Écrire un test : émettre un événement, le recevoir dans un autre module, le logger

### 0.5 Exceptions & Résilience
- [x] Définir la hiérarchie d'exceptions custom (`DataFetchError`, `ValidationError`, `RiskLockError`...)
- [x] Implémenter le handler global d'exceptions dans `main.py`
- [x] Implémenter le mode "dégradation gracieuse" : si une source tombe, le bot continue
- [x] Un module en erreur ne doit jamais planter le bus ou les autres modules

**Validation de phase** : `python src/main.py` démarre sans erreur, charge la config, émet et loggue un événement test. Les modules sont importables sans imports croisés.

---

## Phase 1 — Couche Données

**Objectif** : Le bot récupère, normalise et stocke en temps réel toutes les données nécessaires.

### 1.1 Client API OANDA
- [x] Créer `src/data/oanda_client.py`
- [x] Implémenter l'authentification (clé API depuis `secrets.env`)
- [x] Implémenter `get_candles(pair, timeframe, count)` → retourne OHLCV
- [x] Implémenter le retry avec backoff exponentiel (3 tentatives)
- [x] Implémenter le rate limiting (respect des quotas OANDA)
- [x] Écrire les tests unitaires avec mocking des réponses HTTP

### 1.2 Récupération XAU/USD
- [x] Créer `src/data/fetcher.py`
- [x] Implémenter `fetch_xauusd_m5()` → DataFrame pandas
- [x] Implémenter `fetch_xauusd_m15()` → DataFrame pandas
- [x] Implémenter `fetch_xauusd_h1()` → DataFrame pandas
- [x] Implémenter `fetch_xauusd_h4()` → DataFrame pandas
- [x] Vérifier la cohérence des timestamps (pas de gap > 5 min en M5)

### 1.3 Récupération contexte marché (DXY, Yields, VIX)
- [x] Implémenter `fetch_dxy_m15()`
- [x] Implémenter `fetch_us10y()` (via yfinance ou FRED)
- [x] Implémenter `fetch_tips_10y()` (via FRED API)
- [x] Implémenter `fetch_vix_m15()`
- [x] Implémenter `fetch_sp500()`

### 1.4 Calendrier économique
- [x] Créer `src/data/calendar.py`
- [x] Implémenter le scraper ForexFactory (ou API alternative)
- [x] Parser les événements : date, heure, devise, impact (low/medium/high)
- [x] Identifier les événements à haut impact pour l'or (FOMC, NFP, CPI, PPI, PCE)
- [x] Implémenter le cache (rafraîchissement toutes les 5 minutes)
- [x] Écrire les tests avec HTML mocké

### 1.5 Normalisation & Cache temps réel
- [x] Créer `src/data/normalizer.py`
- [x] Normaliser les OHLCV (types float, timezone UTC, index datetime)
- [x] Créer le `DataStore` en mémoire (dict de DataFrames par pair/timeframe)
- [x] Implémenter `get_latest_ohlcv(pair, timeframe)`
- [x] Implémenter `get_historical_ohlcv(pair, timeframe, bars)`

### 1.6 Gestion des screenshots
- [x] Créer `src/data/screenshot.py`
- [x] Implémenter la capture du chart au moment du signal (via lightweight-charts ou matplotlib)
- [x] Sauvegarder dans `screenshots/SIG-xxx.png`

**Validation de phase** : Un script `python -m src.data.fetcher` récupère XAU/USD M5/M15/H1/H4, DXY, VIX, US10Y et les stocke en mémoire sans erreur.

---

## Phase 2 — Module Technique SMC

**Objectif** : Le bot détecte automatiquement les setups SMC sur XAU/USD.

### 2.1 Structure de Marché
- [ ] Créer `src/modules/technical/core.py`
- [ ] Implémenter `detect_swing_highs_lows(df, lookback)`
- [ ] Implémenter `detect_bos(df, direction)` — Break of Structure
- [ ] Implémenter `detect_choch(df, direction)` — Change of Character
- [ ] Implémenter `get_trend_h4()` / `get_trend_h1()` (BULLISH / BEARISH / NEUTRAL)
- [ ] Écrire les tests avec des fixtures de données connues

### 2.2 Détection des Order Blocks
- [ ] Implémenter `detect_bullish_ob(df, impulsion_threshold)`
- [ ] Implémenter `detect_bearish_ob(df, impulsion_threshold)`
- [ ] Calculer la fraîcheur de l'OB (jamais mitigué / première mitigation / mitigué)
- [ ] Accepter la mitigation à 50% pour l'or
- [ ] Retourner la zone exacte : `[ob_low, ob_high]`
- [ ] Écrire les tests avec des cas réels de charts XAU/USD

### 2.3 Détection des Fair Value Gaps
- [ ] Implémenter `detect_bullish_fvg(df)` — Low(N+2) > High(N)
- [ ] Implémenter `detect_bearish_fvg(df)` — High(N+2) < Low(N)
- [ ] Vérifier la confluence avec un OB (distance entre les zones < seuil)
- [ ] Retourner la zone FVG : `[fvg_low, fvg_high]`

### 2.4 Détection des Liquidité Pools
- [ ] Implémenter `detect_equal_highs(df, tolerance)`
- [ ] Implémenter `detect_equal_lows(df, tolerance)`
- [ ] Implémenter `detect_psychological_levels(price)` — niveaux xx00, xx50
- [ ] Implémenter `detect_previous_session_levels(df)` — day high/low, week high/low
- [ ] Implémenter `detect_trendline_liquidity(df)` (optionnel, version 2)

### 2.5 Scoring Technique
- [ ] Implémenter `score_structure(setup)` — H4/H1 alignés ?
- [ ] Implémenter `score_bos(setup)` — BOS M15 confirmé ?
- [ ] Implémenter `score_ob(setup)` — fraîcheur, timeframe
- [ ] Implémenter `score_fvg(setup)` — confluence ?
- [ ] Implémenter `score_liquidity(setup)` — cible claire ?
- [ ] Implémenter `score_killzone(setup)` — Fix AM/PM / COMEX ?
- [ ] Implémenter `score_dxy_alignment(setup, dxy_trend)` — bonus spécifique Or
- [ ] Implémenter `calculate_technical_score(setup)` — agrégation 0 à 5.5
- [ ] Score minimal pour signal : 3.0. Seuil A+ : 4.0

**Validation de phase** : Un script `python -m src.modules.technical` sur 48h de données XAU/USD détecte au moins 3 OB, 2 FVG, et attribue un score technique cohérent.

---

## Phase 3 — Module Macro

**Objectif** : Le bot calcule le score macro spécifique à l'or en temps réel.

### 3.1 Fetcher Macro
- [ ] Créer `src/modules/macro/core.py`
- [ ] Implémenter `get_dxy_momentum()` — variation M15, tendance H1
- [ ] Implémenter `get_us10y_value()`
- [ ] Implémenter `get_tips_10y_value()` (FRED, quotidien)
- [ ] Implémenter `get_vix_value()`
- [ ] Implémenter `get_sp500_momentum()`

### 3.2 Parser Calendrier Économique
- [ ] Implémenter `get_upcoming_high_impact_events(hours=2)`
- [ ] Implémenter `is_macro_lock_active()` — vérifier les fenêtres de blocage
- [ ] Implémenter `get_last_inflation_surprise()` — écart CPI/PPI vs consensus

### 3.3 Scoring Macro Or
- [ ] Implémenter `calculate_dxy_component(dxy_data)` — poids 30%
- [ ] Implémenter `calculate_yields_component(yields_data)` — poids 25%
- [ ] Implémenter `calculate_fed_policy_component()` — poids 20%
- [ ] Implémenter `calculate_risk_sentiment_component(vix, sp500)` — poids 15%
- [ ] Implémenter `calculate_inflation_surprise_component()` — poids 10%
- [ ] Implémenter `calculate_macro_score()` — agrégation -3 à +3
- [ ] Retourner la justification textuelle (pour le journal et les logs)

### 3.4 Macro Locks
- [ ] Implémenter `check_fomc_lock()`
- [ ] Implémenter `check_nfp_lock()`
- [ ] Implémenter `check_cpi_lock()`
- [ ] Implémenter `check_london_fix_lock()` — AM et PM
- [ ] Implémenter `check_comex_open_lock()`
- [ ] Implémenter `check_dxy_spike_lock()` — move > 0.2% en 5 min
- [ ] Implémenter `check_yield_spike_lock()` — move > 5bps en 5 min
- [ ] Implémenter `get_active_locks()` — liste des locks actifs avec raison

**Validation de phase** : Un script affiche le score macro actuel avec justification, et liste les locks actifs (si applicable).

---

## Phase 4 — Module Sentiment

**Objectif** : Le bot mesure le positionnement des marchés.

### 4.1 COT Report
- [ ] Créer `src/modules/sentiment/core.py`
- [ ] Implémenter le téléchargement hebdo du COT (CFTC.gov)
- [ ] Parser le fichier CSV pour extraire le positionnement Or (Non-Commercials vs Commercials)
- [ ] Calculer le ratio net long/short
- [ ] Détecter les extremes historiques (percentile 90/10)

### 4.2 Retail Ratios
- [ ] Implémenter le fetch des ratios retail (Myfxbook ou OANDA OrderBook)
- [ ] Parser le % de longs vs shorts sur XAU/USD
- [ ] Calculer le signal contrarian

### 4.3 Scoring Sentiment
- [ ] Implémenter `calculate_cot_signal()` — poids 40%
- [ ] Implémenter `calculate_retail_signal()` — poids 40%
- [ ] Implémenter `calculate_fear_greed_signal()` — poids 20%
- [ ] Implémenter `calculate_sentiment_score()` — agrégation -2 à +2

**Validation de phase** : Le module retourne un score sentiment cohérent avec les données du jour.

---

## Phase 5 — Moteur Fusion & Scoring

**Objectif** : Le bot agrège tous les scores et génère (ou rejette) un signal.

### 5.1 Formule de Scoring Globale
- [ ] Créer `src/modules/fusion/scoring.py`
- [ ] Implémenter `calculate_total_score(macro, technical, timing)`
- [ ] Pondération : Macro 30% + Tech 50% + Timing 20%
- [ ] Retourner le score brut et le score ajusté (si cerveau vectoriel actif)

### 5.2 Matrice de Décision
- [ ] Implémenter `evaluate_grade(score_total)` — A+ / B / C / N/A
- [ ] Implémenter `evaluate_macro_technique_matrix(macro, technical)`
- [ ] Vérifier les exceptions autorisées (macro neutre + tech 5.5/5.5)
- [ ] Rejeter tout signal < 2.5

### 5.3 Génération du Plan de Trade
- [ ] Créer `src/modules/fusion/signal.py`
- [ ] Implémenter `generate_trade_plan(setup, score, grade)`
- [ ] Calculer la zone d'entrée exacte (low/high de l'OB)
- [ ] Calculer le SL (wick + buffer ATR × 0.5, min 15$, max 1% prix)
- [ ] Calculer TP1 (premier FVG opposé / liquidité / niveau psy)
- [ ] Calculer TP2 (structure opposée / OB inverse H1)
- [ ] Calculer TP3 (Trail après BE)
- [ ] Calculer le R:R attendu
- [ ] Générer le `signal_id` (SIG-YYYYMMDD-NNN)
- [ ] Générer le `trade_id` (TRADE-YYYYMMDD-NNN) — réservé, activé si exécution

### 5.4 Invalidation Automatique
- [ ] Implémenter `check_invalidation_long(signal, current_price)` — cloture M5 sous OB
- [ ] Implémenter `check_invalidation_short(signal, current_price)` — cloture M5 au-dessus OB
- [ ] Implémenter `check_expiration(signal, current_time)` — 3 candles M15
- [ ] Implémenter `check_macro_invalidation(signal, active_locks)`

**Validation de phase** : Un script injecte un setup fictif et retourne un plan de trade complet avec grade, SL, TP, R:R — ou un rejet justifié.

---

## Phase 6 — Gestion du Risque

**Objectif** : Le bot valide que le plan respecte toutes les règles de risque.

### 6.1 Sizing
- [ ] Créer `src/modules/risk/sizing.py`
- [ ] Implémenter `calculate_position_size(capital, risk_pct, sl_distance_dollars)`
- [ ] Grade A+ → risk 1.0%, Grade B → risk 0.5%
- [ ] Vérifier que la taille en lots est physiquement réalisable

### 6.2 Validation SL
- [ ] Implémenter `validate_sl_distance(sl_distance_dollars, entry_price)`
- [ ] Min 15$, max 1.0% du prix
- [ ] Vérifier que le SL est technique (derrière le wick de l'OB)

### 6.3 Validation R:R
- [ ] Implémenter `validate_rr(rr_expected)`
- [ ] Minimum 1:2.0 sur l'or
- [ ] Rejeter le setup si R:R insuffisant

### 6.4 Locks de Risque
- [ ] Implémenter `check_max_trades_open(current_trades)` — max 1 sur XAU/USD
- [ ] Implémenter `check_drawdown_lock(current_drawdown)` — 2% journalier
- [ ] Implémenter `check_correlation_dxy_lock(direction, dxy_move_5min)` — move > 0.2%
- [ ] Implémenter `check_weekend_gap_lock()` — pas de signal avant cloture H1 dimanche
- [ ] Implémenter `run_full_risk_check(trade_plan)` — checklist complète 10 points

### 6.5 Journal des décisions risque
- [ ] Logger chaque check risque (passé ou rejeté) avec justification

**Validation de phase** : Un script teste 5 plans de trade (valides et invalides) et le risk engine accepte/rejette correctement chacun.

---

## Phase 7 — Journal de Trading

**Objectif** : Chaque trade est tracé avec un ID unique, un cycle de vie complet, et un feedback utilisateur.

### 7.1 Schéma SQLite
- [ ] Créer `src/modules/journal/database.py`
- [ ] Créer la table `trades` avec les 40+ champs (voir [15 — Module Journal](15-module-journal.md))
- [ ] Créer la table `signals` pour les signaux non exécutés
- [ ] Créer les indexes : `idx_trades_date`, `idx_trades_status`, `idx_trades_feedback`, `idx_trades_setup`
- [ ] Implémenter les migrations (Alembic ou version manuelle)

### 7.2 Gestion des IDs
- [ ] Implémenter `generate_signal_id()` → SIG-YYYYMMDD-NNN
- [ ] Implémenter `generate_trade_id()` → TRADE-YYYYMMDD-NNN
- [ ] Garantir l'unicité (incrément atomique, fichier de compteur ou MAX+1 SQL)

### 7.3 Cycle de vie du Trade
- [ ] Implémenter `create_signal(signal_data)` → état GENERATED
- [ ] Implémenter `execute_trade(signal_id, user_confirmed)` → SIG devient TRADE, état EXECUTED
- [ ] Implémenter `activate_trade(trade_id, entry_price)` → état ACTIVE
- [ ] Implémenter `close_trade_virtual(trade_id, exit_price, outcome)` → état CLOSED_WIN/LOSS/BE
- [ ] Implémenter `expire_signal(signal_id)` → état EXPIRED
- [ ] Implémenter `request_feedback(trade_id)` → état FEEDBACK_PENDING
- [ ] Implémenter `submit_feedback(trade_id, feedback_data)` → état VALIDATED
- [ ] Implémenter `auto_close_feedback(trade_id)` → état AUTO_CLOSED après 7 jours

### 7.4 Interface de Feedback
- [ ] Créer `src/modules/journal/queries.py`
- [ ] Implémenter `get_trades_awaiting_feedback()` — liste FBP
- [ ] Implémenter `get_trade_by_id(trade_id)`
- [ ] Implémenter `get_trades_by_setup_type(setup_type)`
- [ ] Implémenter `get_trades_by_killzone(killzone)`
- [ ] Implémenter `export_to_csv(filepath)`
- [ ] Implémenter `export_to_json(filepath)`

### 7.5 Journal Post-Trade
- [ ] Implémenter `log_post_trade(trade_id)` — format structuré pour logs

**Validation de phase** : Un script crée un signal, l'exécute, le cloture virtuellement, soumet un feedback, et vérifie que l'état final est VALIDATED avec tous les champs remplis.

---

## Phase 8 — Cerveau Vectoriel

**Objectif** : Le bot mémorise chaque trade et apprend des similarités.

### 8.1 Setup ChromaDB
- [ ] Créer `src/modules/vector_brain/store.py`
- [ ] Initialiser ChromaDB persistant (`./data/chroma_db/`)
- [ ] Créer la collection `gold_memory`
- [ ] Configurer la distance (cosine)

### 8.2 Embedding Engine
- [ ] Créer `src/modules/vector_brain/embedding.py`
- [ ] Charger le modèle `sentence-transformers/all-MiniLM-L6-v2`
- [ ] Implémenter `generate_embedding(trade_dict)` — texte descriptif → vecteur 384 dims
- [ ] Alternative : implémenter `generate_embedding_numeric(features_dict)` — features normalisées → vecteur

### 8.3 Vectorisation des Trades
- [ ] Implémenter `vectorize_trade(trade_id)`
- [ ] Récupérer le trade depuis SQLite
- [ ] Générer le texte descriptif du contexte + setup
- [ ] Encoder en vecteur
- [ ] Stocker dans ChromaDB avec métadonnées complètes

### 8.4 Retrieval k-NN
- [ ] Créer `src/modules/vector_brain/retrieval.py`
- [ ] Implémenter `find_similar_trades(setup_vector, n=5)`
- [ ] Filtrer : `user_executed = true`, `feedback_status = SUBMITTED`
- [ ] Retourner : trade_ids, similarités scores, métadonnées

### 8.5 Ajustement du Scoring
- [ ] Implémenter `calculate_adjustment(similar_trades)`
- [ ] Calculer WR similaire, P&L moyen, similarité moyenne
- [ ] Règles d'ajustement selon le mode (PASSIF / LÉGER / PLEIN)
- [ ] Intégrer dans `src/modules/fusion/scoring.py` (appel conditionnel)

### 8.6 Modes d'Activation
- [ ] Implémenter `get_vector_db_mode(trades_count)`
- [ ] < 30 trades → PASSIF (ajustement 0)
- [ ] 30–100 trades → LÉGER (±0.1)
- [ ] 100+ trades → PLEIN (±0.3)
- [ ] Configurable via `settings.yaml`

### 8.7 Consolidation Hebdomadaire
- [ ] Implémenter `weekly_clustering()` — clustering des vecteurs de la semaine
- [ ] Implémenter `generate_weekly_insights()` — patterns gagnants/perdants

**Validation de phase** : Un script vectorise 5 trades fictifs, recherche les plus similaires, et retourne un ajustement cohérent.

---

## Phase 9 — Notifications

**Objectif** : Le bot communique avec l'utilisateur via Telegram et un dashboard web.

### 9.1 Bot Telegram
- [ ] Créer `src/modules/notifications/telegram_bot.py`
- [ ] Initialiser le bot avec le token (depuis `secrets.env`)
- [ ] Implémenter la réception des commandes : `/status`, `/journal`, `/feedback`, `/note`
- [ ] Implémenter l'envoi d'alerte de signal (format riche avec boutons)
- [ ] Implémenter l'envoi de mise à jour (TP1 atteint, SL touché)
- [ ] Implémenter l'envoi de demande de feedback
- [ ] Implémenter les rappels automatiques (2h, 24h, 72h)

### 9.2 Templates d'Alertes
- [ ] Créer `src/modules/notifications/templates/`
- [ ] Template `signal_buy.md` / `signal_sell.md`
- [ ] Template `update_tp1.md`, `update_sl.md`, `trade_closed.md`
- [ ] Template `feedback_request.md`
- [ ] Template `daily_report.md`
- [ ] Template `weekly_report.md`

### 9.3 Dashboard Web (Streamlit)
- [ ] Créer `src/modules/notifications/dashboard.py`
- [ ] Page d'accueil : signaux du jour, performance rapide, macro board
- [ ] Page Signaux : liste filtrable, détail par signal
- [ ] Page Performance : graphiques de capital, WR par dimension
- [ ] Page Journal : table complète, export CSV
- [ ] Page Paramètres : capital, risque max, killzones actives

### 9.4 Commandes Utilisateur
- [ ] Implémenter le handler `/status`
- [ ] Implémenter le handler `/journal [open]`
- [ ] Implémenter le handler `/feedback <trade_id>`
- [ ] Implémenter le handler `/note <trade_id> <texte>`
- [ ] Implémenter le handler `/pause` et `/resume`

**Validation de phase** : Le bot envoie une alerte test sur Telegram et le dashboard s'affiche localement (`streamlit run`).

---

## Phase 10 — Agent Rédacteur Kimi

**Objectif** : Un agent optionnel qui rédige les alertes et rapports via Kimi-k2.6.

### 10.1 Client Moonshot AI
- [ ] Créer `src/modules/notifications/writer.py`
- [ ] Implémenter le client API Moonshot AI (compatible OpenAI)
- [ ] Charger la clé API depuis `secrets.env`
- [ ] Implémenter le timeout (5s max)
- [ ] Implémenter le retry (2 tentatives)
- [ ] Implémenter le budget max (0.50€/jour)

### 10.2 Prompts de Rédaction
- [ ] Créer `src/modules/notifications/prompts/`
- [ ] Prompt `alert_signal.md` — JSON technique → message Telegram
- [ ] Prompt `alert_update.md` — événement de trade → notification
- [ ] Prompt `daily_report.md` — KPIs → résumé narratif
- [ ] Prompt `weekly_report.md` — performance → analyse qualitative
- [ ] Prompt `explain_setup.md` — setup → explication pédagogique

### 10.3 Fallback Templates
- [ ] Implémenter `render_template(template_name, data)` (Jinja2)
- [ ] Si l'API Kimi est indisponible → fallback immédiat sur template
- [ ] Si le budget est dépassé → fallback sur template
- [ ] Flag `use_kimi_writer: true/false` dans `settings.yaml`

**Validation de phase** : Un script envoie un JSON technique au writer et retourne un message lisible. Test avec et sans connexion API.

---

## Phase 11 — Tests & Qualité

**Objectif** : Le système est testé, backtesté, et validé avant mise en production.

### 11.1 Tests Unitaires par Module
- [ ] Créer `tests/modules/test_macro.py` — scoring macro avec données mockées
- [ ] Créer `tests/modules/test_technical.py` — détection OB/FVG avec fixtures
- [ ] Créer `tests/modules/test_sentiment.py` — parsing COT, ratios
- [ ] Créer `tests/modules/test_fusion.py` — formule de scoring, matrice de décision
- [ ] Créer `tests/modules/test_risk.py` — sizing, SL, locks, validation
- [ ] Créer `tests/modules/test_journal.py` — cycle de vie complet d'un trade
- [ ] Créer `tests/modules/test_vector_brain.py` — vectorisation, retrieval, similarité
- [ ] Règle : chaque test de module ne mocke que ses dépendances externes (API), pas les autres modules

### 11.2 Tests d'Intégration (Event Bus)
- [ ] Test `test_event_bus_isolation.py` — vérifier que les modules ne s'importent pas directement
- [ ] Test `test_full_pipeline.py` — data → tech → macro → scoring → risk → signal (via bus)
- [ ] Test `test_event_bus_resilience.py` — un module planté ne bloque pas les autres
- [ ] Test `test_notification_pipeline.py` — signal → alerte Telegram simulée

### 11.3 Backtesting Historique
- [ ] Créer `notebooks/backtest.ipynb`
- [ ] Charger 6 mois d'historique XAU/USD M15
- [ ] Faire tourner le module Technique sur chaque candle
- [ ] Enregistrer tous les signaux générés
- [ ] Simuler l'exécution (entrée au milieu de l'OB, SL/TP atteints)
- [ ] Calculer : WR, Profit Factor, R:R moyen, drawdown max
- [ ] Comparer avec la baseline (wr attendu > 50%, PF > 1.5)

### 11.4 Validation du Cerveau Vectoriel
- [ ] Injecter 50 trades fictifs avec labels variés
- [ ] Vérifier que le retrieval trouve les plus proches voisins correctement
- [ ] Vérifier que l'ajustement améliore le score (ou ne le dégrade pas)
- [ ] Mesurer la latence : < 100ms par requête

### 11.5 Tests de Charge & Résilience
- [ ] Simuler le scan de 1000 candles M15 en boucle
- [ ] Mesurer le CPU/RAM usage
- [ ] Vérifier qu'aucune fuite mémoire ne se produit
- [ ] Tester la dégradation gracieuse : couper OANDA, vérifier que le bot continue (en mode dégradé)

**Validation de phase** : `pytest tests/` passe à 100%. Le backtest montre un WR > 50% et un PF > 1.3 sur 6 mois. L'Event Bus isole correctement les modules.

---

## Phase 12 — Déploiement & Documentation Technique

**Objectif** : Le projet est packagé, documenté, et prêt à tourner en continu sur une machine locale.

### 12.1 Packaging (Monolithe)
- [ ] Créer `requirements.txt` et `requirements-dev.txt`
- [ ] Vérifier que `pip install -e .` fonctionne sur une machine vierge
- [ ] Créer un script `run.sh` / `run.bat` pour lancer le bot (un seul processus)
- [ ] Créer un script `setup.sh` pour l'installation initiale
- [ ] **Pas de Docker, pas de docker-compose, pas de Kubernetes** — déploiement monolithique local

### 12.2 Documentation Technique
- [ ] Rédiger `docs/API.md` — interfaces publiques de chaque module (via Event Bus)
- [ ] Rédiger `docs/DATABASE.md` — schéma SQL complet, requêtes exemples
- [ ] Rédiger `docs/DEPLOYMENT.md` — installation, configuration, lancement
- [ ] Rédiger `docs/TROUBLESHOOTING.md` — problèmes courants et solutions
- [ ] Rédiger `docs/ARCHITECTURE.md` — diagramme de l'Event Bus et des modules

### 12.3 CI/CD (Optionnel)
- [ ] Créer `.github/workflows/tests.yml` — exécute pytest à chaque push
- [ ] Créer `.github/workflows/lint.yml` — ruff / black / mypy

### 12.4 Configuration Production
- [ ] Créer `config/settings.prod.yaml`
- [ ] Vérifier que le bot tourne 24/5 sans intervention
- [ ] Implémenter le redémarrage automatique en cas de crash (boucle interne dans `main.py`, pas de systemd obligatoire)
- [ ] Implémenter la sauvegarde automatique de la base SQLite (copie quotidienne dans `data/backups/`)
- [ ] Vérifier que ChromaDB persiste correctement entre les redémarrages

**Validation de phase** : Une personne tierce clone le repo, suit `docs/DEPLOYMENT.md`, et fait tourner le bot en 15 minutes.

---

## Graphe de Dépendances Simplifié

```
Phase 0 (Fondation)
    │
    ├──→ Phase 1 (Données)
    │         │
    │         ├──→ Phase 2 (Technique SMC)
    │         ├──→ Phase 3 (Macro)
    │         └──→ Phase 4 (Sentiment)
    │                   │
    │                   └──→ Phase 5 (Fusion)
    │                             │
    │                             ├──→ Phase 6 (Risque)
    │                             │         │
    │                             │         ├──→ Phase 7 (Journal)
    │                             │         │         │
    │                             │         │         └──→ Phase 8 (Cerveau)
    │                             │         │
    │                             │         └──→ Phase 9 (Notifications)
    │                             │                   │
    │                             │                   └──→ Phase 10 (Kimi)
    │                             │
    │                             └──→ Phase 11 (Tests)
    │                                       │
    │                                       └──→ Phase 12 (Déploiement)
```

---

*Document de planification atomique — Chaque case à cocher est une unité de travail indépendante et vérifiable.*
