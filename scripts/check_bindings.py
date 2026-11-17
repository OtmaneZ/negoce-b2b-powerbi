"""Vérifie que chaque table, colonne et mesure citée par le rapport existe dans le modèle TMDL.

Usage : python scripts/check_bindings.py

Le script parcourt report.json, chaque page.json et chaque visual.json : projections,
tris, filtres, titres et règles de mise en forme conditionnelle.
"""

from __future__ import annotations

import json
import sys

import tmdl

RAPPORT = tmdl.RACINE / "NegoceB2B.Report" / "definition"


def references(noeud, alias: dict[str, str] | None = None):
    """Produit (type, table, nom) pour chaque Column, Measure ou Hierarchy rencontré."""
    alias = dict(alias or {})
    if isinstance(noeud, dict):
        for source in noeud.get("From", []) if isinstance(noeud.get("From"), list) else []:
            if "Name" in source and "Entity" in source:
                alias[source["Name"]] = source["Entity"]
        for type_ in ("Column", "Measure", "Hierarchy"):
            champ = noeud.get(type_)
            if isinstance(champ, dict) and "Property" in champ:
                ref = champ.get("Expression", {}).get("SourceRef", {})
                table = ref.get("Entity") or alias.get(ref.get("Source"), f"?{ref.get('Source')}")
                yield type_, table, champ["Property"]
        for valeur in noeud.values():
            yield from references(valeur, alias)
    elif isinstance(noeud, list):
        for valeur in noeud:
            yield from references(valeur, alias)


def query_refs(noeud):
    """Produit (queryRef, champ) pour chaque projection."""
    if isinstance(noeud, dict):
        if "queryRef" in noeud and "field" in noeud:
            yield noeud["queryRef"], noeud["field"]
        for valeur in noeud.values():
            yield from query_refs(valeur)
    elif isinstance(noeud, list):
        for valeur in noeud:
            yield from query_refs(valeur)


def main() -> int:
    modele = tmdl.lire_modele()
    colonnes = {(table, colonne.nom) for table, colonne in modele.colonnes()}
    mesures = {(table, mesure.nom) for table, mesure in modele.mesures()}
    hierarchies = {
        (nom, h.nom)
        for nom, table in modele.tables.items()
        for h in table.enfants_de_type("hierarchy")
    }
    connus = {"Column": colonnes, "Measure": mesures, "Hierarchy": hierarchies}

    fichiers = [RAPPORT / "report.json", *sorted(RAPPORT.glob("pages/*/page.json"))]
    fichiers += sorted(RAPPORT.glob("pages/*/visuals/*/visual.json"))
    erreurs, verifiees = [], 0
    for fichier in fichiers:
        contenu = json.loads(fichier.read_text(encoding="utf-8"))
        relatif = fichier.relative_to(tmdl.RACINE)
        for type_, table, nom in references(contenu):
            verifiees += 1
            if table not in modele.tables:
                erreurs.append(f"{relatif} : table inconnue « {table} »")
            elif (table, nom) not in connus[type_]:
                erreurs.append(f"{relatif} : {type_} inconnu « {table}[{nom}] »")
        for query_ref, champ in query_refs(contenu):
            for type_ in ("Column", "Measure"):
                if type_ in champ:
                    entite = champ[type_]["Expression"]["SourceRef"].get("Entity")
                    attendu = f"{entite}.{champ[type_]['Property']}"
                    if query_ref != attendu:
                        erreurs.append(
                            f"{relatif} : queryRef « {query_ref} » au lieu de « {attendu} »"
                        )
    for erreur in erreurs:
        print(f"KO {erreur}")
    print(
        f"Liaisons : {verifiees} références dans {len(fichiers)} fichiers, {len(erreurs)} erreur(s)"
    )
    return 1 if erreurs else 0


if __name__ == "__main__":
    sys.exit(main())
