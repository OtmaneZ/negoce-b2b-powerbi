"""Met en cache dans tools/schemas/ les schémas JSON cités par les fichiers du projet.

Usage : python scripts/fetch_schemas.py

Le script parcourt les fichiers JSON du projet Power BI, relève chaque « $schema »,
télécharge le schéma puis, récursivement, chaque schéma référencé par « $ref ».
Les fichiers sont rangés selon leur URL (tools/schemas/<hôte>/<chemin>) : la
validation (scripts/check_schemas.py) fonctionne ensuite hors ligne.
"""

from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
CACHE = RACINE / "tools" / "schemas"
PROJET = ("NegoceB2B.pbip", "NegoceB2B.Report", "NegoceB2B.SemanticModel")
EXTENSIONS = {".json", ".pbip", ".pbir", ".pbism"}


def fichiers_json() -> list[Path]:
    fichiers = []
    for element in PROJET:
        chemin = RACINE / element
        if chemin.is_file():
            fichiers.append(chemin)
        elif chemin.is_dir():
            fichiers += sorted(
                p
                for p in chemin.rglob("*")
                if p.is_file() and (p.suffix in EXTENSIONS or p.name == ".platform")
            )
    return fichiers


def chemin_cache(url: str) -> Path:
    morceaux = urllib.parse.urlsplit(url)
    return CACHE / morceaux.netloc / morceaux.path.lstrip("/")


def telecharger(url: str) -> dict:
    requete = urllib.request.Request(url, headers={"User-Agent": "negoce-b2b-powerbi"})
    with urllib.request.urlopen(requete, timeout=60) as reponse:
        return json.loads(reponse.read().decode("utf-8-sig"))


def references(noeud) -> list[str]:
    trouvees = []
    if isinstance(noeud, dict):
        for cle, valeur in noeud.items():
            if cle == "$ref" and isinstance(valeur, str) and not valeur.startswith("#"):
                trouvees.append(valeur.split("#")[0])
            else:
                trouvees += references(valeur)
    elif isinstance(noeud, list):
        for valeur in noeud:
            trouvees += references(valeur)
    return trouvees


def main() -> None:
    a_traiter = sorted(
        {
            json.loads(f.read_text(encoding="utf-8-sig")).get("$schema")
            for f in fichiers_json()
            if json.loads(f.read_text(encoding="utf-8-sig")).get("$schema")
        }
    )
    vus: set[str] = set()
    while a_traiter:
        url = a_traiter.pop()
        if url in vus:
            continue
        vus.add(url)
        schema = telecharger(url)
        cible = chemin_cache(url)
        cible.parent.mkdir(parents=True, exist_ok=True)
        cible.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        for reference in references(schema):
            a_traiter.append(urllib.parse.urljoin(url, reference))
    for url in sorted(vus):
        print(chemin_cache(url).relative_to(RACINE))


if __name__ == "__main__":
    sys.exit(main())
