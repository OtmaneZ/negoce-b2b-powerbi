# Spécification : démo Power BI « Arvenor, négoce B2B »

Version 2, validée le 17 novembre 2026. Toutes les données sont fictives.

Ce document fixe ce qui est construit : l'entreprise et son histoire, les données générées, le modèle sémantique, les mesures, les deux pages du rapport et le plan de contrôle. Les chiffres cités ici sont des **cibles de génération**, pas des résultats : les valeurs réelles sont calculées par script (`scripts/expected_values.py`) et vérifiées dans Power BI Desktop.

## 0. Décisions de conception

1. **Deux dimensions conformes, Famille et Région.** Le budget est au grain mois × famille × région. Pour le relier au modèle avec des relations 1-* unidirectionnelles uniquement, il faut des dimensions à ce grain, partagées par Ventes et Budget. Sans elles, il faudrait une relation plusieurs-à-plusieurs ou des relations virtuelles (TREATAS) dans chaque mesure de budget. Ventes porte donc directement une clé famille et une clé région (schéma en étoile, pas de flocon).
2. **Une seule table de mesures.** Une pratique répandue consiste plutôt à répartir les mesures dans les tables de faits ; ici la table unique se justifie : plusieurs mesures croisent Ventes et Budget, et le lecteur trouve tout au même endroit, rangé par dossiers.
3. **L'effet prix du pont de marge est scindé en deux** : effet prix catalogue et effet remises (leur somme est l'effet prix). C'est ce qui rend visible la dérive des remises dans le pont.
4. **Volume mesuré à prix constants** dans le pont (section 4.5). Le bouclage du pont est testé sur trois cas : total 2025, région Sud 2025, famille Visserie et fixations 2025.
5. **Taux exprimés en % du CA net.** Pour éviter l'ambiguïté entre « taux de marge » (marge / coût d'achat) et « taux de marque » (marge / prix de vente), les mesures s'appellent « Marge commerciale (% CA) », « Transport (% CA) », etc.
6. **Année sélectionnée par segment**, 2025 par défaut. Les comparaisons N-1 et le pont de marge n'existent que pour 2025 ; si l'on choisit 2024, les textes le disent explicitement.
7. **Textes calculés en DAX et vérifiés par script.** `scripts/expected_values.py` calcule le texte attendu de chaque mesure texte avec les mêmes règles d'arrondi et de format fr-FR que le DAX ; `tests/validation.dax` compare tout dans Desktop en une seule requête.
8. **Budget absent, phrase sans budget.** Toute mesure ou tout texte qui cite le budget gère le cas où le budget est vide (filtre sur Client, Produit ou Commercial) : la phrase omet alors le budget.

## 1. Entreprise fictive

| Élément | Valeur |
|---|---|
| Nom | **Arvenor** (raison sociale fictive : Arvenor SAS) |
| Activité | Négoce B2B de fournitures industrielles : visserie, outillage, abrasifs, équipements de protection, produits de maintenance |
| Implantation | Siège et entrepôt central en région lyonnaise, livraisons dans toute la France métropolitaine |
| Taille | Environ 90 salariés, dont 10 commerciaux terrain ; CA net d'environ 21 M€ en 2024 |
| Clientèle | Environ 900 clients professionnels : industriels, artisans, sociétés de maintenance, collectivités |
| Historique couvert | Exercices 2024 et 2025 (années civiles complètes) |

**Vérification du nom.**

| Date | Recherche | Résultat |
|---|---|---|
| 17 novembre 2026 | « Arvenor » seul | Aucune entreprise ; seule occurrence : un monde fictif d'un jeu de rôle |
| 17 novembre 2026 | « Arvenor » + fournitures industrielles | Aucune entreprise de ce nom dans le secteur |
| 17 novembre 2026 | « Arvenor » + SIREN, Pappers, societe.com | Aucune fiche à ce nom |

Deux autres candidats ont été écartés le même jour : « Valtorne », trop proche de Valtor (robinetterie industrielle), et « Ferandel », nom de famille porté par des dirigeants réels. La base des marques de l'INPI est vérifiée par l'auteur avant publication.

### Régions commerciales

| Région | Poids dans le CA 2024 (cible) | Évolution 2025 (cible) | Remarque |
|---|---|---|---|
| Île-de-France | 26 % | +4 % | Marché mature |
| Nord-Est | 18 % | -3 % | Recul industriel local |
| Ouest | 20 % | +9 % | Dynamique |
| Rhône-Alpes | 22 % | +15 % | Proche de l'entrepôt, transport le moins cher |
| Sud | 14 % | +6 % | Croissance achetée par les remises |

### Commerciaux

Deux commerciaux par région, adresses en `@example.com`.

| Commercial | Région | Particularité |
|---|---|---|
| Camille Roussel | Île-de-France | |
| Mehdi Haddad | Île-de-France | |
| Pauline Mercier | Nord-Est | |
| Laurent Schmitt | Nord-Est | |
| Gaëlle Le Guen | Ouest | |
| Nicolas Hervé | Ouest | |
| Sophie Vernet | Rhône-Alpes | |
| Romain Chabert | Rhône-Alpes | |
| Damien Revol | Sud | **Dérive des remises** : taux moyen d'environ 11 % en 2024, montée progressive tout au long de 2025, environ 19 % sur l'année |
| Inès Fabre | Sud | |

Adresses : `prenom.nom@example.com` sans accents ni espaces (par exemple `gaelle.leguen@example.com`). Une adresse supplémentaire, `direction.commerciale@example.com`, a accès aux cinq régions pour tester une habilitation multirégion.

### Familles de produits

| Famille | Nombre de références | Prix catalogue unitaire 2024 | Taux de marge commerciale cible 2024 | Pondération des volumes 2025 (paramètre) |
|---|---|---|---|---|
| Visserie et fixations | 140 | 3 à 60 € | 38 % | +2 % |
| Outillage à main | 110 | 8 à 150 € | 35 % | -10 % |
| Outillage électroportatif | 70 | 60 à 900 € | 24 % | +12 % |
| Abrasifs et coupe | 90 | 2 à 40 € | 40 % | +5 % |
| Équipements de protection | 100 | 3 à 120 € | 33 % | +16 % |
| Hygiène et maintenance | 90 | 4 à 80 € | 30 % | +7 % |

La pondération des volumes déplace le mix de 2025 entre familles ; elle s'ajoute à l'évolution régionale. Total : 600 références. Libellés produits génériques et descriptifs, sans marque, 32 caractères au plus (par exemple « Vis TH M8x40 zinguée, boîte 100 »).

### Segments clients

| Segment | Part des clients | Panier type | Remise de base |
|---|---|---|---|
| Grands comptes | 5 % | Élevé, commandes fréquentes | 14 % |
| PME industrielles | 45 % | Moyen | 9 % |
| Artisans et TPE | 40 % | Faible | 5 % |
| Collectivités | 10 % | Moyen, saisonnier | 11 % |

Noms de clients : pseudo-raisons sociales construites à partir de racines inventées et d'un mot d'activité (par exemple « Brenvia Usinage »). Ils sont manifestement fictifs ; ils ne sont pas vérifiés un par un contre les registres.

### L'histoire que racontent les données

1. **Croissance inégale.** Le CA net progresse d'environ 8 % en 2025, mais la croissance vient surtout des équipements de protection, de l'électroportatif et de Rhône-Alpes ; l'outillage à main et le Nord-Est reculent.
2. **Saisonnalité.** Creux marqué en août (environ -45 % par rapport à un mois moyen) et en décembre (environ -20 %), pics en mars-juin et septembre-octobre ; les jours fériés et les week-ends n'ont pas de ventes.
3. **Hausse des coûts d'achat sur la visserie.** À partir du 1er mars 2025, le coût d'achat de la visserie et des fixations augmente d'environ 11 % (acier), alors que son prix catalogue n'a augmenté que de 3 % au 1er janvier (2,5 % pour les autres familles). Le taux de marge de la famille perd plusieurs points.
4. **Dérive des remises chez Damien Revol (Sud).** Son taux de remise moyen passe d'environ 11 % à environ 19 %. Le volume de ses clients augmente, le CA de la région Sud progresse, sa marge recule.
5. **Clients et produits déficitaires.** En 2025, au moins 8 clients ont une marge contributive négative : petits clients éloignés aux commandes fréquentes et de faible montant (transport supérieur à la marge) et des clients surremisés de Damien Revol. Au moins 5 références sont vendues sous leur coût d'achat : fins de série d'outillage à main en déstockage.

