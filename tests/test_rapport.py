"""Règles du rapport tirées des tests dans Power BI Desktop."""

import json
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
PAGES = RACINE / "NegoceB2B.Report" / "definition" / "pages"
VISUELS = sorted(PAGES.glob("*/visuals/*/visual.json"))


def _visuel(chemin: Path) -> dict:
    return json.loads(chemin.read_text(encoding="utf-8"))["visual"]


def test_cartes_a_une_seule_valeur():
    """Desktop ignore la grille d'une carte à plusieurs valeurs et rogne les valeurs."""
    for chemin in VISUELS:
        visuel = _visuel(chemin)
        if visuel["visualType"] == "cardVisual":
            projections = visuel["query"]["queryState"]["Data"]["projections"]
            assert len(projections) == 1, chemin.parent.name


def test_filtres_de_rang_bornes_des_deux_cotes():
    """Un rang vide passe un filtre « ≤ 6 » : chaque filtre de rang a aussi une borne basse."""
    filtres_de_rang = 0
    for chemin in VISUELS:
        donnees = json.loads(chemin.read_text(encoding="utf-8"))
        for filtre in donnees.get("filterConfig", {}).get("filters", []):
            mesure = filtre["field"].get("Measure", {}).get("Property", "")
            if not mesure.startswith("Rang "):
                continue
            filtres_de_rang += 1
            condition = filtre["filter"]["Where"][0]["Condition"]
            assert "And" in condition, chemin.parent.name
            bornes = {
                condition["And"][cote]["Comparison"]["ComparisonKind"]: condition["And"][cote][
                    "Comparison"
                ]["Right"]["Literal"]["Value"]
                for cote in ("Left", "Right")
            }
            assert bornes == {2: "1D", 4: "6D"}, chemin.parent.name
    assert filtres_de_rang == 2
