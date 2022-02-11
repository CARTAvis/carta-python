#!/bin/bash

# Fix PEP8 code style violations, but ignore long lines

echo "Fixing issues automatically (except long lines)..."

autopep8 --in-place --ignore E501 carta/*.py

# Check for PEP8 code style violations, but ignore long lines

echo "Outstanding issues (except long lines):"

pycodestyle carta/*.py | grep -v E501
