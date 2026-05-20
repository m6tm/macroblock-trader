# 15 — Module Journal de Trading

## 15.1 Rôle

Le **Journal de Trading** est la mémoire structurée de chaque décision du bot. Il ne se contente pas de logger : il constitue la source de vérité pour l'apprentissage, l'amélioration continue et la traçabilité complète.

Chaque trade se voit attribuer un **numéro unique** (Trade ID) qui permet :
- Au bot de suivre le trade du début à la fin
- À l'utilisateur de revenir **après coup** pour indiquer si le trade a fonctionné ou échoué en réalité
- Au **cerveau vectoriel** de récupérer l'expérience complète pour comparaison future

> **Principe** : *"Ce qui n'est pas mesuré ne peut pas s'améliorer. Ce qui n'est pas journalisé n'a pas existé."*

---

## 15.2 Numérotation unique des trades

### Format du Trade ID

```
TRADE-YYYYMMDD-NNN

Exemples :
  TRADE-20260520-001   (1er trade du 20 mai 2026)
  TRADE-20260520-002   (2ème trade du 20 mai 2026)
  TRADE-20260521-001   (1er trade du 21 mai 2026)
```

| Composant | Signification | Exemple |
|-----------|---------------|---------|
| `TRADE` | Préfixe fixe | Identifie un trade réel (vs signal non exécuté) |
| `YYYYMMDD` | Date de génération du signal | 20260520 = 20 mai 2026 |
| `NNN` | Numéro séquentiel sur la journée | 001, 002, 003... |

### IDs secondaires

| Type | Format | Usage |
|------|--------|-------|
| **Signal ID** | `SIG-YYYYMMDD-NNN` | Identifie un signal avant exécution (même si non exécuté) |
| **Journal ID** | `JNL-YYYYMMDD-NNN` | Identifie une entrée de journal (même sans trade) |

> **Règle** : Un `SIG` devient un `TRADE` uniquement si l'utilisateur confirme l'exécution (`J'EXÉCUTE`).

---

## 15.3 Cycle de vie d'un trade

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  SIG-xxx │───→│ TRADE-xxx│───→│  ACTIVE  │───→│  CLOSED  │───→│ FEEDBACK │───→│ VALIDATED│
│ (signal) │    │(exécuté) │    │(ouvert)  │    │(virtuel) │    │(pending) │    │(final)   │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
                                                                                       │
                                                                                       ▼
                                                                               ┌──────────────┐
                                                                               │  ARCHIVED    │
                                                                               │  (historique)│
                                                                               └──────────────┘
