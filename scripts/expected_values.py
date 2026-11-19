"""Calcule en pandas, indépendamment du DAX, la valeur attendue de chaque mesure.

Usage : python scripts/expected_values.py

Les calculs reproduisent la sémantique des mesures DAX du modèle : une agrégation
sur aucune ligne vaut « vide » (None ici), DIVIDE renvoie vide si le dénominateur
est vide ou nul, une soustraction de deux vides reste vide. Les textes appliquent
les mêmes règles d'arrondi et de format fr-FR que la fonction FORMAT du DAX.

Résultats : un fichier JSON par cas de validation dans tests/expected/.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, replace
from decimal import ROUND_HALF_UP, Decimal
from functools import cache
from pathlib import Path

import pandas as pd

RACINE = Path(__file__).resolve().parent.parent
DOSSIER_DONNEES = RACINE / "data"
DOSSIER_ATTENDUS = RACINE / "tests" / "expected"

TOLERANCES = {
    "montant": 1.0,
    "taux": 0.0005,
    "points": 0.05,
    "nombre": 0.0,
    "ratio": 0.01,
    "bouclage": 0.01,
    "texte": None,
}

# ---------------------------------------------------------------------------
# Format fr-FR, à l'image de FORMAT(valeur, format, "fr-FR") en DAX
# ---------------------------------------------------------------------------


def _arrondir(valeur: float, decimales: int, facteur: int = 1) -> Decimal:
    """Arrondi au plus proche, demi s'éloignant de zéro."""
    nombre = Decimal(repr(abs(valeur))) * facteur
    return nombre.quantize(Decimal(1).scaleb(-decimales), rounding=ROUND_HALF_UP)


def _chiffres(nombre: Decimal, decimales: int, separateur_milliers: bool) -> str:
    texte = f"{nombre:.{decimales}f}"
    entier, _, fraction = texte.partition(".")
    if separateur_milliers:
        groupes = []
        while len(entier) > 3:
            groupes.insert(0, entier[-3:])
            entier = entier[:-3]
        groupes.insert(0, entier)
        entier = " ".join(groupes)
    return entier + ("," + fraction if decimales else "")


def format_fr(valeur: float, format_dax: str) -> str:
    """Reproduit FORMAT(valeur, format_dax, "fr-FR") pour les formats à une section.

    Formats pris en charge : "0.0 %", "0.0", "#,0", "#,0.0". Les textes n'utilisent
    jamais de format à plusieurs sections : le signe est ajouté explicitement.
    """
    pourcentage = format_dax.endswith(" %")
    motif = format_dax.removesuffix(" %")
    milliers = motif.startswith("#,")
    decimales = len(motif.split(".")[1]) if "." in motif else 0
    nombre = _arrondir(valeur, decimales, 100 if pourcentage else 1)
    signe = "-" if valeur < 0 and nombre != 0 else ""
    return signe + _chiffres(nombre, decimales, milliers) + (" %" if pourcentage else "")


def signe(valeur) -> str:
    """IF(valeur < 0, "-", "+") : une valeur vide n'est pas négative."""
    return "-" if valeur is not None and valeur < 0 else "+"


def _format_absolu(valeur, format_dax: str, diviseur: int = 1) -> str:
    """FORMAT(ABS(valeur) / diviseur, format_dax, "fr-FR") ; vide pour une valeur vide."""
    return "" if valeur is None else format_fr(abs(valeur) / diviseur, format_dax)


def pct(valeur) -> str:
    """FORMAT(valeur, "0.0 %", "fr-FR")."""
    return "" if valeur is None else format_fr(valeur, "0.0 %")


def pct_signe(valeur) -> str:
    """Pourcentage signé : signe explicite puis FORMAT(ABS(valeur), "0.0 %")."""
    return signe(valeur) + _format_absolu(valeur, "0.0 %")


def milliers(valeur) -> str:
    """Milliers d'euros signés : signe explicite puis FORMAT(ABS(valeur) / 1000, "#,0")."""
    return signe(valeur) + _format_absolu(valeur, "#,0", 1000) + " k€"


def millions(valeur) -> str:
    """FORMAT(valeur / 1000000, "#,0.0") suivi de « M€ »."""
    return ("" if valeur is None else format_fr(valeur / 1000000, "#,0.0")) + " M€"


def points(valeur) -> str:
    """Points signés : signe explicite puis FORMAT(ABS(valeur), "0.0")."""
    return signe(valeur) + _format_absolu(valeur, "0.0") + " pts"


def normaliser_espaces(texte: str) -> str:
    """Ramène les espaces insécables (U+00A0, U+202F) à une espace simple."""
    return texte.replace("\u00a0", " ").replace("\u202f", " ")


# ---------------------------------------------------------------------------
# Opérations avec la sémantique du vide (BLANK) du DAX
# ---------------------------------------------------------------------------


def moins(a, b):
    if a is None and b is None:
        return None
    return (a or 0) - (b or 0)


def diviser(a, b):
    if a is None or b is None or b == 0:
        return None
    return a / b


def ecart(n, n1):
    """Modèle « écart » : vide si N-1 est vide."""
    return None if n1 is None else moins(n, n1)


def evolution(n, n1):
    """Modèle « évol. » : DIVIDE(N - N-1, N-1)."""
    return diviser(moins(n, n1), n1)


def ecart_points(taux_n, taux_n1):
    """ROUND((taux N - taux N-1) * 100, 1) : arrondi au dixième, demi s'éloignant de zéro."""
    if taux_n is None or taux_n1 is None:
        return None
    valeur = Decimal(repr((taux_n - taux_n1) * 100))
    return float(valeur.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)) + 0.0


