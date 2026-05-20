# 14 — Annexe : Matrice de Décision — XAU/USD

> Document de référence rapide. Synthèse des règles de décision du bot spécialisé sur l'or (XAU/USD).

---

## 14.1 Matrice Macro Or × Technique

|  | **Macro Haussier (+2 / +3)** | **Macro Neutre (0)** | **Macro Baissier (-2 / -3)** |
|:---|:---:|:---:|:---:|
| **Setup A+ (≥ 4.0 tech)** | ✅ **SIGNAL FORT** — Grade A+, sizing 1.0 % | ⚠️ **SIGNAL B** — Grade B, sizing 0.5 % | ❌ **PAS DE TRADE** |
| **Setup B (3.0 – 4.0 tech)** | ✅ **SIGNAL B** — Grade B, sizing 0.5 % | ❌ **PAS DE TRADE** | ❌ **PAS DE TRADE** |
| **Setup C (< 3.0 tech)** | ❌ **PAS DE TRADE** | ❌ **PAS DE TRADE** | ❌ **PAS DE TRADE** |

### Exceptions autorisaées (rares)

| Condition | Dérogation |
|-----------|------------|
| Macro neutre (0) + Tech 5.5/5.5 + Timing 2/2 + FVG + Niveau psy | Signal B autorisé |
| Macro baissier -3 + Tech 5.5/5.5 + DXY en baisse soudaine + Setup contre-trend | Signal B autorisé, sizing réduit à 0.5 % |

---

## 14.2 Matrice de Scoring Complète

### Score Macro (-3 à +3)

| Score | Label | Action |
|:-----:|:-----:|:-------|
| +3 | Vent arrière parfait | Favoriser les achats |
| +2 | Vent arrière modéré | Achats privilégiés |
| +1 | Légère poussée favorable | Achats légèrement favorisés |
| 0 | Neutre | La technique domine seule |
| -1 | Légère tête de vent | Ventes légèrement favorisées |
| -2 | Vent contraire modéré | Ventes privilégiées |
| -3 | Vent contraire fort | Favoriser les ventes |

### Score Technique (0 à 5)

| Critère | Points |
|:--------|:------:|
| Structure H1 alignée | +1 |
| BOS M15 récent dans la direction du trade | +1 |
| OB frais (non mitigé) | +1 |
| FVG confluent avec l'OB | +1 |
| Liquidité ciblée claire pour le TP | +0.5 |
| Killzone active | +0.5 |
| **Minimum pour signal** | **3.0** |

### Score Timing (0 à 2)

| Killzone | Score |
|:---------|:-----:|
| NY Open | 2 |
| London Open | 1 |
| London Close | 1 |
| Asia / NY Close / Hors killzone | 0 |

### Score Total

```
Score Total = (Score Macro Or × 0.30) + (Score Technique × 0.50) + (Score Timing × 0.20)
```

| Score Total | Grade | Action | Sizing Or |
|:-----------:|:-----:|:-------|:---------:|
| ≥ 3.5 | **A+** | Notifier immédiatement | **1.0 %** |
| 2.5 – 3.5 | **B** | Notifier | **0.5 %** |
| 1.5 – 2.5 | **C** | Logger uniquement | 0 % |
| < 1.5 | **N/A** | Ignorer | 0 % |

---

## 14.3 Arbre de Décision (Flowchart textuel)

