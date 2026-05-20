# 10 — Univers de Trading

## 10.1 Actif suivi : XAU/USD (Or)

Le bot est **spécialisé sur l'or**. Il ne surveille qu'un seul actif, mais avec une profondeur d'analyse maximale.

### Caractéristiques de XAU/USD

| Attribut | Valeur | Impact sur le trading |
|----------|--------|----------------------|
| **Pip** | 0.01 $ | 1 lot = 1 $ par 0.01 $ |
| **Spread typique** | 0.30 – 0.80 $ | Acceptable, attention aux spreads en période de news |
| **ATR(14) journalier** | 15 – 30 $ | Volatilité élevée, SL élargis nécessaires |
| **Heures de trading** | 22h00 dimanche – 21h00 vendredi (GMT) | Presque 24/5 |
| **Fix London AM** | 10h00 GMT | Volume institutionnel maximal |
| **Fix London PM** | 15h00 GMT | Deuxième vague institutionnelle |
| **COMEX Open** | 13h20 GMT | Ouverture futures, volatilité |
| **Corrélation DXY** | -0.80 (forte inverse) | DXY ↑ = Or ↓, et inversement |
| **Corrélation Yields** | -0.70 (forte inverse) | Yields ↑ = Or ↓ |
| **Corrélation VIX** | +0.50 (modérée positive) | Peur ↑ = Or ↑ |

### Contexte macro suivi (pour l'analyse de l'or)

Bien que le bot ne trade que XAU/USD, il surveille en permanence :

| Actif / Indicateur | Timeframe | Usage |
|--------------------|-----------|-------|
| **DXY** | M15 | Corrélation inverse principale |
| **US10Y** | M15 | Yields nominaux |
| **TIPS 10Y** | Quotidien | Yields réels |
| **VIX** | M15 | Risk sentiment |
| **S&P 500** | M15 | Risk-on / risk-off |
| **BTC/USD** | H1 | Alternative store of value (optionnel) |

## 10.2 Timeframes opérationnels — XAU/USD

### Hiérarchie des timeframes

| Timeframe | Rôle dans le système | Fréquence d'analyse |
|-----------|----------------------|---------------------|
| **D1** | Tendance de fond de l'or, niveaux psychologiques | Quotidienne |
| **H4** | **Contexte supérieur principal** — Structure, OB H4 clés | Toutes les 4 heures |
| **H1** | Contexte intermédiaire — Confirmation de direction | Toutes les heures |
| **M15** | **Timeframe principal** — Détection des setups | Chaque candle M15 |
| **M5** | **Timeframe de précision** — Timing d'entrée | Chaque candle M5 |

### Règles de timeframe pour l'or

```
RÈGLE 1 : On ne trade jamais contre la structure H4/H1.
RÈGLE 2 : Le setup est identifié sur M15.
RÈGLE 3 : L'entrée est affinée sur M5.
RÈGLE 4 : Le SL est calculé sur M15 (min 15 $, max 1.0% du prix).
RÈGLE 5 : Le contexte H4 filtre la direction globale de l'or.
RÈGLE 6 : Les niveaux psychologiques D1 (xx00, xx50) sont des targets prioritaires.
```

### Fréquence des candles

| Timeframe | Candles par jour | Candles par semaine (5 jours) |
|-----------|------------------|-------------------------------|
| M5 | 288 | 1 440 |
| M15 | 96 | 480 |
| H1 | 24 | 120 |
| H4 | 6 | 30 |
| D1 | 1 | 5 |

## 10.3 Killzones — Horloge de marché

Les killzones sont les créneaux horaires où la probabilité d'un setup propre est maximale. En dehors de ces fenêtres, les setups sont pénalisés ou ignorés.

### Tableau des killzones (GMT)

