"""Génère les données fictives d'Arvenor, négoce B2B de fournitures industrielles.

Usage : python scripts/generate_data.py [dossier_de_sortie]

Le générateur est déterministe : la graine fixe produit des fichiers identiques
octet pour octet à chaque exécution. Les montants sont calculés en centimes
entiers, puis écrits avec deux décimales.
"""

from __future__ import annotations

import sys
import unicodedata
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

GRAINE = 20240101
ANNEES = (2024, 2025)
DOSSIER_DONNEES = Path(__file__).resolve().parent.parent / "data"

# Poids mensuels de saisonnalité (janvier à décembre).
SAISONNALITE = (0.90, 0.95, 1.10, 1.05, 0.95, 1.10, 0.95, 0.55, 1.10, 1.15, 1.05, 0.80)

# Régions : clé, nom, poids dans le CA, évolution cible du CA en 2025, forfait de transport (€).
REGIONS = (
    (1, "Île-de-France", 0.26, 0.04, 14.0),
    (2, "Nord-Est", 0.18, -0.03, 18.0),
    (3, "Ouest", 0.20, 0.09, 17.0),
    (4, "Rhône-Alpes", 0.22, 0.15, 9.0),
    (5, "Sud", 0.14, 0.06, 15.0),
)

# Familles : clé, nom, préfixe de référence, taux de marge cible, évolution des volumes 2025.
FAMILLES = (
    (1, "Visserie et fixations", "VIS", 0.38, 0.02),
    (2, "Outillage à main", "OUT", 0.35, -0.10),
    (3, "Outillage électroportatif", "ELE", 0.24, 0.12),
    (4, "Abrasifs et coupe", "ABR", 0.40, 0.05),
    (5, "Équipements de protection", "EPI", 0.33, 0.16),
    (6, "Hygiène et maintenance", "HYG", 0.30, 0.07),
)
NOMBRE_PRODUITS = {1: 140, 2: 110, 3: 70, 4: 90, 5: 100, 6: 90}
# Objectif de croissance du CA net 2025 par famille, fixé par la direction sur le réel 2024.
OBJECTIFS_BUDGET_2025 = {1: 0.07, 2: 0.00, 3: 0.14, 4: 0.07, 5: 0.08, 6: 0.06}


@dataclass(frozen=True)
class Segment:
    nom: str
    part: float  # part des clients
    commandes: float  # commandes par an
    lignes: float  # nombre moyen de lignes par commande
    valeur_ligne: float  # montant brut visé par ligne (€)
    remise: float  # remise de base
    preferences: tuple[float, ...]  # poids des familles 1 à 6


SEGMENTS = (
    Segment("Grands comptes", 0.05, 48, 3.5, 1200, 0.14, (0.25, 0.10, 0.15, 0.20, 0.20, 0.10)),
    Segment("PME industrielles", 0.45, 14, 3.0, 550, 0.09, (0.22, 0.15, 0.15, 0.18, 0.18, 0.12)),
    Segment("Artisans et TPE", 0.40, 6, 2.2, 180, 0.05, (0.20, 0.25, 0.25, 0.10, 0.12, 0.08)),
    Segment("Collectivités", 0.10, 8, 3.0, 450, 0.11, (0.10, 0.15, 0.10, 0.05, 0.25, 0.35)),
)

# Commerciaux : clé, nom, clé de région, effet sur le taux de remise.
COMMERCIAUX = (
    (1, "Camille Roussel", 1, 0.005),
    (2, "Mehdi Haddad", 1, -0.005),
    (3, "Pauline Mercier", 2, 0.010),
    (4, "Laurent Schmitt", 2, 0.000),
    (5, "Gaëlle Le Guen", 3, -0.010),
    (6, "Nicolas Hervé", 3, 0.005),
    (7, "Sophie Vernet", 4, 0.000),
    (8, "Romain Chabert", 4, -0.005),
    (9, "Damien Revol", 5, 0.000),
    (10, "Inès Fabre", 5, 0.010),
)
COMMERCIAL_DERIVE = 9  # Damien Revol : dérive des remises en 2025
EMAIL_DIRECTION = "direction.commerciale@example.com"

NOMBRE_CLIENTS = 900
PART_CLIENTS_PERDUS = 0.05  # actifs en 2024 seulement
PART_CLIENTS_NOUVEAUX = 0.07  # actifs en 2025 seulement
NOMBRE_PETITS_CLIENTS_ELOIGNES = 10
NOMBRE_CLIENTS_SURREMISES = 5
NOMBRE_FINS_DE_SERIE = 8

HAUSSE_TARIF_2025 = 0.025
HAUSSE_TARIF_2025_VISSERIE = 0.03
HAUSSE_COUTS_2025 = 0.015
HAUSSE_COUTS_VISSERIE = 0.11  # à partir du 1er mars 2025
DEBUT_HAUSSE_VISSERIE = date(2025, 3, 1)
DECOTE_FIN_DE_SERIE = 0.45
REMISE_MOYENNE_ATTENDUE = 0.10  # sert à fixer les coûts : marge cible visée après remises
VOLUME_ACHETE_PAR_REMISES = 0.15  # surcroît de volume 2025 des clients de Damien Revol
DISPERSION_COMMANDES = 0.05
TAUX_TRANSPORT_VARIABLE = 0.015
REMISE_MAXIMALE = 0.40


