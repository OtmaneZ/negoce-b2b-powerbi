# Dictionnaire des mesures

Généré par `scripts/generate_docs.py` depuis le modèle TMDL (`NegoceB2B.SemanticModel/definition/tables/Mesures.tmdl`) ; ne pas modifier à la main.

73 mesures, toutes dans la table Mesures : 67 visibles, 6 masquées. CA : chiffre d'affaires hors taxes. N : période sélectionnée ; N-1 : même période un an plus tôt.

| Dossier | Mesures |
|---|---|
| 1. Chiffre d'affaires | 9 |
| 2. Marge | 11 |
| 3. Comparaison N-1 | 24 |
| 4. Budget | 5 |
| 5. Pont de marge | 10 |
| 6. Textes | 14 |

## 1. Chiffre d'affaires

### CA brut

Chiffre d'affaires hors taxes au prix catalogue, avant remises (CA : chiffre d'affaires).

Format : `#,0 €`.

```dax
SUM('Ventes'[Montant brut])
```

### Remises

Montant des remises accordées sur le prix catalogue.

Format : `#,0 €`.

```dax
SUM('Ventes'[Montant remise])
```

### CA net

Chiffre d'affaires hors taxes facturé, après remises : CA brut - remises.

Format : `#,0 €`.

```dax
SUM('Ventes'[Montant net])
```

### Taux de remise (%)

Part du CA brut cédée en remises : remises / CA brut.

Format : `0.0 %`.

```dax
DIVIDE([Remises], [CA brut])
```

### Quantité

Unités vendues. Additionner des unités de familles différentes n'a de sens que produit par produit ; sert au pont de marge.

Format : `#,0`.

```dax
SUM('Ventes'[Quantité])
```

### # Commandes

Nombre de commandes distinctes sur la période.

Format : `#,0`.

```dax
DISTINCTCOUNT('Ventes'[Numéro commande])
```

### # Clients actifs

Clients ayant passé au moins une commande sur la période.

Format : `#,0`.

```dax
DISTINCTCOUNT('Ventes'[Clé client])
```

### Commandes par client

Fréquence d'achat moyenne : commandes / clients actifs.

Format : `#,0.0`.

```dax
DIVIDE([# Commandes], [# Clients actifs])
```

### Panier moyen

CA net moyen par commande. CA net = clients actifs × commandes par client × panier moyen.

Format : `#,0 €`.

```dax
DIVIDE([CA net], [# Commandes])
```

## 2. Marge

### Coût d'achat

Coût d'achat des marchandises vendues.

Format : `#,0 €`.

```dax
SUM('Ventes'[Coût d'achat])
```

### Marge commerciale

CA net - coût d'achat des marchandises vendues.

Format : `#,0 €`.

```dax
[CA net] - [Coût d'achat]
```

### Marge commerciale (% CA)

Marge commerciale rapportée au CA net (taux de marque).

Format : `0.0 %`.

```dax
DIVIDE([Marge commerciale], [CA net])
```

### Transport

Coûts de livraison supportés par Arvenor.

Format : `#,0 €`.

```dax
SUM('Ventes'[Coût transport])
```

### Transport (% CA)

Poids du transport dans le CA net.

Format : `0.0 %`.

```dax
DIVIDE([Transport], [CA net])
```

### Marge contributive

Marge commerciale - transport : ce que la vente rapporte réellement.

Format : `#,0 €`.

```dax
[Marge commerciale] - [Transport]
```

### Marge contributive (% CA)

Marge contributive rapportée au CA net.

Format : `0.0 %`.

```dax
DIVIDE([Marge contributive], [CA net])
```

### # Clients à marge négative

Clients dont la marge contributive est négative sur la période : ils coûtent plus qu'ils ne rapportent.

Format : `#,0`.

```dax
COUNTROWS(FILTER(VALUES('Client'[Clé client]), [Marge contributive] < 0))
```

### # Produits sous le coût

Références dont la marge commerciale est négative sur la période : vendues sous leur coût d'achat.

Format : `#,0`.

```dax
COUNTROWS(FILTER(VALUES('Produit'[Clé produit]), [Marge commerciale] < 0))
```

### Rang client en recul de marge

Rang du client parmi les clients actifs sur la période et sur N-1, du plus fort recul de marge contributive au plus faible (1 = plus fort recul). Vide pour un client sans vente sur l'une des deux périodes. Sert à filtrer le tableau des clients en recul.

Format : `0` ; masquée.

```dax
VAR _ecart = [Marge contributive écart N-1]
VAR _classement =
    CALCULATETABLE(
        FILTER(
            ADDCOLUMNS(
                VALUES('Client'[Clé client]),
                "@actif", NOT ISBLANK([CA net]),
                "@ecart", [Marge contributive écart N-1]
            ),
            [@actif] && NOT ISBLANK([@ecart])
        ),
        REMOVEFILTERS('Client')
    )
RETURN
    IF(
        HASONEVALUE('Client'[Clé client]) && NOT ISBLANK([CA net]) && NOT ISBLANK(_ecart),
        COUNTROWS(FILTER(_classement, [@ecart] < _ecart)) + 1
    )
```

