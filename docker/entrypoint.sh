#!/usr/bin/env sh
set -eu

python -m canoptek_calculator.cli bootstrap
exec "$@"