# Catalogue : pour chaque famille, des groupes (sous-famille, libellés, fourchette de prix).
def _catalogue() -> dict[int, list[tuple[str, list[str], tuple[float, float]]]]:
    def ftx(valeurs):
        return [str(v).replace(".", ",") for v in valeurs]

    tailles = ("M", "L", "XL", "XXL")
    return {
        1: [
            (
                "Vis",
                [
                    f"Vis TH M{d}x{lg} {m}, boîte 100"
                    for d in (6, 8, 10, 12)
                    for lg in (20, 30, 40, 50, 60, 80)
                    for m in ("zinguée", "inox A2", "inox A4")
                ]
                + [
                    f"Vis agglo {d}x{lg}, boîte 200"
                    for d in ftx((3.5, 4, 5, 6))
                    for lg in (20, 30, 40, 50, 60, 80, 100)
                ],
                (5, 60),
            ),
            (
                "Chevilles",
                [f"Cheville nylon {d} mm, boîte 100" for d in (5, 6, 8, 10, 12, 14)]
                + [f"Cheville métal M{d}, boîte 50" for d in (5, 6, 8, 10)]
                + [f"Cheville chimique {v} ml" for v in (150, 300, 410)],
                (4, 35),
            ),
            (
                "Boulonnerie",
                [
                    f"Écrou HU M{d} {m}, boîte 100"
                    for d in (6, 8, 10, 12)
                    for m in ("zingué", "inox A2")
                ]
                + [
                    f"Rondelle plate M{d} {m}, x100"
                    for d in (6, 8, 10, 12)
                    for m in ("zinguée", "inox A2")
                ]
                + [
                    f"Tige filetée M{d} {m}, 1 m"
                    for d in (6, 8, 10, 12, 16)
                    for m in ("zinguée", "inox A2")
                ],
                (3, 30),
            ),
            (
                "Rivets",
                [
                    f"Rivet aveugle {d}x{lg} alu, x500"
                    for d in ftx((3.2, 4, 4.8))
                    for lg in (8, 10, 12, 16)
                ],
                (8, 30),
            ),
        ],
        2: [
            (
                "Tournevis",
                [f"Tournevis plat {w} mm" for w in ftx((3, 4, 5.5, 6.5, 8))]
                + [f"Tournevis cruciforme PH{n}" for n in (0, 1, 2, 3)]
                + [f"Tournevis Torx T{n}" for n in (10, 15, 20, 25, 30, 40)]
                + [f"Coffret tournevis {n} pièces" for n in (6, 8, 12)],
                (8, 45),
            ),
            (
                "Clés",
                [f"Clé mixte {n} mm" for n in range(8, 25)]
                + [f"Clé à cliquet 1/{x} po" for x in (4, 2)]
                + [f"Coffret douilles {n} pièces" for n in (24, 46, 94)]
                + [f"Jeu de clés Allen {n} pièces" for n in (9, 10)]
                + [f"Clé à molette {n} mm" for n in (150, 200, 250, 300)]
                + [
                    f"Clé plate {a}x{b} mm"
                    for a, b in ((6, 7), (8, 9), (10, 11), (12, 13), (14, 15), (16, 17))
                ]
                + [f"Clé plate {a}x{b} mm" for a, b in ((18, 19), (20, 22), (24, 27))]
                + [f"Clé à pipe {n} mm" for n in range(8, 20)],
                (8, 150),
            ),
            (
                "Pinces",
                [f"Pince universelle {n} mm" for n in (160, 180, 200)]
                + [f"Pince coupante {n} mm" for n in (140, 160, 180)]
                + [f"Pince multiprise {n} mm" for n in (180, 250, 300)]
                + [f"Pince à dénuder {n} mm" for n in (160, 180)],
                (12, 60),
            ),
            (
                "Frappe et mesure",
                [f"Marteau rivoir {n} g" for n in (200, 300, 400, 500)]
                + [f"Massette {n} kg" for n in ftx((1, 1.25, 1.5))]
                + [f"Mètre ruban {n} m" for n in (3, 5, 8, 10)]
                + [f"Niveau à bulle {n} cm" for n in (40, 60, 80, 100, 120)]
                + [f"Équerre de menuisier {n} mm" for n in (250, 300, 400)],
                (8, 80),
            ),
            (
                "Coupe",
                ["Scie à métaux 300 mm"]
                + [f"Cutter lame {n} mm" for n in (9, 18, 25)]
                + [f"Lime plate {n} mm" for n in (150, 200, 250)]
                + [f"Lime ronde {n} mm" for n in (150, 200, 250)]
                + [f"Serre-joint {n} mm" for n in (150, 300, 500, 800)],
                (8, 60),
            ),
        ],
        3: [
            (
                "Perçage et vissage",
                [f"Perceuse visseuse 18 V {a} Ah" for a in (2, 4, 5)]
                + [f"Perceuse à percussion {w} W" for w in (600, 750, 850, 1000)]
                + [f"Perforateur SDS+ {w} W" for w in (650, 800, 1000, 1250)]
                + [f"Visseuse à chocs 18 V {a} Ah" for a in (2, 4, 5)]
                + [f"Boulonneuse 18 V {n} Nm" for n in (300, 600, 1000)]
                + [f"Agrafeuse électrique {n} mm" for n in (8, 10, 14)],
                (90, 650),
            ),
            (
                "Meulage et coupe",
                [
                    f"Meuleuse Ø{d} {w} W"
                    for d, w in (
                        (115, 750),
                        (125, 900),
                        (125, 1200),
                        (150, 1400),
                        (230, 2200),
                        (230, 2600),
                    )
                ]
                + [f"Scie sauteuse {w} W" for w in (500, 650, 800)]
                + [f"Scie circulaire Ø{d} mm" for d in (165, 190, 210, 235)]
                + [f"Scie sabre {w} W" for w in (900, 1100, 1300)]
                + [f"Rainureuse béton Ø{d} mm" for d in (125, 150)]
                + [f"Carotteuse Ø{d} mm" for d in (82, 132)],
                (70, 900),
            ),
            (
                "Ponçage",
                [f"Ponceuse orbitale {w} W" for w in (200, 300, 350)]
                + [f"Ponceuse à bande {w} W" for w in (750, 1000)]
                + [f"Ponceuse excentrique Ø{d} mm" for d in (125, 150)]
                + [f"Rabot électrique {w} W" for w in (650, 850)],
                (60, 400),
            ),
            (
                "Batteries et accessoires",
                [f"Batterie 18 V {a} Ah" for a in (2, 4, 5, 8)]
                + [f"Batterie 12 V {a} Ah" for a in (2, 3, 6)]
                + [f"Chargeur rapide {v} V" for v in (12, 18)]
                + [f"Lampe de chantier 18 V {n} lm" for n in (1000, 2000, 3000)]
                + [f"Aspirateur chantier {n} L" for n in (20, 30, 45)]
                + [f"Décapeur thermique {w} W" for w in (1600, 2000)]
                + [f"Pistolet à colle {w} W" for w in (80, 150)]
                + [f"Malaxeur {w} W" for w in (1200, 1600)],
                (60, 450),
            ),
        ],
        4: [
            (
                "Disques",
                [
                    f"Disque tronçonnage {m} {d}x{e}"
                    for m in ("inox", "métal")
                    for d, e in (
                        (115, "1,0"),
                        (125, "1,0"),
                        (125, "1,6"),
                        (230, "1,9"),
                        (230, "3,0"),
                    )
                ]
                + [f"Disque à lamelles {d} G{g}" for d in (115, 125) for g in (40, 60, 80, 120)]
                + [
                    f"Disque à ébarber {d}x{e}"
                    for d, e in ((115, "6,0"), (125, "6,4"), (230, "6,4"))
                ]
                + [
                    f"Disque diamant {d} {u}"
                    for d in (125, 230)
                    for u in ("béton", "carrelage", "universel")
                ],
                (2, 40),
            ),
            (
                "Perçage",
                [
                    f"Foret HSS Ø{d} mm"
                    for d in ftx((2, 2.5, 3, 3.5, 4, 4.5, 5, 5.5, 6, 6.5, 7, 8, 9, 10, 12))
                ]
                + [f"Foret béton SDS+ Ø{d} mm" for d in (5, 6, 8, 10, 12, 14, 16)]
                + [f"Coffret forets HSS {n} pièces" for n in (13, 19, 25)]
                + [f"Scie cloche Ø{d} mm" for d in (20, 25, 32, 40, 51, 68, 76)]
                + [f"Foret étagé {a} à {b} mm" for a, b in ((4, 20), (6, 30))],
                (2, 40),
            ),
            (
                "Ponçage",
                [
                    f"Bande abrasive {lg}x{w} G{g}"
                    for lg, w in ((75, 457), (75, 533), (100, 610))
                    for g in (40, 80, 120)
                ]
                + [f"Feuille abrasive G{g}, x50" for g in (40, 60, 80, 120, 180, 240)]
                + [f"Rouleau abrasif 115 mm G{g}" for g in (80, 120, 180)],
                (3, 40),
            ),
            (
                "Lames",
                [f"Lame scie sauteuse {u}, x5" for u in ("bois", "métal", "PVC")]
                + [f"Lame scie circulaire Ø{d} {z}D" for d in (165, 190, 210) for z in (24, 48)]
                + [f"Lame cutter {w} mm, x10" for w in (9, 18, 25)],
                (3, 40),
            ),
        ],
        5: [
            (
                "Gants",
                [f"Gants nitrile T{t}, boîte 100" for t in ("S", "M", "L", "XL")]
                + [f"Gants de manutention T{t}" for t in (7, 8, 9, 10, 11)]
                + [f"Gants anticoupure T{t}" for t in (7, 8, 9, 10, 11)]
                + [f"Gants soudeur T{t}" for t in (9, 10, 11)]
                + [f"Sous-gants coton T{t}" for t in (7, 8, 9, 10)],
                (3, 30),
            ),
            (
                "Chaussures",
                [f"Chaussures S3 basses P{p}" for p in range(38, 47)]
                + [f"Chaussures S3 montantes P{p}" for p in range(38, 47)]
                + [f"Bottes de sécurité P{p}" for p in range(39, 47)],
                (45, 120),
            ),
            (
                "Vêtements",
                [f"Gilet haute visibilité T{t}" for t in tailles]
                + [f"Combinaison jetable T{t}" for t in tailles]
                + [f"Parka haute visibilité T{t}" for t in tailles]
                + [f"Pantalon de travail T{t}" for t in (38, 40, 42, 44, 46, 48, 50)]
                + [f"Veste softshell T{t}" for t in tailles]
                + [f"Tee-shirt haute visibilité T{t}" for t in tailles],
                (5, 90),
            ),
            (
                "Tête, yeux et respiration",
                [f"Casque de chantier {c}" for c in ("blanc", "jaune", "bleu", "rouge")]
                + [f"Lunettes de protection {v}" for v in ("incolores", "teintées", "anti-buée")]
                + [f"Masque FFP{n}, boîte 20" for n in (1, 2, 3)]
                + [f"Masque FFP{n} à valve, boîte 10" for n in (2, 3)]
                + [f"Casque antibruit SNR {n} dB" for n in (27, 30, 33)]
                + ["Bouchons d'oreilles, boîte 200"]
                + [f"Écran facial {v}" for v in ("polycarbonate", "grillagé")],
                (4, 60),
            ),
            (
                "Travail en hauteur et secours",
                [f"Harnais antichute {n} points" for n in (1, 2)]
                + [f"Longe antichute {n} m" for n in ftx((1, 1.5, 2))]
                + [f"Genouillères {v}" for v in ("mousse", "gel")]
                + ["Trousse de secours atelier"],
                (15, 120),
            ),
        ],
        6: [
            (
                "Nettoyage",
                [f"Dégraissant atelier {v} L" for v in (1, 5, 20)]
                + [f"Savon d'atelier {v} L" for v in ftx((1, 2.5, 5))]
                + [f"Nettoyant freins {v} ml" for v in (400, 600)]
                + [f"Nettoyant vitres {v} L" for v in (1, 5)]
                + [f"Désinfectant surfaces {v} L" for v in (1, 5)]
                + [f"Lingettes nettoyantes, x{n}" for n in (50, 100, 150)]
                + [f"Gel hydroalcoolique {v} ml" for v in (100, 500, 1000)]
                + [f"Crème protectrice {v} ml" for v in (100, 250)]
                + [f"Savon micro-billes {v} L" for v in (1, 4)]
                + [f"Pulvérisateur {v} L" for v in (1, 5, 8)]
                + [f"Nettoyant sols {v} L" for v in (1, 5)]
                + [f"Pelle à poussière {v}" for v in ("standard", "à manche")],
                (4, 80),
            ),
            (
                "Lubrification et collage",
                [f"Lubrifiant multifonction {v} ml" for v in (150, 400, 500)]
                + [f"Dégrippant {v} ml" for v in (300, 500)]
                + [f"Graisse lithium {v} g" for v in (400, 1000)]
                + [f"Graisse cuivre {v} g" for v in (300, 500)]
                + [f"Huile de coupe {v} L" for v in (1, 5)]
                + ["Spray silicone 400 ml"]
                + [f"Colle cyanoacrylate {v} g" for v in (20, 50)]
                + [f"Mastic silicone {c}" for c in ("blanc", "transparent", "gris")]
                + [f"Mousse expansive {v} ml" for v in (500, 750)],
                (4, 40),
            ),
            (
                "Essuyage et absorption",
                [f"Essuie-mains plié, colis {n}" for n in (6, 12)]
                + [f"Bobine d'essuyage {n} formats" for n in (500, 1000, 1500)]
                + [f"Chiffons coton {n} kg" for n in (5, 10)]
                + [f"Papier toilette, colis de {n}" for n in (48, 96)]
                + [f"Absorbant granulés {n} kg" for n in (10, 20)]
                + [f"Feuilles absorbantes, x{n}" for n in (100, 200)],
                (8, 70),
            ),
            (
                "Entretien et déchets",
                [
                    f"Sacs poubelle {v} L, x{n}"
                    for v, n in ((30, 50), (50, 50), (100, 25), (130, 25), (160, 20))
                ]
                + [f"Balai-brosse {n} cm" for n in (30, 40, 60)]
                + [f"Seau {v} L" for v in (10, 15)]
                + [f"Raclette sol {n} cm" for n in (45, 60)]
                + [f"Bac de rétention {v} L" for v in (20, 60, 220)]
                + [f"Kit antipollution {v} L" for v in (50, 120, 240)]
                + ["Distributeur de savon 1 L"]
                + [f"Ruban adhésif toilé {w} mm" for w in (38, 50)]
                + [f"Ruban de signalisation {v} m" for v in (100, 500)]
                + [f"Film étirable {w} mm, x6" for w in (450, 500)]
                + [f"Adhésif d'emballage {w} mm, x6" for w in (48, 75)]
                + [f"Chariot de ménage {n} seaux" for n in (1, 2)],
                (4, 80),
            ),
        ],
    }


