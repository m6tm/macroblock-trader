# 09 — Interface Utilisateur

## 9.1 Vue d'ensemble

L'interface utilisateur a pour vocation d'être **claire, immédiate et actionnable**. Le trader ne doit pas avoir à chercher l'information. Elle doit lui parvenir au bon moment, dans le bon format.

Le système propose trois canaux d'interface :
1. **Dashboard Web** — Vue globale, historique, analyse.
2. **Alertes Push (Telegram)** — Notifications temps réel sur mobile.
3. **Journal de Trading** — Traçabilité complète, exportable.

## 9.2 Dashboard Web

### 9.2.1 Structure de la page principale

```
┌──────────────────────────────────────────────────────────────────────────┐
│  MACROBLOCK TRADER                              Dernière maj: 14:32:05  │
│  [🟢 En ligne]  [📊 2 actifs]  [🔔 3 signaux aujourd'hui]               │
├──────────────────┬───────────────────────────────────────────────────────┤
│                  │                                                       │
│  📈 MACRO BOARD  │   🎯 SIGNAUX DU JOUR                                  │
│  ──────────────  │   ┌────┬──────┬────────┬───────┬─────────┬────────┐  │
│                  │   │ #  │ Dir  │ Paire  │ Grade │ Résultat│ Statut │  │
│  Or Macro: +2 🟢 │   │ 1  │ BUY  │ XAUUSD │ A+    │ +18 $   │ ✅ Gagné│  │
│  DXY: -1 🟠      │   │ 2  │ SELL │ XAUUSD │ B     │ -8 $    │ ❌ Perdu│  │
│  JPY: -2 🔴      │   │ 3  │ BUY  │ XAUUSD │ A+    │ —       │ 🟡 Ouvert│  │
│  GBP: 0 ⚪       │   └────┴──────┴────────┴───────┴─────────┴────────┘  │
│  CHF: -1 🟠      │                                                       │
│  AUD: +1 🟢      │   📊 PERFORMANCE VIRTUELLE                              │
│  NZD: 0 ⚪       │   ┌─────────────────────────────────────────────────┐ │
│  CAD: 0 ⚪       │   │ Win rate: 62%          │ R:R moyen: 1:2.1       │ │
│  XAU: +1 🟢      │   │ Profit ce mois: +3.2%  │ Drawdown max: 4.1%     │ │
│                  │   │ Trades ce mois: 18     │ Actifs: 7/10           │ │
│  🌍 CALENDRIER   │   └─────────────────────────────────────────────────┘ │
│  ──────────────  │                                                       │
│  14:30 US PPI    │   🗺️ CARTE DES SETUPS (Actif: XAUUSD)                │
│  🔴 Haut Impact  │   ┌─────────────────────────────────────────────────┐ │
│  16:00 UK GDP    │   │ [Chart technique avec OB, FVG, SL, TP marqués]  │ │
│  🟠 Impact Moyen │   │                                                   │ │
│                  │   │  • Zone OB: [1.08450 - 1.08500]                   │ │
│  💭 SENTIMENT    │   │  • FVG: [1.08460 - 1.08490]                       │ │
│  ──────────────  │   │  • SL: 1.08320                                    │ │
│  EUR: 75% Short  │   │  • TP1: 1.08700  |  TP2: 1.08950                  │ │
│  → 🟢 Contrarian │   │  • Liquidité: EQH à 1.08900                       │ │
│  USD: 60% Long   │   └─────────────────────────────────────────────────┘ │
│  → 🟠 Neutre     │                                                       │
│                  │                                                       │
│  ⚙️ ACTIONS      │   📜 JOURNAL RAPIDE                                   │
│  [🔔 Test Alert] │   ┌─────────────────────────────────────────────────┐ │
│  [📊 Export CSV] │   │ 14:32 — XAUUSD BUY A+ — EN ATTENTE              │ │
│  [⚙️ Paramètres] │   │ 12:15 — XAUUSD SELL B — CLOSÉ -8 $              │ │
│  [🔄 Rescan]     │   │ 09:45 — XAUUSD BUY A+ — CLOSÉ +45 pips          │ │
│                  │   └─────────────────────────────────────────────────┘ │
└──────────────────┴───────────────────────────────────────────────────────┘
```

### 9.2.2 Pages du dashboard

| Page | URL | Contenu |
|------|-----|---------|
| **Accueil** | `/` | Vue d'ensemble, signaux du jour, performance rapide |
| **Signaux** | `/signals` | Liste complète des signaux (actifs + historique), filtres |
| **Signal Detail** | `/signals/<id>` | Chart du setup, justification complète, P&L |
| **Performance** | `/performance` | Graphiques de capital, win rate par mois/paire/setup |
| **Macro Board** | `/macro` | Scores macro détaillés, calendrier, yield curve |
| **Journal** | `/journal` | Table de tous les trades, export CSV |
| **Paramètres** | `/settings` | Capital, risque max, notifications, killzones |

### 9.2.3 Chart technique intégré

