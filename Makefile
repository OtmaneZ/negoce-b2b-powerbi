PYTHON ?= python3
VENV := .venv
PY := $(VENV)/bin/python

.PHONY: install data docs test lint check

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

test: ## Lance les tests pytest
	$(PY) -m pytest

lint: ## Vérifie le style et la qualité du code Python
	$(VENV)/bin/ruff check .
	$(VENV)/bin/ruff format --check .

check: lint test ## Enchaîne tous les contrôles automatiques
