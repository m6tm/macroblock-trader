# 17 — Architecture Intelligence : Positionnement des composants IA

> Ce document formalise les décisions d'architecture concernant l'intelligence artificielle dans MacroBlock Trader. Il répond à la question : *"Quel rôle pour l'IA (LLM, vector DB) dans un système de trading algorithmique ?"*

---

## 17.1 Principe directeur

**Les algorithmes pilotent. L'IA assiste. L'IA ne décide jamais d'acheter ou de vendre.**

| Couche | Technologie | Rôle | Autorité |
|--------|-------------|------|----------|
| **Modules métier** | Python, règles, mathématiques | Détection, scoring, sizing, SL/TP | **Décisionnelle** |
| **Cerveau vectoriel** | ChromaDB, embeddings | Mémoire de similarité, patterns implicites | **Informative** (ajuste ±0.3 max) |
| **Agent rédacteur** | LLM léger (optionnel) | Rédaction de texte, résumés, alertes | **Présentationnelle** (zéro autorité sur les trades) |

---

## 17.2 Pourquoi pas de Mono-Agent LLM ?

Un seul LLM qui reçoit tout le contexte et décide du trade a été écarté pour ces raisons :

| Risque | Explication | Conséquence sur le trading |
|--------|-------------|---------------------------|
| **Hallucination** | Le LLM peut inventer un OB qui n'existe pas, ou se tromper de niveau de SL | Perte réelle immédiate |
| **Non-déterminisme** | Même input → outputs différents selon les appels | Impossible de backtester, de debugger, de faire confiance |
| **Latence** | 5–30 secondes par inférence | Trop lent pour du M5/M15 temps réel |
| **Coût** | Envoyer l'historique OHLCV + macro à chaque candle | Facture impraticable à l'échelle 24/5 |
| **Opacité** | Impossible d'expliquer *pourquoi* il a pris cette décision | Non-auditable, non-améliorable |
| **Dérive du prompt** | Le LLM peut "interpréter" une règle de risque au lieu de l'appliquer strictement | SL élargi, sizing excessif |

> **Verdict** : Un mono-agent LLM pour piloter le trading est **dangereux et contre-productif** pour ce projet.

---

## 17.3 Pourquoi pas de Multi-Agents LLM ?

Plusieurs LLM spécialisés (agent Macro, agent Technique, agent Risk) qui débattent puis votent :

| Problème | Explication |
|----------|-------------|
| **Latence multipliée** | 4 agents = 4 appels LLM = 20–60 secondes de délibération |
| **Coût × 4** | Chaque agent consomme des tokens. À l'échelle, la facture explose |
| **Consensus fragile** | Que faire si l'agent Macro dit "achat" et l'agent Technique dit "vente" ? Le vote est arbitraire |
| **Over-engineering** | La stratégie SMC est **algorithmique par nature**. Pourquoi laisser un LLM deviner ce qu'un algo calcule exactement ? |
| **Responsabilité floue** | En cas de perte, qui est responsable ? L'orchestrateur ? Le prompt de l'agent Technique ? |

> **Verdict** : Le multi-agent LLM est **intéressant sur le papier, mais overkill** pour une stratégie dont les règles sont déjà formalisables en code déterministe.

---

## 17.4 Architecture retenue : Hybride Modulaire + IA d'assistance

