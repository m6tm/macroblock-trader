# 16 — Cerveau Vectoriel (Memory & Learning)

## 16.1 Vision

Le **Cerveau Vectoriel** est le système de **mémoire statistique** du bot. Il ne s'agit pas d'une IA générative (LLM), mais d'une **base de données vectorielle** qui effectue des recherches de similarité mathématique (k-NN). Il transforme chaque trade (signal, contexte, résultat) en un **vecteur numérique** stocké dans ChromaDB. Quand un nouveau setup se forme, le cerveau recherche les expériences passées les plus similaires et informe le scoring.

> **Analogie** : Si le module Technique est les yeux (voir le setup), le Cerveau Vectoriel est l'expérience (se souvenir des setups similaires et de leur résultat). C'est un "rappel d'expérience", pas un "cerveau pensant".

## 16.2 Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CERVEAU VECTORIEL                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────────┐        ┌──────────────────┐                      │
│  │   EMBEDDING      │        │   VECTOR DB      │                      │
│  │   ENGINE         │───────→│   (ChromaDB)     │                      │
│  │                  │        │                  │                      │
│  │  Trade → Vecteur │        │  Collection      │                      │
│  │  (384-768 dims)  │        │  "gold_memory"   │                      │
│  └──────────────────┘        └────────┬─────────┘                      │
│                                       │                                 │
│                                       │ Query (k-NN)                    │
│                                       ▼                                 │
│  ┌──────────────────┐        ┌──────────────────┐                      │
│  │  SCORING         │◄───────│  RETRIEVAL       │                      │
│  │  ADJUSTER        │        │  ENGINE          │                      │
│  │                  │        │                  │                      │
│  │  +0.2 si similar │        │  "5 trades       │                      │
│  │  trades = 80% WR │        │   similaires,     │                      │
│  │  -0.3 si 20% WR  │        │   4 gagnants"     │                      │
│  └──────────────────┘        └──────────────────┘                      │
│                                                                         │
│  ┌──────────────────┐        ┌──────────────────┐                      │
│  │  FEEDBACK        │        │  LEARNING        │                      │
│  │  LOOP            │───────→│  LOOP            │                      │
│  │                  │        │                  │                      │
│  │  User confirme   │        │  Mise à jour     │                      │
│  │  résultat réel   │        │  poids du vecteur│                      │
│  └──────────────────┘        └──────────────────┘                      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## 16.3 Technologie : ChromaDB

| Critère | Choix | Justification |
|---------|-------|---------------|
| **Base** | ChromaDB | Open source, Python natif, local, pas de serveur externe |
| **Modèle d'embedding** | `sentence-transformers/all-MiniLM-L6-v2` (ou équivalent) | Léger, rapide, 384 dimensions, suffisant pour la structure de données tabulaires |
| **Alternative** | `OpenAI text-embedding-3-small` ou API Moonshot AI | Meilleure qualité, mais nécessite une clé API (optionnel). Kimi-k2.6 peut aussi générer des embeddings via son API. |
| **Distance** | Cosine Similarity | Standard pour les embeddings sémantiques |
| **Stockage** | Fichier local (`./data/chroma_db/`) | Persistant, sauvegardable avec Git |
| **Déterminisme** | 100% | Même vecteur = mêmes voisins, toujours |
| **Coût** | Gratuit | Aucun appel API externe en mode local |

> **Note** : Pour des embeddings plus riches sur données structurées, on peut aussi utiliser un **auto-encoder** entraîné spécifiquement sur les features des trades, ou simplement normaliser les features numériques en vecteur dense.

## 16.4 Vectorisation d'un trade

### 16.4.1 Features encodées

Le vecteur représente l'**état complet du marché + le setup** au moment du signal.

| Catégorie | Features | Type | Pondération |
|-----------|----------|------|-------------|
| **Prix** | XAU/USD, distance au dernier swing high/low | Normalisé | 1.0x |
| **Macro** | DXY, US10Y, TIPS, VIX (tous normalisés) | Normalisé | 1.2x |
| **Structure** | Tendance H4/H1 (encodée -1/0/+1), BOS confirmé | Encodé | 1.0x |
| **OB** | Position relative de l'OB, fraîcheur | Normalisé | 1.5x |
| **FVG** | Présence, taille, position relative | Normalisé | 1.3x |
| **Liquidité** | Distance à la cible, type (psy/eqh/eql) | Normalisé | 1.0x |
| **Timing** | Killzone (one-hot), heure de la journée | Encodé | 0.8x |
| **Sentiment** | Score sentiment, ratio retail | Normalisé | 0.7x |

