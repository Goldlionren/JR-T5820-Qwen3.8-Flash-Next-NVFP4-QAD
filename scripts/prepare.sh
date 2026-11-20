#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")/.."
export MKL_NUM_THREADS=4 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=1
.venv/bin/python src/tools/nvfp4_local_pack.py prepare --model "$PWD/checkpoint" --out "$PWD/prepared"
install -m644 src/data/draft_vocab.bin prepared/mtp/rt/draft_vocab.bin
python3 scripts/assets.py record
