# 02 — Architecture Système

## 2.1 Vue d'ensemble

Le système est conçu selon une architecture modulaire et découplée. Chaque module a une responsabilité unique. Les modules communiquent via un bus de données interne (messages/events) plutôt que par des appels directs rigides.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         MACROBLOCK TRADER                               │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────────┐  │
│  │   MODULE     │  │   MODULE     │  │      MODULE TECHNIQUE        │  │
│  │   MACRO      │  │  SENTIMENT   │  │    (Order Blocks & SMC)      │  │
│  └──────┬───────┘  └──────┬───────┘  └────────────┬─────────────────┘  │
│         │                 │                       │                    │
│         └─────────────────┼───────────────────────┘                    │
│                           ▼                                            │
│              ┌────────────────────────────┐                           │
│              │      FUSION & SCORING      │                           │
│              │   (Macro + Tech + Risk     │                           │
│              │    + Cerveau Vectoriel)    │                           │
│              └──────────────┬─────────────┘                           │
│                             ▼                                          │
│              ┌────────────────────────────┐                           │
│              │      MOTEUR DE SIGNAUX     │                           │
│              │   (Entrée / Sortie /       │                           │
│              │    Invalidation)           │                           │
│              └──────────────┬─────────────┘                           │
│                             ▼                                          │
│              ┌────────────────────────────┐                           │
│              │      GESTION DU RISQUE     │                           │
│              │   (Sizing, SL, R:R,        │                           │
│              │    Corrélation)            │                           │
│              └──────────────┬─────────────┘                           │
│                             ▼                                          │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │                      NOTIFICATION ENGINE                        │   │
│  │    (Dashboard + Alertes Push + Journal + Cerveau + Rédacteur)  │   │
│  └────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         UTILISATEUR (TOI)                              │
│         Tu reçois le signal → Tu analyses → Tu décides →               │
│                    Tu exécutes manuellement                             │
└─────────────────────────────────────────────────────────────────────────┘
```

## 2.2 Modules fonctionnels

### Module Macro — "Le Vent"
**Responsabilité** : Déterminer la direction privilégiée du marché et filtrer les setups contre-tendance.

### Module Sentiment — "La Foule"
**Responsabilité** : Mesurer le positionnement retail et institutionnel pour identifier les extremes.

### Module Technique — "La Carte"
**Responsabilité** : Identifier les zones de haute probabilité technique (OB, FVG, liquidité, structure).

### Module Fusion & Scoring — "Le Juge"
**Responsabilité** : Agréger les outputs des trois modules en un score unique et une décision binaire (Trade / No Trade). **Le Cerveau Vectoriel peut ajuster ce score de ±0.3 selon l'historique des setups similaires.**

### Module Gestion du Risque — "Le Garde-fou"
**Responsabilité** : Calculer la taille de position, les niveaux de SL/TP, et bloquer les trades non conformes aux règles de risque.

### Module Journal — "L'Historien"
**Responsabilité** : Enregistrer chaque trade avec un **Trade ID unique** (TRADE-YYYYMMDD-NNN), tracer son cycle de vie complet, et collecter le **feedback utilisateur** après coup.

### Module Cerveau Vectoriel — "La Mémoire"
**Responsabilité** : Vectoriser chaque trade dans une base de données vectorielle (ChromaDB), rechercher les expériences similaires lorsqu'un nouveau setup se forme, et ajuster le scoring en fonction de l'historique.

### Module Rédacteur (LLM) — "Le Styliste" (Optionnel)
**Responsabilité** : Transformer les outputs techniques (JSON) en texte humain et lisible pour les alertes Telegram et les rapports. **Zéro autorité décisionnelle** — il ne fait que présenter des données déjà calculées par les modules classiques.

### Module Notification — "Le Messager"
**Responsabilité** : Formater et diffuser les alertes vers l'utilisateur, ainsi que logger tous les événements. Intègre les insights du Cerveau Vectoriel dans les notifications. Utilise l'Agent Rédactur si activé, sinon des templates statiques.

## 2.3 Flux de données

### Flux principal ( temps réel )

```
[Data Sources]
      │
      ├──→ Forex API (prix M5/M15/H1)
      ├──→ Economic Calendar API
      ├──→ COT Report (hebdo)
      ├──→ Sentiment APIs (retail ratios)
      └──→ News Feed (high impact filter)
      │
      ▼
[Ingestion Layer] ──→ Normalisation des données ──→ [Data Store temps réel]
      │
      ▼
[Analyse Layer] ──→ Modules Macro / Sentiment / Tech en parallèle
      │
      ▼
[Fusion Layer] ──→ Scoring ──→ Filtrage risque ──→ Decision Engine
      │
      ▼
[Action Layer] ──→ Génération du plan de trade ──→ Notification
      │
      ▼
[Logging Layer] ──→ Journal CSV/SQLite ──→ Dashboard
```

### Flux de rétroaction ( hebdomadaire / mensuel )

```
[Journal de trades] ──→ Analyse de performance ──→ Rapport
      │
      └──→ Identification des biais (bot vs réel)
      │
      └──→ Ajustement des paramètres de scoring
      │
      └──→ Mise à jour des règles de filtrage
```

## 2.4 Principes d'architecture

| Principe | Application |
|----------|-------------|
| **Modularité** | Chaque module peut être testé, modifié ou remplacé indépendamment. |
| **Idempotence** | Le même snapshot de marché produit toujours le même score. |
| **Observabilité** | Chaque décision du bot est traçable (pourquoi ce score ? pourquoi ce SL ?). |
| **Résilience** | Si une source de données tombe, le bot dégrade gracieusement (ne pas trader plutôt que trader aveuglément). |
| **Localité** | Le système tourne entièrement en local. Aucune donnée sensible ne quitte la machine. |

## 2.5 Schéma de l'Event Bus interne

Les modules communiquent par événements typés :

```python
# Exemples d'événements
MarketDataEvent(pair, timeframe, ohlcv)
MacroUpdateEvent(pair, score_macro, justification)
TechnicalSetupEvent(pair, setup_type, ob_zone, fvg_zone, bos_level)
SignalGeneratedEvent(signal_id, pair, direction, entry_zone, sl, tp_levels, score, sizing)

# Nouveaux événements pour Journal et Cerveau Vectoriel
TradeExecutedEvent(trade_id, signal_id, entry_price, user_confirmed)
TradeClosedEvent(trade_id, exit_price, pnl_virtual, outcome)
UserFeedbackEvent(trade_id, pnl_real, user_notes, exit_reason)
VectorMemoryEvent(trade_id, embedding, metadata, action="CREATE|UPDATE")
SimilarTradesFoundEvent(query_trade_id, similar_trades, adjustment)
```

Ce pattern permet :
- L'ajout futur de nouveaux modules sans modifier les existants.
- Le replay d'une session de marché pour le debugging.
- La parallélisation des traitements.

---

*Documents liés : [03 — Module Macro](03-module-macro.md) | [04 — Module Sentiment](04-module-sentiment.md) | [05 — Module Technique](05-module-technique.md) | [15 — Module Journal](15-module-journal.md) | [16 — Cerveau Vectoriel](16-cerveau-vectoriel.md) | [17 — Architecture Intelligence](17-architecture-intelligence.md)*
