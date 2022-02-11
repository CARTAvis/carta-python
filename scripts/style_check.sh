#!/bin/bash

# Check for PEP8 code style violations, but ignore long lines

pycodestyle carta/*.py | grep -v E501
