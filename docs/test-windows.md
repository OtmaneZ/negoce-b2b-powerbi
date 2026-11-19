# Test dans Power BI Desktop (Windows)

Six étapes, à suivre dans l'ordre. Pour chacune : ce qui doit s'afficher, et ce qu'il faut relever si ce n'est pas le cas. Toutes les valeurs attendues ci-dessous sont calculées par `scripts/expected_values.py` ; elles portent sur l'exercice 2025, sans autre filtre, sauf mention contraire.

## 1. Cloner le dépôt et mettre Power BI Desktop à jour

1. Cloner le dépôt avec GitHub Desktop, par exemple dans `C:\Users\<nom>\Documents\GitHub\negoce-b2b-powerbi`.
2. Installer la dernière version de Power BI Desktop (Microsoft Store ou centre de téléchargement Microsoft). Le projet utilise les versions de schémas PBIR les plus récentes publiées par Microsoft (liste dans le README) : une version ancienne de Desktop refuse de les ouvrir.
3. Si Desktop propose des fonctionnalités en préversion liées aux projets (format PBIP, rapport PBIR, modèle TMDL), les activer dans Fichier > Options et paramètres > Options > Fonctionnalités en préversion, puis redémarrer Desktop.

**Résultat attendu** : le dossier cloné contient `NegoceB2B.pbip`, `NegoceB2B.Report`, `NegoceB2B.SemanticModel` et `data`.

**À relever sinon** : le numéro de version de Desktop (Aide > À propos).

## 2. Ouvrir le projet, renseigner DossierDonnees, actualiser