```

### États détaillés

| État | Code | Description | Transition vers |
|------|------|-------------|-----------------|
| **GENERATED** | `GEN` | Signal créé, en attente de réponse utilisateur | EXECUTED (user) ou EXPIRED (temps) ou IGNORED (user) |
| **EXECUTED** | `EXE` | Utilisateur a confirmé l'exécution | ACTIVE |
| **ACTIVE** | `ACT` | Trade ouvert, suivi en cours | CLOSED_WIN, CLOSED_LOSS, CLOSED_BE, CLOSED_EXPIRED |
| **CLOSED_WIN** | `WIN` | Clôture virtuelle avec gain (TP1/TP2/TP3 atteint) | FEEDBACK_PENDING |
| **CLOSED_LOSS** | `LOSS` | Clôture virtuelle avec perte (SL touché) | FEEDBACK_PENDING |
| **CLOSED_BE** | `BE` | Clôture à break-even | FEEDBACK_PENDING |
| **CLOSED_EXPIRED** | `EXP` | Signal expiré sans entrée | FEEDBACK_PENDING (optionnel) |
| **FEEDBACK_PENDING** | `FBP` | En attente du feedback réel de l'utilisateur | VALIDATED ou AUTO_CLOSED |
| **VALIDATED** | `VAL` | Feedback utilisateur reçu et intégré | ARCHIVED |
| **AUTO_CLOSED** | `AUC` | Feedback automatique après 7 jours sans réponse | ARCHIVED |
| **ARCHIVED** | `ARC` | Trade figé dans l'historique | — |

---

## 15.4 Structure du journal (champs complets)

Chaque trade est stocké avec **plus de 40 champs** répartis en 6 catégories.

### A. Identification

| Champ | Type | Description |
|-------|------|-------------|
| `trade_id` | TEXT PRIMARY KEY | TRADE-YYYYMMDD-NNN |
| `signal_id` | TEXT | SIG-YYYYMMDD-NNN (lien vers le signal d'origine) |
| `created_at` | DATETIME | Timestamp de création du signal |
| `validated_at` | DATETIME | Timestamp de validation du feedback |

### B. Contexte marché (snapshot au moment du signal)

| Champ | Type | Description |
|-------|------|-------------|
| `signal_timestamp` | DATETIME | Heure exacte du signal |
| `xauusd_price` | REAL | Prix XAU/USD au moment du signal |
| `dxy_value` | REAL | Valeur du DXY |
| `dxy_trend_1h` | TEXT | Tendance DXY H1 (UP/DOWN/FLAT) |
| `us10y_yield` | REAL | Yield US10Y |
| `tips_10y` | REAL | Yield réel TIPS 10Y |
| `vix_value` | REAL | VIX |
| `macro_score` | INTEGER | Score macro Or (-3 à +3) |
| `macro_justification` | TEXT | Texte explicatif du score macro |
| `sentiment_score` | INTEGER | Score sentiment (-2 à +2) |
| `news_lock_active` | BOOLEAN | Lock macro actif ? |
| `killzone` | TEXT | Killzone active (Fix AM/PM/COMEX) |

### C. Setup technique

| Champ | Type | Description |
|-------|------|-------------|
| `setup_type` | TEXT | OB, OB+FVG, OB+FVG+Psy, FVG, etc. |
| `structure_h4` | TEXT | Tendance H4 (BULLISH/BEARISH/NEUTRAL) |
| `structure_h1` | TEXT | Tendance H1 |
| `bos_m15_confirmed` | BOOLEAN | BOS M15 confirmé ? |
| `ob_zone_low` | REAL | Low de l'Order Block |
| `ob_zone_high` | REAL | High de l'Order Block |
| `ob_freshness` | TEXT | FRESH / FIRST_MITIGATION / MITIGATED |
| `fvg_present` | BOOLEAN | FVG confluent présent ? |
| `fvg_zone_low` | REAL | Low du FVG |
| `fvg_zone_high` | REAL | High du FVG |
| `liquidity_target` | TEXT | Description de la liquidité ciblée |
| `liquidity_price` | REAL | Prix de la liquidité cible |
| `score_technical` | REAL | Score technique (0 à 5.5) |

### D. Plan de trade

| Champ | Type | Description |
|-------|------|-------------|
| `direction` | TEXT | BUY ou SELL |
| `grade` | TEXT | A+, B, C |
| `score_total` | REAL | Score total (0 à 5) |
| `entry_zone_low` | REAL | Borne basse zone d'entrée |
| `entry_zone_high` | REAL | Borne haute zone d'entrée |
| `entry_price_actual` | REAL | Prix d'entrée réel (si connu) |
| `sl_price` | REAL | Prix du Stop Loss |
| `sl_distance_dollars` | REAL | Distance SL en dollars |
| `tp1_price` | REAL | Prix TP1 |
| `tp2_price` | REAL | Prix TP2 |
| `tp3_price` | REAL | Prix TP3 (NULL si trail) |
| `rr_expected` | REAL | R:R attendu au moment du signal |
| `risk_pct` | REAL | % du capital risqué |
| `position_size_lots` | REAL | Taille en lots |

### E. Résultat virtuel (calculé par le bot)

| Champ | Type | Description |
|-------|------|-------------|
| `status_virtual` | TEXT | WIN / LOSS / BE / EXPIRED |
| `close_timestamp_virtual` | DATETIME | Heure de clôture virtuelle |
| `close_price_virtual` | REAL | Prix de clôture virtuelle |
| `pnl_virtual_dollars` | REAL | P&L virtuel en dollars |
| `pnl_virtual_pct` | REAL | P&L virtuel en % du capital |
| `duration_minutes` | INTEGER | Durée en minutes |
| `tp1_hit` | BOOLEAN | TP1 atteint ? |
| `tp2_hit` | BOOLEAN | TP2 atteint ? |
| `tp3_hit` | BOOLEAN | TP3 atteint ? |
| `sl_hit` | BOOLEAN | SL touché ? |
| `screenshot_path` | TEXT | Chemin vers capture d'écran |

### F. Feedback utilisateur (entrée manuelle)

| Champ | Type | Description |
|-------|------|-------------|
| `user_executed` | BOOLEAN | L'utilisateur a-t-il vraiment exécuté ? |
| `user_entry_price` | REAL | Prix d'entrée réel de l'utilisateur |
| `user_exit_price` | REAL | Prix de sortie réel |
| `user_exit_reason` | TEXT | SL / TP1 / TP2 / TP3 / MANUAL / STILL_OPEN |
| `pnl_real_dollars` | REAL | P&L réel rapporté par l'utilisateur |
| `pnl_real_pct` | REAL | P&L réel en % |
| `user_feedback_status` | TEXT | PENDING / SUBMITTED / AUTO_CLOSED |
| `user_feedback_timestamp` | DATETIME | Heure du feedback |
| `user_notes` | TEXT | Commentaires libres |
| `slippage_vs_bot` | REAL | Différence entrée bot vs entrée user |
| `execution_delay_min` | INTEGER | Délai entre signal et exécution (minutes) |
| `user_satisfaction` | INTEGER | Note 1–5 (optionnel) |

---

## 15.5 Interface de feedback utilisateur

### 15.5.1 Commandes Telegram

L'utilisateur peut interagir avec le journal via le bot Telegram :

| Commande | Usage | Exemple |
|----------|-------|---------|
| `/journal` | Afficher les 5 derniers trades | Liste avec ID et statut |
| `/journal open` | Afficher les trades en attente de feedback | Trades FBP |
| `/feedback <trade_id>` | Ouvrir le formulaire de feedback | `/feedback TRADE-20260520-001` |
| `/status <trade_id>` | Voir le détail complet d'un trade | Résumé + contexte |
| `/note <trade_id> <texte>` | Ajouter une note personnelle | `/note TRADE-20260520-001 J'ai fermé tôt par peur` |