### Rang produit sous le coût

Rang du produit parmi les produits vendus sous leur coût d'achat sur la période, de la plus forte perte à la plus faible (1 = plus forte perte). Vide pour un produit à marge positive ou nulle. Sert à filtrer le tableau des produits.

Format : `0` ; masquée.

```dax
VAR _marge = [Marge commerciale]
VAR _classement =
    CALCULATETABLE(
        ADDCOLUMNS(VALUES('Produit'[Clé produit]), "@marge", [Marge commerciale]),
        REMOVEFILTERS('Produit')
    )
RETURN
    IF(
        HASONEVALUE('Produit'[Clé produit]) && _marge < 0,
        COUNTROWS(FILTER(_classement, [@marge] < _marge)) + 1
    )
```

## 3. Comparaison N-1

### CA net N-1

CA net de la même période un an plus tôt. Vide en 2024, faute d'exercice 2023.

Format : `#,0 €`.

```dax
CALCULATE([CA net], SAMEPERIODLASTYEAR('Date'[Date]))
```

### CA net écart N-1

CA net - CA net N-1 ; vide sans exercice précédent.

Format : `+#,0 €;-#,0 €;0 €`.

```dax
VAR _n1 = [CA net N-1]
RETURN IF(NOT ISBLANK(_n1), [CA net] - _n1)
```

### CA net évol. N-1 (%)

Évolution du CA net par rapport à N-1.

Format : `+0.0 %;-0.0 %;0.0 %`.

```dax
VAR _n1 = [CA net N-1]
RETURN DIVIDE([CA net] - _n1, _n1)
```

### CA net écart N-1 par statut

Écart de CA net avec N-1 réparti selon le statut du client : clients présents sur les deux périodes (écart de leur CA), nouveaux clients (leur CA N), clients perdus (moins leur CA N-1). Les trois parts s'additionnent en CA net écart N-1, valeur renvoyée sans statut sélectionné.

Format : `+#,0 €;-#,0 €;0 €`.

```dax
VAR _statut = SELECTEDVALUE('Statut client'[Ordre])
VAR _clients =
    ADDCOLUMNS(VALUES('Client'[Clé client]), "@n", [CA net], "@n1", [CA net N-1])
VAR _existants =
    SUMX(FILTER(_clients, NOT ISBLANK([@n]) && NOT ISBLANK([@n1])), [@n] - [@n1])
VAR _nouveaux = SUMX(FILTER(_clients, NOT ISBLANK([@n]) && ISBLANK([@n1])), [@n])
VAR _perdus = SUMX(FILTER(_clients, ISBLANK([@n]) && NOT ISBLANK([@n1])), -[@n1])
RETURN
    IF(
        NOT ISBLANK([CA net N-1]),
        SWITCH(_statut, 1, _existants, 2, _nouveaux, 3, _perdus, [CA net écart N-1])
    )
```

### # Nouveaux clients

Clients actifs sur la période qui n'avaient rien acheté sur la même période un an plus tôt ; vide sans exercice précédent.

Format : `#,0`.

```dax
IF(
    NOT ISBLANK([CA net N-1]),
    COUNTROWS(FILTER(VALUES('Client'[Clé client]), NOT ISBLANK([CA net]) && ISBLANK([CA net N-1])))
)
```

### # Clients perdus

Clients actifs un an plus tôt qui n'ont rien acheté sur la période ; vide sans exercice précédent.

Format : `#,0`.

```dax
IF(
    NOT ISBLANK([CA net N-1]),
    COUNTROWS(FILTER(VALUES('Client'[Clé client]), ISBLANK([CA net]) && NOT ISBLANK([CA net N-1])))
)
```

### Marge commerciale N-1

Marge commerciale de la même période un an plus tôt.

Format : `#,0 €`.

```dax
CALCULATE([Marge commerciale], SAMEPERIODLASTYEAR('Date'[Date]))
```

### Marge commerciale écart N-1

Marge commerciale - marge commerciale N-1 ; vide sans exercice précédent.

Format : `+#,0 €;-#,0 €;0 €`.

```dax
VAR _n1 = [Marge commerciale N-1]
RETURN IF(NOT ISBLANK(_n1), [Marge commerciale] - _n1)
```

### Marge commerciale évol. N-1 (%)

Évolution de la marge commerciale par rapport à N-1.

Format : `+0.0 %;-0.0 %;0.0 %`.

```dax
VAR _n1 = [Marge commerciale N-1]
RETURN DIVIDE([Marge commerciale] - _n1, _n1)
```

### Marge commerciale N-1 (% CA)

Marge commerciale (% CA) de la même période un an plus tôt.

Format : `0.0 %`.

```dax
CALCULATE([Marge commerciale (% CA)], SAMEPERIODLASTYEAR('Date'[Date]))
```

### Marge commerciale écart N-1 (pts)

Écart de taux de marge commerciale avec N-1, en points de pourcentage, arrondi au dixième : un écart minime s'affiche 0,0 et non -0,0.

