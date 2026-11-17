PYTHON ?= python3
VENV := .venv
PY := $(VENV)/bin/python

.PHONY: install data test lint check

install: ## Crée l'environnement virtuel et installe les dépendances épinglées
	@$(PYTHON) -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 'Python 3.12 minimum requis')"
	$(PYTHON) -m venv $(VENV)
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -r requirements-dev.txt
	$(VENV)/bin/pre-commit install

data: ## Régénère les CSV de data/ puis les valeurs attendues de tests/expected/
	$(PY) scripts/generate_data.py
	$(PY) scripts/expected_values.py

test: ## Lance les tests pytest
	$(PY) -m pytest

lint: ## Vérifie le style et la qualité du code Python
	$(VENV)/bin/ruff check .
	$(VENV)/bin/ruff format --check .

check: lint test ## Enchaîne tous les contrôles automatiques