| Killzone | Horaire GMT | Horaire CET (Paris) | Caractéristique | Score Timing |
|----------|-------------|---------------------|-----------------|--------------|
| **Asia** | 00:00 – 08:00 | 01:00 – 09:00 | Range, consolidation, faible volume | 0 |
| **London Open** | 08:00 – 10:00 | 09:00 – 11:00 | Breakout de la range Asia, définition du range journée | 1 |
| **NY Open** | 13:30 – 15:30 | 14:30 – 16:30 | Volatilité max, momentum fort, meilleures opportunités | 2 |
| **London Close** | 16:00 – 17:00 | 17:00 – 18:00 | Profit-taking, possibles retournements | 1 |
| **NY Close** | 21:00 – 22:00 | 22:00 – 23:00 | Fin de journée, range, préparation Asia | 0 |

### Impact des killzones sur le scoring

| Setup détecté | Killzone active | Score Timing | Ajustement |
|---------------|-----------------|--------------|------------|
| OB frais + BOS | NY Open | 2 | Signal pleinement valorisé |
| OB frais + BOS | London Open | 1 | Signal acceptable |
| OB frais + BOS | London Close | 1 | Surveiller le profit-taking |
| OB frais + BOS | Asia / NY Close | 0 | Setup rejeté sauf exception justifiée |

### Exceptions hors killzone

Un setup peut être accepté hors killzone s'il remplit **tous** ces critères :
- Score technique = 5/5 (setup parfait)
- Score macro ≥ |2| (fort alignement)
- FVG + OB + Liquidité cible tous alignés
- Pas de news imminente dans les 2 heures
- R:R ≥ 1:2

> **Note** : Ces exceptions doivent rester rares (< 10 % des trades).

## 10.4 Corrélation des paires

Le bot maintient une matrice de corrélation en temps réel pour éviter la sur-exposition.

### Groupes de corrélation forte (> 80 %)

| Groupe | Paires | Risque |
|--------|--------|--------|
| DXY / Or | XAUUSD vs DXY | Corrélation inverse forte (-0.80) |
| Yields / Or | XAUUSD vs US10Y / TIPS | Corrélation inverse forte (-0.70) |
| VIX / Or | XAUUSD vs VIX | Corrélation positive modérée (+0.50) |

### Règle de corrélation DXY / Or

```
Si un trade long XAU/USD est ouvert :
    → Surveiller DXY en temps réel
    → Si DXY monte de > 0.2 % en 5 minutes :
        → Envoyer alerte de précaution
        → Suggérer réduction de position ou SL serré

Si un trade short XAU/USD est ouvert :
    → Surveiller DXY en temps réel
    → Si DXY baisse de > 0.2 % en 5 minutes :
        → Envoyer alerte de précaution
        → Suggérer réduction de position ou SL serré
```

## 10.5 Saisonnalité et contexte hebdomadaire — Or

| Jour | Caractéristique Or | Stratégie |
|------|-------------------|-----------|
| **Dimanche soir** | Ouverture 22h GMT, gap possible sur l'or | Pas de signal avant cloture première H1 |
| **Lundi** | Range Asia, direction du weekend à digérer | Attendre London Open pour la direction |
| **Mardi** | Tendance début de semaine souvent établie | Meilleur jour pour les setups trend |
| **Mercredi** | Volatilité moyenne, parfois reversal mi-semaine | Standard |
| **Jeudi** | Anticipation weekend, parfois profit-taking | Prudent en fin de journée |
| **Vendredi** | Volatilité US PM, puis fade vers NY Close | **Dernier signal à 19h GMT**, pas de trade après |
| **Weekend** | Marché fermé | Maintenance, rapports, révision paramètres |

### Comportement weekend de l'or

| Scénario | Stratégie Bot |
|----------|---------------|
| Gap haussier dimanche soir | Attendre cloture H1, chercher mitigation si contexte haussier |
| Gap baissier dimanche soir | Attendre cloture H1, chercher mitigation si contexte baissier |
| Gap géopolitique majeur (> 20 $) | Pas de signal avant 2–3 candles H1 de consolidation |
| Pas de gap | Analyse normale dès 23h GMT |

---

*Documents liés : [05 — Module Technique](05-module-technique.md) | [07 — Gestion du Risque](07-gestion-risque.md)*