Format : `+0.0 \p\t\s;-0.0 \p\t\s;0.0 \p\t\s`.

```dax
VAR _tauxN = [Marge commerciale (% CA)]
VAR _tauxN1 = [Marge commerciale N-1 (% CA)]
RETURN IF(NOT ISBLANK(_tauxN) && NOT ISBLANK(_tauxN1), ROUND((_tauxN - _tauxN1) * 100, 1))
```

### Taux de remise N-1 (%)

Taux de remise de la même période un an plus tôt.

Format : `0.0 %`.

```dax
CALCULATE([Taux de remise (%)], SAMEPERIODLASTYEAR('Date'[Date]))
```

### Taux de remise écart N-1 (pts)

Écart de taux de remise avec N-1, en points de pourcentage, arrondi au dixième. Une hausse est défavorable.

Format : `+0.0 \p\t\s;-0.0 \p\t\s;0.0 \p\t\s`.

```dax
VAR _tauxN = [Taux de remise (%)]
VAR _tauxN1 = [Taux de remise N-1 (%)]
RETURN IF(NOT ISBLANK(_tauxN) && NOT ISBLANK(_tauxN1), ROUND((_tauxN - _tauxN1) * 100, 1))
```

### Transport N-1 (% CA)

Poids du transport dans le CA net, un an plus tôt.

Format : `0.0 %`.

```dax
CALCULATE([Transport (% CA)], SAMEPERIODLASTYEAR('Date'[Date]))
```

### Transport écart N-1 (pts)

Écart de poids du transport avec N-1, en points de pourcentage, arrondi au dixième. Une hausse est défavorable.

Format : `+0.0 \p\t\s;-0.0 \p\t\s;0.0 \p\t\s`.

```dax
VAR _tauxN = [Transport (% CA)]
VAR _tauxN1 = [Transport N-1 (% CA)]
RETURN IF(NOT ISBLANK(_tauxN) && NOT ISBLANK(_tauxN1), ROUND((_tauxN - _tauxN1) * 100, 1))
```

### Marge contributive N-1

Marge contributive de la même période un an plus tôt.

Format : `#,0 €`.

```dax
CALCULATE([Marge contributive], SAMEPERIODLASTYEAR('Date'[Date]))
```

### Marge contributive écart N-1

Marge contributive - marge contributive N-1 ; vide sans exercice précédent.

Format : `+#,0 €;-#,0 €;0 €`.

```dax
VAR _n1 = [Marge contributive N-1]
RETURN IF(NOT ISBLANK(_n1), [Marge contributive] - _n1)
```

### Marge contributive évol. N-1 (%)

Évolution de la marge contributive par rapport à N-1.

Format : `+0.0 %;-0.0 %;0.0 %`.

```dax
VAR _n1 = [Marge contributive N-1]
RETURN DIVIDE([Marge contributive] - _n1, _n1)
```

### # Clients actifs N-1

Clients actifs de la même période un an plus tôt.

Format : `#,0`.

```dax
CALCULATE([# Clients actifs], SAMEPERIODLASTYEAR('Date'[Date]))
```

### # Clients actifs évol. N-1 (%)

Évolution du nombre de clients actifs par rapport à N-1.

Format : `+0.0 %;-0.0 %;0.0 %`.

```dax
VAR _n1 = [# Clients actifs N-1]
RETURN DIVIDE([# Clients actifs] - _n1, _n1)
```

### Commandes par client N-1

Commandes par client de la même période un an plus tôt.

Format : `#,0.0`.

```dax
CALCULATE([Commandes par client], SAMEPERIODLASTYEAR('Date'[Date]))
```

### Commandes par client évol. N-1 (%)

Évolution de la fréquence d'achat par rapport à N-1.

Format : `+0.0 %;-0.0 %;0.0 %`.

```dax
VAR _n1 = [Commandes par client N-1]
RETURN DIVIDE([Commandes par client] - _n1, _n1)
```

### Panier moyen N-1

Panier moyen de la même période un an plus tôt.

Format : `#,0 €`.

```dax
CALCULATE([Panier moyen], SAMEPERIODLASTYEAR('Date'[Date]))
```

### Panier moyen évol. N-1 (%)

Évolution du panier moyen par rapport à N-1.

Format : `+0.0 %;-0.0 %;0.0 %`.

```dax
VAR _n1 = [Panier moyen N-1]
RETURN DIVIDE([Panier moyen] - _n1, _n1)
```

## 4. Budget

### CA net budget

Budget de CA net. Défini par mois, famille et région seulement : vide dès qu'un filtre porte sur Client, Produit ou Commercial.

Format : `#,0 €`.

```dax
IF(
    ISCROSSFILTERED('Client') || ISCROSSFILTERED('Produit') || ISCROSSFILTERED('Commercial'),
    BLANK(),
    SUM('Budget'[Budget CA net])
)
```

### CA net écart budget

CA net - budget de CA net ; vide si le budget est vide.

Format : `+#,0 €;-#,0 €;0 €`.

