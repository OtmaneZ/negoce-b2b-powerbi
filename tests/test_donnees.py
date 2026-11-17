"""Contrôles des données générées : intégrité, cohérence et présence de l'histoire."""

from datetime import date

import pandas as pd
import pytest

import generate_data

CLES_PRIMAIRES = {
    "clients": ["cle_client"],
    "produits": ["cle_produit"],
    "commerciaux": ["cle_commercial"],
    "familles": ["cle_famille"],
    "regions": ["cle_region"],
    "ventes": ["numero_commande", "numero_ligne"],
    "budget": ["mois", "cle_famille", "cle_region"],
    "acces_regional": ["email", "cle_region"],
}

CLES_ETRANGERES = [
    ("ventes", "cle_client", "clients"),
    ("ventes", "cle_produit", "produits"),
    ("ventes", "cle_commercial", "commerciaux"),
    ("ventes", "cle_region", "regions"),
    ("ventes", "cle_famille", "familles"),
    ("budget", "cle_famille", "familles"),
    ("budget", "cle_region", "regions"),
    ("clients", "cle_region", "regions"),
    ("clients", "cle_commercial", "commerciaux"),
    ("produits", "cle_famille", "familles"),
    ("commerciaux", "cle_region", "regions"),
    ("acces_regional", "cle_region", "regions"),
]


def evolution_ca(ventes: pd.DataFrame, colonne: str) -> pd.Series:
    ca = ventes.groupby([colonne, "annee"])["montant_net_c"].sum().unstack()
    return ca[2025] / ca[2024] - 1


# --- Structure et intégrité ----------------------------------------------------------


def test_huit_fichiers(tables):
    assert set(tables) == set(CLES_PRIMAIRES)


@pytest.mark.parametrize("table, cles", CLES_PRIMAIRES.items())
def test_cles_uniques(tables, table, cles):
    assert not tables[table].duplicated(cles).any()


@pytest.mark.parametrize("table, colonne, reference", CLES_ETRANGERES)
def test_aucune_cle_orpheline(tables, table, colonne, reference):
    connues = set(tables[reference][colonne])
    assert set(tables[table][colonne]) <= connues


def test_aucune_valeur_manquante(tables):
    for nom, table in tables.items():
        assert not table.isna().any().any(), nom


def test_volumes(tables):
    assert len(tables["clients"]) == 900
    assert len(tables["produits"]) == 600
    assert len(tables["commerciaux"]) == 10
    assert len(tables["budget"]) == 24 * 6 * 5
    assert len(tables["acces_regional"]) == 15
    assert 50_000 <= len(tables["ventes"]) <= 80_000


def test_libelles_uniques_et_courts(tables):
    assert tables["clients"]["client"].is_unique
    assert tables["produits"]["produit"].is_unique
    assert tables["commerciaux"]["commercial"].is_unique
    assert tables["produits"]["produit"].str.len().max() <= 32


def test_adresses_fictives(tables):
    adresses = pd.concat([tables["commerciaux"]["email"], tables["acces_regional"]["email"]])
    assert adresses.str.fullmatch(r"[a-z.]+@example\.com").all()


def test_lignes_numerotees_sans_trou(tables):
    v = tables["ventes"]
    attendu = v.groupby("numero_commande").cumcount() + 1
    assert (v["numero_ligne"] == attendu).all()


# --- Montants ------------------------------------------------------------------------


def test_net_egal_brut_moins_remise(ventes):
    ecart = ventes["montant_brut_c"] - ventes["montant_remise_c"] - ventes["montant_net_c"]
    assert (ecart == 0).all()


def test_remises_bornees(ventes):
    assert (ventes["montant_remise_c"] >= 0).all()
    assert (ventes["montant_remise_c"] <= ventes["montant_brut_c"] * 0.40 + 1).all()


def test_quantites_et_couts_positifs(ventes):
    assert (ventes["quantite"] > 0).all()
    assert (ventes["montant_brut_c"] > 0).all()
    assert (ventes["cout_achat_c"] > 0).all()
    assert (ventes["cout_transport_c"] >= 0).all()


def test_chaque_commande_supporte_un_transport(ventes):
    transport = ventes.groupby("numero_commande")["cout_transport_c"].sum()
    assert (transport > 0).all()


def test_montants_a_deux_decimales(tables):
    for colonne in (
        "montant_brut",
        "montant_remise",
        "montant_net",
        "cout_achat",
        "cout_transport",
    ):
        texte = tables["ventes"][colonne].astype(str)
        assert texte.str.fullmatch(r"\d+\.\d{1,2}|\d+").all(), colonne


# --- Dates ----------------------------------------------------------------------------


def test_jours_feries_connus():
    feries = generate_data.jours_feries(2024) | generate_data.jours_feries(2025)
    for jour in (
        date(2024, 4, 1),  # lundi de Pâques
        date(2024, 5, 9),  # Ascension
        date(2024, 5, 20),  # lundi de Pentecôte
        date(2025, 4, 21),
        date(2025, 5, 29),
        date(2025, 6, 9),
        date(2025, 7, 14),
    ):
        assert jour in feries