# ---------------------------------------------------------------------------
# Données et contexte de filtre
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Contexte:
    """Filtres d'un cas de validation, équivalents aux filtres DAX."""

    annee: int | None = None
    mois: int | None = None
    region: str | None = None
    famille: str | None = None
    segment: str | None = None
    commercial: str | None = None
    client: str | None = None
    produit: str | None = None
    etape: int | None = None
    statut: int | None = None

    def avec(self, **filtres) -> Contexte:
        return replace(self, **filtres)

    def precedent(self) -> Contexte:
        return replace(self, annee=self.annee - 1)


ETAPES = {
    1: "Volume",
    2: "Mix",
    3: "Prix catalogue",
    4: "Remises",
    5: "Coût d'achat",
}
STATUTS = {
    1: "Clients existants",
    2: "Nouveaux clients",
    3: "Clients perdus",
}
CARTES_VALEURS = (
    ("Carte CA net", "CA net", lambda v: millions(v)),
    ("Carte budget CA net", "CA net budget", lambda v: millions(v)),
    ("Carte clients actifs", "# Clients actifs", lambda v: format_fr(v, "#,0")),
    ("Carte commandes par client", "Commandes par client", lambda v: format_fr(v, "0.0")),
    ("Carte panier moyen", "Panier moyen", lambda v: format_fr(v, "#,0") + " €"),
    ("Carte marge commerciale", "Marge commerciale", lambda v: millions(v)),
    ("Carte taux de marge", "Marge commerciale (% CA)", lambda v: pct(v)),
    ("Carte taux de remise", "Taux de remise (%)", lambda v: pct(v)),
    ("Carte transport", "Transport (% CA)", lambda v: pct(v)),
    ("Carte marge contributive", "Marge contributive", lambda v: millions(v)),
)
CARTES_EVOLUTIONS = (
    ("Carte CA net évol.", "CA net évol. N-1 (%)", " sur un an"),
    ("Carte budget CA net écart", "CA net écart budget (%)", " vs budget"),
    ("Carte clients actifs évol.", "# Clients actifs évol. N-1 (%)", " sur un an"),
    ("Carte commandes par client évol.", "Commandes par client évol. N-1 (%)", " sur un an"),
    ("Carte panier moyen évol.", "Panier moyen évol. N-1 (%)", " sur un an"),
    ("Carte marge commerciale évol.", "Marge commerciale évol. N-1 (%)", " sur un an"),
    ("Carte taux de marge écart", "Marge commerciale écart N-1 (pts)", " pts sur un an"),
    ("Carte taux de remise écart", "Taux de remise écart N-1 (pts)", " pts sur un an"),
    ("Carte transport écart", "Transport écart N-1 (pts)", " pts sur un an"),
    ("Carte marge contributive évol.", "Marge contributive évol. N-1 (%)", " sur un an"),
)
LIGNES_TABLEAUX = 6  # lignes affichées par les tableaux de la page Marge
EFFETS = (
    ("volume", "Effet volume"),
    ("mix", "Effet mix"),
    ("prix catalogue", "Effet prix catalogue"),
    ("remises", "Effet remises"),
    ("coût d'achat", "Effet coût d'achat"),
)


def _centimes(serie: pd.Series) -> pd.Series:
    return (pd.to_numeric(serie) * 100).round().astype("int64")


