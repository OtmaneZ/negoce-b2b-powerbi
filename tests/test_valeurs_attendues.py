"""Contrôles des valeurs attendues calculées en pandas, indépendamment du DAX."""

import json

import pytest

import expected_values as ev


@pytest.fixture(scope="module")
def moteur() -> ev.Moteur:
    return ev.Moteur()


def test_fichiers_attendus_a_jour():
    """tests/expected/*.json correspond exactement à ce que produit le script."""
    for nom, contenu in ev.calculer().items():
        fichier = ev.DOSSIER_ATTENDUS / f"{nom}.json"
        assert fichier.read_text(encoding="utf-8") == ev.serialiser(contenu), fichier.name
    attendus = {f"{nom}.json" for nom in ev.calculer()}
    assert {f.name for f in ev.DOSSIER_ATTENDUS.glob("*.json")} == attendus


@pytest.mark.parametrize(
    "contexte",
    [
        ev.Contexte(annee=2025),
        ev.Contexte(annee=2025, region="Sud"),
        ev.Contexte(annee=2025, famille="Visserie et fixations"),
    ],
    ids=["total 2025", "région Sud 2025", "famille Visserie et fixations 2025"],
)
def test_bouclage_du_pont(moteur, contexte):
    """Marge N-1 + effets = marge N, à moins d'un centime."""
    m = moteur.numeriques(contexte)
    effets = sum(m[nom] for _, nom in ev.EFFETS)
    assert abs(m["Marge commerciale N-1"] + effets - m["Marge commerciale"]) < 0.01
    assert abs(m["Pont de marge écart de bouclage"]) < 0.01


def test_effet_prix_scinde_en_prix_catalogue_et_remises(moteur):
    """Prix catalogue + remises = effet du prix net moyen par produit."""
    ctx = ev.Contexte(annee=2025)
    termes = moteur._termes(ctx)
    effet_prix_net = float((termes["net"] - termes["q"] * termes["net_n1"]).sum())
    m = moteur.numeriques(ctx)
    assert abs(m["Effet prix catalogue"] + m["Effet remises"] - effet_prix_net) < 0.01


@pytest.mark.parametrize("cas", ev.CAS_PRINCIPAUX, ids=lambda c: c.libelle)
def test_identite_clients_frequence_panier(moteur, cas):
    m = moteur.numeriques(cas.contexte)
    produit = m["# Clients actifs"] * m["Commandes par client"] * m["Panier moyen"]
    assert produit == pytest.approx(m["CA net"], rel=1e-9)


def test_pont_vide_sans_exercice_precedent(moteur):
    m = moteur.numeriques(ev.Contexte(annee=2024))
    for _, nom in ev.EFFETS:
        assert m[nom] is None
    assert m["CA net N-1"] is None
    assert m["CA net évol. N-1 (%)"] is None


def test_fevrier_compare_a_fevrier_bissextile(moteur):
    """Février 2025 est comparé au mois complet de février 2024, 29 février compris."""
    lignes_n1 = moteur.lignes(ev.Contexte(annee=2024, mois=2))
    assert lignes_n1.index.size > 0
    jours = moteur.ventes.loc[lignes_n1.index]
    assert jours["mois"].eq(2).all()
    m = moteur.numeriques(ev.Contexte(annee=2025, mois=2))
    assert m["CA net N-1"] == pytest.approx(int(lignes_n1["net"].sum()) / 100)


def test_budget_vide_si_filtre_hors_budget(moteur):
    m = moteur.numeriques(ev.Contexte(annee=2025, segment="Grands comptes"))
    assert m["CA net budget"] is None
    assert m["CA net écart budget (%)"] is None
    textes = moteur.textes(ev.Contexte(annee=2025, segment="Grands comptes"))
    assert "budget" not in textes["Titre Direction"]
    assert "budget" not in textes["Synthèse Marge"]
    assert textes["Titre écart budget par famille"] == "Écart de CA net au budget par famille"


def test_textes_du_cas_2024():
    contenu = json.loads((ev.DOSSIER_ATTENDUS / "2024_total.json").read_text(encoding="utf-8"))
    textes = {m["mesure"]: m["attendu"] for m in contenu["mesures"] if m["type"] == "texte"}
    assert "pas d'exercice précédent" in textes["Titre Direction"]
    assert textes["Titre pont de marge"].endswith("pas d'exercice précédent à comparer")
    assert textes["Titre tendance CA"] == "CA net mensuel"


def test_textes_complets(moteur):
    """Aucun texte vide, inachevé ou contenant une valeur Python."""
    for cas in ev.CAS_PRINCIPAUX:
        for nom, texte in moteur.textes(cas.contexte).items():
            if nom == "Frein principal (libellé)":
                continue
            assert texte and "None" not in texte and "nan" not in texte, (cas.libelle, nom)
            assert "  " not in texte and "( " not in texte, (cas.libelle, nom)


@pytest.mark.parametrize(
    "valeur, format_dax, attendu",
    [
        (0.0845, "0.0 %", "8,5 %"),
        (-0.05, "0.0 %", "-5,0 %"),
        (1234.56, "#,0.0", "1 234,6"),
        (1234567.5, "#,0", "1 234 568"),
        (0.04, "0.0", "0,0"),
        (2.25, "0.0", "2,3"),
    ],
)
def test_format_fr(valeur, format_dax, attendu):
    assert ev.format_fr(valeur, format_dax) == attendu


def test_textes_signes():
    assert ev.milliers(-310_400) == "-310 k€"
    assert ev.milliers(300) == "+0 k€"
    assert ev.pct_signe(0.0213) == "+2,1 %"
    assert ev.points(-1.7245) == "-1,7 pts"
    assert ev.millions(20_910_165.84) == "20,9 M€"
    assert ev.normaliser_espaces("1 234 €") == "1 234 €"