```dax
VAR _budget = [CA net budget]
RETURN IF(NOT ISBLANK(_budget), [CA net] - _budget)
```

### CA net écart budget (%)

Écart de CA net rapporté au budget.

Format : `+0.0 %;-0.0 %;0.0 %`.

```dax
VAR _budget = [CA net budget]
RETURN DIVIDE([CA net] - _budget, _budget)
```

### Marge commerciale budget

Budget de marge commerciale, avec la même garde que le budget de CA net.

Format : `#,0 €`.

```dax
IF(
    ISCROSSFILTERED('Client') || ISCROSSFILTERED('Produit') || ISCROSSFILTERED('Commercial'),
    BLANK(),
    SUM('Budget'[Budget marge commerciale])
)
```

### Marge commerciale écart budget (%)

Écart de marge commerciale rapporté au budget de marge.

Format : `+0.0 %;-0.0 %;0.0 %`.

```dax
VAR _budget = [Marge commerciale budget]
RETURN DIVIDE([Marge commerciale] - _budget, _budget)
```

## 5. Pont de marge

### CA net N au prix N-1

CA net de N valorisé aux prix nets unitaires de N-1, produit par produit : mesure du volume à prix constants. Une référence sans vente en N-1 garde son prix de N.

Format : `#,0 €` ; masquée.

```dax
SUMX(
    VALUES('Produit'[Clé produit]),
    VAR _q = [Quantité]
    VAR _qN1 = CALCULATE([Quantité], SAMEPERIODLASTYEAR('Date'[Date]))
    VAR _prixNetN1 = IF(_qN1 > 0, DIVIDE([CA net N-1], _qN1), DIVIDE([CA net], _q))
    RETURN _q * _prixNetN1
)
```

### Effet volume

Effet volume du pont de marge : marge N-1 × (CA net N au prix N-1 / CA net N-1 - 1). Volume mesuré à prix constants.

Format : `+#,0 €;-#,0 €;0 €`.

```dax
VAR _margeN1 = [Marge commerciale N-1]
VAR _caN1 = [CA net N-1]
RETURN
    IF(
        HASONEVALUE('Date'[Année]) && NOT ISBLANK(_caN1),
        DIVIDE(_margeN1 * [CA net N au prix N-1], _caN1) - _margeN1
    )
```

### Effet mix

Effet mix du pont de marge : Σ quantité N × marge unitaire N-1 - marge N-1 × (CA net N au prix N-1 / CA net N-1). Positif quand les ventes se déplacent vers des produits plus rentables.

Format : `+#,0 €;-#,0 €;0 €`.

```dax
VAR _margeN1 = [Marge commerciale N-1]
VAR _caN1 = [CA net N-1]
VAR _margeAuxMargesUnitairesN1 =
    SUMX(
        VALUES('Produit'[Clé produit]),
        VAR _q = [Quantité]
        VAR _qN1 = CALCULATE([Quantité], SAMEPERIODLASTYEAR('Date'[Date]))
        VAR _margeUnitaireN1 =
            IF(_qN1 > 0, DIVIDE([Marge commerciale N-1], _qN1), DIVIDE([Marge commerciale], _q))
        RETURN _q * _margeUnitaireN1
    )
RETURN
    IF(
        HASONEVALUE('Date'[Année]) && NOT ISBLANK(_caN1),
        _margeAuxMargesUnitairesN1 - DIVIDE(_margeN1 * [CA net N au prix N-1], _caN1)
    )
```

### Effet prix catalogue

Effet prix catalogue du pont de marge : Σ quantité N × (prix catalogue unitaire N - prix catalogue unitaire N-1).

Format : `+#,0 €;-#,0 €;0 €`.

```dax
IF(
    HASONEVALUE('Date'[Année]) && NOT ISBLANK([CA net N-1]),
    SUMX(
        VALUES('Produit'[Clé produit]),
        VAR _q = [Quantité]
        VAR _qN1 = CALCULATE([Quantité], SAMEPERIODLASTYEAR('Date'[Date]))
        VAR _prixCatalogueN1 =
            IF(
                _qN1 > 0,
                DIVIDE(CALCULATE([CA brut], SAMEPERIODLASTYEAR('Date'[Date])), _qN1),
                DIVIDE([CA brut], _q)
            )
        RETURN [CA brut] - _q * _prixCatalogueN1
    )
)
```

### Effet remises

Effet remises du pont de marge : -Σ quantité N × (remise unitaire N - remise unitaire N-1). Négatif quand les remises augmentent.

Format : `+#,0 €;-#,0 €;0 €`.

```dax
VAR _variation =
    SUMX(
        VALUES('Produit'[Clé produit]),
        VAR _q = [Quantité]
        VAR _qN1 = CALCULATE([Quantité], SAMEPERIODLASTYEAR('Date'[Date]))
        VAR _remiseUnitaireN1 =
            IF(
                _qN1 > 0,
                DIVIDE(CALCULATE([Remises], SAMEPERIODLASTYEAR('Date'[Date])), _qN1),
                DIVIDE([Remises], _q)
            )
        RETURN [Remises] - _q * _remiseUnitaireN1
    )
RETURN
    IF(
        HASONEVALUE('Date'[Année]) && NOT ISBLANK([CA net N-1]) && NOT ISBLANK(_variation),
        -_variation
    )
```

