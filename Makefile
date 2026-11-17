PYTHON ?= python3
VENV := .venv
PY := $(VENV)/bin/python

.PHONY: install data docs schemas test lint check

install: ## Crée l'environnement virtuel et installe les dépendances épinglées
	@$(PYTHON) -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 'Python 3.12 minimum requis')"
	$(PYTHON) -m venv $(VENV)
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -r requirements-dev.txt
	$(VENV)/bin/pre-commit install

data: ## Régénère data/, tests/expected/ et tests/validation.dax
	$(PY) scripts/generate_data.py
	$(PY) scripts/expected_values.py
	$(PY) scripts/build_validation_dax.py

docs: ## Régénère docs/mesures.md depuis le modèle TMDL
	$(PY) scripts/generate_docs.py

schemas: ## Met à jour le cache des schémas JSON de tools/schemas/ (connexion requise)
	$(PY) scripts/fetch_schemas.py

test: ## Lance les tests pytest
	$(PY) -m pytest

lint: ## Vérifie le style et la qualité du code Python
	$(VENV)/bin/ruff check .
	$(VENV)/bin/ruff format --check .

check: lint test ## Enchaîne tous les contrôles automatiques, sans connexion
	$(PY) scripts/check_schemas.py
	$(PY) scripts/check_bindings.py
	$(PY) scripts/check_model.py
	$(PY) scripts/check_layout.py
	$(PY) scripts/check_texts.py
