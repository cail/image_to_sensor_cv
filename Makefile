.PHONY: help quick check validate format lint type-check security clean install black isort flake8 pylint mypy bandit syntax manifest common

help:
	@echo "Image to Sensor CV - Development Commands"
	@echo ""
	@echo "Quick checks:"
	@echo "  make quick       - Fast syntax and config check (no dependencies)"
	@echo "  make check       - Alias for 'make quick'"
	@echo ""
	@echo "Full validation:"
	@echo "  make validate    - Run all static analysis checks"
	@echo ""
	@echo "Individual checks:"
	@echo "  make black       - Check code formatting (Black)"
	@echo "  make isort       - Check import sorting"
	@echo "  make flake8      - Run flake8 linter"
	@echo "  make pylint      - Run pylint with scoring"
	@echo "  make mypy        - Run type checking"
	@echo "  make bandit      - Run security scan"
	@echo "  make syntax      - Check Python syntax"
	@echo "  make manifest    - Validate manifest.json"
	@echo "  make common      - Check for common issues"
	@echo ""
	@echo "Combined checks:"
	@echo "  make lint        - Run flake8 + pylint"
	@echo "  make type-check  - Alias for mypy"
	@echo "  make security    - Alias for bandit"
	@echo ""
	@echo "Code formatting:"
	@echo "  make format      - Auto-format code with black and isort"
	@echo ""
	@echo "Setup:"
	@echo "  make install     - Install development dependencies"
	@echo "  make clean       - Remove cache files and reports"

quick:
	@./quick-check.sh

check: quick

validate:
	@./validate.sh

# Individual checkers
black:
	@./validate.sh black

isort:
	@./validate.sh isort

flake8:
	@./validate.sh flake8

pylint:
	@./validate.sh pylint

mypy:
	@./validate.sh mypy

bandit:
	@./validate.sh bandit

syntax:
	@./validate.sh syntax

manifest:
	@./validate.sh manifest

common:
	@./validate.sh common

# Combined targets
lint: flake8 pylint

type-check: mypy

security: bandit

format:
	@echo "Formatting code with black..."
	@black *.py
	@echo "Sorting imports with isort..."
	@isort *.py
	@echo "✓ Code formatted"

test:
	python3 -m tests.validate_vectors

install:
	@./validate.sh setup

clean:
	@echo "Cleaning up..."
	@rm -rf __pycache__ .mypy_cache .pytest_cache
	@rm -f .pylint_report.txt .mypy_report.txt .bandit_report.txt
	@find . -name "*.pyc" -delete
	@echo "✓ Cleanup complete"
