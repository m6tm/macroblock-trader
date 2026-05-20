# 03 — Module Macro

## 3.1 Rôle

Le module Macro détermine le **vent dominant pour l'or (XAU/USD)**. Il répond à la question : *"Dans quel sens l'or a-t-il le plus de chances d'aller aujourd'hui ?"*

Un setup technique parfait à l'achat alors que le vent macro est baissier pour l'or (DXY fort, yields haussiers) sera rejeté ou fortement pénalisé.

## 3.2 Sources de données

| Source | Fréquence | Indicateur clé | Impact sur l'Or |
|--------|-----------|----------------|-----------------|
| Dollar Index (DXY) | M15 | Force du dollar | **Inverse fort** — DXY ↑ = Or ↓ |
| Yields réels US (TIPS 10Y) | Quotidien | Taux réels | **Inverse fort** — Yields ↑ = Or ↓ |
| Yields nominaux US10Y | Temps réel | Taux nominaux | **Inverse modéré** |
| Calendrier économique | Temps réel | FOMC, NFP, CPI, PPI | **Haut impact** — inflation hawkish = Or ↓ |
| VIX (Fear Index) | M15 | Peur de marché | **Positif** — VIX ↑ = Or ↑ |
| Géopolitique / Crises | Temps réel | News feed | **Positif** — crises = Or ↑ |
| BTC/USD | M15 | Crypto alternative | **Positif croissant** — BTC ↑ parfois = Or ↓ |
| Indice USD | M15 | DXY, USDX | **Inverse** — référence principale |

## 3.3 Logique de scoring

### 3.3.1 Piliers du score macro — Spécifique Or

Le score macro pour l'or est une somme pondérée adaptée aux drivers fondamentaux de l'or :

```
Score Macro Or = (DXY Momentum × 0.30) + (Yields Réels × 0.25) + (Fed Policy × 0.20) + (Risk Sentiment × 0.15) + (Inflation Surprise × 0.10)
```

#### A. DXY Momentum (30 %)

| Condition | Impact sur l'Or |
|-----------|-----------------|
| DXY en hausse forte (> +0.3 % sur M15) | Fortement baissier pour l'Or |
| DXY en hausse modérée | Baissier pour l'Or |
| DXY stable / range | Neutre |
| DXY en baisse modérée | Haussier pour l'Or |
| DXY en baisse forte (< -0.3 % sur M15) | Fortement haussier pour l'Or |

> L'or est coté en dollars. Une hausse du dollar rend l'or plus cher pour les acheteurs non-USD, donc mécaniquement baissier.

#### B. Yields Réels (25 %)

L'or ne rapporte pas d'intérêt. Quand les yields réels montent, le coût d'opportunité de détenir de l'or augmente.

| Condition | Impact sur l'Or |
|-----------|-----------------|
| TIPS 10Y > 2 % et en hausse | Fortement baissier |
| TIPS 10Y > 1 % et en hausse | Baissier |
| TIPS 10Y stable | Neutre |
| TIPS 10Y < 1 % et en baisse | Haussier |
| TIPS 10Y < 0 % (négatif) | Fortement haussier |

#### C. Fed Policy (20 %)

| Condition | Impact sur l'Or |
|-----------|-----------------|
| Hawkish fort (hausse taux, QT) | Fortement baissier |
| Hawkish modéré | Baissier |
| Neutre / Pause | Neutre |
| Dovish modéré (baisse taux anticipée) | Haussier |
| Dovish fort (QE, taux négatifs) | Fortement haussier |

#### D. Risk Sentiment (15 %)

| Régime de marché | Impact sur l'Or | Indicateurs |
|------------------|-----------------|-------------|
| **Risk-Off fort** | Fortement haussier | VIX > 25, S&P ↓ -2 %, crises, guerres |
| **Risk-Off modéré** | Haussier | VIX 20–25, S&P ↓ -1 % |
| **Neutre** | Neutre | VIX 15–20, S&P stable |
| **Risk-On modéré** | Baissier | VIX < 15, S&P ↑ +1 % |
| **Risk-On fort** | Fortement baissier | VIX < 12, S&P ↑ +2 %, euphorie |

#### E. Inflation Surprise (10 %)

| Condition | Impact sur l'Or |
|-----------|-----------------|
| CPI/PPI surprise haussière forte (> +0.3 % vs attendu) | Haussier (or = hedge inflation) |
| CPI/PPI surprise haussière modérée | Légèrement haussier |
| Conforme aux attentes | Neutre |
| Surprise baissière | Baissier (moins d'urgence à hedger) |

## 3.4 Échelle de sortie

Le module produit un score de **-3 (très baissier)** à **+3 (très haussier)** par paire.

| Score | Label | Signification pour l'Or |
|-------|-------|-------------------------|
| +3 | Vent haussier parfait | Favoriser les achats XAU/USD. Setups longs valorisés. |
| +2 | Vent haussier modéré | Achats XAU/USD privilégiés. Shorts nécessitent un setup exceptionnel. |
| +1 | Légère poussée haussière | Achats légèrement favorisés. Neutre technique acceptable. |
| 0 | Neutre / Brouillard | Aucune direction privilégiée. La technique domine seule. |
| -1 | Légère pression baissière | Ventes légèrement favorisées. Longs nécessitent un setup exceptionnel. |
| -2 | Pression baissière modérée | Ventes privilégiées. Longs fortement pénalisés. |
| -3 | Pression baissière forte | Favoriser les ventes XAU/USD. Setups shorts valorisés. |

## 3.5 Fenêtres de blocage

Le module Macro publie des **"Macro Lock"** qui interdisent temporairement tout nouveau signal :

| Événement | Durée du lock |
|-----------|---------------|
| FOMC (décision taux) | 30 min avant → 1h après |
| NFP | 15 min avant → 30 min après |
| CPI / PPI US | 15 min avant → 30 min après |
| Discours Powell / Lagarde majeurs | Pendant + 30 min après |
| Guerre / choc géopolitique majeur | Jusqu'à réévaluation manuelle |

> **Règle d'or** : Mieux vaut rater un trade que de se faire piéger par une annonce imprévisible.

## 3.6 Exemple concret — XAU/USD

**Date fictive** : 15 mai 2026, 13:00 GMT

| Indicateur | Valeur | Impact sur l'Or |
|------------|--------|-----------------|
| DXY | 104.80, en baisse M15 | Haussier (+1) |
| TIPS 10Y | 1.85 %, en baisse | Haussier (+1) |
| Dernière surprise CPI US | +0.3 % vs +0.1 % attendu | Hawkish → Baissier (-1) |
| VIX | 22.5 (élevé, fear) | Haussier (+1) |
| Fed Policy | Pause des taux annoncée | Neutre (0) |

**Calcul** :
- DXY Momentum : DXY ↓ → Or ↑ → **+1**
- Yields Réels : TIPS ↓ → Or ↑ → **+1**
- Fed Policy : Pause → neutre → **0**
- Risk Sentiment : VIX élevé → Or ↑ → **+1**
- Inflation Surprise : CPI haut → hawkish → Or ↓ → **-0.5** (pondéré 0.10)

**Score Macro Or = +2.0** → Vent haussier modéré. Les setups d'achat XAU/USD sont privilégiés. Les setups de vente nécessitent un score technique exceptionnel.

---

*Documents liés : [02 — Architecture Système](02-architecture-systeme.md) | [06 — Moteur de Fusion & Scoring](06-moteur-fusion-scoring.md)*