def test_dates_dans_la_periode_et_ouvrees(ventes):
    assert ventes["date"].min() >= date(2024, 1, 1)
    assert ventes["date"].max() <= date(2025, 12, 31)
    jours = set(ventes["date"])
    ouvres = set(generate_data.jours_ouvres(2024)) | set(generate_data.jours_ouvres(2025))
    assert jours <= ouvres


def test_numero_de_commande_porte_l_annee(ventes):
    assert (ventes["numero_commande"] // 100_000 == ventes["annee"]).all()


def test_budget_au_premier_du_mois(tables):
    mois = pd.to_datetime(tables["budget"]["mois"])
    assert (mois.dt.day == 1).all()
    assert set(mois.dt.year) == {2024, 2025}


# --- Cohérence des clés redondantes -----------------------------------------------------


def test_region_et_commercial_du_client(tables):
    v = tables["ventes"].merge(tables["clients"], on="cle_client", suffixes=("", "_client"))
    assert (v["cle_region"] == v["cle_region_client"]).all()
    assert (v["cle_commercial"] == v["cle_commercial_client"]).all()


def test_famille_du_produit(tables):
    v = tables["ventes"].merge(tables["produits"], on="cle_produit", suffixes=("", "_produit"))
    assert (v["cle_famille"] == v["cle_famille_produit"]).all()


def test_commercial_de_la_region_du_client(tables):
    c = tables["clients"].merge(tables["commerciaux"], on="cle_commercial", suffixes=("", "_com"))
    assert (c["cle_region"] == c["cle_region_com"]).all()


def test_acces_regional(tables):
    acces = tables["acces_regional"]
    commerciaux = tables["commerciaux"]
    attendu = set(zip(commerciaux["email"], commerciaux["cle_region"], strict=True))
    assert attendu <= set(zip(acces["email"], acces["cle_region"], strict=True))
    direction = acces[acces["email"] == "direction.commerciale@example.com"]
    assert set(direction["cle_region"]) == set(tables["regions"]["cle_region"])


def test_toutes_les_references_vendues_chaque_annee(ventes, tables):
    for annee in (2024, 2025):
        vendus = set(ventes.loc[ventes["annee"] == annee, "cle_produit"])
        assert vendus == set(tables["produits"]["cle_produit"]), annee


# --- Histoire ------------------------------------------------------------------------------


def test_croissance_inegale_selon_les_regions(ventes):
    evolution = evolution_ca(ventes, "region")
    assert evolution.idxmax() == "Rhône-Alpes"
    assert evolution["Nord-Est"] < 0


def test_croissance_inegale_selon_les_familles(ventes):
    evolution = evolution_ca(ventes, "famille")
    assert evolution.idxmax() == "Équipements de protection"
    assert evolution["Outillage à main"] < 0


def test_croissance_globale(ventes):
    ca = ventes.groupby("annee")["montant_net_c"].sum()
    assert 0.05 <= ca[2025] / ca[2024] - 1 <= 0.12


def test_saisonnalite_aout_le_plus_faible(ventes):
    for annee in (2024, 2025):
        par_mois = ventes[ventes["annee"] == annee].groupby("mois")["montant_net_c"].sum()
        assert par_mois.idxmin() == 8, annee


def test_hausse_des_couts_de_la_visserie(ventes):
    visserie = ventes[ventes["famille"] == "Visserie et fixations"]
    unitaire = visserie.assign(cout_unitaire=visserie["cout_achat_c"] / visserie["quantite"])
    moyen = unitaire.groupby(["cle_produit", "annee"])["cout_unitaire"].mean().unstack()
    poids = visserie[visserie["annee"] == 2025].groupby("cle_produit")["quantite"].sum()
    hausse = ((moyen[2025] / moyen[2024]) * poids).sum() / poids.sum() - 1
    assert hausse >= 0.08
    autres = ventes[ventes["famille"] != "Visserie et fixations"]
    unitaire = autres.assign(cout_unitaire=autres["cout_achat_c"] / autres["quantite"])
    moyen = unitaire.groupby(["cle_produit", "annee"])["cout_unitaire"].mean().unstack()
    assert (moyen[2025] / moyen[2024] - 1).median() < 0.03


def test_derive_des_remises_d_un_seul_commercial(ventes):
    par_commercial = ventes.groupby(["commercial", "annee"])[
        ["montant_remise_c", "montant_brut_c"]
    ].sum()
    taux = (par_commercial["montant_remise_c"] / par_commercial["montant_brut_c"]).unstack()
    ecart = (taux[2025] - taux[2024]) * 100
    assert ecart["Damien Revol"] >= 5
    assert ecart.drop("Damien Revol").abs().max() <= 1.5


def test_clients_deficitaires_en_2025(ventes):
    contributive = ventes[ventes["annee"] == 2025].groupby("cle_client")["contributive_c"].sum()
    assert (contributive < 0).sum() >= 8


def test_produits_vendus_sous_le_cout_en_2025(ventes):
    marge = ventes[ventes["annee"] == 2025].groupby("cle_produit")["marge_c"].sum()
    assert (marge < 0).sum() >= 5


# --- Reproductibilité ------------------------------------------------------------------------


def test_regeneration_identique(tmp_path):
    generate_data.ecrire(generate_data.generer(), tmp_path)
    for fichier in sorted(generate_data.DOSSIER_DONNEES.glob("*.csv")):
        assert (tmp_path / fichier.name).read_bytes() == fichier.read_bytes(), fichier.name