# Racines inventées pour les raisons sociales des clients.
_DEBUTS = ("Bra", "Bre", "Cal", "Cor", "Dal", "Dur", "Fal", "Gar", "Ker", "Lan")
_DEBUTS += ("Mar", "Mor", "Nor", "Pal", "Ral", "Sar", "Tal", "Val", "Ver", "Vil")
_MILIEUX = ("a", "e", "i", "o", "an", "en", "on", "ar", "or", "el")
_FINS = ("dex", "ga", "lia", "lor", "mat", "nex", "rac", "tis", "vel", "zan", "rin", "tec", "via")
_ACTIVITES = {
    "Grands comptes": ("Industries", "Aéronautique", "Métallurgie", "Automobile", "Énergie"),
    "PME industrielles": (
        "Usinage",
        "Mécanique",
        "Chaudronnerie",
        "Métallerie",
        "Plasturgie",
        "Automatismes",
        "Hydraulique",
        "Maintenance",
        "Tôlerie",
    ),
    "Artisans et TPE": (
        "Menuiserie",
        "Plomberie",
        "Serrurerie",
        "Électricité",
        "Carrosserie",
        "Agencement",
        "Ferronnerie",
    ),
}
_PREFIXES_COLLECTIVITES = ("Régie", "Syndicat", "Services techniques")


