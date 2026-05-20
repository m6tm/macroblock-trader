# 05 — Module Technique

## 5.1 Rôle

Le module Technique est le cœur de la détection des opportunités sur **XAU/USD**. Il identifie les zones de haute probabilité selon la méthodologie **Smart Money Concepts (SMC)**, adaptée à la volatilité et au comportement spécifique de l'or. Il répond à la question : *"Où le prix de l'or a-t-il le plus de chances de réagir ?"*

## 5.2 Concepts SMC utilisés

### 5.2.1 Structure de Marché (Market Structure)

La structure détermine la tendance actuelle et ses points de rupture.

| Terme | Définition | Signification |
|-------|------------|---------------|
| **BOS** (Break of Structure) | Le prix casse un swing high précédent (haussier) ou un swing low (baissier) | Confirmation de continuation |
| **CHoCH** (Change of Character) | Le prix casse un swing low dans une tendance haussière (ou inversement) | Signe de possible retournement |
| **HH / HL** (Higher High / Higher Low) | Sommet et creux ascendants | Tendance haussière |
| **LH / LL** (Lower High / Lower Low) | Sommet et creux descendants | Tendance baissière |

**Règle d'or** : On ne trade jamais contre la structure du timeframe supérieur (H1 minimum). Pour l'or, le contexte H4 est également essentiel en raison des moves plus larges.

### 5.2.2 Order Blocks (OB)

Un Order Block est la dernière candle institutionnelle avant un mouvement impulsif. C'est la trace d'une accumulation ou distribution des smart money.

| Type | Définition | Apparence |
|------|------------|-----------|
| **Bullish OB** | Dernière candle baissière (ou dernière candle rouge) avant un mouvement haussier impulsif | Zone au-dessus de laquelle le prix a fortement monté |
| **Bearish OB** | Dernière candle haussière (ou dernière candle verte) avant un mouvement baissier impulsif | Zone au-dessous de laquelle le prix a fortement baissé |

#### Qualité d'un Order Block — Spécifique Or

| Critère | Impact | Spécificité Or |
|---------|--------|----------------|
| **Fraîcheur** | Jamais mitigé (prix jamais revenu dedans) = meilleur | L'or mitige souvent à 50 % de l'OB |
| **Impulsion générée** | Plus le mouvement après l'OB est violent et sans pullback = plus fort | Un move de 15 $+ sans pullback = OB fort |
| **Timeframe** | OB H4 > OB H1 > OB M15 > OB M5 | OB H4 extrêmement fiables sur l'or |
| **Confluence** | OB aligné avec un FVG ou un niveau de liquidité = zone premium | Confluence avec niveau psychologique (2000, 2100...) = zone premium |

#### Mitigation

La mitigation se produit quand le prix revient dans l'OB. C'est la zone d'entrée potentielle.

```
Bullish OB : Entrée dans la zone [Low de l'OB → High de l'OB]
             SL sous le Low de l'OB (wick le plus bas + buffer)
             TP vers le prochain pool de liquidité / FVG opposé

Bearish OB : Entrée dans la zone [Low de l'OB → High de l'OB]
             SL au-dessus du High de l'OB (wick le plus haut + buffer)
             TP vers le prochain pool de liquidité / FVG opposé
```

### 5.2.3 Fair Value Gaps (FVG) — Spécifique Or

Un FVG est un déséquilibre de prix — une zone où le marché n'a pas négocié. Sur l'or, les FVG sont particulièrement fiables en raison de la volatilité et des moves impulsifs.

| Type | Condition mathématique |
|------|------------------------|
| **Bullish FVG** | Low(candle N+2) > High(candle N) |
| **Bearish FVG** | High(candle N+2) < Low(candle N) |

**Interprétation spécifique Or** :
- Le prix a "sauté" cette zone en signe d'urgence (institutions repositionnant sur l'or).
- Le marché a tendance à revenir combler ces gaps, surtout autour des fixes londoniens.
- Un FVG confluent avec un OB **et** un niveau psychologique crée une **zone premium** sur l'or.
- Les FVG H1 et M15 sont les plus fiables ; les FVG M5 servent à affiner l'entrée.

### 5.2.4 Liquidité Pools — Spécifique Or

Les liquidités sont les stops accumulés au-dessus des sommets ou au-dessous des creux. Sur l'or, les niveaux psychologiques amplifient cet effet.

