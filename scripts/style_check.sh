#!/bin/bash

# Check for PEP8 code style violations, but ignore long lines and ambiguous variable names

flake8 --ignore=E501,E741 carta/*.py tests/*.py