def jours_feries(annee: int) -> set[date]:
    """Jours fériés français de l'année (métropole)."""
    # Date de Pâques, algorithme de Meeus pour le calendrier grégorien.
    a, b, c = annee % 19, annee // 100, annee % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    lettre = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * lettre) // 451
    mois = (h + lettre - 7 * m + 114) // 31
    jour = (h + lettre - 7 * m + 114) % 31 + 1
    paques = date(annee, mois, jour)
    fixes = [(1, 1), (5, 1), (5, 8), (7, 14), (8, 15), (11, 1), (11, 11), (12, 25)]
    mobiles = [
        paques + timedelta(days=n) for n in (1, 39, 50)
    ]  # lundi de Pâques, Ascension, Pentecôte
    return {date(annee, mm, jj) for mm, jj in fixes} | set(mobiles)


def jours_ouvres(annee: int) -> list[date]:
    """Jours du lundi au vendredi, hors jours fériés."""
    feries = jours_feries(annee)
    jour, fin = date(annee, 1, 1), date(annee, 12, 31)
    jours = []
    while jour <= fin:
        if jour.weekday() < 5 and jour not in feries:
            jours.append(jour)
        jour += timedelta(days=1)
    return jours


def email(nom: str) -> str:
    """prenom.nom@example.com, sans accents ni espaces."""
    sans_accents = unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode()
    prenom, *reste = sans_accents.lower().split(" ")
    return f"{prenom}.{''.join(reste).replace('-', '')}@example.com"


