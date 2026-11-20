"""Fetch the exact HF checkpoint without a second weight cache, then verify source bytes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
manifest = json.loads((ROOT / "manifests/checkpoint.json").read_text())
projector = "mmproj-Qwen3.8-Flash-Next-BF16.gguf"
vision_url = ("https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF/resolve/"
              "ed59f92082b1e93c0e96d60a8b11aab089b52f09/" + projector)
vision_sha = "b1a82259702816a5330d7bd7607cd9676b11780e79ff7348c21103ff3ce49bd0"


def verify_checkpoint(directory):
    for file in manifest["files"]:
        path = directory / file["name"]
        if path.stat().st_size != file["size"]:
            raise ValueError(f"Wrong size: {path.name}")
        with path.open("rb") as stream:
            if file["lfs"]:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
                expected = file["lfs"]["sha256"]
            else:
                h = hashlib.sha1(f"blob {file['size']}\0".encode())
                h.update(stream.read())
                digest, expected = h.hexdigest(), file["blob_id"]
        if digest != expected:
            raise ValueError(f"Wrong digest: {path.name}")
    print(f"Verified {len(manifest['files'])} checkpoint files", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--checkpoint", type=Path, default=ROOT/"checkpoint")
    args = parser.parse_args()
    if not args.verify_only:
        os.environ.setdefault("HF_XET_CHUNK_CACHE_SIZE_BYTES","0")
        from huggingface_hub import snapshot_download
        snapshot_download(repo_id=manifest["repo_id"], revision=manifest["revision"],
                          allow_patterns=[f["name"] for f in manifest["files"]],
                          local_dir=args.checkpoint, max_workers=2)
    verify_checkpoint(args.checkpoint)
    if not args.verify_only:
        dest = ROOT/"assets"/projector
        dest.parent.mkdir(exist_ok=True)
        tmp = dest.with_suffix(".partial")
        target = dest if dest.exists() else tmp
        if target == tmp and (not tmp.exists() or tmp.stat().st_size != 907543008):
            subprocess.run(["curl","--fail","--location","--retry","3","--continue-at","-",
                            "--output",str(tmp),vision_url],check=True)
        with target.open("rb") as stream:
            if hashlib.file_digest(stream,"sha256").hexdigest() != vision_sha:
                raise ValueError(f"Vision projector digest mismatch: {target}")
        if target == tmp:
            tmp.replace(dest)