Le chart affiche :
- Les candles M15 (ou M5 au choix)
- Les Order Blocks détectés (rectangles colorés)
- Les Fair Value Gaps (zones hachurées)
- Les niveaux de structure (lignes pointillées)
- Les pools de liquidité (étoiles)
- Le plan de trade actif (entrée, SL, TP1, TP2)
- La killzone active (fond vert clair sur l'axe temporel)

## 9.3 Alertes Push (Telegram)

### 9.3.1 Format des messages

Tous les messages Telegram sont **concis, structurés et sans ambiguïté**.

#### Message de signal

```
🔔 SIGNAL — XAUUSD BUY (A+)

Score: 4.2/5
Macro Or: +2 🟢 | Tech: 5/5 | Timing: 2/2
Setup: Bullish OB M15 + FVG confluent
Killzone: London Fix PM ✅

📍 ENTRÉE: 2345.00 – 2346.50
🛑 SL: 2341.00 (-35 $)
🎯 TP1: 2352.00 (1:2.0) — 50%
🎯 TP2: 2358.00 (1:3.7) — 30%
🎯 TP3: Trail — 20%

💰 Size: 1.0% = 100€
⏱️ Valide jusqu'à 15:45 GMT (20 min)
⚠️ Invalidé si cloture M5 < 2340.50

[⚡ EXÉCUTER] [👀 REGARDER] [❌ IGNORER]
```

#### Message de mise à jour

```
📊 UPDATE — XAUUSD BUY (SIG-001)

✅ TP1 atteint: +6 $
💰 P&L partiel: +50€
🛡️ Déplace ton SL à BE (2345.75)

Position restante: 50% (TP2 + Trail)
```

#### Message de clôture

```
🏁 CLOSÉ — XAUUSD BUY (SIG-001)

Résultat: TP1 + TP2 atteints
P&L total: +78€ (+0.78%)
Durée: 1h13
Setup: OB + FVG confluent
Killzone: London Fix PM

Récap: +6 $ (TP1) + +12 $ (TP2)
```

#### Message d'invalidation

```
❌ INVALIDÉ — XAUUSD BUY (SIG-001)

Raison: Clôture M5 sous l'OB (2340.20)
Setup annulé. Pas de perte virtuelle.
Prochain scan dans 15 min.
```

### 9.3.2 Commandes Telegram utilisateur

| Commande | Action |
|----------|--------|
| `/status` | État actuel du bot, trades ouverts, prochaines news |
| `/performance` | Résumé des performances du jour/semaine/mois |
| `/journal` | Derniers 5 trades |
| `/pause` | Suspendre temporairement les alertes (maintenir le scan) |
| `/resume` | Reprendre les alertes |
| `/settings` | Afficher les paramètres actuels |

## 9.4 Journal de Trading

### 9.4.1 Structure du journal

Chaque trade est enregistré dans une base SQLite avec les champs suivants :

| Champ | Type | Description |
|-------|------|-------------|
| `signal_id` | TEXT | Identifiant unique (ex: SIG-20260520-001) |
| `timestamp_open` | DATETIME | Heure de génération du signal |
| `timestamp_close` | DATETIME | Heure de clôture virtuelle |
| `pair` | TEXT | Paire tradée |
| `direction` | TEXT | BUY ou SELL |
| `grade` | TEXT | A+, B, C |
| `score_total` | REAL | Score final (ex: 4.2) |
| `entry_price` | REAL | Prix d'entrée moyen |
| `sl_price` | REAL | Prix du SL |
| `tp1_price` | REAL | Prix du TP1 |
| `tp2_price` | REAL | Prix du TP2 |
| `tp3_price` | REAL | Prix du TP3 (ou NULL si trail) |
| `position_size` | REAL | Taille en lots |
| `risk_pct` | REAL | Pourcentage du capital risqué |
| `pnl_virtual` | REAL | P&L virtuel en devise |
| `pnl_pips` | REAL | P&L en pips |
| `outcome` | TEXT | WIN / LOSS / BE / EXPIRED |
| `user_executed` | BOOLEAN | L'utilisateur a-t-il exécuté ? |
| `user_pnl_real` | REAL | P&L réel rapporté par l'utilisateur (optionnel) |
| `setup_type` | TEXT | OB, OB+FVG, FVG, etc. |
| `killzone` | TEXT | London, NY, etc. |
| `macro_score` | INTEGER | Score macro au moment du trade |
| `notes` | TEXT | Notes libres |

### 9.4.2 Exports disponibles

| Format | Usage |
|--------|-------|
| **CSV** | Import Excel, analyse externe |
| **JSON** | Intégration avec d'autres outils |
| **PDF (rapport mensuel)** | Archive, présentation |

### 9.4.3 Capture d'écran automatique

Optionnellement, le bot peut capturer automatiquement le chart au moment du signal et le stocker dans le dossier `screenshots/<signal_id>.png`. Cela permet de revoir le contexte visuel plus tard.

## 9.5 Configuration des notifications

L'utilisateur peut configurer :

| Paramètre | Options | Défaut |
|-----------|---------|--------|
| **Canal principal** | Telegram / Dashboard uniquement / Les deux | Les deux |
| **Grade minimum** | A+ uniquement / B et A+ | B et A+ |
| **Killzones actives** | Toutes / London / NY / London+NY | London+NY |
| **Sound alerts** | Oui / Non | Oui |
| **Night mode** | Pas d'alerte 22h–08h GMT | Oui |
| **Récap quotidien** | Oui / Non | Oui (21h GMT) |
| **Récap hebdomadaire** | Oui / Non | Oui (dimanche 20h GMT) |

---

*Documents liés : [08 — Flux de Travail](08-flux-travail.md) | [12 — Métriques & Amélioration](12-metriques-amelioration.md)*