### 16.4.2 Texte sémantique (pour sentence-transformers)

Pour les modèles de type sentence-transformers, on génère un **texte descriptif** du trade qui est ensuite encodé :

```
Context: DXY falling at 104.80, VIX elevated at 22.5, real yields declining.
Setup: Bullish Order Block on M15 with confluent Fair Value Gap.
Structure: H4 bullish, H1 bullish, BOS confirmed on M15.
Timing: London Fix PM active.
Macro score: +2 bullish for gold.
Technical score: 5.0 out of 5.5.
Entry zone: 2345.00 to 2346.50.
Stop loss: 2341.00, 35 dollars below entry.
Take profit 1: 2352.00 toward equal highs.
Risk reward: 1 to 2.0.
```

> **Avantage** : Le texte capture les relations sémantiques ("DXY falling" est proche de "dollar weak"). Le modèle comprend implicitement les corrélations.

### 16.4.3 Métadonnées attachées au vecteur

Chaque vecteur dans ChromaDB est accompagné de métadonnées structurées :

```json
{
  "trade_id": "TRADE-20260520-001",
  "signal_id": "SIG-20260520-001",
  "direction": "BUY",
  "grade": "A+",
  "setup_type": "OB+FVG",
  "killzone": "LONDON_FIX_PM",
  "macro_score": 2,
  "technical_score": 5.0,
  "score_total": 4.2,
  "rr_expected": 2.0,
  "status_virtual": "WIN",
  "pnl_virtual_dollars": 7.8,
  "pnl_real_dollars": 7.5,
  "user_executed": true,
  "user_feedback_status": "SUBMITTED",
  "created_at": "2026-05-20T14:32:05Z",
  "week_of_year": 20,
  "month": 5
}
```

## 16.5 Retrieval — Recherche d'expériences similaires

### 16.5.1 Déclencheur

Le retrieval est déclenché **après la validation technique** (Phase 3) et **avant la décision finale** du moteur de fusion.

```
Nouveau setup détecté
        │
        ▼
[Générer vecteur du nouveau setup]
        │
        ▼
[Query ChromaDB : k=5 plus proches voisins]
        │
        ▼
[Analyser les résultats]
        │
        ▼
[Ajuster le score ou émettre une alerte]
```

### 16.5.2 Requête (k-NN)

```python
# Pseudo-code
results = chroma_collection.query(
    query_embeddings=[new_setup_embedding],
    n_results=5,
    where={
        "user_executed": True,          # Uniquement trades exécutés (feedback réel)
        "user_feedback_status": "SUBMITTED"  # Uniquement trades avec feedback
    }
)
```

### 16.5.3 Analyse des résultats

Pour les 5 trades similaires retrouvés, le bot calcule :

| Métrique | Calcul | Usage |
|----------|--------|-------|
| **Win Rate similaire** | Nombre de WIN / 5 | Si < 40 % → pénaliser le score |
| **P&L moyen similaire** | Moyenne des pnl_real_dollars | Si négatif → alerte forte |
| **Similarité moyenne** | Score cosine moyen | Plus c'est proche de 1, plus l'ajustement est fort |
| **R:R réalisé moyen** | Moyenne des R:R réels | Compare avec le R:R attendu du nouveau setup |

### 16.5.4 Ajustement du score

