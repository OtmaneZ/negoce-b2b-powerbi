"""Vérifie la mise en page des pages du rapport.

Usage : python scripts/check_layout.py

Règles : chaque visuel tient dans le canevas, coordonnées et dimensions multiples
de 8, aucun chevauchement sur une page, et les mêmes zones sur toutes les pages.
"""

from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
PAGES = RACINE / "NegoceB2B.Report" / "definition" / "pages"
TRAME = 8


def lire_pages() -> list[dict]:
    ordre = json.loads((PAGES / "pages.json").read_text(encoding="utf-8"))["pageOrder"]
    pages = []
    for nom in ordre:
        page = json.loads((PAGES / nom / "page.json").read_text(encoding="utf-8"))
        visuels = []
        for fichier in sorted((PAGES / nom / "visuals").glob("*/visual.json")):
            visuel = json.loads(fichier.read_text(encoding="utf-8"))
            p = visuel["position"]
            visuels.append(
                {
                    "nom": visuel["name"],
                    "type": visuel["visual"]["visualType"],
                    "rect": (p["x"], p["y"], p["width"], p["height"]),
                }
            )
        pages.append(
            {
                "nom": page["displayName"],
                "taille": (page["width"], page["height"]),
                "visuels": visuels,
            }
        )
    return pages


def se_chevauchent(a: tuple, b: tuple) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


def controler(pages: list[dict]) -> list[str]:
    erreurs = []
    for page in pages:
        largeur, hauteur = page["taille"]
        for v in page["visuels"]:
            x, y, w, h = v["rect"]
            lieu = f"{page['nom']}, {v['type']} {v['nom']}"
            if x < 0 or y < 0 or x + w > largeur or y + h > hauteur:
                erreurs.append(f"{lieu} : hors du canevas {v['rect']}")
            if any(valeur % TRAME for valeur in v["rect"]):
                erreurs.append(f"{lieu} : position hors trame de {TRAME} px {v['rect']}")
        for a, b in itertools.combinations(page["visuels"], 2):
            if se_chevauchent(a["rect"], b["rect"]):
                erreurs.append(f"{page['nom']} : {a['nom']} chevauche {b['nom']}")
    zones = [sorted(v["rect"] for v in page["visuels"]) for page in pages]
    for page, zones_page in zip(pages[1:], zones[1:], strict=True):
        if zones_page != zones[0]:
            erreurs.append(f"{page['nom']} : zones différentes de la page {pages[0]['nom']}")
    return erreurs


def main() -> int:
    pages = lire_pages()
    erreurs = controler(pages)
    for erreur in erreurs:
        print(f"KO {erreur}")
    total = sum(len(p["visuels"]) for p in pages)
    print(f"Mise en page : {len(pages)} pages, {total} visuels, {len(erreurs)} erreur(s)")
    return 1 if erreurs else 0


if __name__ == "__main__":
    sys.exit(main())
