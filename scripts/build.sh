#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")/.."
cuda=${CUDA_HOME:-/usr/local/cuda-13.0}
jobs=${BUILD_JOBS:-2}
host=${CXX:-g++-15}
host=$(command -v "$host")
test -x "$cuda/bin/nvcc"
export PATH="$cuda/bin:$PATH"
# nvcc's host dialect must match the C++20 headers in the production patch.
cmake -S src -B .build/engine -G Ninja -DCMAKE_BUILD_TYPE=Release \
    -DSTRATA_ENABLE_CUDA=ON -DSTRATA_NATIVE_EXPERTS=ON -DSTRATA_PORTABLE=ON \
    -DCMAKE_CUDA_ARCHITECTURES=120 -DCMAKE_CUDA_FLAGS=-std=c++20 \
    -DCMAKE_CUDA_COMPILER="$cuda/bin/nvcc" -DCUDAToolkit_ROOT="$cuda" \
    -DCMAKE_CXX_COMPILER="$host" -DCMAKE_CUDA_HOST_COMPILER="$host"
cmake --build .build/engine --target strata --parallel "$jobs"
cmake -S src/tools/vision -B .build/vision -G Ninja -DCMAKE_BUILD_TYPE=Release \
    -DLLAMA_DIR="$PWD/src/third_party/llama.cpp" -DSTRATA_VISION_CUDA=OFF -DSTRATA_PORTABLE=ON
cmake --build .build/vision --target strata-vision --parallel "$jobs"
mkdir -p bin
install -m755 .build/engine/strata bin/strata
install -m755 .build/vision/bin/strata-vision bin/strata-vision
(cd bin && sha256sum strata strata-vision > SHA256SUMS)