def centimes_vers_texte(centimes: np.ndarray) -> list[str]:
    return [f"{c // 100}.{c % 100:02d}" for c in centimes.tolist()]


def _generer_produits(rng: np.random.Generator) -> pd.DataFrame:
    catalogue = _catalogue()
    lignes = []
    cle = 0
    for cle_famille, _nom, prefixe, marge, _evolution in FAMILLES:
        candidats = [
            (sous_famille, libelle, fourchette)
            for sous_famille, libelles, fourchette in catalogue[cle_famille]
            for libelle in libelles
        ]
        libelles = [c[1] for c in candidats]
        if len(set(libelles)) != len(libelles):
            raise ValueError(f"Libellés en double dans la famille {cle_famille}")
        trop_longs = [lib for lib in libelles if len(lib) > 32]
        if trop_longs:
            raise ValueError(f"Libellés de plus de 32 caractères : {trop_longs}")
        choix = sorted(rng.choice(len(candidats), NOMBRE_PRODUITS[cle_famille], replace=False))
        for rang, indice in enumerate(choix, start=1):
            sous_famille, libelle, (prix_min, prix_max) = candidats[indice]
            cle += 1
            prix = float(np.exp(rng.uniform(np.log(prix_min), np.log(prix_max))))
            taux_marge = float(np.clip(rng.normal(marge, 0.035), 0.12, 0.55))
            prix_centimes = max(100, round(prix * 100))
            lignes.append(
                {
                    "cle_produit": cle,
                    "reference": f"{prefixe}-{rang:04d}",
                    "produit": libelle,
                    "sous_famille": sous_famille,
                    "cle_famille": cle_famille,
                    "prix_2024": prix_centimes,
                    "cout_2024": round(
                        prix_centimes * (1 - REMISE_MOYENNE_ATTENDUE) * (1 - taux_marge)
                    ),
                }
            )
    produits = pd.DataFrame(lignes)
    # Popularité de type Zipf à l'intérieur de chaque famille.
    produits["popularite"] = 0.0
    for cle_famille in produits["cle_famille"].unique():
        masque = produits["cle_famille"] == cle_famille
        rangs = rng.permutation(int(masque.sum())) + 1
        produits.loc[masque, "popularite"] = 1.0 / rangs**0.8
    # Fins de série d'outillage à main, déstockées sous le coût d'achat en 2025.
    outillage = produits.index[produits["cle_famille"] == 2]
    fins_de_serie = rng.choice(outillage, NOMBRE_FINS_DE_SERIE, replace=False)
    produits["fin_de_serie"] = produits.index.isin(fins_de_serie)
    return produits


def _prix_et_couts(produits: pd.DataFrame) -> dict[str, np.ndarray]:
    """Prix catalogue et coûts d'achat unitaires en centimes, par période."""
    visserie = (produits["cle_famille"] == 1).to_numpy()
    prix_2024 = produits["prix_2024"].to_numpy()
    cout_2024 = produits["cout_2024"].to_numpy()
    hausse = np.where(visserie, HAUSSE_TARIF_2025_VISSERIE, HAUSSE_TARIF_2025)
    prix_2025 = np.rint(prix_2024 * (1 + hausse)).astype(np.int64)
    prix_2025 = np.where(
        produits["fin_de_serie"].to_numpy(),
        np.rint(prix_2025 * (1 - DECOTE_FIN_DE_SERIE)).astype(np.int64),
        prix_2025,
    )
    cout_2025 = np.rint(cout_2024 * (1 + HAUSSE_COUTS_2025)).astype(np.int64)
    cout_2025_hausse = np.where(
        visserie, np.rint(cout_2025 * (1 + HAUSSE_COUTS_VISSERIE)).astype(np.int64), cout_2025
    )
    return {
        "prix_2024": prix_2024.astype(np.int64),
        "cout_2024": cout_2024.astype(np.int64),
        "prix_2025": prix_2025,
        "cout_2025": cout_2025,
        "cout_2025_hausse": cout_2025_hausse,
    }


def _nom_client(rng: np.random.Generator, segment: str) -> str:
    racine = rng.choice(_DEBUTS) + rng.choice(_MILIEUX) + rng.choice(_FINS)
    if segment == "Collectivités":
        return f"{rng.choice(_PREFIXES_COLLECTIVITES)} {racine}"
    return f"{racine} {rng.choice(_ACTIVITES[segment])}"


