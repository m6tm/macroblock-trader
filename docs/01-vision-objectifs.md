# 01 — Vision & Objectifs

## 1.1 Contexte

Le trading sur les marchés de change (Forex) et indices exige une analyse constante de multiples dimensions : fondamentale (macroéconomique), comportementale (sentiment) et technique. La méthodologie **Smart Money Concepts (SMC)**, et notamment la stratégie des **Order Blocks**, permet d'identifier les zones où les institutions ont laissé des traces de leurs positions.

Cependant, surveiller en permanence les timeframes M5/M15 sur plusieurs paires, tout en croisant les données macroéconomiques et le calendrier des news, est une tâche impossible à réaliser manuellement avec rigueur sur le long terme.

## 1.2 Objectif du Projet

Créer un **système automatisé d'analyse et de génération de signaux** qui :

- Analyse le **contexte macroéconomique** en temps réel pour déterminer le vent dominant.
- Détecte les **setups techniques SMC** (Order Blocks, Fair Value Gaps, Break of Structure) sur M5/M15.
- Fusionne les deux dimensions pour attribuer un **score de confiance** à chaque opportunité.
- Génère un **plan de trade complet** (entrée, SL, TP, taille, durée de validité).
- **Notifie l'utilisateur** de manière claire et actionnable.
- **Trace l'historique** de tous les signaux pour mesurer la performance virtuelle.

## 1.3 Philosophie

> **"Le bot pense, toi tu décides et tu exécutes."**

### Paper Trading pur

Le système ne se connecte **jamais** à un compte de trading réel. Il prend des positions fictives (paper trading) et calcule leur performance théorique. L'utilisateur exécute manuellement les trades qu'il souhaite sur sa propre plateforme.

### Pourquoi cette approche ?

- **Souveraineté** : L'utilisateur garde le contrôle total sur son capital.
- **Apprentissage** : La comparaison entre la performance virtuelle du bot et l'exécution réelle révèle les biais comportementaux (peur, cupidité, slippage psychologique).
- **Flexibilité** : Le bot peut tourner 24/5 sans risque, même quand l'utilisateur dort ou travaille.
- **Validation** : Période de test virtuelle illimitée avant tout engagement réel.

## 1.4 Scope

### Ce qui est IN

- Analyse macroéconomique automatisée spécifique à l'or (DXY, yields réels, inflation, géopolitique).
- Détection algorithmique des Order Blocks et structures SMC sur XAU/USD.
- Scoring et filtrage des setups adapté à la volatilité de l'or.
- Gestion du risque intégrée (sizing réduit, SL élargi, R:R ≥ 1:2).
- Notifications en temps réel (alertes détaillées par trade en $).
- Dashboard de suivi et journal de performance dédié XAU/USD.
- Rapports mensuels de performance et d'optimisation.

### Ce qui est HORS scope

- Exécution automatique des ordres (no API broker pour le trading).
- Autres paires Forex (EURUSD, GBPUSD, etc.).
- Trading algorithmique haute fréquence (HFT).
- Gestion multi-comptes ou copy-trading.
- Crypto-monnaies (BTC, ETH).
- Actions et indices boursiers en tant qu'actif principal.

## 1.5 Indicateurs de succès

| Indicateur | Cible |
|------------|-------|
| Win rate virtuel | > 55 % |
| Profit Factor | > 1.5 |
| R:R moyen | > 1:2 |
| Max Drawdown | < 10 % |
| Signaux par semaine | 2–5 |
| Délai moyen alerte → setup | < 30 secondes |

---

*Documents spécifiques : [00 — Spécialisation XAU/USD](00-specialisation-xauusd.md)*

*Prochaine lecture recommandée : [02 — Architecture Système](02-architecture-systeme.md)*
