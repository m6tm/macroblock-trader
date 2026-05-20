# 12 — Métriques & Amélioration Continue

## 12.1 Objectif

Un système de trading n'est jamais terminé. Il doit évoluer en permanence en fonction des données de performance. Ce document définit les métriques à suivre, les rapports à générer, et la boucle d'amélioration continue.

## 12.2 Métriques clés (KPIs)

### 12.2.1 Performance absolue

| Métrique | Formule | Objectif | Fréquence |
|----------|---------|----------|-----------|
| **Profit & Loss (P&L)** | Σ (PnL de tous les trades) | > 0 | Continu |
| **Return on Investment (ROI)** | (Capital final – Capital initial) / Capital initial | > 5 % / mois | Mensuel |
| **Drawdown maximal** | Perte maximale depuis le dernier pic | < 10 % | Continu |
| **Drawdown moyen** | Moyenne des drawdowns journaliers | < 5 % | Hebdo |

### 12.2.2 Qualité des trades

| Métrique | Formule | Objectif | Fréquence |
|----------|---------|----------|-----------|
| **Win Rate** | Trades gagnants / Trades totaux | > 55 % | Hebdo |
| **Profit Factor** | Σ (gains) / Σ (pertes) | > 1.5 | Mensuel |
| **R:R moyen réalisé** | Moyenne des (Profit / Perte) par trade | > 1:2 | Mensuel |
| **R:R moyen attendu** | Moyenne des R:R au moment du signal | > 1:2 | Mensuel |
| **Expectancy** | (Win% × Gain moyen) – (Loss% × Perte moyenne) | > 0 | Mensuel |

### 12.2.3 Efficacité du système

| Métrique | Formule | Objectif | Fréquence |
|----------|---------|----------|-----------|
| **Signaux générés / jour** | Nombre moyen de signaux | 3–8 / semaine | Hebdo |
| **Taux d'exécution utilisateur** | Signaux exécutés / Signaux générés | > 60 % | Mensuel |
| **Temps moyen en position** | Durée entre ouverture et clôture | < 4h | Mensuel |
| **Slippage utilisateur** | Différence entrée bot vs entrée utilisateur | < 2 $ | Mensuel |
| **Feedback utilisateur** | Trades avec feedback / Trades clôturés | > 80 % | Mensuel |
| **Précision cerveau vectoriel** | Trades similaires avec résultat cohérent | > 70 % | Mensuel |
| **Trades en mémoire vectorielle** | Volume de données pour apprentissage | > 50 | Mensuel |
| **Mode cerveau vectoriel** | Passif / Léger / Plein | Plein à 100+ trades | Mensuel |

### 12.2.4 Métriques par catégorie

Le système calcule séparément les KPIs pour chaque dimension :

| Dimension | Exemples de segments |
|-----------|----------------------|
| **Par type de setup** | OB, OB+FVG, OB+FVG+Psy... |
| **Par grade** | A+, B |
| **Par setup** | OB seul, OB+FVG, FVG seul |
| **Par killzone** | London Open, NY Open, London Close |
| **Par jour** | Lundi, Mardi... |
| **Par contexte macro** | Macro aligné, neutre, contre |

## 12.3 Rapports automatiques

### 12.3.1 Rapport quotidien (21h GMT)

Envoyé automatiquement à la fermeture de NY.

```
📊 RAPPORT QUOTIDIEN — 20 Mai 2026

Signaux aujourd'hui: 2
Exécutés par toi: 1
Résultats:
  • XAUUSD BUY A+ : +18 $ ✅
  • XAUUSD SELL B : Non exécuté

P&L virtuel jour: +18 $ (+0.18%)
P&L réel rapporté: +17 $

Prochaines news (demain):
  08:00 GMT — London Fix AM (🔴 Haut impact Or)
  14:30 GMT — Building Permits US (🟠 Moyen)
```

### 12.3.2 Rapport hebdomadaire (dimanche 20h GMT)

Analyse approfondie de la semaine écoulée.

```
📈 RAPPORT HEBDOMADAIRE — Semaine du 18 au 24 Mai 2026

═══ PERFORMANCE ═══
Trades virtuels: 6
Win rate: 66.7% (4/6)
Profit factor: 2.3
P&L virtuel: +312€ (+3.12%)
Drawdown max: 2.1%

═══ PAR PAIRE ═══
  XAUUSD : 4 trades, 66.7% WR, +28 $ net
  OB + FVG + Psy : 2 trades, 100% WR, +30 $
  OB seul : 1 trade, 0% WR, -8 $
  FVG seul : 1 trade, 50% WR, +6 $

═══ PAR SETUP ═══
  OB + FVG : 3 trades, 100% WR, +127 pips ⭐
  OB seul   : 2 trades, 50% WR, +8 pips
  FVG seul  : 1 trade, 0% WR, -12 pips

═══ PAR KILLZONE ═══
  NY Open      : 3 trades, 100% WR ⭐
  London Open  : 2 trades, 50% WR
  London Close : 1 trade, 0% WR

═══ ANALYSE UTILISATEUR ═══
Taux d'exécution: 83% (5/6)
Divergence bot vs réel: -8 pips (slippage d'exécution moyen)
Temps de réponse moyen: 4.2 min

═══ RECOMMANDATIONS ═══
→ Renforcer le critère FVG confluent (edge significatif)
→ Surveiller DXY pendant les trades (corrélation critique)
→ Ton slippage augmente — vérifier ta connexion/latence
```

### 12.3.3 Rapport mensuel (dernier jour du mois)

Rapport complet pour la révision stratégique.

