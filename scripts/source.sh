#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")/.."
base=13eedf552417a6a791a7d13c6597e24300ee3a09
llama=3cf03257f219afbe7334045ff7c6a06ac68c627d
if [[ -e src ]]; then echo 'src already exists; use a fresh directory for a new baseline' >&2; exit 1; fi
mkdir -p .build
tmp=$(mktemp -d .build/source.XXXXXX)
trap 'rm -rf -- "$tmp"' EXIT
checkout() {
    git init -q "$1"
    git -C "$1" fetch -q --depth=1 "$2" "$3"
    git -C "$1" checkout -q --detach FETCH_HEAD
    test "$(git -C "$1" rev-parse HEAD)" = "$3"
}
checkout "$tmp/src" https://github.com/Niko1221/Strata.git "$base"
git -C "$tmp/src" apply --index "$PWD/patches/engine.patch"
test "$(git -C "$tmp/src" write-tree)" = c4a123a442cecfca881967fb1f426da9ea7ee6c3
git -C "$tmp/src" apply --index "$PWD/patches/long-prefill.patch"
test "$(git -C "$tmp/src" write-tree)" = 1b88de958f5a7945f9b70576a86a21a19e866dcb
for patch in server-model server-history; do
    git -C "$tmp/src" apply "$PWD/patches/$patch.patch"
done
checkout "$tmp/src/third_party/llama.cpp" https://github.com/ggml-org/llama.cpp.git "$llama"
(cd "$tmp/src" && sha256sum --check --strict "$OLDPWD/manifests/source.sha256")
mv "$tmp/src" src
