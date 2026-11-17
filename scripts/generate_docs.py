"""Génère docs/mesures.md, le dictionnaire des mesures, depuis le modèle TMDL.

Usage : python scripts/generate_docs.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import tmdl

FICHIER = Path(__file__).resolve().parent.parent / "docs" / "mesures.md"


def construire(modele: tmdl.Modele | None = None) -> str:
    modele = modele or tmdl.lire_modele()
    mesures = modele.mesures()
    masquees = sum(1 for _, mesure in mesures if mesure.masque)
    dossiers: dict[str, list[tmdl.Objet]] = {}
    for _, mesure in mesures:
        dossiers.setdefault(mesure.proprietes.get("displayFolder", "Sans dossier"), []).append(
            mesure
        )

    lignes = [
        "# Dictionnaire des mesures",
        "",
        "Généré par `scripts/generate_docs.py` depuis le modèle TMDL "
        "(`NegoceB2B.SemanticModel/definition/tables/Mesures.tmdl`) ; ne pas modifier à la main.",
        "",
        f"{len(mesures)} mesures, toutes dans la table Mesures : "
        f"{len(mesures) - masquees} visibles, {masquees} masquées. "
        "CA : chiffre d'affaires hors taxes. N : période sélectionnée ; "
        "N-1 : même période un an plus tôt.",
        "",
        "| Dossier | Mesures |",
        "|---|---|",
    ]
    for dossier, contenu in dossiers.items():
        lignes.append(f"| {dossier} | {len(contenu)} |")
    for dossier, contenu in dossiers.items():
        lignes += ["", f"## {dossier}"]
        for mesure in contenu:
            format_ = mesure.proprietes.get("formatString")
            details = [f"Format : `{format_}`" if format_ else "Format : texte"]
            if mesure.masque:
                details.append("masquée")
            lignes += [
                "",
                f"### {mesure.nom}",
                "",
                mesure.description,
                "",
                f"{' ; '.join(details)}.",
                "",
                "```dax",
                mesure.valeur.replace("\t", "    "),
                "```",
            ]
    return "\n".join(lignes) + "\n"


def main() -> None:
    FICHIER.write_text(construire(), encoding="utf-8")
    print(f"docs/mesures.md : {len(tmdl.lire_modele().mesures())} mesures")


if __name__ == "__main__":
    sys.exit(main())