class Moteur:
    """Calcule les mesures du modèle pour un contexte donné."""

    def __init__(self, dossier: Path = DOSSIER_DONNEES) -> None:
        ventes = pd.read_csv(dossier / "ventes.csv")
        clients = pd.read_csv(dossier / "clients.csv")
        produits = pd.read_csv(dossier / "produits.csv")
        commerciaux = pd.read_csv(dossier / "commerciaux.csv")
        regions = pd.read_csv(dossier / "regions.csv")
        familles = pd.read_csv(dossier / "familles.csv")
        budget = pd.read_csv(dossier / "budget.csv")

        dates = pd.to_datetime(ventes["date_commande"])
        self.ventes = pd.DataFrame(
            {
                "commande": ventes["numero_commande"],
                "annee": dates.dt.year,
                "mois": dates.dt.month,
                "client": ventes["cle_client"],
                "produit": ventes["cle_produit"],
                "nom_client": ventes["cle_client"].map(clients.set_index("cle_client")["client"]),
                "nom_produit": ventes["cle_produit"].map(
                    produits.set_index("cle_produit")["produit"]
                ),
                "region": ventes["cle_region"].map(regions.set_index("cle_region")["region"]),
                "famille": ventes["cle_famille"].map(familles.set_index("cle_famille")["famille"]),
                "segment": ventes["cle_client"].map(clients.set_index("cle_client")["segment"]),
                "commercial": ventes["cle_commercial"].map(
                    commerciaux.set_index("cle_commercial")["commercial"]
                ),
                "quantite": ventes["quantite"],
                "brut": _centimes(ventes["montant_brut"]),
                "remise": _centimes(ventes["montant_remise"]),
                "net": _centimes(ventes["montant_net"]),
                "cout": _centimes(ventes["cout_achat"]),
                "transport": _centimes(ventes["cout_transport"]),
            }
        )
        mois_budget = pd.to_datetime(budget["mois"])
        self.budget = pd.DataFrame(
            {
                "annee": mois_budget.dt.year,
                "mois": mois_budget.dt.month,
                "region": budget["cle_region"].map(regions.set_index("cle_region")["region"]),
                "famille": budget["cle_famille"].map(familles.set_index("cle_famille")["famille"]),
                "ca": _centimes(budget["budget_ca_net"]),
                "marge": _centimes(budget["budget_marge_commerciale"]),
            }
        )
        self.familles = sorted(familles["famille"])
        self.regions = sorted(regions["region"])
        self.segments = sorted(clients["segment"].unique())
        self.commerciaux = sorted(commerciaux["commercial"])
        self.cles_clients = clients["cle_client"]
        self.segment_client = clients.set_index("cle_client")["segment"]

    # --- sélection des lignes -------------------------------------------------

    @cache  # noqa: B019 (le moteur vit le temps du script)
    def lignes(self, ctx: Contexte) -> pd.DataFrame:
        v = self.ventes
        masque = pd.Series(True, index=v.index)
        colonnes = {
            "annee": "annee",
            "mois": "mois",
            "region": "region",
            "famille": "famille",
            "segment": "segment",
            "commercial": "commercial",
            "client": "nom_client",
            "produit": "nom_produit",
        }
        for attribut, colonne in colonnes.items():
            valeur = getattr(ctx, attribut)
            if valeur is not None:
                masque &= v[colonne] == valeur
        return v[masque]

    @cache  # noqa: B019
    def agregats(self, ctx: Contexte) -> dict:
        lignes = self.lignes(ctx)
        if lignes.empty:
            return dict.fromkeys(
                ("brut", "remise", "net", "cout", "transport", "quantite", "commandes", "clients")
            )
        return {
            "brut": int(lignes["brut"].sum()) / 100,
            "remise": int(lignes["remise"].sum()) / 100,
            "net": int(lignes["net"].sum()) / 100,
            "cout": int(lignes["cout"].sum()) / 100,
            "transport": int(lignes["transport"].sum()) / 100,
            "quantite": int(lignes["quantite"].sum()),
            "commandes": int(lignes["commande"].nunique()),
            "clients": int(lignes["client"].nunique()),
        }

    @cache  # noqa: B019
    def par_produit(self, ctx: Contexte) -> pd.DataFrame:
        lignes = self.lignes(ctx)
        table = lignes.groupby("produit")[["quantite", "brut", "remise", "net", "cout"]].sum()
        for colonne in ("brut", "remise", "net", "cout"):
            table[colonne] = table[colonne] / 100
        return table

    # --- mesures de base --------------------------------------------------------

    @cache  # noqa: B019
    def base(self, ctx: Contexte) -> dict:
        a = self.agregats(ctx)
        m = {
            "CA brut": a["brut"],
            "Remises": a["remise"],
            "CA net": a["net"],
            "Quantité": a["quantite"],
            "# Commandes": a["commandes"],
            "# Clients actifs": a["clients"],
            "Coût d'achat": a["cout"],
            "Transport": a["transport"],
        }
        m["Taux de remise (%)"] = diviser(m["Remises"], m["CA brut"])
        m["Commandes par client"] = diviser(m["# Commandes"], m["# Clients actifs"])
        m["Panier moyen"] = diviser(m["CA net"], m["# Commandes"])
        m["Marge commerciale"] = moins(m["CA net"], m["Coût d'achat"])
        m["Marge commerciale (% CA)"] = diviser(m["Marge commerciale"], m["CA net"])
        m["Transport (% CA)"] = diviser(m["Transport"], m["CA net"])
        m["Marge contributive"] = moins(m["Marge commerciale"], m["Transport"])
        m["Marge contributive (% CA)"] = diviser(m["Marge contributive"], m["CA net"])
        return m

    def budget_ca_marge(self, ctx: Contexte) -> tuple[float | None, float | None]:
        """Garde du modèle : vide si un filtre porte sur Client, Produit ou Commercial."""
        hors_budget = (ctx.segment, ctx.commercial, ctx.client, ctx.produit)
        if any(filtre is not None for filtre in hors_budget):
            return None, None
        b = self.budget
        masque = pd.Series(True, index=b.index)
        for colonne in ("annee", "mois", "region", "famille"):
            valeur = getattr(ctx, colonne)
            if valeur is not None:
                masque &= b[colonne] == valeur
        lignes = b[masque]
        if lignes.empty:
            return None, None
        return int(lignes["ca"].sum()) / 100, int(lignes["marge"].sum()) / 100

    def compter_negatifs(self, ctx: Contexte, cle: str, mesure: str) -> int | None:
        """COUNTROWS(FILTER(VALUES(...), [mesure] < 0)) : vide si aucun membre."""
        lignes = self.lignes(ctx)
        if lignes.empty:
            return None
        marge = lignes["net"] - lignes["cout"]
        if mesure == "contributive":
            marge = marge - lignes["transport"]
        valeurs = marge.groupby(lignes[cle]).sum()
        nombre = int((valeurs < 0).sum())
        return nombre or None

    def ecart_par_statut(self, ctx: Contexte):
        """CA net écart N-1 par statut : existants, nouveaux, perdus ; écart total sans statut."""
        if self.base(ctx.precedent())["CA net"] is None:
            return None
        if ctx.statut is None:
            return ecart(self.base(ctx)["CA net"], self.base(ctx.precedent())["CA net"])
        n = self.lignes(ctx.avec(statut=None)).groupby("client")["net"].sum()
        n1 = self.lignes(ctx.avec(statut=None).precedent()).groupby("client")["net"].sum()
        if ctx.statut == 1:
            communs = n.index.intersection(n1.index)
            valeur = None if communs.empty else int((n[communs] - n1[communs]).sum())
        elif ctx.statut == 2:
            nouveaux = n.index.difference(n1.index)
            valeur = None if nouveaux.empty else int(n[nouveaux].sum())
        else:
            perdus = n1.index.difference(n.index)
            valeur = None if perdus.empty else -int(n1[perdus].sum())
        return None if valeur is None else valeur / 100

    def compter_statut(self, ctx: Contexte, nouveaux: bool) -> int | None:
        """# Nouveaux clients ou # Clients perdus : vide sans N-1 ou si aucun client."""
        if self.base(ctx.precedent())["CA net"] is None:
            return None
        n = set(self.lignes(ctx)["client"])
        n1 = set(self.lignes(ctx.precedent())["client"])
        nombre = len(n - n1) if nouveaux else len(n1 - n)
        return nombre or None

    @cache  # noqa: B019
    def marges_contributives(self, ctx: Contexte) -> pd.Series:
        """Marge contributive par nom de client, en euros, pour les clients ayant des ventes."""
        lignes = self.lignes(ctx)
        marge = lignes["net"] - lignes["cout"] - lignes["transport"]
        return marge.groupby(lignes["nom_client"]).sum() / 100

    @cache  # noqa: B019
    def ecarts_clients_actifs(self, ctx: Contexte) -> pd.Series:
        """Écart de marge contributive des clients vendus en N et en N-1 (classement)."""
        n = self.marges_contributives(ctx)
        n1 = self.marges_contributives(ctx.precedent())
        communs = n.index.intersection(n1.index)
        return (n[communs] - n1[communs]).sort_values()

    def rang_client(self, ctx: Contexte) -> int | None:
        if ctx.client is None:
            return None
        n = self.marges_contributives(ctx)
        n1 = self.marges_contributives(ctx.precedent())
        if ctx.client not in n.index or ctx.client not in n1.index:
            return None
        propre = n[ctx.client] - n1[ctx.client]
        # Classement sur tous les clients : le tableau regroupe aussi par commercial.
        classement = self.ecarts_clients_actifs(
            ctx.avec(client=None, segment=None, commercial=None)
        )
        return int((classement < propre).sum()) + 1

    @cache  # noqa: B019
    def marges_produits(self, ctx: Contexte) -> pd.Series:
        """Marge commerciale par nom de produit, en euros, pour les produits vendus."""
        lignes = self.lignes(ctx)
        marge = lignes["net"] - lignes["cout"]
        return (marge.groupby(lignes["nom_produit"]).sum() / 100).sort_values()

    def rang_produit(self, ctx: Contexte) -> int | None:
        if ctx.produit is None:
            return None
        marges = self.marges_produits(ctx)
        if ctx.produit not in marges.index or not marges[ctx.produit] < 0:
            return None
        classement = self.marges_produits(ctx.avec(produit=None))
        return int((classement < marges[ctx.produit]).sum()) + 1

    # --- pont de marge ----------------------------------------------------------

    def _termes(self, ctx: Contexte) -> pd.DataFrame | None:
        """Valeurs unitaires de N et N-1 par produit vendu en N."""
        n = self.par_produit(ctx)
        if n.empty:
            return None
        n1 = self.par_produit(ctx.precedent()).reindex(n.index)
        q = n["quantite"].astype(float)
        q1 = n1["quantite"]
        avec_n1 = q1.notna() & (q1 > 0)

        def unitaire_n1(colonne):
            return (n1[colonne] / q1).where(avec_n1, n[colonne] / q)

        return pd.DataFrame(
            {
                "q": q,
                "brut": n["brut"],
                "remise": n["remise"],
                "net": n["net"],
                "cout": n["cout"],
                "catalogue_n1": unitaire_n1("brut"),
                "remise_n1": unitaire_n1("remise"),
                "net_n1": unitaire_n1("net"),
                "cout_n1": unitaire_n1("cout"),
                "marge_n1": ((n1["net"] - n1["cout"]) / q1).where(
                    avec_n1, (n["net"] - n["cout"]) / q
                ),
            }
        )

    @cache  # noqa: B019
    def pont(self, ctx: Contexte) -> dict:
        termes = self._termes(ctx)
        base_n1 = self.base(ctx.precedent())
        marge_n1, ca_n1 = base_n1["Marge commerciale"], base_n1["CA net"]
        resultat = {"CA net N au prix N-1": None}
        if termes is not None:
            resultat["CA net N au prix N-1"] = float((termes["q"] * termes["net_n1"]).sum())
        # Garde commune aux cinq effets : une seule année et un CA N-1 non vide.
        for _, nom in EFFETS:
            resultat[nom] = None
        if ctx.annee is None or ca_n1 is None:
            return resultat
        if termes is None:
            # Aucune vente en N : seul l'effet volume est défini, il annule la marge N-1.
            resultat["Effet volume"] = -marge_n1
            return resultat
        volume_a_prix_n1 = resultat["CA net N au prix N-1"]
        marge_volume = marge_n1 * volume_a_prix_n1 / ca_n1
        resultat["Effet volume"] = marge_volume - marge_n1
        resultat["Effet mix"] = float((termes["q"] * termes["marge_n1"]).sum()) - marge_volume
        resultat["Effet prix catalogue"] = float(
            (termes["brut"] - termes["q"] * termes["catalogue_n1"]).sum()
        )
        resultat["Effet remises"] = -float(
            (termes["remise"] - termes["q"] * termes["remise_n1"]).sum()
        )
        resultat["Effet coût d'achat"] = -float(
            (termes["cout"] - termes["q"] * termes["cout_n1"]).sum()
        )
        return resultat

    # --- toutes les mesures numériques -----------------------------------------------

    @cache  # noqa: B019
    def numeriques(self, ctx: Contexte) -> dict:
        n = self.base(ctx)
        n1 = self.base(ctx.precedent())
        m = dict(n)
        m["# Clients à marge négative"] = self.compter_negatifs(ctx, "client", "contributive")
        m["# Produits sous le coût"] = self.compter_negatifs(ctx, "produit", "commerciale")

        m["Rang client en recul de marge"] = self.rang_client(ctx)
        m["Rang produit sous le coût"] = self.rang_produit(ctx)

        m["CA net N-1"] = n1["CA net"]
        m["CA net écart N-1"] = ecart(n["CA net"], n1["CA net"])
        m["CA net évol. N-1 (%)"] = evolution(n["CA net"], n1["CA net"])
        m["CA net écart N-1 par statut"] = self.ecart_par_statut(ctx)
        m["# Nouveaux clients"] = self.compter_statut(ctx, nouveaux=True)
        m["# Clients perdus"] = self.compter_statut(ctx, nouveaux=False)
        m["Marge commerciale N-1"] = n1["Marge commerciale"]
        m["Marge commerciale écart N-1"] = ecart(n["Marge commerciale"], n1["Marge commerciale"])
        m["Marge commerciale évol. N-1 (%)"] = evolution(
            n["Marge commerciale"], n1["Marge commerciale"]
        )
        m["Marge commerciale N-1 (% CA)"] = n1["Marge commerciale (% CA)"]
        m["Marge commerciale écart N-1 (pts)"] = ecart_points(
            n["Marge commerciale (% CA)"], n1["Marge commerciale (% CA)"]
        )
        m["Taux de remise N-1 (%)"] = n1["Taux de remise (%)"]
        m["Taux de remise écart N-1 (pts)"] = ecart_points(
            n["Taux de remise (%)"], n1["Taux de remise (%)"]
        )
        m["Transport N-1 (% CA)"] = n1["Transport (% CA)"]
        m["Transport écart N-1 (pts)"] = ecart_points(n["Transport (% CA)"], n1["Transport (% CA)"])
        m["Marge contributive N-1"] = n1["Marge contributive"]
        m["Marge contributive écart N-1"] = ecart(n["Marge contributive"], n1["Marge contributive"])
        m["Marge contributive évol. N-1 (%)"] = evolution(
            n["Marge contributive"], n1["Marge contributive"]
        )
        for nom in ("# Clients actifs", "Commandes par client", "Panier moyen"):
            m[f"{nom} N-1"] = n1[nom]
            m[f"{nom} évol. N-1 (%)"] = evolution(n[nom], n1[nom])

        budget_ca, budget_marge = self.budget_ca_marge(ctx)
        m["CA net budget"] = budget_ca
        m["CA net écart budget"] = None if budget_ca is None else moins(n["CA net"], budget_ca)
        m["CA net écart budget (%)"] = diviser(moins(n["CA net"], budget_ca), budget_ca)
        m["Marge commerciale budget"] = budget_marge
        m["Marge commerciale écart budget (%)"] = diviser(
            moins(n["Marge commerciale"], budget_marge), budget_marge
        )

        pont = self.pont(ctx)
        m.update(pont)
        effets = [pont[nom] for _, nom in EFFETS]
        if ctx.annee is not None and n1["Marge commerciale"] is not None:
            m["Pont de marge écart de bouclage"] = (
                n1["Marge commerciale"]
                + sum(e or 0 for e in effets)
                - (n["Marge commerciale"] or 0)
            )
        else:
            m["Pont de marge écart de bouclage"] = None
        valides = [(libelle, pont[nom]) for libelle, nom in EFFETS if pont[nom] is not None]
        if valides:
            m["Frein principal (montant)"] = min(v for _, v in valides)
            m["Frein principal (libellé)"] = min(valides, key=lambda e: e[1])[0]
        else:
            m["Frein principal (montant)"] = None
            m["Frein principal (libellé)"] = None
        total = None
        if ctx.annee is not None and n1["CA net"] is not None:
            total = m["Marge commerciale écart N-1"]
        m["Pont de marge"] = {
            None: total,
            1: m["Effet volume"],
            2: m["Effet mix"],
            3: m["Effet prix catalogue"],
            4: m["Effet remises"],
            5: m["Effet coût d'achat"],
        }[ctx.etape]
        return m

    def mesure(self, ctx: Contexte, nom: str):
        return self.numeriques(ctx)[nom]

    # --- textes ------------------------------------------------------------------------

    def _meilleur(
        self, ctx: Contexte, dimension: str, membres: list[str], nom: str, croissant=False
    ):
        """Membre de plus forte (ou plus faible) valeur, comme TOPN sur VALUES(...)."""
        membres = _membres(ctx, dimension, membres)
        valeurs = [
            (membre, self.mesure(ctx.avec(**{dimension: membre}), nom)) for membre in membres
        ]
        valeurs = [(membre, valeur) for membre, valeur in valeurs if valeur is not None]
        if not valeurs:
            return None, None
        cible = min(v for _, v in valeurs) if croissant else max(v for _, v in valeurs)
        # TOPN renvoie toutes les égalités ; MAXX garde alors le plus grand libellé.
        return max(m for m, v in valeurs if v == cible), cible

    def textes(self, ctx: Contexte) -> dict:
        m = self.numeriques(ctx)
        annee = ctx.annee
        t = {}

        # Titre Direction
        budget = m["CA net écart budget (%)"]
        texte_budget = ""
        if budget is not None:
            texte_budget = (
                " et dépasse le budget de " if budget >= 0 else " et reste sous le budget de "
            ) + pct(abs(budget))
        if annee is None:
            corps = "Sélectionnez une année"
        elif m["CA net"] is None:
            corps = "Aucune vente sur la sélection"
        elif m["CA net évol. N-1 (%)"] is None:
            corps = (
                f"En {annee}, le CA net atteint {millions(m['CA net'])}"
                f"{texte_budget} (pas d'exercice précédent)"
            )
        else:
            evol = m["CA net évol. N-1 (%)"]
            verbe = "progresse" if evol >= 0 else "recule"
            corps = f"En {annee}, le CA net {verbe} de {pct(abs(evol))} sur un an{texte_budget}"
        t["Titre Direction"] = corps

        # Synthèse Direction
        if annee is None:
            t["Synthèse Direction"] = "Sélectionnez une année. Données fictives."
        elif m["CA net N-1"] is None:
            t["Synthèse Direction"] = (
                "Pas d'exercice précédent : contributions à la croissance non calculables. "
                "Données fictives."
            )
        else:
            famille, ecart_famille = self._meilleur(
                ctx, "famille", self.familles, "CA net écart N-1", croissant=True
            )
            region, ecart_region = self._meilleur(
                ctx, "region", self.regions, "CA net écart N-1", croissant=True
            )
            nouveaux = m["# Nouveaux clients"] or 0
            perdus = m["# Clients perdus"] or 0
            texte_nouveaux = " nouveau client, " if nouveaux <= 1 else " nouveaux clients, "
            texte_perdus = " client perdu" if perdus <= 1 else " clients perdus"
            t["Synthèse Direction"] = (
                f"Plus faible contribution : famille {famille} ({milliers(ecart_famille)}), "
                f"région {region} ({milliers(ecart_region)}). "
                f"{nouveaux}{texte_nouveaux}{perdus}{texte_perdus}. Données fictives."
            )

        # Titre tendance CA
        mois_contexte = [ctx.mois] if ctx.mois is not None else list(range(1, 13))
        compares, hausses = 0, 0
        if annee is not None:
            for mois in mois_contexte:
                valeur = self.mesure(ctx.avec(mois=mois), "CA net")
                valeur_n1 = self.mesure(ctx.avec(mois=mois), "CA net N-1")
                if valeur_n1 is not None:
                    compares += 1
                    hausses += (valeur or 0) > valeur_n1
        if annee is None or compares == 0:
            t["Titre tendance CA"] = "CA net mensuel"
        else:
            t["Titre tendance CA"] = (
                f"CA net mensuel : au-dessus de {annee - 1} sur {hausses} mois sur {compares}"
            )

        # Titres des écarts par famille et par région
        libelles = {
            "famille": ("famille", self.familles),
            "region": ("région", self.regions),
        }
        for dimension, (mot, membres) in libelles.items():
            nom_mesure = f"Titre écart par {mot}"
            membre, valeur = self._meilleur(ctx, dimension, membres, "CA net écart N-1")
            if membre is None:
                t[nom_mesure] = f"Écart de CA net par {mot}"
            elif valeur > 0:
                t[nom_mesure] = f"Par {mot} : {membre} en tête ({milliers(valeur)})"
            else:
                t[nom_mesure] = (
                    f"Par {mot} : toutes en recul, {membre} résiste le mieux ({milliers(valeur)})"
                )

        # Titre écart par statut client
        statuts = [
            (nom, self.mesure(ctx.avec(statut=ordre), "CA net écart N-1 par statut"))
            for ordre, nom in STATUTS.items()
        ]
        statuts = [(nom, valeur) for nom, valeur in statuts if valeur is not None]
        if not statuts:
            t["Titre écart par statut client"] = "Écart de CA net par statut client"
        else:
            plus_haut = max(valeur for _, valeur in statuts)
            nom = max(n for n, valeur in statuts if valeur == plus_haut)
            if plus_haut > 0:
                t["Titre écart par statut client"] = (
                    f"Par statut : {nom.lower()} en tête ({milliers(plus_haut)})"
                )
            else:
                t["Titre écart par statut client"] = "Par statut : aucune hausse"

        # Titre écart budget par famille
        ecarts_budget = [
            self.mesure(ctx.avec(famille=f), "CA net écart budget")
            for f in _membres(ctx, "famille", self.familles)
        ]
        ecarts_budget = [e for e in ecarts_budget if e is not None]
        if not ecarts_budget:
            t["Titre écart budget par famille"] = "Écart de CA net au budget par famille"
        else:
            atteints = sum(e >= 0 for e in ecarts_budget)
            if atteints <= 1:
                t["Titre écart budget par famille"] = (
                    f"{atteints} famille sur {len(ecarts_budget)} atteint son budget de CA net"
                )
            else:
                t["Titre écart budget par famille"] = (
                    f"{atteints} familles sur {len(ecarts_budget)} atteignent leur budget de CA net"
                )

        # Titre Marge
        if annee is None:
            corps = "Sélectionnez une année"
        elif m["Marge commerciale"] is None:
            corps = "Aucune vente sur la sélection"
        elif m["Marge commerciale évol. N-1 (%)"] is None:
            corps = (
                f"En {annee}, la marge commerciale atteint {millions(m['Marge commerciale'])}, "
                f"soit {pct(m['Marge commerciale (% CA)'])} du CA net "
                "(pas d'exercice précédent)"
            )
        else:
            evol = m["Marge commerciale évol. N-1 (%)"]
            verbe = "progresse" if evol >= 0 else "recule"
            corps = (
                f"En {annee}, la marge commerciale {verbe} de {pct(abs(evol))} et représente "
                f"{pct(m['Marge commerciale (% CA)'])} du CA net "
                f"({points(m['Marge commerciale écart N-1 (pts)'])})"
            )
        t["Titre Marge"] = corps

        # Synthèse Marge
        frein, montant_frein = m["Frein principal (libellé)"], m["Frein principal (montant)"]
        ecart_ca, ecart_marge = m["CA net écart N-1"], m["Marge commerciale écart N-1"]
        if ecart_ca is None:
            texte_evolution = "Pas d'exercice précédent : évolution de la marge non calculable. "
        else:
            texte_evolution = (
                f"Sur un an : CA net {milliers(ecart_ca)}, "
                f"marge commerciale {milliers(ecart_marge)}"
            )
            if ecart_ca > 0:
                texte_evolution += f" ({pct(diviser(ecart_marge, ecart_ca))} du CA supplémentaire)"
            texte_evolution += ". "
        budget_marge = m["Marge commerciale écart budget (%)"]
        texte_budget = ""
        if budget_marge is not None:
            position = " au-dessus du budget. " if budget_marge >= 0 else " sous le budget. "
            texte_budget = f"Marge commerciale {pct(abs(budget_marge))}{position}"
        if annee is None:
            t["Synthèse Marge"] = "Sélectionnez une année. Données fictives."
        else:
            t["Synthèse Marge"] = f"{texte_evolution}{texte_budget}Données fictives."

        # Titre pont de marge
        if annee is None:
            t["Titre pont de marge"] = "Pont de marge commerciale"
        elif frein is None:
            t["Titre pont de marge"] = (
                "Pont de marge commerciale : pas d'exercice précédent à comparer"
            )
        elif montant_frein < 0:
            t["Titre pont de marge"] = (
                f"Pont de marge {annee - 1} → {annee} : l'effet {frein} pèse le plus "
                f"({milliers(montant_frein)})"
            )
        else:
            t["Titre pont de marge"] = (
                f"Pont de marge {annee - 1} → {annee} : aucun effet défavorable"
            )

        # Titre remises par commercial
        commercial, hausse = self._meilleur(
            ctx, "commercial", self.commerciaux, "Taux de remise écart N-1 (pts)"
        )
        if commercial is None:
            t["Titre remises par commercial"] = (
                "Taux de remise par commercial : écart avec l'exercice précédent"
            )
        elif hausse > 0:
            ctx_commercial = ctx.avec(commercial=commercial)
            t["Titre remises par commercial"] = (
                f"{commercial} : taux de remise de "
                f"{pct(self.mesure(ctx_commercial, 'Taux de remise N-1 (%)'))} à "
                f"{pct(self.mesure(ctx_commercial, 'Taux de remise (%)'))} ({points(hausse)})"
            )
        else:
            t["Titre remises par commercial"] = "Aucun commercial n'augmente ses remises"

        # Titre marge par famille
        famille, baisse = self._meilleur(
            ctx, "famille", self.familles, "Marge commerciale écart N-1 (pts)", croissant=True
        )
        if famille is None:
            t["Titre marge par famille"] = "Écart de taux de marge par famille"
        elif baisse < 0:
            t["Titre marge par famille"] = f"{famille} : taux de marge {points(baisse)}"
        else:
            t["Titre marge par famille"] = "Taux de marge : aucune famille en recul"

        # Titres des tableaux
        if annee is None:
            t["Titre clients en recul"] = "Clients en plus fort recul de marge contributive"
        elif m["CA net N-1"] is None:
            t["Titre clients en recul"] = "Clients en recul de marge : pas d'exercice précédent"
        elif not (self.ecarts_clients_actifs(ctx.avec(etape=None, statut=None)) < 0).any():
            t["Titre clients en recul"] = "Aucun client en recul de marge contributive"
        else:
            t["Titre clients en recul"] = "Clients en plus fort recul de marge contributive"
        # Tous les produits : le titre ignore le filtre des six premiers du tableau.
        pertes = self.marges_produits(ctx.avec(produit=None))
        pertes = pertes[pertes < 0]
        nb_produits = len(pertes)
        perte = f" ({milliers(float(pertes.sum()))})" if nb_produits else ""
        if nb_produits == 0:
            t["Titre produits déficitaires"] = "Aucun produit vendu à perte"
        elif nb_produits == 1:
            t["Titre produits déficitaires"] = f"1 produit vendu à perte{perte}"
        elif nb_produits <= LIGNES_TABLEAUX:
            t["Titre produits déficitaires"] = f"{nb_produits} produits vendus à perte{perte}"
        else:
            t["Titre produits déficitaires"] = (
                f"{nb_produits} produits vendus à perte{perte} : les {LIGNES_TABLEAUX} plus lourds"
            )
        t["Frein principal (libellé)"] = frein

        # Cartes KPI
        for nom, mesure, mise_en_forme in CARTES_VALEURS:
            t[nom] = "n.d." if m[mesure] is None else mise_en_forme(m[mesure])
        for nom, mesure, suffixe in CARTES_EVOLUTIONS:
            valeur = m[mesure]
            if valeur is None:
                t[nom] = "n.d."
            elif suffixe.startswith(" pts"):
                t[nom] = signe(valeur) + _format_absolu(valeur, "0.0") + suffixe
            else:
                t[nom] = pct_signe(valeur) + suffixe
        return t