### Effet coût d'achat

Effet coût d'achat du pont de marge : -Σ quantité N × (coût unitaire N - coût unitaire N-1). Négatif quand les coûts d'achat augmentent.

Format : `+#,0 €;-#,0 €;0 €`.

```dax
VAR _variation =
    SUMX(
        VALUES('Produit'[Clé produit]),
        VAR _q = [Quantité]
        VAR _qN1 = CALCULATE([Quantité], SAMEPERIODLASTYEAR('Date'[Date]))
        VAR _coutUnitaireN1 =
            IF(
                _qN1 > 0,
                DIVIDE(CALCULATE([Coût d'achat], SAMEPERIODLASTYEAR('Date'[Date])), _qN1),
                DIVIDE([Coût d'achat], _q)
            )
        RETURN [Coût d'achat] - _q * _coutUnitaireN1
    )
RETURN
    IF(
        HASONEVALUE('Date'[Année]) && NOT ISBLANK([CA net N-1]) && NOT ISBLANK(_variation),
        -_variation
    )
```

### Pont de marge

Valeur de chaque étape du graphique en cascade : les cinq effets du pont ; au total, l'écart de marge commerciale avec N-1, que les effets expliquent exactement.

Format : `+#,0 €;-#,0 €;0 €`.

```dax
VAR _ordre = SELECTEDVALUE('Étape du pont'[Ordre])
RETURN
    SWITCH(
        _ordre,
        1, [Effet volume],
        2, [Effet mix],
        3, [Effet prix catalogue],
        4, [Effet remises],
        5, [Effet coût d'achat],
        IF(
            HASONEVALUE('Date'[Année]) && NOT ISBLANK([CA net N-1]),
            [Marge commerciale écart N-1]
        )
    )
```

### Pont de marge écart de bouclage

Contrôle : marge N-1 + somme des effets - marge N. Doit valoir 0.

Format : `+#,0.00 €;-#,0.00 €;0.00 €` ; masquée.

```dax
VAR _margeN1 = [Marge commerciale N-1]
RETURN
    IF(
        HASONEVALUE('Date'[Année]) && NOT ISBLANK(_margeN1),
        _margeN1 + [Effet volume] + [Effet mix] + [Effet prix catalogue] + [Effet remises]
            + [Effet coût d'achat] - [Marge commerciale]
    )
```

### Frein principal (libellé)

Nom de l'effet le plus défavorable du pont de marge ; vide sans exercice précédent.

Format : texte ; masquée.

```dax
VAR _effets =
    {
        ("volume", [Effet volume]),
        ("mix", [Effet mix]),
        ("prix catalogue", [Effet prix catalogue]),
        ("remises", [Effet remises]),
        ("coût d'achat", [Effet coût d'achat])
    }
VAR _valides = FILTER(_effets, NOT ISBLANK([Value2]))
RETURN MAXX(TOPN(1, _valides, [Value2], ASC), [Value1])
```

### Frein principal (montant)

Montant de l'effet le plus défavorable du pont de marge.

Format : `+#,0 €;-#,0 €;0 €` ; masquée.

```dax
VAR _effets =
    {
        ("volume", [Effet volume]),
        ("mix", [Effet mix]),
        ("prix catalogue", [Effet prix catalogue]),
        ("remises", [Effet remises]),
        ("coût d'achat", [Effet coût d'achat])
    }
RETURN MINX(FILTER(_effets, NOT ISBLANK([Value2])), [Value2])
```

## 6. Textes

### Titre Direction

Titre de la page Vue Direction : évolution du CA net sur un an et position par rapport au budget (omise si le budget est vide).

Format : texte.

```dax
VAR _annee = SELECTEDVALUE('Date'[Année])
VAR _ca = [CA net]
VAR _evolution = [CA net évol. N-1 (%)]
VAR _ecartBudget = [CA net écart budget (%)]
VAR _texteBudget =
    IF(
        NOT ISBLANK(_ecartBudget),
        IF(_ecartBudget >= 0, " et dépasse le budget de ", " et reste sous le budget de ")
            & FORMAT(ABS(_ecartBudget), "0.0 %", "fr-FR")
    )
RETURN
    SWITCH(
        TRUE(),
        ISBLANK(_annee), "Sélectionnez une année",
        ISBLANK(_ca), "Aucune vente sur la sélection",
        ISBLANK(_evolution),
            "En " & _annee & ", le CA net atteint "
                & FORMAT(_ca / 1000000, "#,0.0", "fr-FR") & " M€"
                & _texteBudget & " (pas d'exercice précédent)",
        "En " & _annee & ", le CA net "
            & IF(_evolution >= 0, "progresse", "recule")
            & " de " & FORMAT(ABS(_evolution), "0.0 %", "fr-FR")
            & " sur un an" & _texteBudget
    )
```

### Synthèse Direction