### 15.5.2 Formulaire de feedback

Quand l'utilisateur tape `/feedback TRADE-20260520-001`, le bot envoie :

```
📋 FEEDBACK — TRADE-20260520-001

Setup: XAUUSD BUY A+ — Bullish OB + FVG
Signal: 20/05 14:32 GMT | Clôture virtuelle: 20/05 15:45 GMT
P&L virtuel: +78€ (+7.8 $)

❓ AS-TU EXÉCUTÉ CE TRADE ?
[✅ OUI]  [❌ NON]

--- (si OUI) ---

❓ QUEL RÉSULTAT AS-TU EU ?
[🎯 TP1]  [🎯 TP2]  [🎯 TP3]  [🛑 SL]  [✋ MANUEL]

❓ PRIX DE SORTIE RÉEL (optionnel):
[_______] $

❓ NOTES (optionnel):
[____________________]

[✅ VALIDER LE FEEDBACK]
```

### 15.5.3 Rappels automatiques

| Timing | Action |
|--------|--------|
| **+2h après clôture virtuelle** | Rappel discret si feedback non soumis |
| **+24h** | Rappel plus insistant |
| **+72h** | Dernier rappel avant auto-clôture |
| **+7 jours** | Auto-clôture avec statut "INCONNU", le trade reste utilisable par le cerveau vectoriel mais sans label réel |

---

## 15.6 Requêtes et exports du journal

### 15.6.1 Requêtes prédéfinies

