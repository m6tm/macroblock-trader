# 04 — Module Sentiment

## 4.1 Rôle

Le module Sentiment mesure le **positionnement des autres acteurs du marché**. Il répond à la question : *"Que font les autres traders, et est-ce que cela crée une opportunité contrarian ?"*

La logique sous-jacente est que la majorité des traders retail perdent de l'argent. Un positionnement retail extrême dans une direction est souvent un signal de retournement.

## 4.2 Sources de données

### 4.2.1 COT Report (Commitment of Traders)

| Attribut | Détail |
|----------|--------|
| Fréquence | Hebdomadaire (publié chaque vendredi, données du mardi) |
| Source | CFTC (Commodity Futures Trading Commission) |
| Utilisation | Positionnement des "Commercials" (smart money : hedgers, institutions) vs "Non-Commercials" (speculateurs, fonds) |

**Interprétation** :

| Positionnement | Signal |
|----------------|--------|
| Commercials net long + Non-Commercials net short | Fondamentalement haussier (smart money achète) |
| Commercials net short + Non-Commercials net long | Fondamentalement baissier (smart money vend) |
| Commercials à un extreme historique de long | Fort signal haussier |
| Non-Commercials à un extreme historique de long | Fort signal baissier (crowded trade) |

### 4.2.2 Ratio Long/Short Retail

| Attribut | Détail |
|----------|--------|
| Fréquence | Temps réel ou quasi temps réel |
| Source | Brokers retail (Myfxbook, OANDA, IG, etc.) |
| Utilisation | Mesurer le déséquilibre entre acheteurs et vendeurs retail |

**Interprétation** :

| Ratio Retail | Signal contrarian |
|--------------|-------------------|
| > 70 % Long | Les retails achètent en masse → prudence haussière → favoriser les shorts |
| > 70 % Short | Les retails vendent en masse → prudence baissière → favoriser les longs |
| 50/50 | Neutre, pas d'edge comportemental |

### 4.2.3 Fear & Greed Index

| Attribut | Détail |
|----------|--------|
| Fréquence | Quotidienne |
| Source | Alternative.me (crypto) / CNN Money (actions) |
| Utilisation | Mesurer l'état émotionnel global du marché |

| Zone | Interprétation |
|------|----------------|
| 0–20 : Extreme Fear | Opportunité d'achat (bottoms potentiels) |
| 21–40 : Fear | Légère opportunité d'achat |
| 41–60 : Neutral | Aucun biais comportemental |
| 61–80 : Greed | Prudence haussière, prendre des profits |
| 81–100 : Extreme Greed | Danger haussier (tops potentiels) |

## 4.3 Logique de scoring

Le module Sentiment produit un score de **-2 (extrême cupidité haussière)** à **+2 (extrême peur baissière)**.

```
Score Sentiment = (COT Signal × 0.40) + (Retail Contrarian × 0.40) + (FearGreed × 0.20)
```

| Score | Label | Signification |
|-------|-------|---------------|
| +2 | Extreme Fear / Smart Money Long | Fort biais haussier comportemental |
| +1 | Fear / Commercials accumulent | Biais haussier modéré |
| 0 | Neutre | Aucun edge comportemental |
| -1 | Greed / Commercials distribuent | Biais baissier modéré |
| -2 | Extreme Greed / Smart Money Short | Fort biais baissier comportemental |

## 4.4 Intégration avec le module Macro

Le sentiment **ne contredit jamais** le macro. Il agit comme un **amplificateur ou un frein** :

| Macro | Sentiment | Effet combiné |
|-------|-----------|---------------|
| Haussier (+2) | Extreme Fear (+2) | Setup long A+ : le macro et la foule sont alignés (foule a tort, macro confirme) |
| Haussier (+2) | Extreme Greed (-2) | Setup long pénalisé : tout le monde est déjà long, peu de fuel restant |
| Baissier (-2) | Extreme Greed (-2) | Setup short A+ : le macro et la foule sont alignés (foule a tort, macro confirme) |
| Baissier (-2) | Extreme Fear (+2) | Setup short pénalisé : tout le monde est déjà short, peu de fuel restant |

## 4.5 Limites et précautions

- **COT est retardé** (3 jours de décalage). À utiliser pour le contexte hebdomadaire, pas pour le timing d'entrée.
- **Retail ratios** peuvent être biaisés selon le broker (démographie des clients).
- **Sentiment est un indicateur de zone, pas de timing** : un marché peut rester greedy longtemps.

> **Règle d'utilisation** : Le sentiment sert à ajuster le sizing et le R:R minimum. Un setup dans la direction opposée au retail peut accepter un R:R plus faible. Un setup dans la direction du retail exige un R:R plus élevé.

---

*Documents liés : [02 — Architecture Système](02-architecture-systeme.md) | [03 — Module Macro](03-module-macro.md) | [06 — Moteur de Fusion & Scoring](06-moteur-fusion-scoring.md)*
