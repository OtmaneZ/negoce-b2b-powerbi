from pathlib import Path

import pandas as pd
import pytest

RACINE = Path(__file__).resolve().parent.parent
DONNEES = RACINE / "data"


@pytest.fixture(scope="session")
def tables() -> dict[str, pd.DataFrame]:
    """Les huit fichiers CSV du dossier data/."""
    return {fichier.stem: pd.read_csv(fichier) for fichier in sorted(DONNEES.glob("*.csv"))}


@pytest.fixture(scope="session")
def ventes(tables) -> pd.DataFrame:
    """Lignes de vente enrichies : année, mois, montants en centimes, libellés."""
    v = tables["ventes"].copy()
    dates = pd.to_datetime(v["date_commande"])
    v["date"] = dates.dt.date
    v["annee"] = dates.dt.year
    v["mois"] = dates.dt.month
    for colonne in (
        "montant_brut",
        "montant_remise",
        "montant_net",
        "cout_achat",
        "cout_transport",
    ):
        v[colonne + "_c"] = (v[colonne] * 100).round().astype("int64")
    v["marge_c"] = v["montant_net_c"] - v["cout_achat_c"]
    v["contributive_c"] = v["marge_c"] - v["cout_transport_c"]
    v = v.merge(tables["regions"], on="cle_region")
    v = v.merge(tables["familles"], on="cle_famille")
    v = v.merge(tables["commerciaux"][["cle_commercial", "commercial"]], on="cle_commercial")
    return v