def _generer_clients(rng: np.random.Generator) -> pd.DataFrame:
    poids_regions = np.array([r[2] for r in REGIONS])
    parts_segments = np.array([s.part for s in SEGMENTS])
    regions = rng.choice(
        [r[0] for r in REGIONS], NOMBRE_CLIENTS, p=poids_regions / poids_regions.sum()
    )
    segments = rng.choice(len(SEGMENTS), NOMBRE_CLIENTS, p=parts_segments / parts_segments.sum())
    noms: list[str] = []
    deja_pris: set[str] = set()
    for indice in segments:
        nom = _nom_client(rng, SEGMENTS[indice].nom)
        while nom in deja_pris:
            nom = _nom_client(rng, SEGMENTS[indice].nom)
        deja_pris.add(nom)
        noms.append(nom)
    commerciaux = []
    for region in regions:
        possibles = [c[0] for c in COMMERCIAUX if c[2] == region]
        commerciaux.append(int(rng.choice(possibles)))
    clients = pd.DataFrame(
        {
            "cle_client": np.arange(1, NOMBRE_CLIENTS + 1),
            "client": noms,
            "segment": [SEGMENTS[i].nom for i in segments],
            "cle_region": regions,
            "cle_commercial": commerciaux,
            "indice_segment": segments,
            "activite": np.exp(rng.normal(0.0, 0.35, NOMBRE_CLIENTS)),
            "effet_remise": rng.normal(0.0, 0.02, NOMBRE_CLIENTS),
        }
    )
    # Cycle de vie : clients perdus fin 2024, nouveaux clients en 2025 (hors grands comptes).
    hors_grands_comptes = clients.index[clients["segment"] != "Grands comptes"].to_numpy()
    ordre = rng.permutation(hors_grands_comptes)
    nb_perdus = round(NOMBRE_CLIENTS * PART_CLIENTS_PERDUS)
    nb_nouveaux = round(NOMBRE_CLIENTS * PART_CLIENTS_NOUVEAUX)
    clients["statut"] = "fidele"
    clients.loc[ordre[:nb_perdus], "statut"] = "perdu"
    clients.loc[ordre[nb_perdus : nb_perdus + nb_nouveaux], "statut"] = "nouveau"
    clients["mois_debut_2025"] = 1
    clients.loc[clients["statut"] == "nouveau", "mois_debut_2025"] = rng.integers(
        1, 11, nb_nouveaux
    )
    # Profils déficitaires : petits clients éloignés, clients surremisés de Damien Revol.
    clients["profil"] = "standard"
    eloignes = clients.index[
        (clients["segment"] == "Artisans et TPE")
        & clients["cle_region"].isin([2, 3])
        & (clients["statut"] == "fidele")
    ]
    clients.loc[rng.choice(eloignes, NOMBRE_PETITS_CLIENTS_ELOIGNES, replace=False), "profil"] = (
        "petit_eloigne"
    )
    surremises = clients.index[
        (clients["cle_commercial"] == COMMERCIAL_DERIVE)
        & (clients["segment"] == "PME industrielles")
        & (clients["statut"] == "fidele")
    ]
    clients.loc[rng.choice(surremises, NOMBRE_CLIENTS_SURREMISES, replace=False), "profil"] = (
        "surremise"
    )
    return clients


def _generer_ventes(
    rng: np.random.Generator, clients: pd.DataFrame, produits: pd.DataFrame
) -> pd.DataFrame:
    tarifs = _prix_et_couts(produits)
    familles_produits = produits["cle_famille"].to_numpy()
    popularite = produits["popularite"].to_numpy()
    fins_de_serie = produits["fin_de_serie"].to_numpy()
    produits_par_famille = {f[0]: np.flatnonzero(familles_produits == f[0]) for f in FAMILLES}
    croissance_region = {r[0]: r[3] for r in REGIONS}
    forfait_region = {r[0]: r[4] for r in REGIONS}
    effet_commercial = {c[0]: c[3] for c in COMMERCIAUX}
    evolution_famille = np.array([f[4] for f in FAMILLES])

    calendrier = {}
    for annee in ANNEES:
        jours = jours_ouvres(annee)
        poids = np.array([SAISONNALITE[j.month - 1] for j in jours])
        calendrier[annee] = (jours, poids)

    commandes = []  # (date, cle_client, lignes [(produit, quantite, brut, remise, cout)])
    for client in clients.itertuples(index=False):
        segment = SEGMENTS[client.indice_segment]
        for annee in ANNEES:
            if (client.statut == "perdu" and annee == 2025) or (
                client.statut == "nouveau" and annee == 2024
            ):
                continue
            jours, poids = calendrier[annee]
            if annee == 2025:
                actifs = np.array([j.month >= client.mois_debut_2025 for j in jours])
                poids = poids * actifs
            frequence = (
                segment.commandes
                * client.activite
                * poids.sum()
                / sum(SAISONNALITE[j.month - 1] for j in jours)
            )
            valeur_ligne = segment.valeur_ligne
            lignes_moyennes = segment.lignes
            if client.profil == "petit_eloigne":
                frequence, valeur_ligne, lignes_moyennes = 40.0, 25.0, 1.0
            if annee == 2025:
                # Volume 2025 : évolution régionale ; la hausse des tarifs s'y ajoute.
                frequence *= 1 + croissance_region[client.cle_region]
                if client.cle_commercial == COMMERCIAL_DERIVE:
                    frequence *= 1 + VOLUME_ACHETE_PAR_REMISES
            # Nombre de commandes proche de la fréquence attendue : dispersion de 5 %.
            nb_commandes = int(np.rint(frequence * (1 + rng.normal(0.0, DISPERSION_COMMANDES))))
            if nb_commandes <= 0:
                continue
            dates = rng.choice(len(jours), nb_commandes, p=poids / poids.sum())
            preferences = np.array(segment.preferences)
            if client.profil == "petit_eloigne":
                # Petites commandes de consommables : ni outillage ni électroportatif.
                preferences = preferences * np.array([1, 0, 0, 1, 1, 1])
            if annee == 2025:
                preferences = preferences * (1 + evolution_famille)
            preferences = preferences / preferences.sum()
            for indice_jour in sorted(dates.tolist()):
                jour = jours[indice_jour]
                nb_lignes = (
                    1
                    if lignes_moyennes <= 1
                    else int(np.clip(1 + rng.poisson(lignes_moyennes - 1), 1, 8))
                )
                familles = rng.choice(len(FAMILLES), nb_lignes, p=preferences) + 1
                lignes = []
                for cle_famille in familles.tolist():
                    candidats = produits_par_famille[cle_famille]
                    poids_produits = popularite[candidats].copy()
                    if annee == 2025:
                        poids_produits[fins_de_serie[candidats]] *= 3.0
                    indice = int(rng.choice(candidats, p=poids_produits / poids_produits.sum()))
                    if annee == 2024:
                        prix, cout = tarifs["prix_2024"][indice], tarifs["cout_2024"][indice]
                    else:
                        prix = tarifs["prix_2025"][indice]
                        cle_cout = (
                            "cout_2025_hausse" if jour >= DEBUT_HAUSSE_VISSERIE else "cout_2025"
                        )
                        cout = tarifs[cle_cout][indice]
                    quantite = int(
                        np.clip(
                            np.rint(np.exp(rng.normal(np.log(valeur_ligne * 100 / prix), 0.7))),
                            1,
                            400,
                        )
                    )
                    taux = (
                        segment.remise
                        + effet_commercial[client.cle_commercial]
                        + client.effet_remise
                        + rng.normal(0.0, 0.012)
                    )
                    if client.cle_commercial == COMMERCIAL_DERIVE and annee == 2025:
                        taux += 0.10 * jour.timetuple().tm_yday / 365
                        if client.profil == "surremise":
                            taux = rng.uniform(0.37, 0.40)
                    taux = float(np.clip(taux, 0.0, REMISE_MAXIMALE))
                    brut = quantite * int(prix)
                    remise = int(brut * taux + 0.5)
                    lignes.append((indice, quantite, brut, remise, quantite * int(cout)))
                commandes.append((jour, client.cle_client, client.cle_region, lignes))

    # Numérotation des commandes par année, dans l'ordre chronologique.
    commandes.sort(key=lambda c: (c[0], c[1]))
    enregistrements = []
    compteur = {annee: 0 for annee in ANNEES}
    for jour, cle_client, cle_region, lignes in commandes:
        compteur[jour.year] += 1
        numero = jour.year * 100000 + compteur[jour.year]
        nets = np.array([brut - remise for _, _, brut, remise, _ in lignes], dtype=np.int64)
        transport = round(
            (forfait_region[cle_region] + TAUX_TRANSPORT_VARIABLE * nets.sum() / 100) * 100
        )
        # Répartition du transport au prorata du montant net, au centime près (plus forts restes).
        parts = transport * nets / nets.sum()
        repartition = np.floor(parts).astype(np.int64)
        reste = transport - int(repartition.sum())
        if reste:
            ordre = np.argsort(-(parts - repartition), kind="stable")
            repartition[ordre[:reste]] += 1
        for numero_ligne, ((indice, quantite, brut, remise, cout), frais) in enumerate(
            zip(lignes, repartition.tolist(), strict=True), start=1
        ):
            enregistrements.append(
                (
                    numero,
                    numero_ligne,
                    jour,
                    cle_client,
                    indice,
                    quantite,
                    brut,
                    remise,
                    cout,
                    frais,
                )
            )
    ventes = pd.DataFrame(
        enregistrements,
        columns=[
            "numero_commande",
            "numero_ligne",
            "date_commande",
            "cle_client",
            "indice_produit",
            "quantite",
            "brut",
            "remise",
            "cout",
            "transport",
        ],
    )
    ventes = _completer_references_non_vendues(rng, ventes, produits, tarifs)
    return ventes


