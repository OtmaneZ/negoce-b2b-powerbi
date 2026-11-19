"""Vérifie les règles de modélisation sur le TMDL.

Usage : python scripts/check_model.py

Règles : aucune relation bidirectionnelle ; date/heure automatique désactivée ;
table de dates marquée ; description, dossier et format sur chaque mesure (les
mesures texte n'ont pas de format) ; description sur chaque table et chaque
colonne visible ; format sur chaque colonne visible non textuelle ; clés masquées.
"""

from __future__ import annotations

import sys

import tmdl

DOSSIERS_TEXTES = {"6. Textes", "7. Cartes KPI"}
MESURES_TEXTE_HORS_DOSSIER = {"Frein principal (libellé)"}


def controler(modele: tmdl.Modele) -> list[str]:
    erreurs = []
    for relation in modele.relations:
        sens = relation.proprietes.get("crossFilteringBehavior", "oneDirection")
        if sens != "oneDirection":
            erreurs.append(f"relation « {relation.nom} » : filtrage {sens}")
        if relation.proprietes.get("isActive") == "false":
            erreurs.append(f"relation « {relation.nom} » inactive")
        table, colonne = tmdl.reference_colonne(relation.proprietes["fromColumn"])
        cote_plusieurs = next(
            c for c in modele.tables[table].enfants_de_type("column") if c.nom == colonne
        )
        if not cote_plusieurs.masque:
            erreurs.append(f"clé étrangère visible : {table}[{colonne}]")

    if modele.modele.annotations.get("__PBI_TimeIntelligenceEnabled") != "0":
        erreurs.append("date/heure automatique non désactivée")
    if "discourageImplicitMeasures" not in modele.modele.drapeaux:
        erreurs.append("mesures implicites non découragées")

    tables_dates = [t for t in modele.tables.values() if t.proprietes.get("dataCategory") == "Time"]
    if len(tables_dates) != 1 or not any(
        "isKey" in c.drapeaux for c in tables_dates[0].enfants_de_type("column")
    ):
        erreurs.append("table de dates non marquée (dataCategory: Time et colonne isKey)")

    for table, mesure in modele.mesures():
        lieu = f"mesure « {mesure.nom} »"
        if not mesure.description:
            erreurs.append(f"{lieu} : description manquante")
        dossier = mesure.proprietes.get("displayFolder")
        if not dossier:
            erreurs.append(f"{lieu} : dossier manquant")
        texte = dossier in DOSSIERS_TEXTES or mesure.nom in MESURES_TEXTE_HORS_DOSSIER
        if not texte and not mesure.proprietes.get("formatString"):
            erreurs.append(f"{lieu} : format manquant")
        if table != "Mesures":
            erreurs.append(f"{lieu} : hors de la table Mesures")

    for nom, table in modele.tables.items():
        if not table.description:
            erreurs.append(f"table « {nom} » : description manquante")
    for table, colonne in modele.colonnes():
        lieu = f"colonne {table}[{colonne.nom}]"
        if colonne.nom.startswith("Clé") and not colonne.masque:
            erreurs.append(f"{lieu} : clé visible")
        if colonne.proprietes.get("summarizeBy") != "none":
            erreurs.append(f"{lieu} : agrégation implicite possible (summarizeBy)")
        cachee = colonne.masque or table_masquee(modele, table)
        if cachee:
            continue
        if not colonne.description:
            erreurs.append(f"{lieu} : description manquante")
        if colonne.proprietes.get("dataType") != "string" and not colonne.proprietes.get(
            "formatString"
        ):
            erreurs.append(f"{lieu} : format manquant")
    return erreurs


def table_masquee(modele: tmdl.Modele, table: str) -> bool:
    return modele.tables[table].masque


def main() -> int:
    modele = tmdl.lire_modele()
    erreurs = controler(modele)
    for erreur in erreurs:
        print(f"KO {erreur}")
    mesures = modele.mesures()
    print(
        f"Règles de modèle : {len(modele.tables)} tables, {len(modele.relations)} relations, "
        f"{len(mesures)} mesures, {len(modele.colonnes())} colonnes, {len(erreurs)} erreur(s)"
    )
    return 1 if erreurs else 0


if __name__ == "__main__":
    sys.exit(main())
