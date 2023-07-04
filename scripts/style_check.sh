#!/bin/bash

# Check for PEP8 code style violations, but ignore long lines and ambiguous variable names

pycodestyle --ignore=E501,E741 carta/*.py tests/*.py