def _completer_references_non_vendues(
    rng: np.random.Generator,
    ventes: pd.DataFrame,
    produits: pd.DataFrame,
    tarifs: dict[str, np.ndarray],
) -> pd.DataFrame:
    """Ajoute une ligne aux commandes existantes pour toute référence non vendue dans l'année.

    La ligne ajoutée porte une quantité de 1, sans remise ni transport supplémentaire.
    """
    ajouts = []
    annees_ventes = ventes["numero_commande"] // 100000
    for annee in ANNEES:
        vendus = set(ventes.loc[annees_ventes == annee, "indice_produit"].tolist())
        commandes_annee = ventes.loc[annees_ventes == annee].drop_duplicates("numero_commande")
        for indice in range(len(produits)):
            if indice in vendus:
                continue
            commande = commandes_annee.iloc[int(rng.integers(len(commandes_annee)))]
            numero = int(commande["numero_commande"])
            jour = commande["date_commande"]
            if annee == 2024:
                prix, cout = tarifs["prix_2024"][indice], tarifs["cout_2024"][indice]
            else:
                prix = tarifs["prix_2025"][indice]
                cle_cout = "cout_2025_hausse" if jour >= DEBUT_HAUSSE_VISSERIE else "cout_2025"
                cout = tarifs[cle_cout][indice]
            ajouts.append(
                (
                    numero,
                    0,
                    jour,
                    int(commande["cle_client"]),
                    indice,
                    1,
                    int(prix),
                    0,
                    int(cout),
                    0,
                )
            )
    if not ajouts:
        return ventes
    complement = pd.DataFrame(ajouts, columns=ventes.columns)
    ventes = pd.concat([ventes, complement], ignore_index=True)
    ventes = ventes.sort_values(["numero_commande", "numero_ligne"], kind="stable")
    ventes["numero_ligne"] = ventes.groupby("numero_commande").cumcount() + 1
    return ventes.reset_index(drop=True)


