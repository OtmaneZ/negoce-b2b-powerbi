"""Vérifie la typographie des fichiers texte du dépôt : aucun tiret cadratin ni demi-cadratin.

Usage : python scripts/check_texts.py

Seuls les fichiers suivis par git sont lus. Les fichiers tiers, repris tels quels
de Microsoft, sont exclus : schémas JSON en cache et thème de base de Power BI Desktop.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
TIRETS = {"—": "tiret cadratin", "–": "tiret demi-cadratin"}
EXCLUS = ("tools/schemas/", "NegoceB2B.Report/StaticResources/SharedResources/")


def fichiers_suivis() -> list[Path]:
    sortie = subprocess.run(
        ["git", "ls-files", "-z"], cwd=RACINE, capture_output=True, check=True
    ).stdout.decode("utf-8")
    return [RACINE / nom for nom in sortie.split("\0") if nom and not nom.startswith(EXCLUS)]


def main() -> int:
    erreurs = 0
    fichiers = 0
    for fichier in fichiers_suivis():
        try:
            texte = fichier.read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError):
            continue
        fichiers += 1
        for numero, ligne in enumerate(texte.splitlines(), start=1):
            for caractere, nom in TIRETS.items():
                if caractere in ligne:
                    erreurs += 1
                    print(f"KO {fichier.relative_to(RACINE)}:{numero} : {nom}")
    print(f"Typographie : {fichiers} fichiers texte, {erreurs} erreur(s)")
    return 1 if erreurs else 0


if __name__ == "__main__":
    sys.exit(main())
