# MacroBlock Trader — Documentation de Conception

> Bot d'analyse macro-technique basé sur la stratégie Order Blocks (Smart Money Concepts) en timeframes M5/M15.
> Paper trading. L'utilisateur garde le contrôle total de l'exécution.

---

## 📑 Table des matières

| # | Document | Description |
|---|----------|-------------|
| 01 | [Vision & Objectifs](01-vision-objectifs.md) | Philosophie, scope et objectifs du projet |
| 02 | [Architecture Système](02-architecture-systeme.md) | Architecture globale, modules et flux de données |
| 03 | [Module Macro](03-module-macro.md) | Analyse macroéconomique et filtre directionnel |
| 04 | [Module Sentiment](04-module-sentiment.md) | Positionnement des marchés et indicateurs de foule |
| 05 | [Module Technique](05-module-technique.md) | Smart Money Concepts : OB, FVG, structure, liquidité |
| 06 | [Moteur de Fusion & Scoring](06-moteur-fusion-scoring.md) | Agrégation des signaux et scoring des setups |
| 07 | [Gestion du Risque](07-gestion-risque.md) | Sizing, SL/TP, R:R, règles de blocage |
| 08 | [Flux de Travail](08-flux-travail.md) | Du scan permanent à la notification utilisateur |
| 09 | [Interface Utilisateur](09-interface-utilisateur.md) | Dashboard, alertes, journal de trading |
| 00 | [Spécialisation XAU/USD](00-specialisation-xauusd.md) | Spécificités de l'or, macro or, killzones LBMA/COMEX |
| 10 | [Univers de Trading](10-univers-trading.md) | XAU/USD, timeframes, killzones et horloge de marché |
| 11 | [Stack Technique](11-stack-technique.md) | Technologies et outils suggérés |
| 12 | [Métriques & Amélioration](12-metriques-amelioration.md) | KPIs, rapports et boucle d'amélioration continue |
| 13 | [Checklist de Lancement](13-checklist-lancement.md) | Points à valider avant le développement |
| 14 | [Annexe — Matrice de Décision](14-annexe-matrice-decision.md) | Tableau récapitulatif des conditions de trading |
| 15 | [Module Journal](15-module-journal.md) | Journal de trading structuré avec Trade ID unique |
| 16 | [Cerveau Vectoriel](16-cerveau-vectoriel.md) | Mémoire vectorielle statistique (ChromaDB), apprentissage par similarité |
| 17 | [Architecture Intelligence](17-architecture-intelligence.md) | Positionnement de l'IA : modules classiques + mémoire vectorielle + Kimi rédacteur optionnel |
| 18 | [Plan d'Implémentation Atomique](18-plan-implementation.md) | Phases et sous-phases de développement, découpage atomique sans notion de temps |
| 19 | [Classification Architecturale](19-classification-architecturale.md) | Taxonomies et patterns architecturaux du projet |

---

## 🎯 Résumé Exécutif

**MacroBlock Trader** est un système d'aide à la décision pour le trading manuel. Il ne prend pas de positions réelles. Il analyse le marché en continu, identifie les setups de haute probabilité selon une méthodologie Smart Money Concepts, et notifie l'utilisateur avec un plan de trade clé-en-main.

### Principes directeurs

1. **Qualité > Quantité** — 3 à 8 trades par semaine maximum.
2. **Macro filtre la Technique** — Pas de setup contre le vent macro.
3. **Transparence totale** — Chaque décision du bot est traçable et justifiable.
4. **Contrôle utilisateur** — Le bot propose, l'utilisateur dispose.
5. **Amélioration continue** — Feedback loop mensuelle sur la performance.
6. **Mémoire vectorielle** — Le bot apprend de chaque trade passé via une base de données vectorielle.
7. **Feedback humain** — L'utilisateur valide chaque trade réel pour enrichir l'apprentissage.

### Timeframes opérationnels

| Timeframe | Rôle |
|-----------|------|
| H4 / D1 | Contexte macro et tendance de fond |
| H1 | Structure supérieure et direction globale |
| M15 | Timeframe principal de détection des setups |
| M5 | Précision d'entrée et mitigation des OB |

---

*Document généré le 2026-05-20 — Phase : Conception.*

> **Spécialisation** : Ce bot est conçu pour trader exclusivement l'**or (XAU/USD)**. Voir [00 — Spécialisation XAU/USD](00-specialisation-xauusd.md) pour les spécificités.
