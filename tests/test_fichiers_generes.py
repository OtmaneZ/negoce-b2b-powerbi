"""Les fichiers générés par script sont à jour dans le dépôt."""

import build_validation_dax
import expected_values
import generate_docs
import tmdl


def test_dictionnaire_des_mesures_a_jour():
    assert generate_docs.FICHIER.read_text(encoding="utf-8") == generate_docs.construire()


def test_requete_de_validation_a_jour():
    actuel = build_validation_dax.FICHIER_DAX.read_text(encoding="utf-8")
    assert actuel == build_validation_dax.construire()


def test_requete_de_validation_couvre_chaque_valeur_attendue():
    lignes = build_validation_dax.lignes_attendues()
    texte = build_validation_dax.FICHIER_DAX.read_text(encoding="utf-8")
    assert texte.count('ROW("N°"') == len(lignes)


def test_mesures_du_modele_et_valeurs_attendues_coherentes():
    """Chaque mesure du modèle a une valeur attendue, et réciproquement."""
    modele = {mesure.nom for _, mesure in tmdl.lire_modele().mesures()}
    contenu = expected_values.calculer()["2025_total"]
    attendues = {ligne["mesure"] for ligne in contenu["mesures"]}
    assert modele == attendues