# ---------------------------------------------------------------------------
# Cas de validation
# ---------------------------------------------------------------------------


def _membres(ctx: Contexte, dimension: str, tous: list[str]) -> list[str]:
    """Membres visibles d'une dimension : le seul membre filtré, sinon tous."""
    valeur = getattr(ctx, dimension)
    return [valeur] if valeur is not None else tous


def type_mesure(nom: str) -> str:
    if nom == "Pont de marge écart de bouclage":
        return "bouclage"
    if "(pts)" in nom:
        return "points"
    if "(%)" in nom or "(% CA)" in nom:
        return "taux"
    if nom.startswith(("#", "Rang ")) or nom == "Quantité":
        return "nombre"
    if nom.startswith("Commandes par client"):
        return "ratio"
    return "montant"


@dataclass(frozen=True)
class Cas:
    fichier: str
    libelle: str
    contexte: Contexte


CAS_PRINCIPAUX = (
    Cas("2025_total", "2025 total", Contexte(annee=2025)),
    Cas("2024_total", "2024 total", Contexte(annee=2024)),
    Cas("2025_region_sud", "2025 région Sud", Contexte(annee=2025, region="Sud")),
    Cas(
        "2025_famille_visserie",
        "2025 famille Visserie et fixations",
        Contexte(annee=2025, famille="Visserie et fixations"),
    ),
    Cas("2025_fevrier", "Février 2025", Contexte(annee=2025, mois=2)),
)


