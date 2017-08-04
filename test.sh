#! /bin/bash
mypy --ignore-missing-imports rememberscript/*.py
pytest
