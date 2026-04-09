#!/bin/bash

# Fix PEP8 code style violations, but ignore long lines

echo "Fixing issues automatically..."

autopep8 --in-place --ignore E501 carta/*.py tests/*.py

echo "Outstanding issues:"

# Check for PEP8 code style violations, but ignore long lines and ambiguous variable names
# Check only for missing docstrings, except for __init__

flake8 --ignore=E501,E741,D --extend-select D10 --extend-ignore D107 carta/*.py

# Also ignore docstring warnings in unit tests

flake8 --ignore=E501,E741,D tests/*.py