1. Ouvrir `NegoceB2B.pbip` (double-clic ou Fichier > Ouvrir).
2. Accueil > Transformer les données > Modifier les paramètres : renseigner `DossierDonnees` avec le chemin complet du dossier `data` du clone, **terminé par une barre oblique inverse**, par exemple `C:\Users\<nom>\Documents\GitHub\negoce-b2b-powerbi\data\`.
3. Appliquer les modifications, puis Accueil > Actualiser.

**Résultat attendu** : l'ouverture et l'actualisation se terminent sans message d'erreur. Dans la vue Tableau, le nombre de lignes affiché en bas de l'écran pour chaque table est :

| Table | Lignes |
|---|---|
| Ventes | 63 500 |
| Budget | 720 |
| Client | 900 |
| Produit | 600 |
| Commercial | 10 |
| Famille | 6 |
| Région | 5 |
| Accès régional | 15 |
| Date | 731 |
| Étape du pont | 5 |
| Statut client | 3 |

**À relever sinon** : le texte exact du message d'erreur (ou une capture), l'étape où il apparaît (ouverture, paramètre, actualisation) et la table concernée.

## 3. Exécuter la requête de validation

1. Ouvrir `tests/validation.dax` dans le Bloc-notes, tout sélectionner, copier.
2. Dans Desktop, vue Requête DAX : coller la requête, puis Exécuter.

**Résultat attendu** : deux résultats.

- Le premier affiche **Contrôles = 580** et **KO = 0**.
- Le second détaille chaque contrôle (colonnes Cas, Mesure, Attendu, Obtenu, Écart, Statut), lignes KO en premier.

**À relever sinon** : si la requête échoue, le message d'erreur complet ; si KO est supérieur à 0, toutes les lignes KO du second résultat (bouton de copie du tableau de résultats).

## 4. Parcourir les deux pages

Sur chaque page, le segment Année est sur 2025 et le segment Région sur « Tout ».

**Résultat attendu, page Vue Direction** :

- Titre : « En 2025, le CA net progresse de 8,3 % sur un an et dépasse le budget de 0,9 % ».
- Synthèse : « Plus faible contribution : famille Outillage à main (-125 k€), région Nord-Est (-215 k€). 63 nouveaux clients, 45 clients perdus. Données fictives. »
- Bande de cinq KPI, chacun sur deux lignes : libellé et valeur en haut (« CA net », « 22,6 M€ »), évolution juste en dessous (« +8,3 % sur un an », « +0,9 % vs budget ») ; libellés et valeurs entiers, sans « … ».
- Courbe mensuelle titrée « CA net mensuel : au-dessus de 2024 sur 10 mois sur 12 », avec trois séries (2025 en bleu épais, 2024 en gris, budget en pointillés fins) et un axe en millions.
- Quatre graphiques en barres : barres bleues pour les hausses, rouges pour les baisses ; titres sur une ligne ; noms de famille entiers, sans « … ». Le graphique du bas au centre est titré « Par statut : clients existants en tête (+1 617 k€) » et montre, dans cet ordre, Clients existants, Nouveaux clients et Clients perdus.

**Résultat attendu, page Marge** :

- Titre : « En 2025, la marge commerciale progresse de 2,6 % et représente 31,4 % du CA net (-1,7 pts) ».
- Synthèse : « Sur un an : CA net +1 727 k€, marge commerciale +181 k€ (10,5 % du CA supplémentaire). Marge commerciale 4,0 % sous le budget. Données fictives. »
- Graphique en cascade titré « Pont de marge 2024 → 2025 : l'effet coût d'achat pèse le plus (-504 k€) », dans l'ordre Volume, Mix, Prix catalogue, Remises, Coût d'achat, puis la barre de total (+181 k€, l'écart de marge sur un an).
- Barres des commerciaux titrées « Damien Revol : taux de remise de 10,9 % à 19,2 % (+8,3 pts) » : la barre de Damien Revol est rouge, les neuf autres, inférieures à un point, sont grises.
- Tableau titré « Clients en plus fort recul de marge contributive » : six clients avec leur commercial, de Falarin Hydraulique (-19 119 €) à Duretec Énergie (-12 525 €) ; les deux premiers, chez Damien Revol, ont un écart de remise de plus de 25 points.
- Tableau titré « 8 produits vendus à perte (-40 k€) : les 6 plus lourds » : six produits, de Pince universelle 180 mm (-7 588 €) à Niveau à bulle 80 cm (-3 766 €).
- Aucun des deux tableaux n'a de barre de défilement ni de ligne de total.

**Points à observer en particulier** : libellé de la barre de total de la cascade (« Total » par défaut) ; titres et synthèses affichés en entier, sans coupure ; volet Filtres signalé comme masqué en lecture (icône en forme d'œil barré à côté de son titre) ; aucun visuel en erreur.

**À relever sinon** : une capture de chaque page et, pour chaque visuel en erreur, le message affiché par « Afficher les détails ».

## 5. Tester les deux comptes RLS

Modélisation > Afficher en tant que : cocher **Autre utilisateur**, saisir l'adresse, cocher le rôle **Commercial**, puis OK.

| Adresse | Résultat attendu |
|---|---|
| `damien.revol@example.com` | Le segment Région ne propose que Sud. Titre de la Vue Direction : « En 2025, le CA net progresse de 9,9 % sur un an et dépasse le budget de 2,2 % ». |
| `direction.commerciale@example.com` | Les cinq régions sont visibles. Titre de la Vue Direction identique à celui de l'étape 4. |

Revenir ensuite à l'affichage normal (Arrêter l'affichage).

**À relever sinon** : pour chaque adresse, une capture de la page Vue Direction.

## 6. Enregistrer et faire un commit

1. Fichier > Enregistrer.
2. Dans GitHub Desktop, relire la liste des fichiers modifiés, puis faire un commit (par exemple « Enregistrement du projet dans Power BI Desktop »).

**Résultat attendu** : seuls des fichiers de `NegoceB2B.Report` et de `NegoceB2B.SemanticModel` sont modifiés (Desktop peut, par exemple, ajouter des identifiants `lineageTag` au modèle ou réécrire la mise en forme des fichiers). Aucun fichier de `data` ni de `tests` n'est modifié. Les fichiers `.pbi/localSettings.json` et `cache.abf` n'apparaissent pas : ils sont exclus par `.gitignore`.

**À relever sinon** : la liste des fichiers modifiés affichée par GitHub Desktop.
