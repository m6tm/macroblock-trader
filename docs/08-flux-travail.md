# 08 — Flux de Travail du Bot

## 8.1 Vue d'ensemble

Le bot opère selon un cycle continu de **5 phases** : Scan → Détection → Validation → Notification → Suivi. Chaque phase est automatisée, sauf l'exécution finale qui reste manuelle.

```
┌─────────┐    ┌───────────┐    ┌────────────┐    ┌──────────────┐    ┌─────────┐
│  SCAN   │───→│ DÉTECTION │───→│ VALIDATION │───→│ NOTIFICATION │───→│ SUIVI   │
│(permanent)│   │(sur event) │   │ (1-5 min)  │   │  (instant)   │   │(continu)│
└─────────┘    └───────────┘    └────────────┘    └──────────────┘    └─────────┘
     ↑                                                                      │
     │                                                                      ▼
     │                                                             ┌─────────────┐
     │                                                             │   FEEDBACK  │
     │                                                             │  UTILISATEUR│
     │                                                             │  (manuel)   │
     │                                                             └──────┬──────┘
     │                                                                    │
     │                                                             ┌─────────────┐
     │                                                             │   CERVEAU   │
     │                                                             │  VECTORIEL  │
     │                                                             │(apprentissage)│
     │                                                             └─────────────┘
     └──────────────────────────────────────────────────────────────────────┘
                              (Boucle infinie)
```

## 8.2 Phase 1 : Scan (permanent)

**Fréquence** : En continu (temps réel sur M5/M15)

### Actions du bot

1. **Récupération des prix**
   - OHLCV M5 et M15 pour XAU/USD
   - Mise à jour des structures (swings highs/lows, BOS, CHoCH)

2. **Mise à jour du contexte macro**
   - Vérification du calendrier économique (news imminentes ?)
   - Mise à jour du score macro si nouvelle donnée économique
   - Vérification des locks macro actifs

3. **Mise à jour du sentiment**
   - Récupération des ratios retail (si source temps réel disponible)
   - Mise à jour hebdomadaire du COT (vendredi)

4. **Surveillance des trades ouverts**
   - Vérification si SL/TP atteints
   - Vérification des invalidations (clôture sous OB, etc.)
   - Déclenchement des trailing stops

### Fréquence des mises à jour par source — Spécifique Or

| Source | Fréquence de scan | Raison |
|--------|-------------------|--------|
| Prix XAU/USD M5/M15 | Temps réel (chaque nouvelle candle) | Actif principal |
| DXY M15 | Toutes les 5 minutes | Corrélation inverse critique |
| Calendrier économique | Toutes les 5 minutes | News US = impact direct |
| Yields US10Y / TIPS | Toutes les 15 minutes | Driver fondamental |
| VIX | Toutes les 15 minutes | Risk sentiment |
| Géopolitique / News | Toutes les 5 minutes | L'or est ultra-sensible |
| London Fix | Automatique 09:45 / 14:45 GMT | Lock fix |
| Ratios retail | Toutes les 30 minutes | Sentiment |
| COT Report | Vendredi après publication | Positionnement institutions or |

## 8.3 Phase 2 : Détection (sur événement)

**Déclencheur** : Un événement technique significatif est détecté sur une paire.

### Conditions de déclenchement — XAU/USD

- Un **BOS** ou **CHoCH** vient de se former sur M15
- Un **Order Block frais** est identifié sur XAU/USD
- Un **FVG** est formé en confluence avec un OB
- Le prix approche une zone d'intérêt technique ou un niveau psychologique
- Le DXY confirme la direction (ou est neutre)

### Actions du bot

1. Identifier la direction potentielle sur XAU/USD
2. Lire le **score macro Or** actuel
3. Vérifier la corrélation DXY (move brusque ?)
4. Vérifier les locks (news, fix, drawdown, trade déjà ouvert)
5. Si premiers filtres passés → passer en Phase 3

## 8.4 Phase 3 : Validation (1–5 minutes)

**Objectif** : Confirmer que le setup est valide, calculer le plan de trade exact, et consulter la mémoire vectorielle (si activée).

### Consultation du Cerveau Vectoriel

Cette étape est **optionnelle** selon le volume de données historiques :

| Mode | Nb trades | Action |
|------|-----------|--------|
| **Passif** | < 30 | Le cerveau observe et stocke, mais n'ajuste pas le scoring |
| **Léger** | 30–100 | Recherche des 5 trades similaires, ajustement max ±0.1 |
| **Plein** | 100+ | Recherche et ajustement max ±0.3 |

> Le cerveau vectoriel informe, il ne décide pas. Un signal rejeté par les règles reste rejeté, quelle que soit la mémoire.

### Checklist de validation — XAU/USD

