"""Lecture minimale des fichiers TMDL du modèle, pour la documentation et les contrôles.

Le lecteur couvre la syntaxe utilisée par ce projet : tables, colonnes, mesures,
hiérarchies, partitions, relations, rôles, annotations et descriptions « /// ».
Il ne remplace pas l'analyseur de Power BI Desktop.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
DOSSIER_MODELE = RACINE / "NegoceB2B.SemanticModel" / "definition"

_DECLARATION = re.compile(
    r"^(?P<type>table|column|measure|hierarchy|level|partition|relationship|role|"
    r"tablePermission|expression|model|database|annotation|cultureInfo|linguisticMetadata)"
    r"(?:\s+(?P<nom>'(?:[^']|'')*'|[^\s=]+))?(?:\s*=\s*(?P<valeur>.*))?$"
)
_PROPRIETE = re.compile(r"^(?P<cle>[A-Za-z][A-Za-z0-9]*)\s*:\s*(?P<valeur>.*)$")
_DRAPEAU = re.compile(r"^[A-Za-z][A-Za-z0-9]*$")


def nom_objet(brut: str | None) -> str | None:
    """Retire les guillemets simples d'un nom TMDL ('Coût d''achat' -> Coût d'achat)."""
    if brut is None:
        return None
    if brut.startswith("'") and brut.endswith("'"):
        return brut[1:-1].replace("''", "'")
    return brut


def reference_colonne(valeur: str) -> tuple[str, str]:
    """Découpe une référence Table.Colonne, avec ou sans guillemets."""
    correspondance = re.fullmatch(r"('(?:[^']|'')*'|[^.']+)\.('(?:[^']|'')*'|.+)", valeur.strip())
    if not correspondance:
        raise ValueError(f"Référence de colonne illisible : {valeur}")
    return nom_objet(correspondance.group(1)), nom_objet(correspondance.group(2))


@dataclass
class Objet:
    type: str
    nom: str | None
    niveau: int
    description: str = ""
    valeur: str = ""
    proprietes: dict[str, str] = field(default_factory=dict)
    drapeaux: set[str] = field(default_factory=set)
    annotations: dict[str, str] = field(default_factory=dict)
    enfants: list[Objet] = field(default_factory=list)

    def enfants_de_type(self, type_: str) -> list[Objet]:
        return [e for e in self.enfants if e.type == type_]

    @property
    def masque(self) -> bool:
        return "isHidden" in self.drapeaux


def _niveau(ligne: str) -> int:
    return len(ligne) - len(ligne.lstrip("\t"))


def lire_fichier(chemin: Path) -> list[Objet]:
    """Renvoie les objets de premier niveau d'un fichier TMDL, avec leurs enfants."""
    lignes = chemin.read_text(encoding="utf-8").split("\n")
    racines: list[Objet] = []
    pile: list[Objet] = []
    description: list[str] = []
    i = 0
    while i < len(lignes):
        ligne = lignes[i]
        contenu = ligne.strip()
        i += 1
        if not contenu:
            continue
        niveau = _niveau(ligne)
        if contenu.startswith("///"):
            description.append(contenu[3:].strip())
            continue
        while pile and pile[-1].niveau >= niveau:
            pile.pop()
        if contenu.startswith("ref "):
            description = []
            continue
        declaration = _DECLARATION.match(contenu)
        parent = pile[-1] if pile else None
        if declaration and (parent is None or declaration.group("type") != "annotation"):
            objet = Objet(
                type=declaration.group("type"),
                nom=nom_objet(declaration.group("nom")),
                niveau=niveau,
                description=" ".join(description),
            )
            description = []
            valeur = (declaration.group("valeur") or "").strip()
            if valeur == "```":
                bloc = []
                while i < len(lignes) and lignes[i].strip() != "```":
                    bloc.append(lignes[i])
                    i += 1
                i += 1
                objet.valeur = _desindenter(bloc)
            elif valeur:
                objet.valeur = valeur
            if parent is None:
                racines.append(objet)
            else:
                parent.enfants.append(objet)
            pile.append(objet)
            continue
        description = []
        if parent is None:
            continue
        if contenu.startswith("annotation "):
            cle, _, valeur = contenu[len("annotation ") :].partition("=")
            parent.annotations[cle.strip()] = valeur.strip()
            continue
        propriete = _PROPRIETE.match(contenu)
        if propriete:
            cle, valeur = propriete.group("cle"), propriete.group("valeur").strip()
            if valeur == "" or valeur == "```":
                # Valeur sur plusieurs lignes (expression Power Query ou bloc).
                bloc = []
                while i < len(lignes) and (not lignes[i].strip() or _niveau(lignes[i]) > niveau):
                    if lignes[i].strip() == "```":
                        i += 1
                        break
                    bloc.append(lignes[i])
                    i += 1
                valeur = _desindenter(bloc)
            parent.proprietes[cle] = valeur
            continue
        if contenu.endswith("=") and contenu[:-1].strip().isidentifier():
            # Expression multiligne : « source = » suivi de lignes plus indentées.
            cle = contenu[:-1].strip()
            bloc = []
            while i < len(lignes) and (not lignes[i].strip() or _niveau(lignes[i]) > niveau):
                bloc.append(lignes[i])
                i += 1
            parent.proprietes[cle] = _desindenter(bloc)
            continue
        if _DRAPEAU.match(contenu):
            parent.drapeaux.add(contenu)
            continue
        raise ValueError(f"{chemin.name}, ligne {i} : syntaxe non reconnue : {contenu}")
    return racines


def _desindenter(bloc: list[str]) -> str:
    utiles = [ligne for ligne in bloc if ligne.strip()]
    if not utiles:
        return ""
    marge = min(_niveau(ligne) for ligne in utiles)
    return "\n".join(ligne[marge:] for ligne in bloc).strip("\n")


@dataclass
class Modele:
    tables: dict[str, Objet]
    relations: list[Objet]
    roles: list[Objet]
    modele: Objet
    expressions: list[Objet]

    def mesures(self) -> list[tuple[str, Objet]]:
        return [
            (nom_table, mesure)
            for nom_table, table in self.tables.items()
            for mesure in table.enfants_de_type("measure")
        ]

    def colonnes(self) -> list[tuple[str, Objet]]:
        return [
            (nom_table, colonne)
            for nom_table, table in self.tables.items()
            for colonne in table.enfants_de_type("column")
        ]


def lire_modele(dossier: Path = DOSSIER_MODELE) -> Modele:
    tables = {}
    for chemin in sorted((dossier / "tables").glob("*.tmdl")):
        for objet in lire_fichier(chemin):
            if objet.type == "table":
                tables[objet.nom] = objet
    relations = [
        o for o in lire_fichier(dossier / "relationships.tmdl") if o.type == "relationship"
    ]
    roles = [
        o for chemin in sorted((dossier / "roles").glob("*.tmdl")) for o in lire_fichier(chemin)
    ]
    modele = next(o for o in lire_fichier(dossier / "model.tmdl") if o.type == "model")
    expressions = [o for o in lire_fichier(dossier / "expressions.tmdl") if o.type == "expression"]
    return Modele(tables, relations, roles, modele, expressions)