| Type | Localisation | Pourquoi cible ? | Exemple Or |
|------|--------------|------------------|------------|
| **Equal Highs (EQH)** | Deux sommets approximativement égaux | Stops des shorts au-dessus | 2350.00 et 2350.20 |
| **Equal Lows (EQL)** | Deux creux approximativement égaux | Stops des longs au-dessous | 2320.00 et 2319.80 |
| **Trendline Liquidity** | Trendlines évidentes | Stops accumulés | Trendline sur H4 |
| **Niveaux Psychologiques** | 2000.00, 2100.00, 2200.00... | Stops des retail au-dessus/au-dessous | 2400.00 = magnète |
| **Previous Day High/Low** | High/Low de la veille | Liquidité journalière | High hier = target |
| **Previous Week High/Low** | High/Low de la semaine | Liquidité hebdomadaire | Weekly high = target fort |

**Inducement** : Le prix crée une fausse sortie pour chasser ces stops avant de repartir dans la vraie direction. Sur l'or, les inducements sont fréquents autour des fixes (10h et 15h GMT).

> **Règle pour l'or** : On place ses TP vers les pools de liquidité du bon côté. Les niveaux psychologiques (xx00, xx50) sont des targets prioritaires.

### 5.2.5 Killzones — Horloge de Marché Spécifique Or

Les killzones pour l'or sont définies par les fixes LBMA et l'ouverture du COMEX.

| Killzone | Horaire GMT | Horaire CET | Caractéristique | Score Timing |
|----------|-------------|-------------|-----------------|--------------|
| **Asia** | 00:00 – 08:00 | 01:00 – 09:00 | Range, consolidation, peu de momentum | 0 |
| **London Open** | 08:00 – 09:00 | 09:00 – 10:00 | Définition de la tendance, préparation fix | 1 |
| **London Fix AM** | 10:00 – 11:00 | 11:00 – 12:00 | Fix LBMA, volume élevé, moves nets | 2 |
| **NY Open / COMEX** | 13:20 – 14:30 | 14:20 – 15:30 | Ouverture futures COMEX, volatilité max | 2 |
| **London Fix PM** | 15:00 – 16:00 | 16:00 – 17:00 | Deuxième fix, momentum après-midi | 2 |
| **London Close** | 16:00 – 17:00 | 17:00 – 18:00 | Profit-taking, possibles retournements | 1 |
| **NY Close** | 21:00 – 22:00 | 22:00 – 23:00 | Fin de journée, range | 0 |

**Stratégie pour l'or** :
- **London Fix AM (10h GMT)** : Les institutions ajustent leurs positions. Les moves post-fix sont souvent propres.
- **NY Open / COMEX (13h20 GMT)** : Volatilité maximale. Les setups autour de l'ouverture COMEX sont de grande qualité.
- **London Fix PM (15h GMT)** : Deuxième vague institutionnelle. Bon pour les continuations ou retournements.
- **London Open** : Définition de la tendance. Attendre le fix pour confirmation.
- **Asia** : Évité par défaut (sauf accumulation visible en range).

## 5.3 Algorithme de détection d'un setup

```
ÉTAPE 1 — Contexte H1
    └─→ Structure H1 haussière ou baissière ?
    └─→ Si neutre → pas de trade (attendre un BOS/CHoCH)

ÉTAPE 2 — Structure M15
    └─→ BOS récent dans la direction du H1 ?
    └─→ Si CHoCH contre H1 → possible retournement (setup de contre-tendance H1, A+ only)

ÉTAPE 3 — Détection OB M15
    └─→ Dernier candle baissier/haussier avant l'impulsion
    └─→ Vérifier fraîcheur (non mitigé ou première mitigation)

ÉTAPE 4 — Détection FVG confluent
    └─→ FVG dans la même zone que l'OB ?
    └─→ Zone serrée = meilleur R:R

ÉTAPE 5 — Liquidité ciblée
    └─→ Y a-t-il un pool de liquidité dans la direction du trade ?
    └─→ Le TP est-il avant un obstacle majeur (OB inverse, support/résistance) ?

ÉTAPE 6 — Killzone
    └─→ Heure actuelle dans une killzone active ?
    └─→ Si non → setup pénalisé ou ignoré

ÉTAPE 7 — Confirmation d'entrée M5
    └─→ Le prix entre dans l'OB en M5 ?
    └─→ Rejet visible (wick, engulfing, pin bar) ?
    └─→ Si oui → SIGNAL DÉCLENCHÉ
```

## 5.4 Score Technique

Le module attribue un score de **0 à 5** selon les critères validés :

| Critère | Points |
|---------|--------|
| Structure H1 alignée | +1 |
| BOS M15 récent dans la direction du trade | +1 |
| OB frais (non mitigé) | +1 |
| FVG confluent avec l'OB | +1 |
| Liquidité ciblée claire pour le TP | +0.5 |
| Killzone active | +0.5 |

**Score minimal pour un signal** : **3.0**

---

*Documents liés : [02 — Architecture Système](02-architecture-systeme.md) | [06 — Moteur de Fusion & Scoring](06-moteur-fusion-scoring.md) | [10 — Univers de Trading](10-univers-trading.md)*