```
START
 │
 ├─→ Scan des paires (M5/M15)
 │
 ├─→ Setup technique détecté ?
 │   └─→ NON → Retour au scan
 │   └─→ OUI → Vérifier structure H1
 │
 ├─→ Structure H1 alignée ?
 │   └─→ NON → Vérifier CHoCH exceptionnel
 │   └─→ OUI → Continuer
 │
 ├─→ Score technique ≥ 3 ?
 │   └─→ NON → Retour au scan
 │   └─→ OUI → Lire score macro
 │
 ├─→ Macro Lock actif (news) ?
 │   └─→ OUI → Signal suspendu
 │   └─→ NON → Continuer
 │
 ├─→ Score macro aligné ou neutre ?
 │   └─→ NON (contre fort) → Vérifier exception
 │   └─→ OUI → Continuer
 │
 ├─→ Killzone active ou exception ?
 │   └─→ NON → Pénaliser timing
 │   └─→ OUI → Continuer
 │
 ├─→ Calculer R:R
 │
 ├─→ R:R ≥ 1:1.5 ?
 │   └─→ NON → Setup rejeté
 │   └─→ OUI → Continuer
 │
 ├─→ Vérifier locks risque
 │   ├─→ 2 trades ouverts ? → REJET
 │   ├─→ Corrélation > 80% ? → REJET
 │   ├─→ Drawdown journalier > 3% ? → REJET
 │   ├─→ SL > 1.5% du prix ? → REJET
 │   └─→ Tous validés → Continuer
 │
 ├─→ Calculer score total
 │
 ├─→ Score total ≥ 2.5 ?
 │   └─→ NON → Logger, pas d'alerte
 │   └─→ OUI → GÉNÉRER SIGNAL
 │
 └─→ Notifier utilisateur
      ├─→ "J'EXÉCUTE" → Tracer trade, suivi actif
      ├─→ "JE REGARDE" → Surveillance continue
      └─→ "IGNORER" → Archiver
```

---

## 14.4 Règles de Gestion du Risque (Résumé)

| Règle | Valeur | Action si non respectée |
|:------|:------:|:------------------------|
| Risque max par trade (A+) | 1.5 % | Rejeter ou downgrader en B |
| Risque max par trade (B) | 1.0 % | Rejeter |
| SL max distance | 1.5 % du prix | Rejeter le setup |
| SL min distance | 5 pips | Rejeter le setup |
| R:R minimum | 1:1.5 | Rejeter le setup |
| Max trades ouverts | 2 | Rejeter nouveau signal |
| Max trades par devise | 1 | Rejeter |
| Corrélation max | 80 % | Rejeter |
| Drawdown journalier max | 3 % | Lock trading |
| Drawdown hebdomadaire max | 6 % | Réduction sizing 50 % |

---

## 14.5 Checklist Pré-Trade (Récap)

Avant d'envoyer toute alerte, le bot vérifie :

```
□ Score total ≥ 2.5
□ Macro non verrouillé par news
□ Risque entre 0.5 % et 1.5 %
□ SL entre 5 pips et 1.5 % du prix
□ R:R ≥ 1:1.5
□ Moins de 2 trades ouverts
□ Aucun trade sur la même devise
□ Corrélation < 80 % avec trades ouverts
□ Killzone active OU setup exceptionnel justifié
□ Drawdown journalier < 3 %
```

---

## 14.6 Killzones Récapitulatif — Or (GMT / CET)

| Killzone | GMT | CET (Paris) | Score Timing | Usage |
|:---------|:---:|:-----------:|:------------:|:------|
| Asia | 00:00–08:00 | 01:00–09:00 | 0 | Évité |
| London Open | 08:00–09:00 | 09:00–10:00 | 1 | Préparation fix |
| **London Fix AM** | **10:00–11:00** | **11:00–12:00** | **2** | **Fix LBMA** |
| **NY Open / COMEX** | **13:20–14:30** | **14:20–15:30** | **2** | **Ouverture futures** |
| **London Fix PM** | **15:00–16:00** | **16:00–17:00** | **2** | **Deuxième fix** |
| London Close | 16:00–17:00 | 17:00–18:00 | 1 | Reversals |
| NY Close | 21:00–22:00 | 22:00–23:00 | 0 | Évité |

---

## 14.7 Corrélation DXY / Or (Temps réel)

| Actif | Corrélation XAU/USD | Seuil d'alerte |
|:------|:-------------------:|:---------------|
| DXY | -0.80 (forte inverse) | Move > 0.2 % en 5 min |
| US10Y | -0.70 (forte inverse) | Move > 5 bps en 5 min |
| VIX | +0.50 (modérée positive) | Spike > 20 % |

> **Règle** : Si DXY bouge brusquement contre la direction du trade ouvert, alerte de précaution envoyée immédiatement.

---

*Document de référence rapide — Pour consultation lors du développement et du trading.*
