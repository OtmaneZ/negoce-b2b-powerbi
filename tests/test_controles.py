"""Les contrôles automatiques détectent bien les défauts qu'ils doivent signaler."""

import copy
import json

from referencing import Registry

import check_bindings
import check_layout
import check_model
import check_schemas
import tmdl


def test_schema_detecte_une_propriete_inconnue(tmp_path):
    source = next(check_layout.PAGES.rglob("visual.json"))
    visuel = json.loads(source.read_text(encoding="utf-8"))
    visuel["visual"]["proprieteInconnue"] = 1
    visuel["position"]["x"] = "vingt"
    fichier = tmp_path / "visual.json"
    fichier.write_text(json.dumps(visuel), encoding="utf-8")
    erreurs = check_schemas.valider(fichier, Registry(retrieve=check_schemas._recuperer))
    assert len(erreurs) == 2


def test_liaison_detecte_une_mesure_inconnue():
    visuel = {
        "visual": {
            "query": {
                "queryState": {
                    "Y": {
                        "projections": [
                            {
                                "field": {
                                    "Measure": {
                                        "Expression": {"SourceRef": {"Entity": "Mesures"}},
                                        "Property": "Mesure absente",
                                    }
                                },
                                "queryRef": "Mesures.Mesure absente",
                            }
                        ]
                    }
                }
            }
        }
    }
    trouvees = list(check_bindings.references(visuel))
    assert trouvees == [("Measure", "Mesures", "Mesure absente")]
    connues = {mesure.nom for _, mesure in tmdl.lire_modele().mesures()}
    assert "Mesure absente" not in connues


def test_liaison_resout_les_alias_de_filtre():
    filtre = {
        "From": [{"Name": "m", "Entity": "Mesures", "Type": 0}],
        "Where": [
            {
                "Condition": {
                    "Comparison": {
                        "Left": {
                            "Measure": {
                                "Expression": {"SourceRef": {"Source": "m"}},
                                "Property": "CA net",
                            }
                        }
                    }
                }
            }
        ],
    }
    assert list(check_bindings.references(filtre)) == [("Measure", "Mesures", "CA net")]


def test_regles_de_modele_detectent_les_ecarts():
    modele = copy.deepcopy(tmdl.lire_modele())
    assert check_model.controler(modele) == []
    modele.relations[0].proprietes["crossFilteringBehavior"] = "bothDirections"
    mesure = modele.tables["Mesures"].enfants_de_type("measure")[0]
    mesure.description = ""
    del mesure.proprietes["formatString"]
    modele.modele.annotations.pop("__PBI_TimeIntelligenceEnabled")
    erreurs = " | ".join(check_model.controler(modele))
    assert "bothDirections" in erreurs
    assert "description manquante" in erreurs
    assert "format manquant" in erreurs
    assert "date/heure automatique" in erreurs


def test_mise_en_page_detecte_chevauchement_debordement_et_trame():
    pages = check_layout.lire_pages()
    assert check_layout.controler(pages) == []
    pages = copy.deepcopy(pages)
    visuels = pages[0]["visuels"]
    visuels[0]["rect"] = visuels[1]["rect"]
    visuels[2]["rect"] = (1200, 700, 120, 40)
    visuels[3]["rect"] = (25, 32, 120, 96)
    erreurs = " | ".join(check_layout.controler(pages))
    assert "chevauche" in erreurs
    assert "hors du canevas" in erreurs
    assert "hors trame" in erreurs
    assert "zones différentes" in erreurs