| Requête | Description |
|---------|-------------|
| **Trades du jour** | Tous les trades avec signal_timestamp >= aujourd'hui |
| **En attente de feedback** | WHERE status = 'FEEDBACK_PENDING' |
| **Win rate par setup** | GROUP BY setup_type, COUNT(WIN)/COUNT(*) |
| **Win rate par killzone** | GROUP BY killzone |
| **Meilleurs trades** | ORDER BY pnl_real DESC LIMIT 10 |
| **Pires trades** | ORDER BY pnl_real ASC LIMIT 10 |
| **Trades similaires** | Utilisée par le cerveau vectoriel (voir doc 16) |

### 15.6.2 Exports

| Format | Contenu | Usage |
|--------|---------|-------|
| **CSV** | Tous les champs | Excel, analyse externe |
| **JSON** | Tous les champs + métadonnées | Intégration API |
| **PDF Rapport** | Synthèse mensuelle | Archive, présentation |

---

## 15.7 Schéma SQL (SQLite)

```sql
CREATE TABLE trades (
    -- Identification
    trade_id TEXT PRIMARY KEY,
    signal_id TEXT NOT NULL UNIQUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    validated_at DATETIME,

    -- Contexte marché
    signal_timestamp DATETIME NOT NULL,
    xauusd_price REAL,
    dxy_value REAL,
    dxy_trend_1h TEXT,
    us10y_yield REAL,
    tips_10y REAL,
    vix_value REAL,
    macro_score INTEGER,
    macro_justification TEXT,
    sentiment_score INTEGER,
    news_lock_active BOOLEAN DEFAULT 0,
    killzone TEXT,

    -- Setup technique
    setup_type TEXT,
    structure_h4 TEXT,
    structure_h1 TEXT,
    bos_m15_confirmed BOOLEAN DEFAULT 0,
    ob_zone_low REAL,
    ob_zone_high REAL,
    ob_freshness TEXT,
    fvg_present BOOLEAN DEFAULT 0,
    fvg_zone_low REAL,
    fvg_zone_high REAL,
    liquidity_target TEXT,
    liquidity_price REAL,
    score_technical REAL,

    -- Plan de trade
    direction TEXT NOT NULL,
    grade TEXT,
    score_total REAL,
    entry_zone_low REAL,
    entry_zone_high REAL,
    entry_price_actual REAL,
    sl_price REAL,
    sl_distance_dollars REAL,
    tp1_price REAL,
    tp2_price REAL,
    tp3_price REAL,
    rr_expected REAL,
    risk_pct REAL,
    position_size_lots REAL,

    -- Résultat virtuel
    status_virtual TEXT DEFAULT 'PENDING',
    close_timestamp_virtual DATETIME,
    close_price_virtual REAL,
    pnl_virtual_dollars REAL DEFAULT 0,
    pnl_virtual_pct REAL DEFAULT 0,
    duration_minutes INTEGER,
    tp1_hit BOOLEAN DEFAULT 0,
    tp2_hit BOOLEAN DEFAULT 0,
    tp3_hit BOOLEAN DEFAULT 0,
    sl_hit BOOLEAN DEFAULT 0,
    screenshot_path TEXT,

    -- Feedback utilisateur
    user_executed BOOLEAN DEFAULT 0,
    user_entry_price REAL,
    user_exit_price REAL,
    user_exit_reason TEXT,
    pnl_real_dollars REAL,
    pnl_real_pct REAL,
    user_feedback_status TEXT DEFAULT 'PENDING',
    user_feedback_timestamp DATETIME,
    user_notes TEXT,
    slippage_vs_bot REAL,
    execution_delay_min INTEGER,
    user_satisfaction INTEGER,

    -- Index pour performance
    FOREIGN KEY (signal_id) REFERENCES signals(signal_id)
);

CREATE INDEX idx_trades_date ON trades(signal_timestamp);
CREATE INDEX idx_trades_status ON trades(status_virtual);
CREATE INDEX idx_trades_feedback ON trades(user_feedback_status);
CREATE INDEX idx_trades_setup ON trades(setup_type, killzone);
```

---

*Documents liés : [08 — Flux de Travail](08-flux-travail.md) | [16 — Cerveau Vectoriel](16-cerveau-vectoriel.md) | [09 — Interface Utilisateur](09-interface-utilisateur.md)*