```python
# Logique d'ajustement
SIMILAR_TRADES = 5
WR_SIMILAR = count_wins(similar_trades) / SIMILAR_TRADES
AVG_PNL = mean([t.pnl_real for t in similar_trades])
SIMILARITY_SCORE = mean([t.similarity for t in similar_trades])

# Règles d'ajustement (selon le mode d'activation)
if vector_db_mode == "PASSIVE":
    score_adjustment = 0  # Observation seule, pas assez de données
elif vector_db_mode == "LIGHT":
    if WR_SIMILAR >= 0.80 and AVG_PNL > 0:
        score_adjustment = +0.1
    elif WR_SIMILAR <= 0.40 and AVG_PNL < 0:
        score_adjustment = -0.1
    else:
        score_adjustment = 0
elif vector_db_mode == "FULL":
    if WR_SIMILAR >= 0.80 and AVG_PNL > 0:
        score_adjustment = +0.2
        confidence_boost = "Trades similaires historiquement très performants"
    elif WR_SIMILAR <= 0.40 and AVG_PNL < 0:
        score_adjustment = -0.3
        confidence_drop = "Trades similaires historiquement perdants — prudence"
    elif WR_SIMILAR >= 0.60 and AVG_PNL > 0:
        score_adjustment = +0.1
        confidence_boost = "Trades similaires légèrement favorables"
    else:
        score_adjustment = 0

adjusted_score = base_score + score_adjustment
```

> **Règle** : L'ajustement du cerveau vectoriel ne peut pas changer un Grade B en A+, ni un A+ en rejet. Il peut uniquement **renforcer ou affaiblir** un signal existant.

> **Modes d'activation** (voir [17 — Architecture Intelligence](17-architecture-intelligence.md)) :
> - **PASSIF** (0–30 trades) : Ajustement = 0. Observation et stockage uniquement.
> - **LÉGER** (30–100 trades) : Ajustement max ±0.1.
> - **PLEIN** (100+ trades) : Ajustement max ±0.3.

## 16.6 Apprentissage — Feedback Loop

### 16.6.1 Cycle d'apprentissage

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   TRADE     │────→│   USER      │────→│   VECTOR    │
│   CLOSED    │     │   FEEDBACK  │     │   UPDATE    │
│   (virtuel) │     │   (réel)    │     │   (label)   │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                                │
                                                ▼
                                       ┌─────────────┐
                                       │   FUTURE    │
                                       │   RETRIEVAL │
                                       │   (meilleur)│
                                       └─────────────┘
```

### 16.6.2 Mise à jour du vecteur

Quand l'utilisateur soumet son feedback (`/feedback TRADE-xxx`) :

1. **Récupération** : Le vecteur du trade est récupéré dans ChromaDB via son `trade_id`
2. **Labelisation** : Les métadonnées sont mises à jour avec :
   - `pnl_real_dollars`
   - `user_exit_reason`
   - `user_executed = true`
   - `user_feedback_status = "SUBMITTED"`
3. **Recalcul** : Si le résultat réel diffère significativement du résultat virtuel (> 20 % de divergence), une alerte est envoyée à l'utilisateur pour identifier le biais.

### 16.6.3 Apprendre des échecs

Le cerveau vectoriel apprend particulièrement bien des **échecs** :

| Scénario | Action du cerveau |
|----------|-------------------|
| Setup A+ similaire → perte réelle | Chercher la différence (DXY ? Killzone ?) et ajuste la prochaine fois |
| Setup B similaire → gain réel | Surveiller si ce pattern devient fiable, potentiellement upgrader les B similaires |
| Divergence bot vs user systématique | Identifier le biais (ex: slippage, exécution tardive, fermeture prématurée) |

### 16.6.4 Consolidation hebdomadaire

Chaque dimanche soir, le cerveau vectoriel effectue une **consolidation** :

1. **Regroupement** : Clustering des vecteurs de la semaine (K-Means ou HDBSCAN)
2. **Identification des patterns** : Quels types de setups ont le mieux performé ?
3. **Mise à jour des règles implicites** : Si tous les trades "OB+FVG+Fix AM" ont gagné → renforcer ce pattern
4. **Génération d'insights** : "Tes 3 dernières pertes étaient toutes des setups sans FVG confluent."

## 16.7 Interface avec les autres modules

### 16.7.1 Intégration avec le Moteur de Fusion

```
Module Technique détecte un setup (Score Tech = 4.5)
        │
        ▼
Module Macro calcule le vent (Score Macro = +2)
        │
        ▼
CERVEAU VECTORIEL intervient :
        ├──→ Recherche des 5 setups similaires passés
        ├──→ WR similaire = 40 % (2 wins / 5 trades)
        ├──→ Ajustement = -0.2
        │
        ▼