Synthèse de la Vue Direction : plus faibles contributions à l'évolution du CA net, par famille et par région, puis nombre de nouveaux clients et de clients perdus.

Format : texte.

```dax
VAR _annee = SELECTEDVALUE('Date'[Année])
VAR _familles =
    FILTER(
        ADDCOLUMNS(VALUES('Famille'[Famille]), "@ecart", [CA net écart N-1]),
        NOT ISBLANK([@ecart])
    )
VAR _derniereFamille = TOPN(1, _familles, [@ecart], ASC)
VAR _famille = MAXX(_derniereFamille, 'Famille'[Famille])
VAR _ecartFamille = MAXX(_derniereFamille, [@ecart])
VAR _regions =
    FILTER(
        ADDCOLUMNS(VALUES('Région'[Région]), "@ecart", [CA net écart N-1]),
        NOT ISBLANK([@ecart])
    )
VAR _derniereRegion = TOPN(1, _regions, [@ecart], ASC)
VAR _region = MAXX(_derniereRegion, 'Région'[Région])
VAR _ecartRegion = MAXX(_derniereRegion, [@ecart])
VAR _nouveaux = [# Nouveaux clients] + 0
VAR _perdus = [# Clients perdus] + 0
RETURN
    SWITCH(
        TRUE(),
        ISBLANK(_annee), "Sélectionnez une année. Données fictives.",
        ISBLANK([CA net N-1]),
            "Pas d'exercice précédent : contributions à la croissance non calculables. Données fictives.",
        "Plus faible contribution : famille " & _famille & " ("
            & IF(_ecartFamille < 0, "-", "+") & FORMAT(ABS(_ecartFamille) / 1000, "#,0", "fr-FR")
            & " k€), région " & _region & " ("
            & IF(_ecartRegion < 0, "-", "+") & FORMAT(ABS(_ecartRegion) / 1000, "#,0", "fr-FR")
            & " k€). " & _nouveaux & IF(_nouveaux <= 1, " nouveau client, ", " nouveaux clients, ")
            & _perdus & IF(_perdus <= 1, " client perdu", " clients perdus")
            & ". Données fictives."
    )
```

### Titre tendance CA

Titre de la courbe mensuelle : nombre de mois où le CA net dépasse celui de N-1.

Format : texte.

```dax
VAR _annee = SELECTEDVALUE('Date'[Année])
VAR _mois =
    FILTER(
        ADDCOLUMNS(VALUES('Date'[Numéro mois]), "@ca", [CA net], "@caN1", [CA net N-1]),
        NOT ISBLANK([@caN1])
    )
VAR _nbMois = COUNTROWS(_mois) + 0
VAR _nbHausses = COUNTROWS(FILTER(_mois, [@ca] > [@caN1])) + 0
RETURN
    IF(
        ISBLANK(_annee) || _nbMois = 0,
        "CA net mensuel",
        "CA net mensuel : au-dessus de " & (_annee - 1) & " sur " & _nbHausses & " mois sur " & _nbMois
    )
```

### Titre écart par famille

Titre des écarts de CA net par famille : la famille qui apporte la plus forte hausse.

Format : texte.

```dax
VAR _membres =
    FILTER(
        ADDCOLUMNS(VALUES('Famille'[Famille]), "@ecart", [CA net écart N-1]),
        NOT ISBLANK([@ecart])
    )
VAR _meilleur = TOPN(1, _membres, [@ecart], DESC)
VAR _nom = MAXX(_meilleur, 'Famille'[Famille])
VAR _ecart = MAXX(_meilleur, [@ecart])
VAR _ecartTexte =
    IF(_ecart < 0, "-", "+") & FORMAT(ABS(_ecart) / 1000, "#,0", "fr-FR") & " k€"
RETURN
    SWITCH(
        TRUE(),
        ISBLANK(_nom), "Écart de CA net par famille",
        _ecart > 0, "Par famille : " & _nom & " en tête (" & _ecartTexte & ")",
        "Par famille : toutes en recul, " & _nom & " résiste le mieux (" & _ecartTexte & ")"
    )
```

### Titre écart par région

Titre des écarts de CA net par région : la région qui apporte la plus forte hausse.

Format : texte.

```dax
VAR _membres =
    FILTER(
        ADDCOLUMNS(VALUES('Région'[Région]), "@ecart", [CA net écart N-1]),
        NOT ISBLANK([@ecart])
    )
VAR _meilleur = TOPN(1, _membres, [@ecart], DESC)
VAR _nom = MAXX(_meilleur, 'Région'[Région])
VAR _ecart = MAXX(_meilleur, [@ecart])
VAR _ecartTexte =
    IF(_ecart < 0, "-", "+") & FORMAT(ABS(_ecart) / 1000, "#,0", "fr-FR") & " k€"
RETURN
    SWITCH(
        TRUE(),
        ISBLANK(_nom), "Écart de CA net par région",
        _ecart > 0, "Par région : " & _nom & " en tête (" & _ecartTexte & ")",
        "Par région : toutes en recul, " & _nom & " résiste le mieux (" & _ecartTexte & ")"
    )
```

