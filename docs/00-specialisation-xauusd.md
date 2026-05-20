# 00 — Spécialisation XAU/USD (Or)


## 0.1 Pourquoi l'Or ?

L'or (XAU/USD) est un actif unique qui se prête particulièrement bien à une stratégie macro-technique SMC pour plusieurs raisons :

| Avantage | Explication |
|----------|-------------|
| **Sensibilité macro extrême** | L'or réagit immédiatement aux taux, au dollar, à l'inflation, aux crises |
| **Mouvements propres et nets** | Moins de bruit que les paires FX majeures, structures SMC très lisibles |
| **Liquidité permanente** | Marché 23/5, pas de gap weekend sauf exception |
| **Corrélation claire** | Inverse au DXY, sensibles aux yields réels, baromètre du fear |
| **Pas de swap négatif disproportionné** | Contrairement à certaines paires exotiques |

## 0.2 Ce qui change par rapport à la version multi-paires

| Aspect | Version Multi-Paires | Version XAU/USD |
|--------|----------------------|-----------------|
| Univers | 10 paires | **XAU/USD uniquement** |
| Focus macro | Général (EUR, GBP, JPY...) | **DXY, yields réels, inflation, géopolitique** |
| Volatilité attendue | Variable selon la paire | **Haute et constante** |
| Sizing | 1.5% max | **1.0% max (A+), 0.5% (B)** |
| SL typique | 10–20 pips | **20–40 pips** |
| R:R minimum | 1:1.5 | **1:2.0** |
| Killzones | London + NY | **London Fix + NY Open + COMEX** |
| Fréquence des trades | 3–8 / semaine | **2–5 / semaine** |

## 0.3 Macro spécifique à l'Or

### Facteurs fondamentaux clés

| Facteur | Corrélation avec l'Or | Source à suivre |
|---------|----------------------|-----------------|
| **DXY (Dollar Index)** | Forte inverse | M15 temps réel |
| **Yields réels US (TIPS 10Y)** | Forte inverse | Quotidien (FRED) |
| **Yields nominaux US10Y** | Inverse modérée | Temps réel |
| **Inflation (CPI, PPI, PCE)** | Positive (or = hedge inflation) | Sur publication |
| **FOMC / Taux directeurs** | Forte inverse | Sur événement |
| **Géopolitique / Crises** | Forte positive | News feed temps réel |
| **VIX (fear index)** | Positive | M15 temps réel |
| **BTC/USD** | Corrélation croissante (alternative store of value) |

### Score Macro Or (spécifique)

Le score macro pour l'or est calculé différemment des paires FX classiques :

```
Score Macro Or = (DXY Momentum × 0.30) + (Yields Réels × 0.25) + (Fed Policy × 0.20) + (Risk Sentiment × 0.15) + (Inflation Surprise × 0.10)
```

| Composant | Haussier pour l'Or | Baissier pour l'Or |
|-----------|--------------------|--------------------|
| DXY | En baisse ou range faible | En hausse forte |
| Yields réels | En baisse | En hausse |
| Fed Policy | Dovish (baisse taux, QE) | Hawkish (hausse taux, QT) |
| Risk Sentiment | VIX élevé, crises, guerres | VIX bas, stabilité |
| Inflation | Surprise haussière | Surprise baissière |

### Échelle de sortie spécifique Or

| Score | Label | Signification |
|-------|-------|---------------|
| +3 | Vent haussier parfait | Or très favorisé, setups longs valorisés |
| +2 | Vent haussier modéré | Achats privilégiés |
| +1 | Légère poussée haussière | Achats légèrement favorisés |
| 0 | Neutre | La technique domine |
| -1 | Légère pression baissière | Ventes légèrement favorisées |
| -2 | Pression baissière modérée | Ventes privilégiées |
| -3 | Pression baissière forte | Or très pénalisé, setups shorts valorisés |

## 0.4 Killzones Spécifiques à l'Or

