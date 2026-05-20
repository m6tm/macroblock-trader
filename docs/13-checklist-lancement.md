# 13 — Checklist de Lancement

> Ce document liste tous les points à valider avant de démarrer le développement. Chaque élément doit être discuté et confirmé par l'utilisateur.

---

## 13.1 Stratégie & Méthodologie

- [ ] **Valider la méthodologie SMC** : Es-tu formé aux concepts d'Order Blocks, FVG, BOS/CHoCH ? Le bot applique cette méthode à la lettre.
- [ ] **Valider les timeframes** : M5 pour l'entrée, M15 pour le setup, H1 pour le filtre. Est-ce conforme à ta pratique actuelle ?
- [ ] **Valider l'approche paper trading** : Confirmes-tu que le bot ne prend pas de positions réelles et que tu exécutes manuellement ?
- [ ] **Définir ton style** : Scalping (positions < 1h) ou Swing court (1–4h) ? Le système est conçu pour du swing court.

---

## 13.2 Univers de Trading

- [ ] **Valider la spécialisation XAU/USD** : Confirmes-tu que le bot ne tradera que l'or ?
- [ ] **Broker de données et exécution** : Quel broker utilises-tu pour trader l'or ? (Spread, exécution, levier disponible sur XAU/USD)
- [ ] **Compte de trading** : Quel est le capital réel sur ton compte ? (Le capital virtuel du bot sera calibré en proportion.)

---

## 13.3 Gestion du Risque

- [ ] **Capital virtuel initial** : 10 000 € par défaut. Veux-tu un autre montant ?
- [ ] **Risque maximal par trade** : 1.0 % pour les A+, 0.5 % pour les B (adapté à la volatilité de l'or). Tes limites personnelles sont-elles différentes ?
- [ ] **R:R minimum acceptable** : 1:2.0 par défaut sur l'or. Acceptes-tu des trades avec un R:R plus faible ?
- [ ] **Nombre max de trades simultanés** : 2 par défaut. Suffisant pour toi ?
- [ ] **Drawdown journalier max** : 3 % = lock jusqu'au lendemain. Cela te convient-il ?
- [ ] **Gestion des weekends** : Le bot ne trade pas le weekend (Forex fermé). Veux-tu qu'il analyse le gap de dimanche soir ?

---

## 13.4 Notifications & Interface

- [ ] **Canal principal** : Telegram est suggéré pour les alertes mobiles. Utilises-tu Telegram ? Préfères-tu Discord, email, ou autre ?
- [ ] **Grade minimum pour alerte** : B et A+ par défaut. Veux-tu recevoir uniquement les A+ pour commencer ?
- [ ] **Killzones préférées** : NY Open + London Open par défaut. trades-tu l'Asia ou le London Close ?
- [ ] **Mode nuit** : Pas d'alerte 22h–08h GMT par défaut. Veux-tu désactiver cette règle ?
- [ ] **Dashboard web** : Veux-tu un dashboard accessible depuis ton navigateur ? Sur quel device principalement ?
- [ ] **Récapitulatifs** : Récap quotidien à 21h GMT et hebdo le dimanche. Horaires à ajuster ?

---

## 13.5 Macro & Calendrier

- [ ] **Sources macro Or** : Le bot utilise DXY, yields réels, inflation, géopolitique, VIX. Y a-t-il d'autres indicateurs que tu suis pour l'or ? (Ex: COT Gold, ETF flows, production minière...)
- [ ] **Fenêtres de news** : 30 min avant/après FOMC, 15 min avant/après NFP/CPI. Trop prudent ? Pas assez ?
- [ ] **Devises de focus macro** : Le macro est calculé par devise (EUR, USD, GBP, JPY...). Y a-t-il des devises que tu considères comme toujours neutres ?

---

## 13.6 Technique & SMC

- [ ] **Détection des OB** : Le bot détecte les OB automatiquement sur l'or. Acceptes-tu qu'il te propose des OB que tu n'aurais peut-être pas choisis manuellement ?
- [ ] **FVG confluent + niveau psy** : Le bot valorise fortement les setups OB+FVG+niveau psychologique. Es-tu d'accord pour exiger FVG pour les setups de grade B ?
- [ ] **Invalidation** : Le bot annule un signal si le prix cloture sous l'OB (long). Cette règle te convient-elle ?
- [ ] **Screenshots** : Veux-tu que le bot capture le chart à chaque signal pour archive visuelle ?

---

## 13.7 Développement & Technique

- [ ] **Stack technologique** : Python + SQLite + Streamlit + Telegram. As-tu une préférence ou une aversion pour l'une de ces technologies ?
- [ ] **Hébergement** : Local (ton PC) au départ. Es-tu prêt à laisser ton PC allumé pendant les heures de marché ?
- [ ] **VPS futur** : Envisages-tu de passer sur un VPS pour un uptime 24/5 ?
- [ ] **Git / Versioning** : Le code sera versionné avec Git. Veux-tu un dépôt privé (GitHub/GitLab) pour sauvegarde et suivi ?

---

## 13.8 Performance & Attentes

- [ ] **Objectif de win rate** : Le système vise > 55 %. Quel est ton objectif personnel ?
- [ ] **Objectif de rendement** : Le système vise 5–10 % par mois (avec un risque contenu). Est-ce réaliste selon toi ?
- [ ] **Période de test** : Combien de temps veux-tu tester en paper trading avant de trader réellement derrière les signaux ? (Suggestion : 1–2 mois.)
- [ ] **Critère de succès** : À quel moment considéreras-tu que le bot est "prêt" ? (Ex: 1 mois de WR > 50 % et profit factor > 1.3.)

---

## 13.9 Questions ouvertes

Réponds aux questions suivantes pour affiner la conception :

1. **Quel est ton plus gros point faible en trading actuellement ?** (Ex: overtrading, peur de manquer, tenir les losers trop longtemps...)
2. **Quel est ton point fort ?** (Ex: patience, lecture de la structure, timing d'entrée...)
3. **Y a-t-il une fonctionnalité "rêvée" que tu n'as jamais trouvée dans les outils existants ?**
4. **Préfères-tu recevoir peu d'alertes de très haute qualité, ou plus d'alertes avec un filtre manuel ?**
5. **Comment évalues-tu actuellement tes performances ?** (Excel, tête, application...)

---

## 13.10 Validation finale

Avant de passer à la phase de développement, les éléments suivants doivent être verrouillés :

- [ ] Tous les points de la section 13.1 validés
- [ ] Liste des paires finale confirmée
- [ ] Paramètres de risque confirmés
- [ ] Canal de notification choisi et configuré
- [ ] Stack technique validé
- [ ] Questions ouvertes 1–5 répondues
- [ ] **GO / NO-GO** pour le développement

---

> **Prochaine étape** : Une fois cette checklist complétée et validée, nous passerons à la spécification technique détaillée (diagrammes de classes, schéma de base de données, API endpoints), puis au développement par itérations.

*Document interactif — À compléter avec l'utilisateur.*
