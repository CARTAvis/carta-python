#!/bin/bash

# Fix PEP8 code style violations, but ignore long lines

echo "Fixing issues automatically..."

autopep8 --in-place --ignore E501 carta/*.py tests/*.py

# Check for PEP8 code style violations, but ignore long lines and ambiguous variable names

echo "Outstanding issues:"

flake8 --ignore=E501,E741 carta/*.py tests/*.py
