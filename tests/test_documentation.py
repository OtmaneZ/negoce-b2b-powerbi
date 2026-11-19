"""Les chiffres cités par la documentation sont ceux des scripts et du modèle."""

import json
import re
from collections import Counter
from pathlib import Path

import pandas as pd
import pytest

import expected_values as ev
import fetch_schemas
import tmdl

RACINE = Path(__file__).resolve().parent.parent
README = (RACINE / "README.md").read_text(encoding="utf-8")
TEST_WINDOWS = (RACINE / "docs" / "test-windows.md").read_text(encoding="utf-8")
FICHIERS_CAS = {
    "2025 total": "2025_total",
    "2024 total": "2024_total",
    "2025 région Sud": "2025_region_sud",
    "2025 famille Visserie et fixations": "2025_famille_visserie",
    "Février 2025": "2025_fevrier",
}


def attendu(cas: str, mesure: str):
    contenu = json.loads((ev.DOSSIER_ATTENDUS / f"{FICHIERS_CAS[cas]}.json").read_text("utf-8"))
    ligne = next(m for m in contenu["mesures"] if m["mesure"] == mesure)
    return ligne["attendu"], ligne["type"]


def affichage(valeur, type_: str) -> str:
    """Format d'affichage utilisé dans la documentation."""
    if valeur is None:
        return "(vide)"
    formats = {"montant": ("#,0", " €"), "taux": ("0.0 %", ""), "points": ("0.0", " pts")}
    format_, suffixe = formats.get(type_, ("#,0", ""))
    return ev.format_fr(valeur, format_) + suffixe


def lignes_tableau_attendu() -> list[list[str]]:
    section = README.split("## Valeurs attendues et obtenues")[1].split("\n## ")[0]
    lignes = [ligne for ligne in section.splitlines() if ligne.startswith("| ")]
    return [[cellule.strip() for cellule in ligne.strip("|").split("|")] for ligne in lignes[1:]]


@pytest.mark.parametrize("cas, mesure, valeur, obtenue", lignes_tableau_attendu())
def test_tableau_attendu_du_readme(cas, mesure, valeur, obtenue):
    assert valeur == affichage(*attendu(cas, mesure))


def test_chiffres_cles_du_readme():
    textes = ev.Moteur().textes(ev.Contexte(annee=2025))
    for fragment in (
        "Par famille : Équipements de protection en tête (+778 k€)",
        "Par région : Rhône-Alpes en tête (+699 k€)",
        "Par statut : clients existants en tête (+1 617 k€)",
        "63 nouveaux clients, 45 clients perdus",
        "marge commerciale +181 k€ (10,5 % du CA supplémentaire)",
        "8 produits vendus à perte (-40 k€)",
        "taux de remise de 10,9 % à 19,2 %",
        "l'effet coût d'achat pèse le plus (-504 k€)",
        "progresse de 8,3 % sur un an et dépasse le budget de 0,9 %",
        "progresse de 2,6 % et représente 31,4 % du CA net (-1,7 pts)",
    ):
        assert any(fragment in texte for texte in textes.values()), fragment
    for fragment in (
        "+778 k€",
        "+699 k€",
        "10,9 % à 19,2 %",
        "-504 k€",
        "8,3 %",
        "0,9 %",
        "2,6 %",
        "31,4 %",
        "-1,7 pts",
        "+1 617 k€",
        "63 nouveaux clients +806 k€",
        "45 clients perdus en retirent 696 k€",
        "10,5 % de marge",
        "8 produits",
        "-40 k€",
        "-204 k€",
    ):
        assert fragment in README, fragment
    assert ev.milliers(attendu("2025 total", "Effet remises")[0]) == "-204 k€"
    moteur = ev.Moteur()
    statuts = [
        ev.milliers(
            moteur.mesure(ev.Contexte(annee=2025, statut=ordre), "CA net écart N-1 par statut")
        )
        for ordre in ev.STATUTS
    ]
    assert statuts == ["+1 617 k€", "+806 k€", "-696 k€"]
    revol = ev.Contexte(annee=2025, commercial="Damien Revol")
    premiers = moteur.ecarts_clients_actifs(ev.Contexte(annee=2025)).index[:2]
    for client in premiers:
        assert moteur.lignes(revol.avec(client=client)).index.size > 0, client