Score ajusté = (2×0.30) + (4.5×0.50) + (2×0.20) - 0.2 = 3.55
Grade = B (limite A+)
Alerte dans la notification : "⚠️ Trades similaires historiquement mitigés (40% WR)"
```

### 16.7.2 Intégration avec le Journal

Le Journal est la **source de vérité** pour le cerveau vectoriel :
- Chaque trade validé dans le Journal est automatiquement vectorisé
- Les métadonnées ChromaDB sont synchronisées avec SQLite
- Le `trade_id` sert de clé de liaison entre les deux systèmes

### 16.7.3 Intégration avec les Notifications

Le cerveau vectoriel enrichit les alertes avec du contexte historique :

```
🔔 SIGNAL — XAUUSD BUY (A+) [Score: 3.8]

... (plan de trade standard) ...

🧠 AVIS DU CERVEAU :
  5 trades similaires trouvés dans l'historique
  → Win rate: 60 % (3/5)
  → P&L moyen: +4.2 $
  → Dernier trade similaire: WIN (+6 $ le 18/05)
  
  💡 Insight: "Les setups OB+FVG au Fix PM ont bien performé
     cette semaine."
```

## 16.8 Métriques du cerveau vectoriel

| Métrique | Objectif | Signification |
|----------|----------|---------------|
| **Trades vectorisés** | > 50 | Volume minimal pour apprendre |
| **Précision du retrieval** | > 70 % | Les trades similaires ont des résultats cohérents |
| **Amélioration post-ajustement** | +5 % WR | Le cerveau améliore-t-il vraiment les décisions ? |
| **Divergence bot/user** | < 15 % | Le bot et l'utilisateur sont-ils alignés ? |
| **Temps de query** | < 100 ms | La recherche vectorielle doit être instantanée |

## 16.9 Stack technique

| Composant | Technologie | Rôle |
|-----------|-------------|------|
| **Vector DB** | ChromaDB | Stockage et recherche k-NN |
| **Embedding model** | `sentence-transformers/all-MiniLM-L6-v2` | Encodage texte → vecteur (384 dims) |
| **Alternative** | Modèle custom (scikit-learn PCA/AutoEncoder) | Encodage features numériques → vecteur |
| **Synchronisation** | Event bus interne | Propagation trade_closed → vectorisation |
| **Persistant** | Fichier local `./data/chroma_db/` | Survie aux redémarrages |

## 16.10 Exemple complet d'un cycle

**Étape 1** — Signal généré
```
Nouveau setup détecté sur XAU/USD à 2345.50
Score technique: 5.0, Score macro: +2, Timing: 2
```

**Étape 2** — Vectorisation
```
Texte généré: "Bullish OB M15 with FVG confluent. DXY falling.
               London Fix PM. H4 bullish..."
Embedding: [0.12, -0.05, 0.88, ...] (384 dimensions)
```

**Étape 3** — Retrieval
```
5 voisins similaires trouvés :
  1. TRADE-20260518-003 (sim: 0.94) → WIN (+6 $)
  2. TRADE-20260515-001 (sim: 0.91) → WIN (+8 $)
  3. TRADE-20260510-002 (sim: 0.89) → LOSS (-4 $)
  4. TRADE-20260505-004 (sim: 0.87) → WIN (+5 $)
  5. TRADE-20260428-001 (sim: 0.85) → WIN (+7 $)

WR similaire = 80 % | Avg P&L = +4.4 $ | Ajustement = +0.15
```

**Étape 4** — Décision ajustée
```
Score final = 4.2 + 0.15 = 4.35 → Grade A+ confirmé
Notification inclut: "🧠 Trades similaires: 80% win rate"
```

**Étape 5** — Trade exécuté et suivi
```
L'utilisateur exécute, le trade se déroule, TP1+TP2 atteints
P&L virtuel: +78 € | P&L réel rapporté: +75 €
```

**Étape 6** — Apprentissage
```
Le vecteur est mis à jour avec :
  - status_virtual: WIN
  - pnl_real_dollars: 7.5
  - user_feedback_status: SUBMITTED

Le cerveau a maintenant une expérience de plus pour les futurs setups similaires.
```

---

*Documents liés : [02 — Architecture Système](02-architecture-systeme.md) | [15 — Module Journal](15-module-journal.md) | [06 — Moteur de Fusion & Scoring](06-moteur-fusion-scoring.md)*
