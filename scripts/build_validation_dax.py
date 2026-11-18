"""Génère tests/validation.dax depuis tests/expected/*.json.

Usage : python scripts/build_validation_dax.py

La requête produite se colle telle quelle dans la vue Requête DAX de Power BI
Desktop. Elle embarque les valeurs attendues, recalcule chaque mesure dans le
modèle pour chaque cas et renvoie deux résultats : le nombre de contrôles et de
KO, puis le détail, lignes KO en premier.
"""

from __future__ import annotations

import json
import sys
from decimal import Decimal
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
DOSSIER_ATTENDUS = RACINE / "tests" / "expected"
FICHIER_DAX = RACINE / "tests" / "validation.dax"

TOLERANCES = {
    "montant": 1.0,
    "taux": 0.0005,
    "points": 0.05,
    "nombre": 0.0,
    "ratio": 0.01,
    "bouclage": 0.01,
}

FILTRES_DAX = {
    "annee": ("'Date'[Année]", False),
    "mois": ("'Date'[Numéro mois]", False),
    "region": ("'Région'[Région]", True),
    "famille": ("'Famille'[Famille]", True),
    "segment": ("'Client'[Segment]", True),
    "commercial": ("'Commercial'[Commercial]", True),
    "client": ("'Client'[Client]", True),
    "produit": ("'Produit'[Produit]", True),
    "etape": ("'Étape du pont'[Ordre]", False),
    "statut": ("'Statut client'[Ordre]", False),
}


def chaine(texte: str) -> str:
    """Littéral texte DAX : guillemets doublés."""
    return '"' + texte.replace('"', '""') + '"'


def nombre(valeur: float) -> str:
    """Littéral numérique DAX en notation décimale."""
    if isinstance(valeur, int):
        return str(valeur)
    texte = format(Decimal(repr(valeur)), "f")
    if "." in texte:
        texte = texte.rstrip("0").rstrip(".")
    return texte if texte not in ("", "-0") else "0"


def filtres(filtres_cas: dict) -> str:
    morceaux = []
    for cle, valeur in filtres_cas.items():
        colonne, texte = FILTRES_DAX[cle]
        morceaux.append(f"{colonne} = {chaine(valeur) if texte else valeur}")
    return ", ".join(morceaux)


def lignes_attendues() -> list[dict]:
    """Une entrée par cas et par mesure, dans un ordre stable."""
    lignes = []
    for fichier in sorted(DOSSIER_ATTENDUS.glob("*.json")):
        contenu = json.loads(fichier.read_text(encoding="utf-8"))
        if "mesures" in contenu:
            for mesure in contenu["mesures"]:
                lignes.append({"cas": contenu["cas"], "filtres": contenu["filtres"], **mesure})
        else:
            lignes.extend(contenu["lignes"])
    return lignes


def reference_mesure(nom: str) -> str:
    return "[" + nom.replace("]", "]]") + "]"