L'or a des horaires spécifiques en raison des fixes de Londres et de l'ouverture du COMEX.

| Killzone | Horaire GMT | Horaire CET | Caractéristique | Score Timing |
|----------|-------------|-------------|-----------------|--------------|
| **London Fix AM** | 10:00 – 11:00 | 11:00 – 12:00 | Fix quotidien LBMA, volume élevé, moves nets | 2 |
| **London Fix PM** | 15:00 – 16:00 | 16:00 – 17:00 | Deuxième fix, momentum de l'après-midi | 2 |
| **NY Open / COMEX** | 13:20 – 14:30 | 14:20 – 15:30 | Ouverture futures COMEX, volatilité maximale | 2 |
| **London Open** | 08:00 – 09:00 | 09:00 – 10:00 | Définition de la tendance de la session | 1 |
| **Asia** | 00:00 – 08:00 | 01:00 – 09:00 | Range, consolidation, peu de momentum | 0 |
| **NY Close** | 21:00 – 22:00 | 22:00 – 23:00 | Profit-taking, range | 0 |

> **Note** : Le London Fix est un moment clé pour l'or. Les institutions ajustent leurs positions. Les moves autour de 10h et 15h GMT sont souvent les plus propres.

## 0.5 Gestion du Risque — Spécifique Or

### Volatilité de l'or

| Métrique | Valeur typique | vs EURUSD |
|----------|---------------|-----------|
| ATR(14) journalier | 15–30 $ | ~3x |
| Mouvement moyen M15 | 3–8 $ | ~2x |
| Écart type quotidien | 1.2 % | ~2x |
| Gap weekend | 5–20 $ | Équivalent |

### Ajustements de risque

| Paramètre | Valeur générique | Valeur Or | Justification |
|-----------|-----------------|-----------|---------------|
| Risque A+ | 1.5 % | **1.0 %** | Volatilité plus élevée |
| Risque B | 1.0 % | **0.5 %** | Prudence renforcée |
| SL max | 1.5 % du prix | **1.0 % du prix** | Éviter les stops trop larges |
| SL min | 5 pips | **15 pips ($0.15)** | Respecter la volatilité intrinsèque |
| R:R minimum | 1:1.5 | **1:2.0** | L'or permet des moves plus grands |
| Distance SL typique | 10–20 pips | **25–40 pips ($0.25–$0.40)** | Adapté à l'ATR |
| Distance TP1 typique | 15–30 pips | **50–80 pips ($0.50–$0.80)** | Objectif réaliste |
| Max trades simultanés | 2 | **1** | Un seul actif = un seul trade à la fois |

### Règles spécifiques à l'or

- **Pas de trade avant un fix londonien** si le setup se forme à 09:55 GMT : attendre le fix de 10h pour voir la direction post-fix.
- **Attention aux gaps weekend** : Le bot ne génère pas de signal dimanche soir avant la cloture de la première candle H1 (risque de gap).
- **Corrélation DXY en temps réel** : Si le DXY fait un mouvement brusque de +0.3 % en 5 minutes, suspendre les nouveaux signaux longs pendant 15 minutes.

## 0.6 Analyse Technique — Spécificités de l'Or

### Comportement des Order Blocks sur XAU/USD

| Caractéristique | Observation |
|-----------------|-------------|
| **OB H4/H1** | Extrêmement fiables, souvent re-testés une seule fois |
| **OB M15** | Fiables si formés pendant une killzone active |
| **OB M5** | À utiliser uniquement pour l'affinement d'entrée |
| **Mitigation** | L'or mitige souvent à 50 % de l'OB avant de repartir |
| **Fakeout** | Plus fréquents que sur EURUSD (institutions chassent les stops) |

### Niveaux clés à surveiller