def _arrondi(valeur, type_):
    if valeur is None or isinstance(valeur, str):
        return valeur
    if type_ in ("montant", "bouclage"):
        return round(float(valeur), 2)
    if type_ == "nombre":
        return int(valeur)
    return round(float(valeur), 10)


@dataclass
class Calcul:
    moteur: Moteur

    def cas_principal(self, cas: Cas) -> dict:
        numeriques = self.moteur.numeriques(cas.contexte)
        textes = self.moteur.textes(cas.contexte)
        mesures = []
        for nom in sorted(numeriques):
            if nom == "Frein principal (libellé)":
                continue
            type_ = type_mesure(nom)
            mesures.append(
                {"mesure": nom, "type": type_, "attendu": _arrondi(numeriques[nom], type_)}
            )
        for nom in sorted(textes):
            mesures.append({"mesure": nom, "type": "texte", "attendu": textes[nom]})
        return {"cas": cas.libelle, "filtres": _filtres(cas.contexte), "mesures": mesures}

    def categories(self) -> dict:
        """Valeurs par catégorie de chaque graphique, pour le cas 2025 total."""
        m = self.moteur
        base = Contexte(annee=2025)
        lignes = []

        def ajouter(libelle, ctx, noms):
            for nom in noms:
                type_ = type_mesure(nom)
                lignes.append(
                    {
                        "cas": libelle,
                        "filtres": _filtres(ctx),
                        "mesure": nom,
                        "type": type_,
                        "attendu": _arrondi(m.mesure(ctx, nom), type_),
                    }
                )

        for mois in range(1, 13):
            ajouter(
                f"2025 total, mois {mois:02d}",
                base.avec(mois=mois),
                ("CA net", "CA net N-1", "CA net budget"),
            )
        for famille in m.familles:
            ajouter(
                f"2025 total, famille {famille}",
                base.avec(famille=famille),
                ("CA net écart N-1", "CA net écart budget", "Marge commerciale écart N-1 (pts)"),
            )
        for region in m.regions:
            ajouter(f"2025 total, région {region}", base.avec(region=region), ("CA net écart N-1",))
        for ordre, statut in STATUTS.items():
            ajouter(
                f"2025 total, statut {ordre} {statut}",
                base.avec(statut=ordre),
                ("CA net écart N-1 par statut",),
            )
        for commercial in m.commerciaux:
            ajouter(
                f"2025 total, commercial {commercial}",
                base.avec(commercial=commercial),
                ("Taux de remise écart N-1 (pts)",),
            )
        for ordre, etape in ETAPES.items():
            ajouter(
                f"2025 total, étape {ordre} {etape}", base.avec(etape=ordre), ("Pont de marge",)
            )
        commercial_du_client = m.ventes.groupby("nom_client")["commercial"].first()
        for client in m.ecarts_clients_actifs(base).index[:LIGNES_TABLEAUX]:
            ajouter(
                f"2025 total, client {client}",
                base.avec(client=client),
                ("Rang client en recul de marge", "Marge contributive écart N-1"),
            )
            # Contexte d'une ligne du tableau, regroupé par client et par commercial.
            commercial = commercial_du_client[client]
            ajouter(
                f"2025 total, client {client}, commercial {commercial}",
                base.avec(client=client, commercial=commercial),
                ("Rang client en recul de marge",),
            )
        # Clients perdus en tête du tri du tableau : rang vide, donc hors du filtre 1 à 6.
        perdus = m.marges_contributives(base.precedent()).drop(
            m.marges_contributives(base).index, errors="ignore"
        )
        for client in perdus.sort_values(ascending=False).index[:2]:
            commercial = commercial_du_client[client]
            ajouter(
                f"2025 total, client perdu {client}, commercial {commercial}",
                base.avec(client=client, commercial=commercial),
                ("Rang client en recul de marge",),
            )
        produits = m.marges_produits(base)
        for produit in produits[produits < 0].index[:LIGNES_TABLEAUX]:
            ajouter(
                f"2025 total, produit {produit}",
                base.avec(produit=produit),
                ("Rang produit sous le coût", "Marge commerciale"),
            )
            # Contexte du titre du tableau, filtré sur les produits affichés.
            ctx = base.avec(produit=produit)
            lignes.append(
                {
                    "cas": f"2025 total, produit {produit}",
                    "filtres": _filtres(ctx),
                    "mesure": "Titre produits déficitaires",
                    "type": "texte",
                    "attendu": m.textes(ctx)["Titre produits déficitaires"],
                }
            )
        return {"cas": "2025 total, par catégorie", "lignes": lignes}


def _filtres(ctx: Contexte) -> dict:
    return {k: v for k, v in ctx.__dict__.items() if v is not None}


def calculer(dossier: Path = DOSSIER_DONNEES) -> dict[str, dict]:
    """Renvoie le contenu de chaque fichier de tests/expected, par nom de fichier."""
    calcul = Calcul(Moteur(dossier))
    resultats = {cas.fichier: calcul.cas_principal(cas) for cas in CAS_PRINCIPAUX}
    resultats["2025_categories"] = calcul.categories()
    return resultats


def serialiser(contenu: dict) -> str:
    return json.dumps(contenu, ensure_ascii=False, indent=2) + "\n"


def main() -> None:
    DOSSIER_ATTENDUS.mkdir(parents=True, exist_ok=True)
    for nom, contenu in calculer().items():
        (DOSSIER_ATTENDUS / f"{nom}.json").write_text(serialiser(contenu), encoding="utf-8")
        nombre = len(contenu.get("mesures", contenu.get("lignes", [])))
        print(f"tests/expected/{nom}.json : {nombre} valeurs")


if __name__ == "__main__":
    sys.exit(main())