### Titre écart par statut client

Titre des écarts de CA net par statut client : le statut qui apporte la plus forte hausse.

Format : texte.

```dax
VAR _statuts =
    FILTER(
        ADDCOLUMNS(VALUES('Statut client'[Statut]), "@ecart", [CA net écart N-1 par statut]),
        NOT ISBLANK([@ecart])
    )
VAR _meilleur = TOPN(1, _statuts, [@ecart], DESC)
VAR _nom = MAXX(_meilleur, 'Statut client'[Statut])
VAR _ecart = MAXX(_meilleur, [@ecart])
RETURN
    SWITCH(
        TRUE(),
        ISBLANK(_nom), "Écart de CA net par statut client",
        _ecart > 0,
            "Par statut : " & LOWER(_nom) & " en tête ("
                & IF(_ecart < 0, "-", "+") & FORMAT(ABS(_ecart) / 1000, "#,0", "fr-FR") & " k€)",
        "Par statut : aucune hausse"
    )
```

### Titre écart budget par famille

Titre des écarts au budget par famille : nombre de familles qui atteignent leur budget de CA net.

Format : texte.

```dax
VAR _familles =
    FILTER(
        ADDCOLUMNS(VALUES('Famille'[Famille]), "@ecart", [CA net écart budget]),
        NOT ISBLANK([@ecart])
    )
VAR _nombre = COUNTROWS(_familles) + 0
VAR _atteints = COUNTROWS(FILTER(_familles, [@ecart] >= 0)) + 0
RETURN
    SWITCH(
        TRUE(),
        _nombre = 0, "Écart de CA net au budget par famille",
        _atteints <= 1, _atteints & " famille sur " & _nombre & " atteint son budget de CA net",
        _atteints & " familles sur " & _nombre & " atteignent leur budget de CA net"
    )
```

### Titre Marge

Titre de la page Marge : évolution de la marge commerciale et taux de marge, avec l'écart en points sur un an.

Format : texte.

```dax
VAR _annee = SELECTEDVALUE('Date'[Année])
VAR _marge = [Marge commerciale]
VAR _evolution = [Marge commerciale évol. N-1 (%)]
VAR _taux = [Marge commerciale (% CA)]
VAR _ecart = [Marge commerciale écart N-1 (pts)]
RETURN
    SWITCH(
        TRUE(),
        ISBLANK(_annee), "Sélectionnez une année",
        ISBLANK(_marge), "Aucune vente sur la sélection",
        ISBLANK(_evolution),
            "En " & _annee & ", la marge commerciale atteint "
                & FORMAT(_marge / 1000000, "#,0.0", "fr-FR") & " M€, soit "
                & FORMAT(_taux, "0.0 %", "fr-FR")
                & " du CA net (pas d'exercice précédent)",
        "En " & _annee & ", la marge commerciale "
            & IF(_evolution >= 0, "progresse", "recule")
            & " de " & FORMAT(ABS(_evolution), "0.0 %", "fr-FR")
            & " et représente " & FORMAT(_taux, "0.0 %", "fr-FR") & " du CA net ("
            & IF(_ecart < 0, "-", "+") & FORMAT(ABS(_ecart), "0.0", "fr-FR") & " pts)"
    )
```

### Synthèse Marge

Synthèse de la page Marge : écarts de CA net et de marge commerciale sur un an, taux de marge du CA supplémentaire, écart au budget de marge (omis si le budget est vide).

Format : texte.

```dax
VAR _annee = SELECTEDVALUE('Date'[Année])
VAR _ecartCA = [CA net écart N-1]
VAR _ecartMarge = [Marge commerciale écart N-1]
VAR _ecartBudget = [Marge commerciale écart budget (%)]
VAR _texteEvolution =
    IF(
        ISBLANK(_ecartCA),
        "Pas d'exercice précédent : évolution de la marge non calculable. ",
        "Sur un an : CA net "
            & IF(_ecartCA < 0, "-", "+") & FORMAT(ABS(_ecartCA) / 1000, "#,0", "fr-FR")
            & " k€, marge commerciale "
            & IF(_ecartMarge < 0, "-", "+") & FORMAT(ABS(_ecartMarge) / 1000, "#,0", "fr-FR")
            & " k€"
            & IF(
                _ecartCA > 0,
                ", soit une marge de " & FORMAT(DIVIDE(_ecartMarge, _ecartCA), "0.0 %", "fr-FR")
                    & " sur le CA supplémentaire"
            )
            & ". "
    )
VAR _texteBudget =
    IF(
        NOT ISBLANK(_ecartBudget),
        "Marge commerciale " & FORMAT(ABS(_ecartBudget), "0.0 %", "fr-FR")
            & IF(_ecartBudget >= 0, " au-dessus du budget. ", " sous le budget. ")
    )
RETURN
    IF(
        ISBLANK(_annee),
        "Sélectionnez une année. Données fictives.",
        _texteEvolution & _texteBudget & "Données fictives."
    )
```

### Titre pont de marge