| Type de niveau | Exemples | Usage |
|----------------|----------|-------|
| **Psychologiques** | 2000.00, 2100.00, 2200.00, 2300.00 | Targets, zones de liquidité |
| **Demi-centenaires** | 2050.00, 2150.00 | Supports/résistances mineurs |
| **Demi-dizaines** | 2025.00, 2075.00 | Micro-niveaux pour SL/TP |
| **Previous day high/low** | Variable | Liquidité journalière |
| **Previous week high/low** | Variable | Liquidité hebdomadaire |

### Liquidité spécifique à l'or

- **Equal highs/lows** autour des niveaux psychologiques (2000, 2100...) sont des magnètes puissants.
- **Previous session highs/lows** : L'or a une forte mémoire des extremes de la session précédente.
- **Range Asia** : Les extremes de la range Asia sont souvent chassés au London Open.

## 0.7 Notifications Spécifiques Or

Format adapté pour l'or (en dollars, pas en pips) :

```
╔══════════════════════════════════════════════════════════════════╗
║  🔔 SIGNAL MACROBLOCK — [XAUUSD] — ACHAT                         ║
╠══════════════════════════════════════════════════════════════════╣
║  Grade: A+ (4.2/5)                                               ║
╠══════════════════════════════════════════════════════════════════╣
║  📊 CONTEXTE OR                                                   ║
║  Macro Or: +2 🟢 (DXY ↓ -0.15%, Yields ↓, VIX ↑)                ║
║  Setup: Bullish OB M15 + FVG confluent                            ║
║  Killzone: London Fix PM ✅                                       ║
╠══════════════════════════════════════════════════════════════════╣
║  📍 PLAN DE TRADE                                                 ║
║  Entrée : 2345.00 – 2346.50 (zone OB)                           ║
║  SL      : 2341.00 (-4.00 $ / -0.17%)                           ║
║  TP1     : 2352.00 (+6.00 $ / 1:1.5) — 50%                       ║
║  TP2     : 2358.00 (+12.00 $ / 1:3.0) — 30%                      ║
║  TP3     : Trail après BE — 20%                                  ║
╠══════════════════════════════════════════════════════════════════╣
║  💰 GESTION DU RISQUE                                             ║
║  Taille suggérée : 1.0% du capital = 100€                        ║
║  R:R attendu : 1:2.3                                              ║
╠══════════════════════════════════════════════════════════════════╣
║  ⏱️  VALIDE JUSQU'À : 16:00 GMT (25 min)                        ║
║  ⚠️  INVALIDÉ SI : Clôture M5 sous 2340.50                      ║
║  🎯  Liquidité cible : Equal Highs à 2355.00                    ║
╠══════════════════════════════════════════════════════════════════╣
║  [⚡ J'EXÉCUTE]  [👀 JE REGARDE]  [❌ IGNORER]                  ║
╚══════════════════════════════════════════════════════════════════╝
```

## 0.8 Comportement weekend et gaps

| Jour | Spécificité Or | Stratégie Bot |
|------|---------------|---------------|
| **Dimanche soir** | Ouverture à 22h GMT, gap possible | Pas de signal avant la cloture de la première H1 |
| **Vendredi soir** | Fermeture à 21h GMT, positions à clôturer | Dernier signal accepté à 19h GMT |
| **Gaps géopolitiques** | Ouverture avec gap de 10–30 $ | Attendre la cloture de H1 pour valider la direction |

## 0.9 Métriques spécifiques Or

| Métrique | Objectif | Justification |
|----------|----------|---------------|
| Win Rate | > 50 % | La volatilité de l'or rend les setups plus risqués, mais le R:R plus élevé compense |
| Profit Factor | > 1.6 | Nécessaire pour couvrir les pertes plus importantes en $ |
| R:R moyen réalisé | > 1:2.5 | L'or permet naturellement des moves plus importants |
| Trades par semaine | 2–5 | Sélection drastique, un seul actif |
| P&L moyen gagnant | +8 $ | Objectif réaliste sur M15 |
| P&L moyen perdant | -4 $ | SL respecté |

---

*Ce document prime sur les sections génériques des autres fichiers en cas de contradiction.*