## 2. Données

### Principes

- Générateur unique `scripts/generate_data.py`, graine fixe (`numpy.random.default_rng(20240101)`), régénération à l'identique octet pour octet.
- CSV UTF-8 sans BOM dans `data/`, séparateur virgule, point décimal, dates ISO `AAAA-MM-JJ`, en-têtes en minuscules ASCII avec tirets bas. Les noms métier sont donnés dans Power Query.
- Montants calculés en centimes entiers puis écrits avec deux décimales : aucune erreur d'arrondi, `montant_net = montant_brut - montant_remise` exactement.
- La table de dates n'est pas un CSV : elle est générée dans Power Query.

### Tables et colonnes

**`ventes.csv`** (fait, grain : ligne de commande ; environ 63 500 lignes sur deux ans, environ 22 300 commandes)

| Colonne | Type | Règle |
|---|---|---|
| `numero_commande` | entier | `AAAA` + numéro sur 5 chiffres (par exemple `202500137`) |
| `numero_ligne` | entier | 1 à n dans la commande ; clé unique : (`numero_commande`, `numero_ligne`) |
| `date_commande` | date | Jour ouvré (lundi à vendredi, hors jours fériés français 2024-2025) |
| `cle_client` | entier | Clé étrangère vers `clients.csv` |
| `cle_produit` | entier | Clé étrangère vers `produits.csv` |
| `cle_commercial` | entier | Commercial du client (portefeuille stable sur deux ans) |
| `cle_region` | entier | Région du client |
| `cle_famille` | entier | Famille du produit |
| `quantite` | entier | Strictement positive ; plus élevée pour les articles bon marché |
| `montant_brut` | décimal | Quantité × prix catalogue unitaire en vigueur |
| `montant_remise` | décimal | Montant brut × taux de remise de la ligne (0 à 40 %) |
| `montant_net` | décimal | Montant brut - montant remise |
| `cout_achat` | décimal | Quantité × coût d'achat unitaire en vigueur |
| `cout_transport` | décimal | Coût de livraison supporté par Arvenor, réparti sur les lignes au prorata du montant net |

**`budget.csv`** (fait, grain : mois × famille × région ; 24 × 6 × 5 = 720 lignes)

| Colonne | Type | Règle |
|---|---|---|
| `mois` | date | Premier jour du mois |
| `cle_famille` | entier | Clé étrangère vers `familles.csv` |
| `cle_region` | entier | Clé étrangère vers `regions.csv` |
| `budget_ca_net` | décimal | Voir règles de génération |
| `budget_marge_commerciale` | décimal | Voir règles de génération |

**Dimensions**

| Fichier | Lignes | Colonnes |
|---|---|---|
| `clients.csv` | environ 900 | `cle_client`, `client`, `segment`, `cle_region`, `cle_commercial` |
| `produits.csv` | 600 | `cle_produit`, `reference`, `produit`, `sous_famille`, `cle_famille` |
| `commerciaux.csv` | 10 | `cle_commercial`, `commercial`, `email`, `cle_region` |
| `familles.csv` | 6 | `cle_famille`, `famille` |
| `regions.csv` | 5 | `cle_region`, `region` |
| `acces_regional.csv` | 15 | `email`, `cle_region` (un couple par commercial, cinq pour la direction commerciale) |

Les colonnes `clients.cle_region`, `clients.cle_commercial`, `produits.cle_famille`, `produits.reference` et `commerciaux.email` servent au générateur et aux tests ; elles ne sont pas chargées dans le modèle (voir section 3).

### Règles de génération

