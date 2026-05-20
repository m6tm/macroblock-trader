# 19 — Classification Architecturale

> Ce document positionne MacroBlock Trader dans les taxonomies architecturales reconnues. Il sert à communiquer clairement le type de système que nous construisons, aussi bien pour des discussions techniques internes que pour des présentations externes.

---

## 19.1 Résumé Exécutif

> **MacroBlock Trader est une architecture *Event-Driven Modular Pipeline* avec *Polyglot Persistence*, un *Rule-Based Decision Engine* piloté par un *Human-in-the-Loop*, enrichi d'une *Memory Vectorielle* (k-NN) et d'un *LLM présentationnel optionnel*.**

Ou, plus compact :

> **Un monolithe modulaire event-driven qui génère des signaux de trading via des règles déterministes, apprend de son historique par similarité vectorielle, et présente ses analyses via Kimi-k2.6 (optionnel) — tout en gardant l'humain maître des décisions.**

---

## 19.2 Architecture Logicielle — Niveau Application

### Event-Driven Modular Pipeline

| Dimension | Classification | Justification |
|-----------|---------------|---------------|
| **Style global** | *Modular Monolith* | Un seul processus Python, mais 8 modules fortement découplés avec responsabilités uniques — doc [02](02-architecture-systeme.md), §2.2 |
| **Communication** | *Event-Driven Architecture (EDA)* | Les modules ne s'appellent pas directement. Ils publient et s'abonnent à un Event Bus interne (`MarketDataEvent`, `SignalGeneratedEvent`, `TradeClosedEvent`...) — doc [02](02-architecture-systeme.md), §2.5 |
| **Flux de données** | *Pipeline Pattern* | Flux unidirectionnel : Ingestion → Normalisation → Analyse (parallèle) → Fusion → Risque → Action → Logging — doc [02](02-architecture-systeme.md), §2.3 |
| **Couplage** | *Loosely Coupled* | Chaque module peut être testé, remplacé ou désactivé indépendamment sans affecter les autres — doc [02](02-architecture-systeme.md), §2.4 |

### Pourquoi pas microservices ?

| Critère | Microservices | Modular Monolith (notre choix) |
|---------|--------------|-------------------------------|
| Déploiement | Indépendant | Unique |
| Communication | HTTP/gRPC | Event Bus en mémoire |
| Latence | Réseau | < 1 ms |
| Complexité | Élevée (orchestration) | Maîtrisée |
| Ressources | 1 service = 1 conteneur | 1 processus Python |

> **Verdict** : Pour un bot temps réel M5/M15 qui tourne sur un laptop, la latence réseau des microservices serait un handicap inutile. Le monolithe modulaire offre le même découplage logique sans la complexité opérationnelle.

---

## 19.3 Architecture de Données — Polyglot Persistence

Le système utilise **3 types de stockage simultanés**, chacun adapté à son usage :

| Stockage | Type architectural | Données | Usage | Justification |
|----------|-------------------|---------|-------|---------------|
| **SQLite** | *OLTP relationnel* | Trades, signals, feedbacks | Journal, requêtes SQL, intégrité | Transactions ACID, requêtes structurées, zero-config — doc [15](15-module-journal.md), §15.7 |
| **ChromaDB** | *Vector Database* | Embeddings des trades | Similarité, retrieval, clustering | Recherche k-NN en < 50 ms, local, gratuit — doc [16](16-cerveau-vectoriel.md), §16.3 |
| **DataFrame (RAM)** | *Time-Series Cache* | OHLCV M5/M15/H1/H4 | Calculs temps réel, indicateurs | Latence nulle pour le backtesting et la détection SMC — doc [11](11-stack-technique.md), §11.3.3 |

> **Terme technique** : *Polyglot Persistence* — chaque type de donnée vit dans le stockage adapté à son usage. Pas de "one size fits all".

---

## 19.4 Architecture IA — Retrieval-Augmented with Human-in-the-Loop

Ce n'est **ni un agent autonome**, **ni un simple système de règles**. C'est une architecture hybride spécifique :

| Composant | Type architectural | Rôle | Autorité |
|-----------|-------------------|------|----------|
| **Modules classiques** | *Rule-Based System* | Décision déterministe (OB, FVG, scoring, sizing) | **100%** — doc [17](17-architecture-intelligence.md), §17.4.2 |
| **Cerveau Vectoriel** | *k-NN Retrieval + Memory* | Recherche de similarité historique | Informe (ajuste ±0.3 max) — doc [16](16-cerveau-vectoriel.md), §16.5 |
| **Kimi rédacteur** | *LLM présentationnel* | Rédaction de texte à partir de JSON technique | **0%** — doc [17](17-architecture-intelligence.md), §17.4.3 |

### Ce que ce n'est PAS

| Type architectural | Pourquoi ce n'est pas ça | Document |
|-------------------|-------------------------|----------|
| **Agent LLM autonome** | Un LLM qui décide du trade = non-déterminisme, hallucination, latence. Rejeté explicitement. | [17](17-architecture-intelligence.md), §17.2 |
| **Multi-Agent System** | Plusieurs LLM qui débattent = coût ×4, consensus fragile, over-engineering. Rejeté. | [17](17-architecture-intelligence.md), §17.3 |
| **Pure RAG** | Le retrieval n'alimente pas un LLM génératif. Il alimente un scoring numérique déterministe. | [16](16-cerveau-vectoriel.md), §16.1 |
| **Expert System** | Pas de moteur d'inférence symbolique. Des règles codées + une mémoire vectorielle. | — |