```
□ Structure H4/H1 alignée avec la direction du trade
□ BOS M15 récent dans la direction du H4/H1
□ OB frais identifié avec coordonnées exactes (ou mitigation 50%)
□ FVG confluent (optionnel mais valorisant)
□ Pool de liquidité cible identifié pour le TP (niveau psy prioritaire)
□ Killzone active (Fix AM/PM ou COMEX) OU justification exceptionnelle
□ Score macro Or ≥ -1 (pour un long) OU ≤ +1 (pour un short)
□ DXY aligné (pas de move > 0.2 % contre en cours)
□ SL technique entre 15 $ et 1.0 % du prix
□ R:R attendu ≥ 1:2.0
□ Aucun trade ouvert sur XAU/USD
□ Tous les locks de risque respectés
□ Pas de gap weekend non résolu
```

### Calculs effectués — XAU/USD

| Calcul | Méthode | Spécificité Or |
|--------|---------|----------------|
| Zone d'entrée | [Low de l'OB, High de l'OB] sur M15, affinée en M5 | Accepter mitigation 50 % |
| SL exact | Wick le plus extrême de l'OB + buffer ATR(14) × 0.5 | Min 15 $, max 1.0 % prix |
| TP1 | Premier FVG opposé / Equal Highs / **niveau psychologique** | Target psy = priorité |
| TP2 | Prochaine structure significative (swing opposé) / OB inverse H1 | |
| TP3 | Trailing après BE | |
| Taille | Risque en € / (SL en $ × valeur du $) | Valeur du $ XAU/USD ≈ 1 €/lot |
| R:R | (TP1 – Entrée) / (Entrée – SL) | Minimum 1:2.0 |
| Score total | (Macro Or × 0.30) + (Tech × 0.50) + (Timing × 0.20) | Macro Or spécifique |

### Durée de validité du signal — XAU/USD

| Type de setup | Durée de validité | Spécificité Or |
|---------------|-------------------|----------------|
| Standard | 3 candles M15 (45 minutes) | |
| Setup agressif (M5 précis) | 2 candles M5 (10 minutes) | Précision d'entrée |
| Setup swing (M15 + H4) | 5 candles M15 (75 minutes) | Contexte H4 |
| **Avant London Fix** | Jusqu'à 5 min avant le fix | Éviter le fix si pas entré |
| **Avant COMEX Open** | Jusqu'à 13:15 GMT | Éviter l'ouverture si pas entré |

> Si le prix n'entre pas dans la zone dans ce délai → signal expiré.

## 8.5 Phase 4 : Notification (instantanée)

**Déclencheur** : Le signal est validé avec un score ≥ 2.5 (Grade B ou A+).

### Format de l'alerte

```
╔══════════════════════════════════════════════════════════════════╗
║  🔔 SIGNAL MACROBLOCK — [XAUUSD] — ACHAT (BUY)                  ║
╠══════════════════════════════════════════════════════════════════╣
║  Grade: A+ (4.2/5)                                               ║
╠══════════════════════════════════════════════════════════════════╣
║  📊 CONTEXTE                                                      ║
║  Macro: +2 🟢 (DXY faible, CPI US dans la cible)                ║
║  Setup: Bullish OB M15 + FVG confluent                          ║
║  Killzone: NY Open ✅                                            ║
╠══════════════════════════════════════════════════════════════════╣
║  📍 PLAN DE TRADE                                                 ║
║  Entrée : 1.08450 – 1.08500 (zone OB)                           ║
║  SL      : 1.08320 (‐13 pips / ‐1.2%)                           ║
║  TP1     : 1.08700 (+22 pips / 1:1.7) — 50% position             ║
║  TP2     : 1.08950 (+45 pips / 1:3.4) — 30% position             ║
║  TP3     : Trail après BE — 20% position                         ║
╠══════════════════════════════════════════════════════════════════╣
║  💰 GESTION DU RISQUE                                             ║
║  Taille suggérée : 1.5% du capital = 150€                        ║
║  R:R attendu : 1:2.8                                              ║
╠══════════════════════════════════════════════════════════════════╣
║  ⏱️  VALIDE JUSQU'À : 14:30 GMT (45 min)                        ║
║  ⚠️  INVALIDÉ SI : Clôture M5 sous 1.08430                      ║
╠══════════════════════════════════════════════════════════════════╣
║  [⚡ J'EXÉCUTE]  [👀 JE REGARDE]  [❌ IGNORER]                  ║
╚══════════════════════════════════════════════════════════════════╝
```

### Canaux de notification

| Canal | Usage | Priorité |
|-------|-------|----------|
| **Telegram Bot** | Alertes temps réel sur mobile + feedback | Principal |
| **Dashboard Web** | Vue détaillée, charts, historique, journal | Secondaire |
| **Log fichier** | Traçabilité complète, debugging | Technique |

### Actions utilisateur possibles

| Action | Effet sur le bot |
|--------|------------------|
| **"J'EXÉCUTE"** | Le bot trace le trade XAU/USD comme "exécuté" et commence le suivi |
| **"JE REGARDE"** | Le bot continue de surveiller le setup mais ne le trace pas dans le journal actif |
| **"IGNORER"** | Le bot annule le signal et loggue la raison si fournie |
| **Aucune réponse** | Après expiration du délai, le signal est archivé comme "non exécuté" |

## 8.6 Phase 5 : Suivi (continu)

**Déclencheur** : Un trade a été marqué comme "exécuté" par l'utilisateur.

### Suivi en temps réel — XAU/USD

