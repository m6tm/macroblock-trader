# 06 — Moteur de Fusion & Scoring

## 6.1 Rôle

Le moteur de fusion est le **cerveau décisionnel** du système. Il agrège les outputs des modules Macro, Sentiment et Technique pour produire une décision univoque : **Trade** ou **No Trade**, avec un niveau de confiance et un plan d'action complet.

## 6.2 Formule de scoring globale

```
SCORE TOTAL = (Score Macro × 0.30) + (Score Technique × 0.50) + (Score Timing × 0.20)
```

| Composant | Poids | Justification |
|-----------|-------|---------------|
| **Score Macro** | 30 % | Le contexte économique oriente les probabilités, mais le timing est imprécis. |
| **Score Technique** | 50 % | La qualité du setup est le facteur le plus important pour le timing d'entrée. |
| **Score Timing** | 20 % | La killzone et l'horloge de marché amplifient ou réduisent la probabilité d'execution propre. |

### Détails des sous-scores

| Sous-score | Plage | Source |
|------------|-------|--------|
| Score Macro | -3 à +3 | Module Macro (voir [03](03-module-macro.md)) |
| Score Technique | 0 à 5 | Module Technique (voir [05](05-module-technique.md)) |
| Score Timing | 0 à 2 | Killzone idéale = 2, acceptable = 1, mauvaise = 0 |

## 6.3 Grille de niveaux de confiance

| Score Total | Grade | Action | Couleur |
|-------------|-------|--------|---------|
| ≥ 3.5 | **A+** (Signal Fort) | Notifier immédiatement, sizing max | 🟢 |
| 2.5 – 3.5 | **B** (Signal Moyen) | Notifier, sizing standard | 🟡 |
| 1.5 – 2.5 | **C** (Signal Faible) | Logger, ne pas notifier (trop risqué) | 🟠 |
| < 1.5 | **N/A** | Ignorer complètement | 🔴 |

> **Règle d'or** : Un score B dans le sens du macro vaut mieux qu'un score A+ contre le macro.

## 6.4 Matrice de décision détaillée

### Matrice Macro × Technique

```
                    │ MACRO ALIGNED (+2/+3) │ MACRO NEUTRE (0) │ MACRO CONTRE (-2/-3)
────────────────────┼───────────────────────┼──────────────────┼─────────────────────
SETUP A+ (5/5 tech) │    ✅ SIGNAL FORT     │   ⚠️ SIGNAL B    │      ❌ PAS DE TRADE
SETUP B (3-4/5)     │    ✅ SIGNAL B        │   ❌ PAS DE TRADE │      ❌ PAS DE TRADE
SETUP C (<3/5)      │    ❌ PAS DE TRADE    │   ❌ PAS DE TRADE │      ❌ PAS DE TRADE
```

### Exceptions et ajustements

| Condition | Ajustement |
|-----------|------------|
| Score Macro = 0 (neutre) + Score Tech = 5 + Score Timing = 2 | Signal B autorisé (setup exceptionnel sans vent contraire) |
| Score Macro = -3 + Score Tech = 5 + Sentiment = +2 (extrême fear) | Signal B autorisé si contre-trend exceptionnel et liquidité claire |
| News haute impact dans les 30 minutes | Lock automatique, score ignoré |
| 2 trades déjà ouverts | Pas de nouveau signal, quelle que soit le score |
| Corrélation > 80 % avec un trade ouvert | Signal rejeté |

## 6.5 Génération du plan de trade

Une fois le score calculé et validé, le moteur génère un objet **Trade Plan** :

```json
{
  "signal_id": "SIG-20260520-001",
  "timestamp_generated": "2026-05-20T14:32:05Z",
  "valid_until": "2026-05-20T15:15:00Z",
  "pair": "XAUUSD",
  "direction": "BUY",
  "grade": "A+",
  "score_total": 4.2,
  "score_breakdown": {
    "macro": 2.0,
    "technical": 5.0,
    "timing": 2.0
  },
  "setup_type": "Bullish OB + FVG confluent",
  "entry_zone": {
    "min": 2345.00,
    "max": 2346.50,
    "preferred": 2345.75
  },
  "stop_loss": {
    "price": 2341.00,
    "distance_dollars": 35.0,
    "distance_pct": 0.15
  },
  "take_profit": [
    {"level": 1, "price": 2352.00, "ratio": "1:2.0", "allocation_pct": 50},
    {"level": 2, "price": 2358.00, "ratio": "1:3.7", "allocation_pct": 30},
    {"level": 3, "price": null, "ratio": "Trail", "allocation_pct": 20, "trail_trigger": "BE"}
  ],
  "risk": {
    "risk_pct": 1.0,
    "position_size_units": 0.28,
    "rr_expected": 2.8
  },
  "macro_context": {
    "score": 2,
    "justification": "DXY faible -0.15%, Yields en baisse, VIX élevé"
  },
  "technical_context": {
    "structure": "BOS haussier M15 confirmé, H4 haussier",
    "ob_zone": "2345.00-2346.50",
    "fvg_zone": "2345.20-2346.00",
    "liquidity_target": "Equal highs à 2355.00, niveau psychologique 2360"
  },
  "killzone": "London Fix PM",
  "notes": "Attendre rejet M5 dans l'OB. Ne pas entrer si cloture M5 sous 2340.50. Surveiller DXY."
}
```

## 6.6 Invalidation automatique

Le moteur surveille en continu chaque signal actif et peut l'invalider avant l'entrée :

| Scénario d'invalidation | Action |
|-------------------------|--------|
| Clôture M5 sous l'OB (pour un long) | Signal annulé, notification "Invalidé" |
| 3 candles M15 sans retour dans l'OB | Signal expiré (temps écoulé) |
| News haute impact imprévue | Signal suspendu, réévaluation après la news |
| Macro Lock déclenché | Signal mis en attente jusqu'à fin du lock |
| Setup inverse plus fort apparaît | Signal original remplacé par le nouveau |

## 6.7 Journal des décisions

Chaque décision du moteur est tracée avec la justification complète. Cela permet le debugging et l'amélioration continue :

```
[2026-05-20 14:32:05] SIGNAL XAUUSD BUY A+ (4.2/5)
  Macro Or: +2 (DXY↓ -0.15%, Yields↓, VIX↑)
  Tech: 5/5 (BOS✓ OB✓ FVG✓ Liquidity✓ Killzone✓ DXY✓)
  Timing: 2/2 (London Fix PM active)
  Entry: 2345.00-2346.50 | SL: 2341.00 | TP1: 2352.00 | TP2: 2358.00 | TP3: Trail
  Risk: 1.0% | Size: 0.28 lots | R:R: 2.8
  Valid until: 15:45 GMT
```

---

*Documents liés : [03 — Module Macro](03-module-macro.md) | [04 — Module Sentiment](04-module-sentiment.md) | [05 — Module Technique](05-module-technique.md) | [07 — Gestion du Risque](07-gestion-risque.md)*