Titre du graphique en cascade : effet le plus défavorable entre N-1 et N.

Format : texte.

```dax
VAR _annee = SELECTEDVALUE('Date'[Année])
VAR _frein = [Frein principal (libellé)]
VAR _montant = [Frein principal (montant)]
RETURN
    SWITCH(
        TRUE(),
        ISBLANK(_annee), "Pont de marge commerciale",
        ISBLANK(_frein), "Pont de marge commerciale : pas d'exercice précédent à comparer",
        _montant < 0,
            "Pont de marge " & (_annee - 1) & " → " & _annee & " : l'effet " & _frein & " pèse le plus ("
                & IF(_montant < 0, "-", "+") & FORMAT(ABS(_montant) / 1000, "#,0", "fr-FR") & " k€)",
        "Pont de marge " & (_annee - 1) & " → " & _annee & " : aucun effet défavorable"
    )
```

### Titre remises par commercial

Titre des écarts de taux de remise par commercial : le commercial dont le taux de remise augmente le plus.

Format : texte.

```dax
VAR _commerciaux =
    FILTER(
        ADDCOLUMNS(
            VALUES('Commercial'[Commercial]),
            "@ecart", [Taux de remise écart N-1 (pts)],
            "@taux", [Taux de remise (%)],
            "@tauxN1", [Taux de remise N-1 (%)]
        ),
        NOT ISBLANK([@ecart])
    )
VAR _premier = TOPN(1, _commerciaux, [@ecart], DESC)
VAR _nom = MAXX(_premier, 'Commercial'[Commercial])
VAR _ecart = MAXX(_premier, [@ecart])
VAR _taux = MAXX(_premier, [@taux])
VAR _tauxN1 = MAXX(_premier, [@tauxN1])
RETURN
    SWITCH(
        TRUE(),
        ISBLANK(_nom), "Taux de remise par commercial : écart avec l'exercice précédent",
        _ecart > 0,
            _nom & " : taux de remise de " & FORMAT(_tauxN1, "0.0 %", "fr-FR") & " à "
                & FORMAT(_taux, "0.0 %", "fr-FR") & " ("
                & IF(_ecart < 0, "-", "+") & FORMAT(ABS(_ecart), "0.0", "fr-FR") & " pts)",
        "Aucun commercial n'augmente ses remises"
    )
```

### Titre marge par famille

Titre des écarts de taux de marge par famille : la famille qui perd le plus de points.

Format : texte.

```dax
VAR _familles =
    FILTER(
        ADDCOLUMNS(VALUES('Famille'[Famille]), "@ecart", [Marge commerciale écart N-1 (pts)]),
        NOT ISBLANK([@ecart])
    )
VAR _pire = TOPN(1, _familles, [@ecart], ASC)
VAR _nom = MAXX(_pire, 'Famille'[Famille])
VAR _ecart = MAXX(_pire, [@ecart])
RETURN
    SWITCH(
        TRUE(),
        ISBLANK(_nom), "Écart de taux de marge par famille",
        _ecart < 0,
            _nom & " : taux de marge "
                & IF(_ecart < 0, "-", "+") & FORMAT(ABS(_ecart), "0.0", "fr-FR") & " pts",
        "Taux de marge : aucune famille en recul"
    )
```

### Titre clients en recul

Titre du tableau des clients dont la marge contributive recule le plus sur un an.

Format : texte.

```dax
VAR _annee = SELECTEDVALUE('Date'[Année])
VAR _reculs =
    COUNTROWS(
        FILTER(
            VALUES('Client'[Clé client]),
            NOT ISBLANK([CA net]) && [Marge contributive écart N-1] < 0
        )
    )
RETURN
    SWITCH(
        TRUE(),
        ISBLANK(_annee), "Clients en plus fort recul de marge contributive",
        ISBLANK([CA net N-1]), "Clients en recul de marge : pas d'exercice précédent",
        ISBLANK(_reculs), "Aucun client en recul de marge contributive",
        "Clients en plus fort recul de marge contributive"
    )
```

### Titre produits déficitaires

Titre du tableau des produits vendus sous leur coût d'achat : nombre, perte totale et, au-delà de six, mention des six plus lourds affichés.

Format : texte.

```dax
VAR _produits =
    FILTER(
        ADDCOLUMNS(VALUES('Produit'[Clé produit]), "@marge", [Marge commerciale]),
        [@marge] < 0
    )
VAR _nombre = COUNTROWS(_produits) + 0
VAR _perte = SUMX(_produits, [@marge])
VAR _perteTexte =
    " (" & IF(_perte < 0, "-", "+") & FORMAT(ABS(_perte) / 1000, "#,0", "fr-FR") & " k€)"
RETURN
    SWITCH(
        TRUE(),
        _nombre = 0, "Aucun produit vendu à perte",
        _nombre = 1, "1 produit vendu à perte" & _perteTexte,
        _nombre <= 6, _nombre & " produits vendus à perte" & _perteTexte,
        _nombre & " produits vendus à perte" & _perteTexte & " : les 6 plus lourds"
    )
```