| Section | Contenu |
|---------|---------|
| **Executive Summary** | P&L, WR, drawdown, nombre de trades |
| **Analyse par dimension** | Setup, killzone, macro, grade, pattern vectoriel |
| **Analyse des pertes** | Quels setups ont perdu ? Pourquoi ? |
| **Analyse des gains manqués** | Signaux non exécutés qui auraient gagné |
| **Divergence bot/utilisateur** | Comparaison performance virtuelle vs réelle |
| **Recommandations d'ajustement** | Paramètres à modifier + insights du cerveau vectoriel + mode d'activation conseillé |
| **Objectifs du mois prochain** | Cibles réalistes basées sur les données + seuil d'activation du cerveau vectoriel |

## 12.4 Boucle d'amélioration continue

```
┌──────────────────────────────────────────────────────────────────────┐
│                 BOUCLE D'AMÉLIORATION CONTINUE                       │
│                                                                      │
│   ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌──────────────┐  │
│   │  TRADER │────→│  JOURNAL│────→│ RAPPORT │────→│    ANALYSE   │  │
│   │         │     │         │     │         │     │              │  │
│   └─────────┘     └─────────┘     └─────────┘     └───────┬──────┘  │
│                                                           │         │
│   ┌─────────────┐     ┌─────────┐     ┌─────────┐         │         │
│   │   CERVEAU   │←────│  TESTE  │←────│ HYPOTHÈSE│←────────┘         │
│   │  VECTORIEL  │     │         │     │          │                   │
│   │  (mémoire)  │     └─────────┘     └─────────┘                    │
│   └──────┬──────┘                                                   │
│          │                                                           │
│          └────────────────────────────────────────────────→ [RETOUR]  │
└──────────────────────────────────────────────────────────────────────┘
```

### 12.4.1 Processus mensuel

**Semaine 1 du mois** : Analyse du rapport mensuel + Cerveau Vectoriel
- Identifier les patterns gagnants et perdants (humain + machine)
- Consulter les insights du cerveau vectoriel (clusters, corrélations cachées)
- Évaluer le volume de trades : faut-il passer le cerveau en mode Passif / Léger / Plein ?
- Noter les divergences bot vs réel
- Formuler 1–3 hypothèses d'amélioration

**Semaine 2–3** : Test des ajustements
- Modifier un seul paramètre à la fois
- Surveiller l'impact sur les signaux générés
- Observer si le cerveau vectoriel confirme ou infirme l'ajustement
- Comparer avec la baseline du mois précédent
- Si le cerveau est en mode Passif, prioriser l'accumulation de feedback utilisateur

**Semaine 4** : Validation et documentation
- Les nouveaux paramètres améliorent-ils les métriques ?
- Le cerveau vectoriel montre-t-il une meilleure cohérence des clusters ?
- Le volume de trades justifie-t-il un changement de mode (Passif → Léger → Plein) ?
- Si oui → les garder. Si non → revenir en arrière.
- Documenter la décision dans le journal
- Mettre à jour les poids des features du cerveau si nécessaire

### 12.4.2 Paramètres ajustables

| Paramètre | Valeur par défaut | Plage d'ajustement |
|-----------|-------------------|--------------------|
| Seuil score total pour signal | 2.5 | 2.0 – 3.5 |
| Poids macro dans le scoring | 0.30 | 0.20 – 0.40 |
| Risque max par trade | 1.0 % | 0.5 % – 1.5 % |
| R:R minimum | 1:2.0 | 1:1.5 – 1:3.0 |
| Buffer SL (ATR multiplier) | 0.5 | 0.3 – 1.0 |
| Validité d'un signal | 3 candles M15 | 2 – 5 candles |
| Killzones actives | Fix AM/PM + COMEX | Toutes combinaisons |
| **Poids cerveau vectoriel** | **0.0 (désactivé)** | **0.0 – 0.3** |

> **Règle d'or** : Ne jamais changer plus d'un paramètre par mois. Sinon, on ne sait pas ce qui fonctionne.

## 12.5 Détection des biais utilisateur

Le système compare systématiquement la performance virtuelle du bot avec l'exécution réelle de l'utilisateur pour identifier les biais comportementaux.

| Biais | Indicateur | Solution suggérée |
|-------|------------|-------------------|
| **Peur (FOMO inverse)** | Taux d'exécution < 50 % | Réduire la fréquence des alertes (A+ uniquement) |
| **Cupidité** | SL élargi manuellement vs plan | Rappel automatique du SL initial |
| **Revenge trading** | Plusieurs trades rapides après une perte | Lock automatique 2h après 2 pertes consécutives |
| **Overtrading** | Taux d'exécution > 90 % | Limiter à 2 trades/jour max |
| **Slippage excessif** | Divergence > 5 pips systématique | Vérifier latence, spread, qualité d'exécution du broker |
| **Modification des TP** | TP2/3 jamais atteints car fermé trop tôt | Rappel du plan initial, trailing auto suggéré |

## 12.6 Tableau de bord de suivi mensuel

Le bot génère un tableau récapitulatif mensuel pour l'utilisateur :

| Mois | Trades | WR | P&L Virtuel | P&L Réel | Diff | Drawdown | Ajustement |
|------|--------|----|-------------|----------|------|----------|------------|
| Mai | 18 | 62 % | +3.2 % | +2.1 % | -1.1 % | 4.1 % | Baseline |
| Juin | 22 | 58 % | +2.8 % | +2.5 % | -0.3 % | 3.8 % | FVG obligatoire pour B |
| Juillet | 15 | 67 % | +4.1 % | +3.9 % | -0.2 % | 2.9 % | Killzone NY only |

---

*Documents liés : [09 — Interface Utilisateur](09-interface-utilisateur.md) | [13 — Checklist de Lancement](13-checklist-lancement.md)*