def _generer_budget(rng: np.random.Generator, ventes: pd.DataFrame) -> pd.DataFrame:
    """Budget mensuel par famille et région.

    2024 : CA net réel 2024 avec une erreur de prévision de ±3 %.
    2025 : CA net réel 2024 × (1 + objectif de croissance de la famille).
    Les deux années sont réparties par mois selon la saisonnalité et le nombre de jours
    ouvrés ; la marge budgétée applique le taux de marge commerciale réel 2024.
    """
    reel_2024 = (
        ventes[ventes["annee"] == 2024]
        .groupby(["cle_famille", "cle_region"])[["net", "cout"]]
        .sum()
        .reset_index()
    )
    reel_2024["taux_marge"] = (reel_2024["net"] - reel_2024["cout"]) / reel_2024["net"]
    lignes = []
    for annee in ANNEES:
        jours = jours_ouvres(annee)
        poids_mois = np.zeros(12)
        for jour in jours:
            poids_mois[jour.month - 1] += SAISONNALITE[jour.month - 1]
        poids_mois /= poids_mois.sum()
        for ligne in reel_2024.itertuples(index=False):
            if annee == 2024:
                annuel = ligne.net * (1 + rng.uniform(-0.03, 0.03))
            else:
                annuel = ligne.net * (1 + OBJECTIFS_BUDGET_2025[int(ligne.cle_famille)])
            mensuel = np.rint(annuel * poids_mois).astype(np.int64)
            marge = np.rint(mensuel * ligne.taux_marge).astype(np.int64)
            for mois in range(12):
                lignes.append(
                    (
                        date(annee, mois + 1, 1),
                        int(ligne.cle_famille),
                        int(ligne.cle_region),
                        int(mensuel[mois]),
                        int(marge[mois]),
                    )
                )
    budget = pd.DataFrame(
        lignes, columns=["mois", "cle_famille", "cle_region", "budget_ca", "budget_marge"]
    )
    return budget.sort_values(["mois", "cle_famille", "cle_region"]).reset_index(drop=True)


def generer() -> dict[str, pd.DataFrame]:
    """Construit toutes les tables, prêtes à être écrites en CSV."""
    rng = np.random.default_rng(GRAINE)
    produits = _generer_produits(rng)
    clients = _generer_clients(rng)
    ventes = _generer_ventes(rng, clients, produits)

    ventes["cle_produit"] = produits["cle_produit"].to_numpy()[ventes["indice_produit"].to_numpy()]
    ventes["cle_famille"] = produits["cle_famille"].to_numpy()[ventes["indice_produit"].to_numpy()]
    ventes = ventes.merge(clients[["cle_client", "cle_commercial", "cle_region"]], on="cle_client")
    ventes = ventes.sort_values(["numero_commande", "numero_ligne"]).reset_index(drop=True)
    ventes["net"] = ventes["brut"] - ventes["remise"]
    ventes["annee"] = ventes["numero_commande"] // 100000
    budget = _generer_budget(rng, ventes)

    tables = {
        "ventes": pd.DataFrame(
            {
                "numero_commande": ventes["numero_commande"],
                "numero_ligne": ventes["numero_ligne"],
                "date_commande": [j.isoformat() for j in ventes["date_commande"]],
                "cle_client": ventes["cle_client"],
                "cle_produit": ventes["cle_produit"],
                "cle_commercial": ventes["cle_commercial"],
                "cle_region": ventes["cle_region"],
                "cle_famille": ventes["cle_famille"],
                "quantite": ventes["quantite"],
                "montant_brut": centimes_vers_texte(ventes["brut"].to_numpy()),
                "montant_remise": centimes_vers_texte(ventes["remise"].to_numpy()),
                "montant_net": centimes_vers_texte(ventes["net"].to_numpy()),
                "cout_achat": centimes_vers_texte(ventes["cout"].to_numpy()),
                "cout_transport": centimes_vers_texte(ventes["transport"].to_numpy()),
            }
        ),
        "budget": pd.DataFrame(
            {
                "mois": [m.isoformat() for m in budget["mois"]],
                "cle_famille": budget["cle_famille"],
                "cle_region": budget["cle_region"],
                "budget_ca_net": centimes_vers_texte(budget["budget_ca"].to_numpy()),
                "budget_marge_commerciale": centimes_vers_texte(budget["budget_marge"].to_numpy()),
            }
        ),
        "clients": clients[["cle_client", "client", "segment", "cle_region", "cle_commercial"]],
        "produits": produits[
            ["cle_produit", "reference", "produit", "sous_famille", "cle_famille"]
        ],
        "commerciaux": pd.DataFrame(
            {
                "cle_commercial": [c[0] for c in COMMERCIAUX],
                "commercial": [c[1] for c in COMMERCIAUX],
                "email": [email(c[1]) for c in COMMERCIAUX],
                "cle_region": [c[2] for c in COMMERCIAUX],
            }
        ),
        "familles": pd.DataFrame(
            {"cle_famille": [f[0] for f in FAMILLES], "famille": [f[1] for f in FAMILLES]}
        ),
        "regions": pd.DataFrame(
            {"cle_region": [r[0] for r in REGIONS], "region": [r[1] for r in REGIONS]}
        ),
    }
    acces = [(email(c[1]), c[2]) for c in COMMERCIAUX] + [(EMAIL_DIRECTION, r[0]) for r in REGIONS]
    tables["acces_regional"] = (
        pd.DataFrame(acces, columns=["email", "cle_region"])
        .sort_values(["email", "cle_region"])
        .reset_index(drop=True)
    )
    return tables


def ecrire(tables: dict[str, pd.DataFrame], dossier: Path) -> None:
    dossier.mkdir(parents=True, exist_ok=True)
    for nom, table in tables.items():
        table.to_csv(dossier / f"{nom}.csv", index=False, lineterminator="\n", encoding="utf-8")


def main(arguments: list[str]) -> None:
    dossier = Path(arguments[0]) if arguments else DOSSIER_DONNEES
    tables = generer()
    ecrire(tables, dossier)
    for nom, table in tables.items():
        print(f"{nom}.csv : {len(table)} lignes")


if __name__ == "__main__":
    main(sys.argv[1:])
