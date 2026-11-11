#!/usr/bin/env sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements/linux.txt
if [ ! -f .env ]; then cp .env.example .env; chmod 600 .env; fi
printf '%s\n' 'Configure .env, crie o banco e instale Pango conforme README.md antes de migrar.'
