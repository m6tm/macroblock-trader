# 07 — Gestion du Risque

## 7.1 Philosophie

> **"Un bon système de trading avec une mauvaise gestion du risque finit à zéro. Un mauvais système avec une excellente gestion du risque survit et prospère."**

Le module de gestion du risque a un droit de veto absolu sur tous les signaux générés par le moteur de fusion. Même un signal A+ peut être bloqué si les paramètres de risque ne sont pas respectés.

## 7.2 Sizing — Taille des positions

### Capital virtuel de référence

| Paramètre | Valeur par défaut | Modifiable |
|-----------|-------------------|------------|
| Capital virtuel initial | 10 000 € (ou devise choisie) | Oui |
| Risque maximal par trade | **1.0 %** | Oui, max 1.5 % |
| Risque minimal par trade | 0.5 % | Oui |

### Table de sizing par niveau de confiance — Spécifique Or

| Grade du signal | Risque du capital | Exemple (10 000 €) | Conditions |
|-----------------|-------------------|--------------------|------------|
| **A+** (≥ 4.0) | **1.0 %** | **100 €** | Setup parfait, macro aligné, killzone idéale |
| **B** (2.5 – 4.0) | **0.5 %** | **50 €** | Setup solide, contexte acceptable |
| **C** (< 2.5) | 0 % | 0 € | Pas de trade |

> **Pourquoi un sizing réduit ?** L'or est plus volatile que les paires FX majeures. Un move de 1 % en quelques minutes est courant. Le sizing est réduit pour compenser cette volatilité supérieure.

### Formule de calcul du lotage — Spécifique Or

```
Taille (lots) = Risque en € / (Distance SL en $ × Valeur du $ par lot)
```

**Exemple XAU/USD** :
- Risque = 100 €
- SL = 35 $ (0.35 % du prix à 2340 $)
- Valeur du $ XAU/USD (1 lot) = 1 $ = 1 € (approximatif)
- Taille = 100 / 35 = **0.28 lots**

> Sur l'or, on raisonne en **dollars** plutôt qu'en pips. Un "pip" sur l'or = 0.01 $, mais il est plus intuitif de raisonner directement en dollars.

### Limites de sizing — Spécifique Or

| Limite | Valeur | Action si dépassée |
|--------|--------|--------------------|
| **Max 1 trade ouvert simultanément** | **1** | **Nouveaux signaux rejetés** |
| Max perte journalière | **2 %** | Lock trading jusqu'au lendemain |
| Max perte hebdomadaire | **4 %** | Réduction du sizing de 50 % la semaine suivante |

> **Pourquoi un seul trade ?** Le bot est spécialisé sur un seul actif (XAU/USD). Il n'y a aucune raison d'être exposé plusieurs fois au même risque. Qualité > quantité.

## 7.3 Stop Loss (SL)

### Positionnement du SL — Spécifique Or

| Type de setup | Règle de positionnement | Distance typique |
|---------------|------------------------|------------------|
| **Long sur OB** | Sous le wick le plus bas de l'OB + buffer ATR(14) × 0.5 | 25–40 $ |
| **Short sur OB** | Au-dessus du wick le plus haut de l'OB + buffer ATR(14) × 0.5 | 25–40 $ |
| **Long sur FVG** | Sous le low du FVG + buffer | 20–35 $ |
| **Short sur FVG** | Au-dessus du high du FVG + buffer | 20–35 $ |

> **Note** : Sur l'or, le SL ne doit jamais être inférieur à 15 $ (sauf setup M5 exceptionnel avec contexte H4 fort). L'or a besoin de "respirer".

### Règles de validation du SL — Spécifique Or