### 17.4.1 Vue d'ensemble

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    MACROBLOCK TRADER — ARCHITECTURE IA                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │              COUCHE DÉCISIONNELLE (Modules Classiques)             │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────┐ │  │
│  │  │  Macro  │ │Sentiment│ │  Tech   │ │ Scoring │ │    Risk     │ │  │
│  │  │ (règles)│ │(règles) │ │  (algo) │ │(règles) │ │   (règles)  │ │  │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────────┘ │  │
│  │                                                                   │  │
│  │  Autorité : 100% déterministe, traçable, testable                 │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                    │                                     │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │              COUCHE MÉMOIRE (Cerveau Vectoriel)                    │  │
│  │  ChromaDB + Embeddings — Recherche de similarité                   │  │
│  │                                                                   │  │
│  │  Rôle : "Ce setup ressemble à 5 trades passés, 4 ont gagné"       │  │
│  │  Autorité : Informe le scoring (±0.3 max), ne décide jamais       │  │
│  │  Mode : Passif (0–30 trades) → Actif léger (30–100) → Plein (100+│  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                    │                                     │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │              COUCHE PRÉSENTATION (Agent Rédacteur — Optionnel)     │  │
│  │  Kimi-k2.6 (Moonshot AI / Local)                             │  │
│  │                                                                   │  │
│  │  Rôle : Rédiger les alertes, résumer les rapports, expliquer      │  │
│  │  Autorité : Zéro. Ne touche jamais aux chiffres (SL, TP, size)    │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 17.4.2 Les 3 couches en détail

#### Couche 1 : Modules Classiques (Le pilote)

C'est le cœur du système. Tout ce qui est **décisionnel** passe par des algorithmes Python :

| Module | Technologie | Pourquoi pas de LLM ? |
|--------|-------------|----------------------|
| Détection OB/FVG | Algo sur OHLCV (pandas, numpy) | Un algo calcule exactement. Un LLM approxime. |
| Scoring | Formule pondérée déterministe | Reproductible, backtestable, auditable |
| Sizing/SL/TP | Mathématiques exactes | Un LLM pourrait arrondir ou "interpréter" une règle de risque |
| Gestion risque | Règles strictes (if/then) | Pas de négociation possible avec le risque |

#### Couche 2 : Cerveau Vectoriel (La mémoire)

Ce n'est **pas** un LLM. C'est une **base de données vectorielle** (ChromaDB) qui stocke les trades sous forme de vecteurs numériques et effectue des recherches de similarité (k-NN).

| Aspect | Réalité |
|--------|---------|
| **Nature** | Recherche mathématique de similarité (cosine distance) |
| **Déterminisme** | 100% — même vecteur = mêmes voisins |
| **Latence** | < 50 ms par requête |
| **Coût** | Gratuit (local) |
| **Décision** | Aucune. Elle informe le scoring. |

**Ce qu'elle apporte que les règles fixes ne peuvent pas :**
- Détection de patterns implicites (ex: "les OB après gap weekend performent mal")
- Apprentissage des biais utilisateur (ex: "tu fermes trop tôt au Fix PM")
- Garde-fou statistique (ex: "5 setups similaires = 20% WR → prudence")

**Seuils d'activation recommandés :**

| Volume de trades | Mode | Ajustement scoring | Justification |
|------------------|------|-------------------|---------------|
| 0 – 30 | **Passif** | 0 (observation seule) | Pas assez de données pour des similarités fiables |
| 30 – 100 | **Actif léger** | ±0.1 | Patterns émergents, prudence |
| 100+ | **Actif plein** | ±0.3 | Clusters stables, valeur ajoutée réelle |

#### Couche 3 : Agent Rédactur (Le styliste — Optionnel)

Un LLM léger utilisé uniquement pour des tâches **textuelles** et **présentationnelles**.

| Tâche | Input | Output | Exemple |
|-------|-------|--------|---------|
| **Rédaction d'alertes** | JSON technique | Message Telegram lisible | "Setup OB + FVG détecté au Fix PM..." |
| **Résumé macro** | Données brutes (DXY, yields, CPI) | 2 phrases actionnables | "DXY faible et yields en baisse favorisent l'or" |
| **Rapport hebdo** | KPIs (WR, P&L, drawdown) | Texte narratif | "Cette semaine, ton edge était au Fix PM..." |
| **Explication de setup** | Contexte technique | Texte pédagogique | "Pourquoi cet OB ? Parce que..." |

**Règles strictes de l'agent rédactur :**
- Il reçoit les **chiffres finaux** (SL, TP, size, score) — il ne les calcule jamais
- Il ne peut pas modifier une décision déjà prise par les modules classiques
- Il est **désactivable** en un flag (fallback : messages template basiques)
- Coût cible : < 0.01 € par alerte (Kimi-k2.6 ou modèle local)

---

## 17.5 Tableau comparatif des approches

| Critère | Mono-Agent LLM | Multi-Agents LLM | Modules Classiques seuls | **Architecture Hybride (retenue)** |
|---------|---------------|------------------|-------------------------|-----------------------------------|
| **Déterminisme** | ❌ Non | ❌ Non | ✅ Oui | ✅ Oui (modules) + ✅ Oui (vectoriel) |
| **Latence** | ❌ 5–30s | ❌ 20–60s | ✅ < 1s | ✅ < 1s + < 50ms |
| **Coût** | ❌ Élevé | ❌ Très élevé | ✅ Gratuit | ✅ Gratuit + ~0.01€/alerte (optionnel) |
| **Backtestable** | ❌ Non | ❌ Non | ✅ Oui | ✅ Oui |
| **Apprentissage** | ⚠️ Opaque | ⚠️ Opaque | ❌ Non | ✅ Transparent (similarité) |
| **Alertes lisibles** | ✅ Oui | ✅ Oui | ❌ Template basique | ✅ Oui (Kimi rédacteur) |
| **Maintenance** | ❌ Complexe | ❌ Très complexe | ✅ Simple | ✅ Simple |
| **Adapté SMC** | ❌ Non | ❌ Non | ✅ Oui | ✅✅ Parfaitement |

---

## 17.6 Flux de décision avec l'architecture hybride

```
Nouveau setup détecté sur XAU/USD
        │
        ├──→ Module Macro (règles) → Score Macro = +2
        │
        ├──→ Module Technique (algo) → Score Tech = 5.0
        │
        ├──→ Module Risque (règles) → Valide sizing 1.0%, SL 2341.00
        │
        ├──→ Cerveau Vectoriel (k-NN) → 5 similaires, WR 80% → +0.15
        │                              (optionnel, selon volume de données)
        │
        ├──→ Moteur Fusion → Score final = 4.35 (A+)
        │
        ├──→ Agent Rédactur (LLM optionnel) → "Setup OB+FVG au Fix PM..."
        │
        └──→ Notification Telegram
```

**Point clé** : Si l'agent rédacteur Kimi tombe en panne, si le cerveau vectoriel est désactivé, ou s'il n'y a pas de connexion Internet, **les modules classiques continuent de fonctionner parfaitement**. L'IA est un enrichissement, pas une dépendance.

---

## 17.7 Recommandation technique pour l'agent rédacteur

| Option | Modèle | Coût estimé | Usage |
|--------|--------|-------------|-------|
| **A (recommandé)** | **Kimi-k2.6 (Moonshot AI)** | ~0.003€/alerte | Rapide, qualité de rédaction excellente, API compatible OpenAI |
| **B (local)** | Kimi local / Llama 3.1 8B (Ollama) | 0€ | 100% offline, nécessite 8GB RAM |
| **C (désactivé)** | Templates Jinja2 | 0€ | Messages basiques sans IA |

> **Recommandation** : Commencer avec l'**Option D** (templates), passer à l'**Option A** si les alertes manquent de clarté.

---

## 17.8 Sécurité et résilience

| Menace | Mitigation |
|--------|------------|
| API Moonshot AI indisponible | Fallback immédiat sur templates. Le bot ne s'arrête jamais. |
| Coût API qui explose | Limite de tokens par alerte (max 500). Budget quotidien max 0.50€. |
| Hallucination du rédacteur | Kimi ne reçoit que les chiffres finaux. Il ne calcule rien. |
| Fuite de données | Kimi optionnel = données sensibles (prix, P&L) ne quittent pas la machine si mode local. |

---

*Document de décision d'architecture — Sert de référence pour toute discussion future sur l'IA dans le projet.*

*Documents liés : [02 — Architecture Système](02-architecture-systeme.md) | [11 — Stack Technique](11-stack-technique.md) | [16 — Cerveau Vectoriel](16-cerveau-vectoriel.md)*
