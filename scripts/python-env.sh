#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")/.."
python3.14 -m venv .venv
.venv/bin/python -m pip install --index-url https://download.pytorch.org/whl/cpu 'torch==2.14.1+cpu'
.venv/bin/python -m pip install -r src/requirements.txt -r src/requirements-nvfp4-local.txt 'huggingface_hub==0.36.2' 'tokenizers==0.22.2'
.venv/bin/python -m pip check
.venv/bin/python src/tools/nvfp4_local_pack.py --help >/dev/null
.venv/bin/python src/serve/server.py --help >/dev/null
