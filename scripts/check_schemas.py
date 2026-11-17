"""Valide chaque fichier JSON du projet Power BI contre son « $schema », hors ligne.

Usage : python scripts/check_schemas.py

Les schémas sont lus dans tools/schemas/ (voir scripts/fetch_schemas.py). Seul le
thème de base fourni par Power BI Desktop, sans « $schema », est exclu.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft7Validator
from jsonschema.validators import validator_for
from referencing import Registry, Resource
from referencing.exceptions import NoSuchResource
from referencing.jsonschema import DRAFT7

from fetch_schemas import RACINE, chemin_cache, fichiers_json

SANS_SCHEMA_AUTORISES = {"BaseThemes"}


def _recuperer(uri: str) -> Resource:
    chemin = chemin_cache(uri)
    if not chemin.exists():
        raise NoSuchResource(ref=uri)
    contenu = json.loads(chemin.read_text(encoding="utf-8"))
    return Resource.from_contents(contenu, default_specification=DRAFT7)


def valider(fichier: Path, registre: Registry) -> list[str]:
    document = json.loads(fichier.read_text(encoding="utf-8-sig"))
    url = document.get("$schema")
    if not url:
        if SANS_SCHEMA_AUTORISES & set(fichier.parts):
            return []
        return ["aucun $schema"]
    if not chemin_cache(url).exists():
        return [f"schéma absent du cache : {url} (lancer scripts/fetch_schemas.py)"]
    schema = _recuperer(url).contents
    classe = validator_for(schema, default=Draft7Validator)
    validateur = classe({"$ref": url}, registry=registre)
    return [
        f"{'/'.join(str(p) for p in erreur.absolute_path) or '(racine)'} : {erreur.message[:200]}"
        for erreur in validateur.iter_errors(document)
    ]


def main() -> int:
    registre = Registry(retrieve=_recuperer)
    fichiers = fichiers_json()
    echecs = 0
    for fichier in fichiers:
        for erreur in valider(fichier, registre):
            echecs += 1
            print(f"KO {fichier.relative_to(RACINE)} : {erreur}")
    print(f"Schémas JSON : {len(fichiers)} fichiers, {echecs} erreur(s)")
    return 1 if echecs else 0


if __name__ == "__main__":
    sys.exit(main())