### Ce que c'est

> **Classification exacte** : *Human-in-the-Loop Decision Support System (DSS)* avec une couche de *Retrieval-Augmented Memory*.
>
> Le bot **suggère**, l'humain **décide**, le bot **apprend** du résultat réel pour affiner les suggestions futures.

---

## 19.5 Architecture Métier — Signal Generator (Paper Trading)

Dans la taxonomie des systèmes de trading :

| Type de système | MacroBlock Trader | Justification |
|-----------------|-------------------|---------------|
| **Execution Engine** | ❌ Non | Pas de connexion à un broker, pas d'ordres automatiques — doc [01](01-vision-objectifs.md), §1.3 |
| **Signal Generator** | ✅ Oui | Détecte les setups et génère des plans de trade clé-en-main | — |
| **Paper Trading Engine** | ✅ Oui | Trace des positions fictives et calcule leur P&L virtuel | — |
| **Advisory Bot** | ✅ Oui | Recommande, l'utilisateur exécute manuellement — doc [01](01-vision-objectifs.md), §1.3 |
| **Risk Management System** | ✅ Partiel | Gère le risque virtuel, pas le risque réel | — |

> **Terme métier** : *Signal Generation Engine* ou *Trading Advisory Bot*.

---

## 19.6 Patterns Architecturaux Utilisés

| Pattern | Implémentation | Justification | Document |
|---------|---------------|---------------|----------|
| **Event Bus / Pub-Sub** | `EventBus` en mémoire, classes `Event` typées | Découplage total entre modules | [02](02-architecture-systeme.md), §2.5 |
| **Repository** | `database.py` (SQLite), `vector_store.py` (ChromaDB) | Abstraction du stockage, testable | [11](11-stack-technique.md), §11.5 |
| **Strategy** | Modes du cerveau vectoriel (`PASSIVE` / `LIGHT` / `FULL`) | Comportement interchangeable selon le volume de données | [16](16-cerveau-vectoriel.md), §16.5.4 |
| **Observer** | Modules qui s'abonnent aux événements du bus | Réactivité sans polling actif | [02](02-architecture-systeme.md), §2.5 |
| **Pipeline** | Flux Ingestion → Analyse → Fusion → Action | Traitement séquentiel des données avec étapes claires | [02](02-architecture-systeme.md), §2.3 |
| **Plugin** | Agent rédacteur Kimi (optionnel, activable/désactivable) | Extension non-critique, remplaçable | [17](17-architecture-intelligence.md), §17.4.3 |
| **Circuit Breaker** | Fallback sur templates Jinja2 si API Kimi indisponible | Résilience face aux défaillances externes | [17](17-architecture-intelligence.md), §17.8 |
| **State Machine** | Cycle de vie du trade (11 états : `GENERATED` → `EXECUTED` → `ACTIVE` → `CLOSED_WIN` → `FEEDBACK_PENDING` → `VALIDATED`) | Traçabilité et gestion des transitions | [15](15-module-journal.md), §15.3 |
| **CQRS (léger)** | Séparation lecture/écriture : SQLite pour écriture, DataFrame en mémoire pour lecture temps réel | Performance sur les séries temporelles | [11](11-stack-technique.md), §11.3.5 |

---

## 19.7 Comparaison avec des Architectures Connues

| Architecture connue | Ressemblance | Différence |
|---------------------|-------------|------------|
| **AutoGPT** | Utilise un LLM | Nous : LLM uniquement pour la rédaction, jamais pour la décision |
| **CrewAI** | Multi-agents spécialisés | Nous : modules classiques (pas des LLM), pas de délibération |
| **RAG classique** | Retrieval + génération | Nous : Retrieval + scoring numérique (pas de génération) |
| **Système expert Mycin** | Règles + scoring | Nous : Règles + mémoire vectorielle + feedback humain |
| **Bloomberg Terminal** | Données + analyse + alertes | Nous : Automatisé, spécialisé XAU/USD, avec apprentissage |
| **TradingView Pine Script** | Détection technique | Nous : Macro + sentiment + mémoire + journal + feedback |

---

## 19.8 Glossaire des Termes Utilisés

| Terme | Définition dans notre contexte |
|-------|-------------------------------|
| **EDA** | Event-Driven Architecture — communication par événements asynchrones |
| **k-NN** | k-Nearest Neighbors — algorithme de recherche des plus proches voisins dans un espace vectoriel |
| **DSS** | Decision Support System — système qui aide à la décision sans la remplacer |
| **Human-in-the-Loop** | L'humain reste dans la boucle de décision, valide et corrige le système |
| **Polyglot Persistence** | Utilisation de plusieurs technologies de stockage adaptées à leurs usages |
| **Rule-Based System** | Système dont les décisions sont prises par des règles explicites (if/then) |
| **Vector Database** | Base de données optimisée pour le stockage et la recherche de vecteurs (embeddings) |
| **Retrieval-Augmented** | Système dont les performances sont améliorées par la récupération d'informations pertinentes en contexte |

---

*Document de référence architecturale — À consulter pour toute discussion technique externe ou onboarding.*

*Documents liés : [02 — Architecture Système](02-architecture-systeme.md) | [17 — Architecture Intelligence](17-architecture-intelligence.md) | [18 — Plan d'Implémentation](18-plan-implementation.md)*