def test_comptes_du_modele_dans_le_readme():
    modele = tmdl.lire_modele()
    mesures = modele.mesures()
    masquees = sum(mesure.masque for _, mesure in mesures)
    dossiers = Counter(mesure.proprietes["displayFolder"] for _, mesure in mesures)
    assert f"{len(modele.tables)} tables" in README
    assert f"{len(modele.relations)} relations" in README
    visibles = len(mesures) - masquees
    assert f"{len(mesures)} mesures dans la table Mesures, {visibles} visibles" in README
    assert f"et {masquees} masquées" in README
    for dossier, nombre in dossiers.items():
        assert f"{dossier.split('. ', 1)[1]} ({nombre})".lower() in README.lower(), dossier
    categories = (ev.DOSSIER_ATTENDUS / "2025_categories.json").read_text("utf-8")
    total = len(json.loads(categories)["lignes"])
    total += sum(
        len(json.loads((ev.DOSSIER_ATTENDUS / f"{f}.json").read_text("utf-8"))["mesures"])
        for f in FICHIERS_CAS.values()
    )
    assert f"les {total} valeurs" in README
    assert f"Contrôles = {total}" in TEST_WINDOWS


def test_versions_de_schemas_du_readme():
    for fichier in fetch_schemas.fichiers_json():
        url = json.loads(fichier.read_text(encoding="utf-8-sig")).get("$schema")
        if not url:
            continue
        trouve = re.search(r"/([^/]+)/(\d+\.\d+(?:\.\d+)?)/schema", url)
        if not trouve:
            assert "reportThemeSchema-2.159" in url
            continue
        famille, version = trouve.groups()
        assert f"{famille} {version}" in README, url
    assert "reportThemeSchema 2.159" in README


def test_lignes_par_table_de_la_procedure():
    attendues = {
        "Ventes": "ventes",
        "Budget": "budget",
        "Client": "clients",
        "Produit": "produits",
        "Commercial": "commerciaux",
        "Famille": "familles",
        "Région": "regions",
        "Accès régional": "acces_regional",
    }
    for table, fichier in attendues.items():
        lignes = len(pd.read_csv(RACINE / "data" / f"{fichier}.csv"))
        assert f"| {table} | {ev.format_fr(lignes, '#,0')} |" in TEST_WINDOWS, table
    assert "| Date | 731 |" in TEST_WINDOWS
    assert "| Étape du pont | 5 |" in TEST_WINDOWS
    assert "| Statut client | 3 |" in TEST_WINDOWS


def test_textes_cites_par_la_procedure():
    moteur = ev.Moteur()
    total = moteur.textes(ev.Contexte(annee=2025))
    sud = moteur.textes(ev.Contexte(annee=2025, region="Sud"))
    for texte in (
        total["Titre Direction"],
        total["Synthèse Direction"],
        total["Titre tendance CA"],
        total["Titre Marge"],
        total["Synthèse Marge"],
        total["Titre pont de marge"],
        total["Titre remises par commercial"],
        total["Titre écart par statut client"],
        total["Titre clients en recul"],
        total["Titre produits déficitaires"],
        sud["Titre Direction"],
    ):
        assert f"« {texte} »" in TEST_WINDOWS, texte


def test_tableau_attendu_sans_doublon():
    lignes = [tuple(ligne[:2]) for ligne in lignes_tableau_attendu()]
    doublons = [ligne for ligne, nombre in Counter(lignes).items() if nombre > 1]
    assert not doublons