| Règle | Valeur | Action si non respectée |
|-------|--------|------------------------|
| Distance SL max | **1.0 % du prix** | Setup rejeté (SL trop loin = mauvais R:R) |
| Distance SL min | **15 $** | Setup rejeté (trop serré, risque de stop hunting sur l'or) |
| SL technique > SL money management | Privilégier le plus proche du prix | Toujours protéger le capital avant l'idéal technique |

## 7.4 Take Profit (TP) — Stratégie de sortie

Le système utilise une stratégie de sortie échelonnée (partial profits) pour maximiser les gains tout en sécurisant des profits rapides.

| Niveau | Allocation | Cible | R:R | Action |
|--------|------------|-------|-----|--------|
| **TP1** | 50 % de la position | Premier FVG opposé / Premier pool de liquidité | 1:1.5 minimum | Fermeture partielle, déplacer SL à BE |
| **TP2** | 30 % de la position | Structure opposée (swing high/low) / OB inverse | 1:2 à 1:3 | Fermeture partielle |
| **TP3** | 20 % de la position | Trail | Variable | Laisser courir avec trailing stop |

### Règles de TP

- **R:R minimum acceptable** : **1:2.0** (un trade avec un R:R inférieur est rejeté — l'or permet des moves suffisamment grands pour justifier ce minimum)
- **TP1 doit être atteignable** : Avant un obstacle majeur (support/résistance hebdomadaire, OB H4)
- **Si le prix atteint 50 % du chemin vers TP1 sans rejet** : Réduire l'allocation à 0.5 % (setup moins propre)

## 7.5 Règles de blocage (Risk Locks)

### Blocage par corrélation

> **Non applicable** : Le bot ne trade que XAU/USD. Il n'y a pas de corrélation inter-paires à gérer.
>
> En revanche, le bot surveille la **corrélation inverse DXY / Or** en temps réel. Si le DXY fait un move brusque de +0.3 % en 5 minutes pendant un trade long ouvert, une alerte de précaution est envoyée.

### Corrélation DXY / Or

```
Si un trade long XAU/USD est ouvert :
    → Surveiller DXY en temps réel
    → Si DXY monte de > 0.2 % en 5 minutes :
        → Envoyer alerte de précaution
        → Suggérer réduction de position ou SL serré

Si un trade short XAU/USD est ouvert :
    → Surveiller DXY en temps réel
    → Si DXY baisse de > 0.2 % en 5 minutes :
        → Envoyer alerte de précaution
        → Suggérer réduction de position ou SL serré
```

### Blocage par news — Spécifique Or

| Type de news | Fenêtre de blocage | Raison pour l'Or |
|--------------|-------------------|------------------|
| FOMC (taux + conférence) | 30 min avant → 1h après | Ultra-sensible aux taux |
| NFP | 15 min avant → 30 min après | Impact dollar + yields |
| CPI / PPI US | 15 min avant → 30 min après | Inflation = driver clé |
| PCE (Fed preferred) | 15 min avant → 30 min après | Métrique inflation préférée de la Fed |
| **London Fix AM** | **09:45 – 10:15** | Fix LBMA, volume énorme |
| **London Fix PM** | **14:45 – 15:15** | Deuxième fix |
| COMEX Open | 13:15 – 13:30 | Ouverture futures, volatilité |
| Discours majeurs (Powell) | Pendant + 30 min après | Forward guidance |
| Choc géopolitique | Jusqu'à réévaluation manuelle | L'or peut gapper 20–50 $ |
| DXY move > 0.3 % en 5 min | 15 minutes | Corrélation inverse immédiate |

### Blocage par drawdown — Spécifique Or

| Seuil | Action |
|-------|--------|
| **-2 %** sur la journée | Lock trading jusqu'au lendemain |
| **-4 %** sur la semaine | Réduction du sizing de 50 % la semaine suivante |
| **-8 %** sur le mois | Révision complète des paramètres, pause obligatoire de 3 jours |

> **Pourquoi des seuils plus bas ?** La volatilité de l'or amplifie les drawdowns. Une protection plus stricte est nécessaire.

## 7.6 Récapitulatif des règles de risque

```
AVANT CHAQUE TRADE, LE BOT VÉRIFIE :
□ Le score est ≥ 2.5 (B ou A+)
□ Le macro n'est pas verrouillé par une news
□ Le risque est entre 0.5 % et 1.5 %
□ Le SL est entre 5 pips et 1.5 % du prix
□ Le R:R minimum est ≥ 1:1.5
□ Moins de 2 trades ouverts
□ Aucun trade sur la même devise
□ Corrélation < 80 % avec les trades ouverts
□ Killzone active OU setup exceptionnel justifié
□ Drawdown journalier < 3 %
```

Si une seule case n'est pas cochée → **PAS DE TRADE**.

---

*Documents liés : [06 — Moteur de Fusion & Scoring](06-moteur-fusion-scoring.md) | [08 — Flux de Travail](08-flux-travail.md)*