1. **Calendrier.** Jours ouvrés 2024-2025 ; poids mensuels de saisonnalité : janvier 0,90 ; février 0,95 ; mars 1,10 ; avril 1,05 ; mai 0,95 ; juin 1,10 ; juillet 0,95 ; août 0,55 ; septembre 1,10 ; octobre 1,15 ; novembre 1,05 ; décembre 0,80.
2. **Clients.** Région tirée selon les poids régionaux, segment selon les parts ci-dessus, commercial tiré parmi les deux de sa région. Hors grands comptes, 5 % des clients sont perdus fin 2024 et 7 % sont nouveaux en 2025, à partir d'un mois tiré entre janvier et octobre (le nombre de clients actifs bouge).
3. **Commandes.** Fréquence annuelle par client selon le segment et un niveau d'activité propre au client, avec une dispersion de 5 % d'une année sur l'autre ; en 2025, elle suit l'évolution de la région (+15 % de volume en plus pour les clients de Damien Revol). Dates tirées selon la saisonnalité. 1 à 8 lignes par commande, montant brut visé par ligne selon le segment.
4. **Produits.** Choix pondéré par les préférences de famille du segment et une popularité de type Zipf à l'intérieur de chaque famille. Toutes les références sont vendues au moins une fois chaque année (contrôlé par test).
5. **Prix et coûts.** Prix catalogue 2024 tiré dans la fourchette de la sous-famille ; coût d'achat = prix × (1 - 10 % de remise moyenne attendue) × (1 - taux de marge cible de la famille ± bruit), pour que le taux cible s'entende après remises. Au 1er janvier 2025 : prix catalogue +2,5 %, +3 % pour la visserie, coûts d'achat +1,5 %. Au 1er mars 2025 : coût d'achat de la visserie +11 % supplémentaires. Huit références d'outillage à main passent en fin de série en 2025, prix catalogue réduit de 45 %, sous leur coût d'achat.
6. **Remises.** Remise de base du segment + effet commercial + effet client + bruit, bornée à [0 %, 40 %]. Damien Revol : supplément croissant tout au long de 2025, jusqu'à +10 points en fin d'année, et cinq clients remisés entre 37 % et 40 %.
7. **Transport.** Par commande : forfait selon la région (9 € en Rhône-Alpes, 14 € en Île-de-France, 15 € dans le Sud, 17 € dans l'Ouest, 18 € dans le Nord-Est) plus 1,5 % du montant net ; un peu plus de 2 % du CA en moyenne, bien plus sur les petites commandes. Dix petits clients du Nord-Est et de l'Ouest commandent une quarantaine de fois par an pour de faibles montants, en consommables.
8. **Budget.** 2024 : CA net réel 2024 par famille × région, avec une erreur de prévision tirée entre -3 % et +3 %, réparti par mois selon la saisonnalité et le nombre de jours ouvrés. 2025 : CA net réel 2024 par famille × région × 1,06, réparti de la même façon. Budget de marge = budget de CA × taux de marge commerciale réel 2024 de la famille × région : le budget 2025 n'anticipe ni la hausse des coûts de la visserie ni la dérive des remises.

## 3. Modèle sémantique

### Structure du projet

```text
NegoceB2B.pbip
NegoceB2B.SemanticModel/
  definition.pbism
  definition/
    database.tmdl, model.tmdl, relationships.tmdl, expressions.tmdl
    tables/*.tmdl
    roles/Commercial.tmdl
    cultures/fr-FR.tmdl
NegoceB2B.Report/
  definition.pbir
  definition/...
```

### Paramètres du modèle

- Mode Import, Power Query (M) pour toutes les tables.
- Culture du modèle `fr-FR` (affichage), culture `en-US` pour la lecture des nombres et des dates dans Power Query.
- Date/heure automatique désactivée ; `discourageImplicitMeasures` activé.
- Paramètre Power Query `DossierDonnees` (texte, obligatoire) : chemin du dossier `data/` terminé par une barre oblique inverse. Valeur par défaut indicative `C:\negoce-b2b-powerbi\data\`, à adapter sur le poste Windows.
- Chaque requête : `Csv.Document(File.Contents(DossierDonnees & "<fichier>.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv])`, en-têtes promus, colonnes sélectionnées et renommées, types explicites avec la culture `en-US`.

### Tables et colonnes du modèle

Clés et colonnes techniques masquées ; colonnes agrégées par des mesures masquées ; `summarizeBy: none` sur toutes les colonnes numériques ; description sur chaque table et chaque colonne visible.

| Table | Rôle | Colonnes visibles | Colonnes masquées |
|---|---|---|---|
| Ventes | Fait, ligne de commande | aucune | Numéro commande (Int64), Date commande (DateTime), Clé client, Clé produit, Clé commercial, Clé région, Clé famille (Int64), Quantité (Int64), Montant brut, Montant remise, Montant net, Coût d'achat, Coût transport (Decimal) |
| Budget | Fait, mois × famille × région | aucune | Mois (DateTime), Clé famille, Clé région (Int64), Budget CA net, Budget marge commerciale (Decimal) |
| Date | Dimension, marquée comme table de dates | Date (format `dd/MM/yyyy`), Année (Int64, format `0`), Trimestre (« T1 » à « T4 »), Mois (« janv. » à « déc. », trié par Numéro mois), Mois année (« janv. 2024 », trié par Clé mois année) | Numéro mois (Int64), Clé mois année (Int64, `AAAAMM`) |
| Client | Dimension | Client, Segment | Clé client |
| Produit | Dimension | Produit, Sous-famille | Clé produit |
| Commercial | Dimension | Commercial | Clé commercial |
| Famille | Dimension conforme | Famille | Clé famille |
| Région | Dimension conforme | Région | Clé région |
| Accès régional | Sécurité, table masquée, sans relation | | E-mail, Clé région |
| Étape du pont | Utilitaire du pont de marge, sans relation | Étape (triée par Ordre) | Ordre (Int64) |
| Mesures | Table de mesures | toutes les mesures | une colonne technique masquée |

- La table **Date** couvre du 1er janvier 2024 au 31 décembre 2025 (731 jours, 2024 est bissextile), générée en M avec `List.Dates`. Libellés de mois fixés par une liste en M, sans dépendance à la langue du poste. Hiérarchie « Calendrier » : Année > Trimestre > Mois.
- La table **Étape du pont** est une table littérale en M (`#table`) de six lignes : 1 Marge N-1, 2 Volume, 3 Mix, 4 Prix catalogue, 5 Remises, 6 Coût d'achat.

### Relations

Toutes de cardinalité un-à-plusieurs, filtrage dans un seul sens (de la dimension vers le fait), actives.

| De (côté 1) | Vers (côté plusieurs) |
|---|---|
| Date[Date] | Ventes[Date commande] |
| Date[Date] | Budget[Mois] |
| Client[Clé client] | Ventes[Clé client] |
| Produit[Clé produit] | Ventes[Clé produit] |
| Commercial[Clé commercial] | Ventes[Clé commercial] |
| Famille[Clé famille] | Ventes[Clé famille] |
| Famille[Clé famille] | Budget[Clé famille] |
| Région[Clé région] | Ventes[Clé région] |
| Région[Clé région] | Budget[Clé région] |

Conséquences assumées :

- Le budget n'est défini que par mois, famille et région. Les mesures de budget renvoient une valeur vide dès qu'un filtre porte sur Client, Produit ou Commercial, plutôt qu'un chiffre faux.
- Le budget est rattaché au premier jour du mois : il se lit au mois, au trimestre ou à l'année, jamais au jour.
- Pour filtrer à la fois les ventes et le budget, on utilise Famille[Famille] et Région[Région], pas des attributs portés par Produit ou Client.

### Sécurité au niveau des lignes (RLS)

Rôle **Commercial**, deux filtres de table :

```dax
// Table Région
VAR _regionsAutorisees =
    CALCULATETABLE(
        VALUES('Accès régional'[Clé région]),
        'Accès régional'[E-mail] = USERPRINCIPALNAME()
    )
RETURN
    'Région'[Clé région] IN _regionsAutorisees

// Table Accès régional
'Accès régional'[E-mail] = USERPRINCIPALNAME()
```

Le filtre sur Région se propage à Ventes et à Budget. La comparaison de texte en DAX ne tient pas compte de la casse : aucune fonction de manipulation de chaîne n'est nécessaire. Les dimensions Client, Produit et Commercial ne sont pas filtrées : un commercial voit leurs libellés mais aucun chiffre hors de sa région. Un utilisateur sans rôle (direction) voit tout. Test dans Desktop : « Afficher en tant que », rôle Commercial, autre utilisateur `damien.revol@example.com` (région Sud), puis `direction.commerciale@example.com` (cinq régions).

## 4. Mesures

Toutes les mesures sont dans la table **Mesures**, avec une description, un dossier d'affichage et une chaîne de format. Conventions : `VAR` pour les étapes, `DIVIDE` pour toute division, filtres de colonne plutôt que `FILTER` sur une table entière, colonnes toujours qualifiées par leur table, mesures jamais qualifiées. Nommage : base, puis période (« N-1 », « écart N-1 », « évol. N-1 », « budget »), puis unité entre parenthèses.

Formats (culture d'affichage fr-FR) :

| Code | Chaîne de format | Exemple d'affichage |
|---|---|---|
| EUR | `#,0 €` | 18 245 310 € |
| EUR± | `+#,0 €;-#,0 €;0 €` | +412 380 € |
| PCT | `0.0 %` | 31,8 % |
| PCT± | `+0.0 %;-0.0 %;0.0 %` | +8,4 % |
| PTS | `+0.0 "pts";-0.0 "pts";0.0 "pts"` | -2,3 pts |
| NB | `#,0` | 11 204 |
| DEC | `#,0.0` | 12,4 |
| TXT | aucun (mesure texte) | |

Les cartes affichent les montants en millions d'euros et les barres en milliers d'euros grâce à l'unité d'affichage du visuel ; la chaîne de format de la mesure reste celle indiquée ci-dessus.

### 1. Chiffre d'affaires

| Mesure | Définition métier | DAX | Format |
|---|---|---|---|
| CA brut | Chiffre d'affaires hors taxes au prix catalogue, avant remises (CA : chiffre d'affaires) | `SUM('Ventes'[Montant brut])` | EUR |
| Remises | Montant des remises accordées | `SUM('Ventes'[Montant remise])` | EUR |
| CA net | Chiffre d'affaires hors taxes facturé, après remises | `SUM('Ventes'[Montant net])` | EUR |
| Taux de remise (%) | Part du CA brut cédée en remises | `DIVIDE([Remises], [CA brut])` | PCT |
| Quantité | Unités vendues ; additionner des unités de familles différentes n'a de sens que produit par produit | `SUM('Ventes'[Quantité])` | NB |
| # Commandes | Nombre de commandes distinctes | `DISTINCTCOUNT('Ventes'[Numéro commande])` | NB |
| # Clients actifs | Clients ayant au moins une ligne de commande sur la période | `DISTINCTCOUNT('Ventes'[Clé client])` | NB |
| Commandes par client | Fréquence d'achat moyenne des clients actifs | `DIVIDE([# Commandes], [# Clients actifs])` | DEC |
| Panier moyen | CA net moyen par commande | `DIVIDE([CA net], [# Commandes])` | EUR |

Identité vérifiée par test : CA net = # Clients actifs × Commandes par client × Panier moyen, donc (1 + évol. du CA) = (1 + évol. des clients) × (1 + évol. de la fréquence) × (1 + évol. du panier). La bande de KPI de la Vue Direction se lit comme cette décomposition.

### 2. Marge

| Mesure | Définition métier | DAX | Format |
|---|---|---|---|
| Coût d'achat | Coût d'achat des marchandises vendues | `SUM('Ventes'[Coût d'achat])` | EUR |
| Marge commerciale | CA net - coût d'achat des marchandises vendues | `[CA net] - [Coût d'achat]` | EUR |
| Marge commerciale (% CA) | Marge commerciale rapportée au CA net (taux de marque) | `DIVIDE([Marge commerciale], [CA net])` | PCT |
| Transport | Coûts de livraison supportés par Arvenor | `SUM('Ventes'[Coût transport])` | EUR |
| Transport (% CA) | Poids du transport dans le CA net | `DIVIDE([Transport], [CA net])` | PCT |
| Marge contributive | Marge commerciale - transport : ce que la vente rapporte réellement | `[Marge commerciale] - [Transport]` | EUR |
| Marge contributive (% CA) | Marge contributive rapportée au CA net | `DIVIDE([Marge contributive], [CA net])` | PCT |
| # Clients à marge négative | Clients dont la marge contributive est négative sur la période | `COUNTROWS(FILTER(VALUES('Client'[Clé client]), [Marge contributive] < 0))` | NB |
| # Produits sous le coût | Références dont la marge commerciale est négative sur la période | `COUNTROWS(FILTER(VALUES('Produit'[Clé produit]), [Marge commerciale] < 0))` | NB |

### 3. Comparaison N-1

Modèle commun, appliqué à chaque indicateur suivi :

```dax
CA net N-1 =
CALCULATE([CA net], SAMEPERIODLASTYEAR('Date'[Date]))

CA net écart N-1 =
VAR _n1 = [CA net N-1]
RETURN IF(NOT ISBLANK(_n1), [CA net] - _n1)

CA net évol. N-1 (%) =
VAR _n1 = [CA net N-1]
RETURN DIVIDE([CA net] - _n1, _n1)

Marge commerciale écart N-1 (pts) =
VAR _tauxN = [Marge commerciale (% CA)]
VAR _tauxN1 = [Marge commerciale N-1 (% CA)]
RETURN IF(NOT ISBLANK(_tauxN) && NOT ISBLANK(_tauxN1), (_tauxN - _tauxN1) * 100)
```

La table Date étant marquée comme table de dates, le filtre posé par `SAMEPERIODLASTYEAR` sur Date[Date] remplace le filtre du segment Année. Pour 2024, la période N-1 (2023) n'existe pas : les mesures N-1 sont vides, les écarts et évolutions aussi.

| Mesure | Construction | Format |
|---|---|---|
| CA net N-1 | `CALCULATE` + `SAMEPERIODLASTYEAR` sur [CA net] | EUR |
| CA net écart N-1 | Modèle « écart » | EUR± |
| CA net évol. N-1 (%) | Modèle « évol. » | PCT± |
| Marge commerciale N-1 | `CALCULATE` + `SAMEPERIODLASTYEAR` | EUR |
| Marge commerciale évol. N-1 (%) | Modèle « évol. » | PCT± |
| Marge commerciale N-1 (% CA) | `CALCULATE` + `SAMEPERIODLASTYEAR` sur [Marge commerciale (% CA)] | PCT |
| Marge commerciale écart N-1 (pts) | Modèle « points » | PTS |
| Taux de remise N-1 (%) | `CALCULATE` + `SAMEPERIODLASTYEAR` | PCT |
| Taux de remise écart N-1 (pts) | Modèle « points » | PTS |
| Transport N-1 (% CA) | `CALCULATE` + `SAMEPERIODLASTYEAR` | PCT |
| Transport écart N-1 (pts) | Modèle « points » | PTS |
| Marge contributive N-1 | `CALCULATE` + `SAMEPERIODLASTYEAR` | EUR |
| Marge contributive évol. N-1 (%) | Modèle « évol. » | PCT± |
| # Clients actifs N-1 | `CALCULATE` + `SAMEPERIODLASTYEAR` | NB |
| # Clients actifs évol. N-1 (%) | Modèle « évol. » | PCT± |
| Commandes par client N-1 | `CALCULATE` + `SAMEPERIODLASTYEAR` | DEC |
| Commandes par client évol. N-1 (%) | Modèle « évol. » | PCT± |
| Panier moyen N-1 | `CALCULATE` + `SAMEPERIODLASTYEAR` | EUR |
| Panier moyen évol. N-1 (%) | Modèle « évol. » | PCT± |

### 4. Budget

```dax
CA net budget =
IF(
    ISCROSSFILTERED('Client') || ISCROSSFILTERED('Produit') || ISCROSSFILTERED('Commercial'),
    BLANK(),
    SUM('Budget'[Budget CA net])
)
```

| Mesure | Définition métier | Construction | Format |
|---|---|---|---|
| CA net budget | Budget de CA net ; vide si un filtre porte sur une dimension absente du budget | Ci-dessus | EUR |
| CA net écart budget | CA net - budget | `VAR _b = [CA net budget] RETURN IF(NOT ISBLANK(_b), [CA net] - _b)` | EUR± |
| CA net écart budget (%) | Écart rapporté au budget | `VAR _b = [CA net budget] RETURN DIVIDE([CA net] - _b, _b)` | PCT± |
| Marge commerciale budget | Budget de marge commerciale, même garde que le budget de CA | `SUM('Budget'[Budget marge commerciale])` avec la même garde | EUR |
| Marge commerciale écart budget (%) | Écart de marge rapporté au budget | Comme ci-dessus | PCT± |

### 5. Pont de marge N-1 → N

Le pont explique l'écart de marge commerciale entre l'année sélectionnée (N) et l'année précédente (N-1). Il est calculé produit par produit (i), avec, pour chaque année, Q la quantité, L le prix catalogue unitaire moyen (CA brut / Q), R la remise unitaire moyenne (Remises / Q), P = L - R le prix net unitaire moyen, C le coût d'achat unitaire moyen et m = P - C la marge unitaire. M désigne la marge commerciale totale.

Le volume se mesure **en valeur à prix constants** (CA de N valorisé aux prix nets de N-1) plutôt qu'en unités : additionner des boîtes de vis et des perceuses n'aurait pas de sens.

- V0 = Σ Q0ᵢ × P0ᵢ = CA net N-1
- V1 = Σ Q1ᵢ × P0ᵢ = CA net N au prix N-1
- **Effet volume** = M0 × (V1 / V0 - 1)
- **Effet mix** = Σ Q1ᵢ × m0ᵢ - M0 × V1 / V0
- **Effet prix catalogue** = Σ Q1ᵢ × (L1ᵢ - L0ᵢ)
- **Effet remises** = -Σ Q1ᵢ × (R1ᵢ - R0ᵢ)
- **Effet coût d'achat** = -Σ Q1ᵢ × (C1ᵢ - C0ᵢ)

Bouclage : M0 + volume + mix + prix catalogue + remises + coût d'achat = Σ Q1ᵢ × m0ᵢ + Σ Q1ᵢ × (m1ᵢ - m0ᵢ) = M1, exactement. Une référence sans vente en N-1 reçoit les valeurs unitaires de N (L0 = L1, R0 = R1, C0 = C1) : elle n'a ni effet prix ni effet coût, sa marge passe dans le mix. Une référence sans vente en N n'intervient que par M0 et V0. Les effets ne sont calculés que si une seule année est sélectionnée.

```dax
Effet prix catalogue =
IF(
    HASONEVALUE('Date'[Année]),
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

CA net N au prix N-1 =
SUMX(
    VALUES('Produit'[Clé produit]),
    VAR _q = [Quantité]
    VAR _qN1 = CALCULATE([Quantité], SAMEPERIODLASTYEAR('Date'[Date]))
    VAR _prixNetN1 =
        IF(_qN1 > 0, DIVIDE([CA net N-1], _qN1), DIVIDE([CA net], _q))
    RETURN _q * _prixNetN1
)

Effet volume =
VAR _margeN1 = [Marge commerciale N-1]
VAR _caN1 = [CA net N-1]
RETURN
    IF(
        HASONEVALUE('Date'[Année]) && NOT ISBLANK(_caN1),
        DIVIDE(_margeN1 * [CA net N au prix N-1], _caN1) - _margeN1
    )

Effet mix =
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

Effet remises et Effet coût d'achat suivent le modèle d'Effet prix catalogue, sur [Remises] et [Coût d'achat], avec le signe moins.

```dax
Pont de marge =
VAR _ordre = SELECTEDVALUE('Étape du pont'[Ordre])
RETURN
    SWITCH(
        _ordre,
        1, [Marge commerciale N-1],
        2, [Effet volume],
        3, [Effet mix],
        4, [Effet prix catalogue],
        5, [Effet remises],
        6, [Effet coût d'achat],
        [Marge commerciale]
    )
```

| Mesure | Visible | Format |
|---|---|---|
| CA net N au prix N-1 | non (intermédiaire) | EUR |
| Effet volume, Effet mix, Effet prix catalogue, Effet remises, Effet coût d'achat | oui | EUR± |
| Pont de marge | oui (graphique en cascade) | EUR± |
| Pont de marge écart de bouclage | non ; M0 + somme des effets - M1, attendu 0 au centime près | EUR± |
| Frein principal (libellé) | non ; nom de l'effet le plus négatif (`TOPN` sur une table construite des cinq effets) | TXT |
| Frein principal (montant) | non ; montant de cet effet | EUR± |

### 6. Textes calculés

Les mesures texte suivent des règles communes, appliquées à l'identique par le DAX et par `scripts/expected_values.py` :

- **Formats.** Tous les nombres passent par `FORMAT(valeur, format, "fr-FR")`, indépendant du poste, avec des formats à une seule section : pourcentage `0.0 %` (« 8,4 % »), millions `#,0.0` puis « M€ », milliers `#,0` puis « k€ », points `0.0` puis « pts ». Pour les valeurs signées, le signe est ajouté explicitement (`IF(x < 0, "-", "+") & FORMAT(ABS(x), …)`) : une valeur non nulle arrondie à zéro s'écrit ainsi « +0 k€ » quel que soit le moteur. Arrondi au plus proche, demi s'éloignant de zéro.
- **Comparaison.** Les textes attendus sont comparés après normalisation des espaces : espaces insécables (U+00A0, U+202F) ramenées à une espace simple.
- **Cas limites.** Aucune année ou plusieurs années : « Sélectionnez une année ». Pas d'exercice N-1 : le texte le dit. Budget vide : la partie budgétaire est omise. Compteurs : singulier pour 0 et 1, pluriel au-delà.
- **Préfixe et mention.** Les titres de page commencent par le nom de la page (« Vue Direction · », « Marge · ») ; les synthèses se terminent par « Données fictives. ».
- **Meilleur et pire.** Les classements utilisent `TOPN` sur les membres dont la valeur n'est pas vide.

| Mesure | Où | Texte (exemple sur des valeurs fictives) et variantes |
|---|---|---|
| Titre Direction | Titre de page Vue Direction | « Vue Direction · En 2025, le CA net progresse de 8,4 % sur un an et dépasse le budget de 1,2 % ». Variantes : « recule », « reste sous le budget de » ; sans N-1 : « En 2024, le CA net atteint 18,2 M€ et reste sous le budget de 0,8 % (pas d'exercice précédent à comparer) » ; sans budget, la partie budgétaire disparaît |
| Synthèse Direction | Sous-titre Vue Direction | « Meilleure contribution : famille Équipements de protection (+640 k€), région Rhône-Alpes (+590 k€). Clients actifs +2,1 %, commandes par client +1,8 %, panier moyen +4,3 %. Données fictives. » Sans N-1 : « Pas d'exercice précédent : contributions à la croissance non calculables. Données fictives. » |
| Titre tendance CA | Courbe mensuelle | « CA net mensuel : au-dessus de 2024 sur 10 mois sur 12 » ; sans N-1 : « CA net mensuel » |
| Titre écart par famille | Barres familles | « Plus forte hausse de CA net : famille Équipements de protection (+640 k€) » ; si aucune hausse : « Toutes les familles reculent ; la famille Visserie et fixations résiste le mieux (-20 k€) » ; sans N-1 : « Écart de CA net par famille » |
| Titre écart par région | Barres régions | Même modèle : « région … », « Toutes les régions reculent ; la région … » |
| Titre écart par segment | Barres segments | Même modèle : « segment … », « Tous les segments reculent ; le segment … » |
| Titre écart budget par famille | Barres budget | « 4 familles sur 6 atteignent leur budget de CA net » ; « 1 famille sur 6 atteint son budget de CA net » ; budget vide : « Écart de CA net au budget par famille » |
| Titre Marge | Titre de page Marge | « Marge · En 2025, la marge commerciale recule de 1,5 % et représente 30,1 % du CA net (-2,6 pts) » ; sans N-1 : « Marge · En 2024, la marge commerciale atteint 5,8 M€, soit 32,0 % du CA net (pas d'exercice précédent à comparer) » |
| Synthèse Marge | Sous-titre Marge | « Principal frein : coût d'achat (-310 k€). Marge commerciale 4,2 % sous le budget. 11 clients à marge contributive négative, 9 produits vendus sous leur coût. Données fictives. » Variantes : « Aucun effet défavorable dans le pont de marge. » ; sans N-1 : « Pas d'exercice précédent : pont de marge non calculable. » ; budget vide : phrase budgétaire omise |
| Titre pont de marge | Cascade | « Pont de marge 2024 → 2025 : l'effet coût d'achat pèse le plus (-310 k€) » ; « Pont de marge 2024 → 2025 : aucun effet défavorable » ; sans N-1 : « Pont de marge commerciale : pas d'exercice précédent à comparer » |
| Titre remises par commercial | Barres commerciaux | « Damien Revol : taux de remise de 9,1 % à 15,8 % (+6,7 pts) » (plus forte hausse) ; « Aucun commercial n'augmente ses remises » ; sans N-1 : « Taux de remise par commercial : écart avec l'exercice précédent » |
| Titre marge par famille | Barres familles | « Plus forte baisse de taux de marge : famille Visserie et fixations (-5,2 pts) » ; « Toutes les familles maintiennent ou améliorent leur taux de marge » ; sans N-1 : « Taux de marge commerciale par famille : écart avec l'exercice précédent » |
| Titre clients déficitaires | Tableau clients | « 11 clients à marge contributive négative » ; « 1 client … » ; « Aucun client à marge contributive négative » |
| Titre produits déficitaires | Tableau produits | « 9 produits vendus sous leur coût d'achat » ; « 1 produit vendu sous son coût d'achat » ; « Aucun produit vendu sous son coût d'achat » |

Exemple complet (le DAX de chaque mesure est dans le modèle et dans `docs/mesures.md`) :

```dax
Titre Direction =
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
    "Vue Direction · "
        & SWITCH(
            TRUE(),
            ISBLANK(_annee), "Sélectionnez une année",
            ISBLANK(_ca), "Aucune vente sur la sélection",
            ISBLANK(_evolution),
                "En " & _annee & ", le CA net atteint "
                    & FORMAT(_ca / 1000000, "#,0.0", "fr-FR") & " M€"
                    & _texteBudget & " (pas d'exercice précédent à comparer)",
            "En " & _annee & ", le CA net "
                & IF(_evolution >= 0, "progresse", "recule")
                & " de " & FORMAT(ABS(_evolution), "0.0 %", "fr-FR")
                & " sur un an" & _texteBudget
        )
```

Récapitulatif des dossiers : 1. Chiffre d'affaires (9 mesures), 2. Marge (9), 3. Comparaison N-1 (19), 4. Budget (5), 5. Pont de marge (10, dont 4 masquées), 6. Textes (14). Total : 66 mesures.

## 5. Rapport

### Principes communs aux deux pages

- Canevas 1280 × 720, alignement vertical « Milieu », fond de page `#F3F2F1`, visuels sur fond blanc, sans bordure, en-têtes de visuel masqués.
- Grille unique : 12 colonnes et 12 lignes, marges de 24 px à gauche et à droite, 32 px en haut et en bas, gouttières de 16 px, tout sur une trame de 8 px. Colonne : 88 px de large, pas de 104 px. Ligne : 40 px de haut, pas de 56 px. Une zone [c1, l1, c2, l2] (fin exclue) occupe x = 24 + 104 × (c1 - 1), y = 32 + 56 × (l1 - 1), largeur = 104 × (c2 - c1) - 16, hauteur = 56 × (l2 - l1) - 16.
- Les deux pages partagent exactement les mêmes zones :

| Zone | Grille | x | y | Largeur | Hauteur |
|---|---|---|---|---|---|
| titre | [1, 1, 10, 2] | 24 | 32 | 920 | 40 |
| synthese | [1, 2, 10, 3] | 24 | 88 | 920 | 40 |
| filtres | [10, 1, 13, 3] | 960 | 32 | 296 | 96 |
| kpis | [1, 3, 13, 5] | 24 | 144 | 1232 | 96 |
| principal | [1, 5, 8, 9] | 24 | 256 | 712 | 208 |
| secondaire | [8, 5, 13, 9] | 752 | 256 | 504 | 208 |
| bas_gauche | [1, 9, 5, 13] | 24 | 480 | 400 | 208 |
| bas_centre | [5, 9, 9, 13] | 440 | 480 | 400 | 208 |
| bas_droite | [9, 9, 13, 13] | 856 | 480 | 400 | 208 |

- Deux segments dans la zone filtres, synchronisés entre les pages : **Année** (Date[Année], liste horizontale affichée en vignettes, sélection unique, 2025 par défaut ; x 960, y 32, 120 × 96) et **Région** (Région[Région], liste déroulante, sélection multiple avec « Tout sélectionner » ; x 1096, y 32, 160 × 96). Les segments occupent toute la hauteur de la bande du titre et de la synthèse : un segment en liste déroulante avec en-tête demande au moins 80 px avec des marges de 8 px.
- Les titres de page et de visuels sont des mesures texte (section 4.6) : ils répondent à la question métier et restent justes quel que soit le filtre ou le rôle RLS. Titre et synthèse de page sont affichés par une carte à valeur unique (`cardVisual`, libellé masqué, retour à la ligne activé, alignement à gauche) ; les titres des graphiques sont des titres de visuel liés à la mesure. Aucune zone de texte à valeur dynamique n'est utilisée : son encodage PBIR n'est pas documenté de façon assez fiable pour être vérifié sans Desktop.
- Interactions : un clic sur une barre, une ligne ou un tableau **filtre** les autres visuels de la page (paramètre du rapport « filtrer plutôt que mettre en surbrillance »). Exceptions déclarées dans la page : la cascade ne filtre rien (sa table d'étapes n'est reliée à rien) ; le graphique des segments clients n'agit pas sur le graphique budgétaire (le budget n'existe pas par segment).
- Navigation par les onglets natifs des pages ; pas de boutons. Le volet de filtres reste visible : il montre le filtre de visuel des deux tableaux, également annoncé dans leurs titres.
- Ordre de tabulation = ordre de lecture (titre, synthèse, segments, KPI, principal, secondaire, bas gauche, centre, droite). Texte de remplacement sur chaque visuel de données, lié à la même mesure que son titre.

### Page 1 : « Vue Direction » (d'où vient la croissance)

| Id | Zone | Type | Champs | Question métier |
|---|---|---|---|---|
| D1 | titre | cardVisual (valeur unique, 14 pt semi-gras) | [Titre Direction] | Le CA progresse-t-il, et par rapport au budget ? |
| D2 | synthese | cardVisual (valeur unique, 10 pt) | [Synthèse Direction] | Qu'est-ce qui porte la croissance ? |
| D3 | filtres | slicer (vignettes) | Date[Année] | Quel exercice ? |
| D4 | filtres | slicer (liste déroulante) | Région[Région] | Quelle région ? |
| D5 | kpis | cardVisual, 10 valeurs sur 2 rangées de 5 | Première rangée : CA net · CA net écart budget (%) · # Clients actifs · Commandes par client · Panier moyen. Seconde rangée, sous chaque valeur : CA net évol. N-1 (%) · CA net budget · # Clients actifs évol. N-1 (%) · Commandes par client évol. N-1 (%) · Panier moyen évol. N-1 (%) | La croissance vient-elle de plus de clients, de commandes plus fréquentes ou de paniers plus gros ? |
| D6 | principal | lineChart | Axe : Date[Mois] ; valeurs : CA net, CA net N-1, CA net budget ; titre : [Titre tendance CA] | Quand la croissance se produit-elle, et suit-elle le budget ? |
| D7 | secondaire | clusteredBarChart (horizontal) | Axe : Famille[Famille] ; valeur : CA net écart N-1 ; tri décroissant ; titre : [Titre écart par famille] | Quelles familles apportent la croissance ? |
| D8 | bas_gauche | clusteredBarChart | Région[Région] ; CA net écart N-1 ; tri décroissant ; titre : [Titre écart par région] | Quelles régions apportent la croissance ? |
| D9 | bas_centre | clusteredBarChart | Client[Segment] ; CA net écart N-1 ; tri décroissant ; titre : [Titre écart par segment] | Quels types de clients apportent la croissance ? |
| D10 | bas_droite | clusteredBarChart | Famille[Famille] ; CA net écart budget ; tri décroissant ; titre : [Titre écart budget par famille] | Quelles familles tiennent leur budget ? |

Infobulles : D7 à D9 ajoutent CA net, CA net N-1 et CA net évol. N-1 (%) ; D10 ajoute CA net budget et CA net écart budget (%).

Les deux bandes de KPI affichent l'évolution de chaque indicateur juste sous sa valeur, dans la même carte. Les étiquettes de référence de la carte n'ont pas été retenues : leur encodage PBIR n'est pas documenté de façon vérifiable sans Desktop. Une valeur vide s'affiche « n.d. ».

### Page 2 : « Marge » (où part la marge)

| Id | Zone | Type | Champs | Question métier |
|---|---|---|---|---|
| M1 | titre | cardVisual (valeur unique, 14 pt semi-gras) | [Titre Marge] | La marge suit-elle le chiffre d'affaires ? |
| M2 | synthese | cardVisual (valeur unique, 10 pt) | [Synthèse Marge] | Qu'est-ce qui fait perdre de la marge ? |
| M3, M4 | filtres | slicers | Identiques à D3 et D4, synchronisés | |
| M5 | kpis | cardVisual, 10 valeurs sur 2 rangées de 5 | Première rangée : Marge commerciale · Marge commerciale (% CA) · Taux de remise (%) · Transport (% CA) · Marge contributive. Seconde rangée : Marge commerciale évol. N-1 (%) · Marge commerciale écart N-1 (pts) · Taux de remise écart N-1 (pts) · Transport écart N-1 (pts) · Marge contributive évol. N-1 (%) | Où se situe la perte : prix, remises, coûts, transport ? |
| M6 | principal | waterfallChart | Catégorie : 'Étape du pont'[Étape], triée par 'Étape du pont'[Ordre] (jamais par valeur) ; valeur : [Pont de marge] ; total automatique = marge N ; titre : [Titre pont de marge] | Pourquoi la marge a-t-elle changé depuis N-1 ? |
| M7 | secondaire | clusteredBarChart | Commercial[Commercial] ; Taux de remise écart N-1 (pts) ; tri décroissant ; infobulles : Taux de remise (%), Taux de remise N-1 (%) ; titre : [Titre remises par commercial] | Qui accorde plus de remises qu'avant ? |
| M8 | bas_gauche | clusteredBarChart | Famille[Famille] ; Marge commerciale écart N-1 (pts) ; tri croissant ; titre : [Titre marge par famille] | Quelle famille perd du taux de marge ? |
| M9 | bas_centre | tableEx | Client[Client], CA net, Marge contributive, Marge contributive (% CA) ; filtre de visuel : Marge contributive < 0 ; tri croissant sur la marge ; titre : [Titre clients déficitaires] | Quels clients coûtent plus qu'ils ne rapportent ? |
| M10 | bas_droite | tableEx | Produit[Produit], CA net, Marge commerciale, Marge commerciale (% CA) ; filtre de visuel : Marge commerciale < 0 ; tri croissant ; titre : [Titre produits déficitaires] | Quels produits sont vendus à perte ? |

La cascade M6 affiche : Marge N-1, Volume, Mix, Prix catalogue, Remises, Coût d'achat, puis la barre de total. Le total automatique égale la marge N, ce que garantit le test de bouclage. Le format PBIR du graphique en cascade n'offre aucune propriété pour renommer la barre de total : son libellé « Total » et la couleur de la première barre (traitée comme une hausse) restent à contrôler dans Desktop.

### Thème « Arvenor sobre »

Une seule couleur d'accent ; le rouge est réservé au défavorable ; le reste est en gris.

| Rôle | Couleur | Contraste sur blanc | Usage |
|---|---|---|---|
| Accent | `#1F4E79` | 8,66 | Série de l'année N, écarts favorables, hausses de la cascade |
| Alerte | `#B42318` | 6,57 | Écarts défavorables uniquement, baisses de la cascade |
| Texte principal | `#252423` | 15,49 | Titres, valeurs, étiquettes de données, ligne de budget (pointillés) |
| Texte secondaire | `#605E5C` | 6,46 | Libellés d'axe, barre de total de la cascade |
| Gris N-1 | `#8A8886` | 3,53 | Série de l'année N-1 |
| Quadrillage | `#E1DFDD` | | Quadrillage, séparateurs |
| Fond de page | `#F3F2F1` | | Fond du canevas |

- **Sémantique favorable / défavorable** : une hausse de CA ou de taux de marge est favorable (accent), une hausse du taux de remise ou du transport est défavorable (alerte). La couleur double toujours une information déjà portée par le signe et la position de la barre ; pas de vert, ce qui évite la confusion rouge-vert.
- `dataColors` : `#1F4E79`, `#8A8886`, `#252423`, `#B42318`, `#6F93B8`, `#C9D8E8`, `#605E5C`, `#E1DFDD`. Sentiments : good `#1F4E79`, neutral `#605E5C`, bad `#B42318`.
- Typographie Segoe UI : titre de page 14 pt semi-gras ; titres de visuel 11 pt semi-gras ; valeurs des cartes 20 pt ; libellés de carte 9 pt ; axes et étiquettes 9 pt.
- Règles de mise en forme : barres partant de zéro ; montants signés dans les écarts ; k€ dans les barres, M€ dans les cartes, € dans les tableaux ; aucune 3D, aucun camembert, aucune jauge ; étiquettes de données en `#252423` ; quadrillage horizontal seulement sur les courbes.

## 6. Plan de contrôle

### Cas de validation

Chaque mesure affichée sur les deux pages est calculée en pandas, indépendamment du DAX, pour chaque cas ; les résultats sont dans `tests/expected/*.json`.

| Cas | Filtre | Ce qu'il vérifie |
|---|---|---|
| 2025 total | Année 2025 | Valeurs de référence de la démo |
| 2024 total | Année 2024 | Mesures N-1 vides, pont vide, textes en mode « pas d'exercice précédent » |
| 2025 région Sud | Année 2025, Région Sud | Filtre de dimension conforme ; mêmes chiffres que le rôle RLS de Damien Revol |
| 2025 famille Visserie et fixations | Année 2025, Famille Visserie et fixations | Hausse des coûts d'achat |
| Février 2025 | Année 2025, Numéro mois 2 | Comparaison avec février 2024, mois de 29 jours |

S'y ajoutent, pour le cas 2025 total, les valeurs par catégorie de chaque graphique : par mois (CA net, CA net N-1, CA net budget), par famille, par région et par segment (écart N-1), par famille (écart au budget, écart de taux de marge), par commercial (écart de taux de remise).

Tolérances : 1 € sur les montants, 0,05 point sur les taux, égalité exacte sur les nombres entiers et sur les textes après normalisation des espaces.

### Contrôles automatiques (`make check`, et CI sur ubuntu-latest en Python 3.12 et 3.14)

| Contrôle | Outil |
|---|---|
| Style et qualité du code Python | ruff (lint et format) |
| Clés uniques dans chaque table ; aucune clé étrangère orpheline | pytest |
| Montants cohérents : net = brut - remise au centime, remise entre 0 et 40 % du brut, coûts strictement positifs, transport positif ou nul et identique pour toute la commande | pytest |
| Dates comprises entre le 1er janvier 2024 et le 31 décembre 2025, jours ouvrés uniquement | pytest |
| Cohérence des clés redondantes : région et commercial de la ligne = ceux du client, famille de la ligne = celle du produit | pytest |
| Histoire présente : Rhône-Alpes en plus forte hausse et Nord-Est en recul ; Équipements de protection en tête et Outillage à main en recul ; coût unitaire de la visserie en hausse d'au moins 8 % à référence égale ; taux de remise de Damien Revol en hausse d'au moins 5 points, celui des autres stable à ±1,5 point ; au moins 8 clients à marge contributive négative et 5 produits sous le coût en 2025 ; août est le mois le plus faible chaque année | pytest |
| Régénération identique : le générateur relancé dans un dossier temporaire produit des fichiers identiques à ceux de `data/` | pytest |
| Valeurs attendues à jour : `tests/expected/*.json` et `tests/validation.dax` identiques à ce que produisent les scripts | pytest |
| Bouclage du pont à moins d'un centime sur trois cas : total 2025, région Sud 2025, famille Visserie et fixations 2025 ; identité clients × fréquence × panier | pytest |
| Chaque fichier JSON du projet (pbip, pbir, pbism, report, pages, visuels, thème) valide contre son `$schema`, schémas en cache dans `tools/schemas/` pour fonctionner hors ligne | jsonschema |
| Liaisons : chaque table, colonne et mesure citée par un visuel existe dans le TMDL | script |
| Règles de modèle : aucune relation bidirectionnelle, date/heure automatique désactivée, description, format et dossier sur chaque mesure, format sur chaque colonne visible, clés masquées | script |
| Mise en page : visuels dans le canevas, coordonnées multiples de 8, aucun chevauchement, mêmes zones sur les deux pages | script |
| Textes : aucun tiret cadratin dans les fichiers du dépôt | script |

### Requête de validation dans Desktop

`tests/validation.dax` est généré depuis `tests/expected/*.json` par `scripts/build_validation_dax.py`. C'est une seule requête à coller dans la vue Requête DAX :

- les valeurs attendues sont embarquées dans la requête (`DATATABLE`, un bloc pour les nombres, un pour les textes) ;
- chaque mesure est recalculée par le modèle pour chaque cas ;
- un premier résultat donne le nombre de contrôles et le nombre de KO ;
- un second résultat liste une ligne par cas et par mesure, avec les colonnes Cas, Mesure, Attendu, Obtenu, Écart, Statut (OK ou KO), lignes KO en premier.

### Contrôles dans Power BI Desktop

La procédure pas à pas est dans `docs/test-windows.md` : mise à jour de Desktop, ouverture et actualisation, requête de validation (« 0 KO » attendu), parcours des deux pages, test des deux comptes RLS, enregistrement et commit. Points qui ne se vérifient que dans Desktop : rendu des visuels, lisibilité des titres longs, libellé « Total » et couleur de la première barre de la cascade, comportement des segments synchronisés, RLS.

## Annexe : contrat de mise en page

Version structurée de la section 5, qui sert de référence à la construction des pages en phase 4. En cas de divergence entre les deux, la section 5 est corrigée avant toute implémentation.

```yaml
Design Brief:
  contract_version: 1
  mode: greenfield
  design_identity:
    tone: "Sobre et financier : fond neutre, une seule couleur d'accent, rouge réservé au défavorable"
    signature: "Titres rédigés comme des réponses, calculés en DAX, et bande de KPI qui décompose la performance"
  archetype: Executive Summary
  navigation_model: none
  color_map:
    - measure: "Mesures[CA net]"
      color: "#1F4E79"
      tint: "#C9D8E8"
    - measure: "Mesures[CA net N-1]"
      color: "#8A8886"
    - measure: "Mesures[CA net budget]"
      color: "#252423"
    - measure: "Mesures[Marge commerciale]"
      color: "#1F4E79"
      tint: "#C9D8E8"
  pages:
    - name: "Vue Direction"
      role: landing
      archetype: Executive
      layout_variant: B
      variant_rationale: "Cinq KPI de même importance qui décomposent le CA, sans indicateur héros unique, puis quatre visuels d'explication."
      navigation: []
      page_background: "#F3F2F1"
      layout_summary: "Titre et synthèse dynamiques, segments à droite, bande de cinq KPI, tendance mensuelle et contributions par famille, puis trois analyses d'écart."
      layout_contract:
        canvas: { width: 1280, height: 720, margin: 24, margin_vertical: 32, gutter: 16, snap: 8 }
        grid:
          columns: 12
          rows: 12
          regions:
            titre: [1, 1, 10, 2]
            synthese: [1, 2, 10, 3]
            filtres: [10, 1, 13, 3]
            kpis: [1, 3, 13, 5]
            principal: [1, 5, 8, 9]
            secondaire: [8, 5, 13, 9]
            bas_gauche: [1, 9, 5, 13]
            bas_centre: [5, 9, 9, 13]
            bas_droite: [9, 9, 13, 13]
        placements:
          - id: page_title
            region: titre
            kind: cardVisual
            text: "[Titre Direction]"
            purpose: "Dire si le CA progresse et où il se situe par rapport au budget."
          - id: synthese
            region: synthese
            kind: cardVisual
            text: "[Synthèse Direction]"
            insight_basis: "Meilleures contributions à l'écart N-1 et décomposition clients, fréquence, panier."
          - id: annee
            region: filtres
            kind: slicer
            field_bindings: "Date[Année]"
            slicer_type: horizontal_list
            position_px: { x: 960, y: 32, width: 120, height: 96 }
          - id: region
            region: filtres
            kind: slicer
            field_bindings: "Région[Région]"
            slicer_type: dropdown
            position_px: { x: 1096, y: 32, width: 160, height: 96 }
          - id: kpi
            region: kpis
            kind: cardVisual
            purpose: "La croissance vient-elle de plus de clients, de commandes plus fréquentes ou de paniers plus gros ?"
            field_bindings: ["Mesures[CA net]", "Mesures[CA net écart budget (%)]", "Mesures[# Clients actifs]", "Mesures[Commandes par client]", "Mesures[Panier moyen]", "Mesures[CA net évol. N-1 (%)]", "Mesures[CA net budget]", "Mesures[# Clients actifs évol. N-1 (%)]", "Mesures[Commandes par client évol. N-1 (%)]", "Mesures[Panier moyen évol. N-1 (%)]"]
            comparison_basis: "N-1 pour quatre cartes, budget pour la deuxième"
            color_strategy: measure_match
          - id: tendance
            region: principal
            kind: lineChart
            purpose: "Quand la croissance se produit-elle, et suit-elle le budget ?"
            field_bindings: { Category: "Date[Mois]", Y: ["Mesures[CA net]", "Mesures[CA net N-1]", "Mesures[CA net budget]"] }
            color_strategy: measure_match
          - id: ecart_famille
            region: secondaire
            kind: clusteredBarChart
            purpose: "Quelles familles apportent la croissance ?"
            field_bindings: { Category: "Famille[Famille]", X: "Mesures[CA net écart N-1]" }
            sort_policy: value_desc
            color_strategy: semantic
          - id: ecart_region
            region: bas_gauche
            kind: clusteredBarChart
            purpose: "Quelles régions apportent la croissance ?"
            field_bindings: { Category: "Région[Région]", X: "Mesures[CA net écart N-1]" }
            sort_policy: value_desc
            color_strategy: semantic
          - id: ecart_segment
            region: bas_centre
            kind: clusteredBarChart
            purpose: "Quels types de clients apportent la croissance ?"
            field_bindings: { Category: "Client[Segment]", X: "Mesures[CA net écart N-1]" }
            sort_policy: value_desc
            color_strategy: semantic
          - id: ecart_budget
            region: bas_droite
            kind: clusteredBarChart
            purpose: "Quelles familles tiennent leur budget ?"
            field_bindings: { Category: "Famille[Famille]", X: "Mesures[CA net écart budget]" }
            sort_policy: value_desc
            color_strategy: semantic
            comparison_basis: "Budget"
        space_audit:
          content_cell_count: 120
          placed_cell_count: 120
          empty_cell_pct: 0
          unplaced_regions: []
          largest_region: { name: principal, pct_of_content: 23 }
          balance_rationale: "La bande de KPI pose la décomposition, la tendance occupe la plus grande zone, les trois analyses d'écart se partagent la dernière rangée à parts égales."
    - name: "Marge"
      role: detail
      archetype: Executive
      layout_variant: B
      variant_rationale: "Même grille que la Vue Direction pour une lecture identique ; le pont de marge prend la zone principale."
      navigation: []
      page_background: "#F3F2F1"
      layout_summary: "Titre et synthèse dynamiques, bande de cinq KPI de marge, pont N-1 vers N et remises par commercial, puis marge par famille et listes des clients et produits déficitaires."
      layout_contract:
        canvas: { width: 1280, height: 720, margin: 24, margin_vertical: 32, gutter: 16, snap: 8 }
        grid:
          columns: 12
          rows: 12
          regions:
            titre: [1, 1, 10, 2]
            synthese: [1, 2, 10, 3]
            filtres: [10, 1, 13, 3]
            kpis: [1, 3, 13, 5]
            principal: [1, 5, 8, 9]
            secondaire: [8, 5, 13, 9]
            bas_gauche: [1, 9, 5, 13]
            bas_centre: [5, 9, 9, 13]
            bas_droite: [9, 9, 13, 13]
        placements:
          - id: page_title
            region: titre
            kind: cardVisual
            text: "[Titre Marge]"
            purpose: "Dire si la marge suit le CA et quel est son taux."
          - id: synthese
            region: synthese
            kind: cardVisual
            text: "[Synthèse Marge]"
            insight_basis: "Effet le plus défavorable du pont, écart au budget de marge, nombre de clients et de produits déficitaires."
          - id: annee
            region: filtres
            kind: slicer
            field_bindings: "Date[Année]"
            slicer_type: horizontal_list
            position_px: { x: 960, y: 32, width: 120, height: 96 }
          - id: region
            region: filtres
            kind: slicer
            field_bindings: "Région[Région]"
            slicer_type: dropdown
            position_px: { x: 1096, y: 32, width: 160, height: 96 }
          - id: kpi
            region: kpis
            kind: cardVisual
            purpose: "Où se situe la perte : prix, remises, coûts, transport ?"
            field_bindings: ["Mesures[Marge commerciale]", "Mesures[Marge commerciale (% CA)]", "Mesures[Taux de remise (%)]", "Mesures[Transport (% CA)]", "Mesures[Marge contributive]", "Mesures[Marge commerciale évol. N-1 (%)]", "Mesures[Marge commerciale écart N-1 (pts)]", "Mesures[Taux de remise écart N-1 (pts)]", "Mesures[Transport écart N-1 (pts)]", "Mesures[Marge contributive évol. N-1 (%)]"]
            comparison_basis: "N-1"
            color_strategy: measure_match
          - id: pont
            region: principal
            kind: waterfallChart
            purpose: "Pourquoi la marge a-t-elle changé depuis N-1 ?"
            field_bindings: { Category: "Étape du pont[Étape]", Y: "Mesures[Pont de marge]" }
            sort_policy: category_asc
            sort_column: "Étape du pont[Ordre]"
            color_strategy: semantic
          - id: remises_commercial
            region: secondaire
            kind: clusteredBarChart
            purpose: "Qui accorde plus de remises qu'avant ?"
            field_bindings: { Category: "Commercial[Commercial]", X: "Mesures[Taux de remise écart N-1 (pts)]" }
            sort_policy: value_desc
            color_strategy: semantic
          - id: marge_famille
            region: bas_gauche
            kind: clusteredBarChart
            purpose: "Quelle famille perd du taux de marge ?"
            field_bindings: { Category: "Famille[Famille]", X: "Mesures[Marge commerciale écart N-1 (pts)]" }
            sort_policy: value_asc
            color_strategy: semantic
          - id: clients_deficitaires
            region: bas_centre
            kind: tableEx
            purpose: "Quels clients coûtent plus qu'ils ne rapportent ?"
            field_bindings: ["Client[Client]", "Mesures[CA net]", "Mesures[Marge contributive]", "Mesures[Marge contributive (% CA)]"]
            sort_policy: value_asc
            insight_basis: "Filtre de visuel : marge contributive négative"
          - id: produits_deficitaires
            region: bas_droite
            kind: tableEx
            purpose: "Quels produits sont vendus à perte ?"
            field_bindings: ["Produit[Produit]", "Mesures[CA net]", "Mesures[Marge commerciale]", "Mesures[Marge commerciale (% CA)]"]
            sort_policy: value_asc
            insight_basis: "Filtre de visuel : marge commerciale négative"
        space_audit:
          content_cell_count: 120
          placed_cell_count: 120
          empty_cell_pct: 0
          unplaced_regions: []
          largest_region: { name: principal, pct_of_content: 23 }
          balance_rationale: "Le pont de marge est la preuve principale ; les remises par commercial l'expliquent à côté ; la dernière rangée descend au détail, famille puis clients puis produits."
  interaction_pattern:
    drill_targets: []
    cross_filter_rules: "Filtrer entre visuels de données ; cascade : aucune interaction sortante ; segments clients vers écart au budget : aucune"
  accessibility:
    alt_text_strategy: "Même mesure texte que le titre du visuel"
    contrast_notes: "Accent 8,66:1, alerte 6,57:1, gris N-1 3,53:1 sur blanc ; la couleur double toujours le signe de la valeur"
  theme:
    base: "Thème personnalisé Arvenor sobre (section 5)"
    user_overrides: "Aucun"
```