Le bot surveille le prix de l'or et notifie l'utilisateur aux jalons clés :

| Événement | Notification |
|-----------|--------------|
| Prix entre dans la zone d'entrée | "Setup XAUUSD actif — prix dans la zone OB" |
| SL touché | "❌ SL atteint sur XAUUSD — P&L virtuel : -100€ (-35 $)" |
| TP1 atteint | "✅ TP1 atteint (+6 $) — Déplace ton SL à BE" |
| TP2 atteint | "✅ TP2 atteint (+12 $) — Réduction de position" |
| BE atteint après TP1 | "🛡️ Trade sécurisé — SL à BE" |
| Invalidation technique | "⚠️ Setup XAUUSD invalidé — clôture sous OB" |
| DXY move contre le trade | "⚠️ DXY monte fort — Surveille ton trade long Or" |
| Fin de killzone sans atteinte | "⏰ Killzone terminée — Surveille le prochain fix" |
| London Fix imminent | "⏰ Fix London dans 5 min — Volatilité attendue" |

### Clôture du trade

Un trade est considéré comme fermé virtuellement quand :
- Le SL est touché
- TP2 est atteint (TP3 est trail, géré séparément)
- Le setup s'invalide technique
- L'utilisateur signale une fermeture manuelle

### Journal post-trade

```
[2026-05-20 15:45:00] TRADE CLOSED XAUUSD BUY
  Résultat: TP1 + TP2 atteints
  P&L virtuel: +78 € (+7.8 $ moyen)
  Durée: 1h13
  Setup: Bullish OB + FVG confluent
  Killzone: London Fix PM
  Macro Or: +2 (DXY ↓, Yields ↓)
  Exécuté par user: OUI
  Feedback user: [à remplir]
```

## 8.7 Phase 6 : Feedback Utilisateur (manuel)

**Déclencheur** : Un trade est clôturé virtuellement (WIN, LOSS, BE).

### Actions du bot

1. **Notification de clôture** : Le bot informe l'utilisateur du résultat virtuel
2. **Demande de feedback** : Après 2h, rappel discret demandant le résultat réel
3. **Commandes disponibles** :
   - `/feedback TRADE-xxx` — Ouvrir le formulaire
   - `/journal open` — Voir les trades en attente de feedback
   - `/note TRADE-xxx <texte>` — Ajouter une note

### Informations collectées

| Info | Obligatoire | Usage |
|------|-------------|-------|
| Trade exécuté ? | Oui | Différencier trades réels des manqués |
| Résultat réel | Oui | WIN / LOSS / BE / MANUEL |
| Prix de sortie | Non | Calculer le slippage vs le bot |
| Notes | Non | Contexte qualitatif pour le cerveau |

> **Pourquoi le feedback est critique** : Sans le feedback réel, le cerveau vectoriel ne peut pas apprendre. Le bot vit dans le virtuel, l'utilisateur vit dans le réel.

## 8.8 Phase 7 : Apprentissage Vectoriel (automatique)

**Déclencheur** : Feedback utilisateur soumis OU auto-clôture après 7 jours.

### Actions du bot

1. **Mise à jour du Journal** : Les champs `pnl_real`, `user_exit_reason`, `user_notes` sont enregistrés
2. **Vectorisation** : Le trade est encodé en vecteur et stocké dans ChromaDB
3. **Labelisation** : Le vecteur est taggué avec le résultat réel (WIN/LOSS)
4. **Consolidation** : Le cerveau recalcule les statistiques par cluster de setups

### Insight généré

Si un pattern émerge, le bot l'indique dans le prochain rapport :
```
🧠 CERVEAU — Insight de la semaine :
"Tes 3 dernières pertes étaient toutes des setups sans FVG confluent
 au London Fix PM. Les setups OB+FVG+Fix PM ont un win rate de 80%.
 → Recommandation: Exiger FVG pour les trades au Fix PM."
```

## 8.9 Flux de rétroaction hebdomadaire

Chaque dimanche, le bot génère automatiquement un rapport :

```
📈 RAPPORT HEBDOMADAIRE XAU/USD — Semaine du 18 au 24 Mai 2026

Signaux générés : 4
Signaux exécutés par toi : 3
Win rate virtuel : 66.7% (2/3)
Profit factor : 2.4
P&L virtuel : +156 € (+1.56%)

Meilleur setup : XAUUSD BUY A+ (+18 $)
Pire setup : XAUUSD SELL B (-8 $)

Analyse :
- London Fix PM : 100% win rate (2 trades) ⭐
- COMEX Open : 50% win rate (1 trade)
- OB + FVG + niveau psy : 100% win rate
- OB seul : 0% win rate

DXY correlation :
- Trades gagnants : DXY baissait en moyenne -0.2%
- Trade perdant : DXY montait +0.35% après l'entrée

Recommandation :
→ Focus renforcé sur London Fix PM et COMEX
→ Exiger FVG + niveau psy pour les grades B
→ Surveiller DXY en temps réel pendant le trade
```

---

*Documents liés : [07 — Gestion du Risque](07-gestion-risque.md) | [09 — Interface Utilisateur](09-interface-utilisateur.md)*