def construire() -> str:
    lignes = lignes_attendues()
    nombres = [ligne for ligne in lignes if ligne["type"] != "texte"]
    textes = [ligne for ligne in lignes if ligne["type"] == "texte"]

    def rangee_nombre(cle: int, ligne: dict) -> str:
        vide = ligne["attendu"] is None
        attendu = 0 if vide else ligne["attendu"]
        return (
            f"            {{ {cle}, {chaine(ligne['cas'])}, {chaine(ligne['mesure'])}, "
            f"{nombre(attendu)}, {'TRUE' if vide else 'FALSE'}, "
            f"{nombre(TOLERANCES[ligne['type']])} }}"
        )

    def rangee_texte(cle: int, ligne: dict) -> str:
        attendu = ligne["attendu"] or ""
        cas, mesure = chaine(ligne["cas"]), chaine(ligne["mesure"])
        return f"            {{ {cle}, {cas}, {mesure}, {chaine(attendu)} }}"

    def calcul(cle: int, ligne: dict) -> str:
        expression = f"CALCULATE({reference_mesure(ligne['mesure'])}, {filtres(ligne['filtres'])})"
        return f'        ROW("N°", {cle}, "Obtenu", {expression})'

    cles_nombres = list(enumerate(nombres, start=1))
    cles_textes = list(enumerate(textes, start=len(nombres) + 1))
    sep = ",\n"
    return f"""// Requête de validation du modèle NegoceB2B.
// Générée par scripts/build_validation_dax.py depuis tests/expected/*.json ;
// ne pas modifier à la main.
//
// À coller dans la vue Requête DAX de Power BI Desktop, puis Exécuter.
// Premier résultat : nombre de contrôles et nombre de KO (0 attendu).
// Second résultat : détail par cas et par mesure, lignes KO en premier.
// Tolérances : 1 € sur les montants, 0,05 point sur les taux, égalité exacte sur les
// nombres entiers et sur les textes après normalisation des espaces insécables.

DEFINE
    VAR _attendusNombres =
        DATATABLE(
            "Clé", INTEGER,
            "Cas", STRING,
            "Mesure", STRING,
            "Attendu", DOUBLE,
            "Vide", BOOLEAN,
            "Tolérance", DOUBLE,
            {{
{sep.join(rangee_nombre(cle, ligne) for cle, ligne in cles_nombres)}
            }}
        )
    VAR _attendusTextes =
        DATATABLE(
            "Clé", INTEGER,
            "Cas", STRING,
            "Mesure", STRING,
            "Attendu", STRING,
            {{
{sep.join(rangee_texte(cle, ligne) for cle, ligne in cles_textes)}
            }}
        )
    VAR _obtenusNombres =
        UNION(
{sep.join(calcul(cle, ligne) for cle, ligne in cles_nombres)}
        )
    VAR _obtenusTextes =
        UNION(
{sep.join(calcul(cle, ligne) for cle, ligne in cles_textes)}
        )
    VAR _resultatsNombres =
        ADDCOLUMNS(
            _attendusNombres,
            "Obtenu",
                VAR _cle = [Clé]
                RETURN MAXX(FILTER(_obtenusNombres, [N°] = _cle), [Obtenu])
        )
    VAR _controlesNombres =
        SELECTCOLUMNS(
            _resultatsNombres,
            "Cas", [Cas],
            "Mesure", [Mesure],
            "Attendu", IF([Vide], "(vide)", FORMAT([Attendu], "0.0000", "fr-FR")),
            "Obtenu", IF(ISBLANK([Obtenu]), "(vide)", FORMAT([Obtenu], "0.0000", "fr-FR")),
            "Écart", IF([Vide] || ISBLANK([Obtenu]), BLANK(), [Obtenu] - [Attendu]),
            "Statut",
                IF(
                    [Vide],
                    IF(ISBLANK([Obtenu]), "OK", "KO"),
                    IF(
                        NOT ISBLANK([Obtenu]) && ABS([Obtenu] - [Attendu]) <= [Tolérance],
                        "OK",
                        "KO"
                    )
                )
        )
    VAR _controlesTextes =
        SELECTCOLUMNS(
            ADDCOLUMNS(
                _attendusTextes,
                "Obtenu",
                    VAR _cle = [Clé]
                    VAR _texte = MAXX(FILTER(_obtenusTextes, [N°] = _cle), [Obtenu])
                    VAR _sansInsecables = SUBSTITUTE(_texte & "", UNICHAR(160), " ")
                    RETURN SUBSTITUTE(_sansInsecables, UNICHAR(8239), " ")
            ),
            "Cas", [Cas],
            "Mesure", [Mesure],
            "Attendu", [Attendu],
            "Obtenu", [Obtenu],
            "Écart", BLANK(),
            "Statut", IF(EXACT([Obtenu], [Attendu]), "OK", "KO")
        )
    VAR _controles = UNION(_controlesNombres, _controlesTextes)

EVALUATE
    ROW(
        "Contrôles", COUNTROWS(_controles),
        "KO", COUNTROWS(FILTER(_controles, [Statut] = "KO")) + 0
    )

EVALUATE
    _controles
    ORDER BY [Statut] ASC, [Cas] ASC, [Mesure] ASC
"""


def main() -> None:
    FICHIER_DAX.write_text(construire(), encoding="utf-8")
    print(f"tests/validation.dax : {len(lignes_attendues())} contrôles")


if __name__ == "__main__":
    sys.exit(main())
