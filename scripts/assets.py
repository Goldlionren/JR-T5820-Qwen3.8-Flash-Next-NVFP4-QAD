"""Check pack, projector, source and local binaries. Rehash changed assets at startup."""
import argparse
import hashlib
import json
from pathlib import Path
import os
import tempfile

root = Path(__file__).resolve().parents[1]


def stamp(p):
    s = p.stat()
    return [s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns]


def lines(manifest, prefix):
    for line in manifest.read_text().splitlines():
        sha, name = line.split("  ", 1)
        yield str(prefix / name), sha


def check(record):
    out = root / "runtime/asset-stamps.json"
    known = {} if record else json.loads(out.read_text())
    verified = {}
    items = list(lines(root/"manifests/pack.sha256", Path("prepared")))
    items += list(lines(root/"manifests/source.sha256", Path("src")))
    items += list(lines(root/"bin/SHA256SUMS", Path("bin")))
    items.append(("assets/mmproj-Qwen3.8-Flash-Next-BF16.gguf",
                  "b1a82259702816a5330d7bd7607cd9676b11780e79ff7348c21103ff3ce49bd0"))
    for name, sha in items:
        path = root/name
        meta = stamp(path)
        if record or known.get(name) != [sha, meta]:
            with path.open("rb") as f:
                if hashlib.file_digest(f, "sha256").hexdigest() != sha or stamp(path) != meta:
                    raise ValueError(f"Asset mismatch: {name}")
        verified[name] = [sha, meta]
    if record or known != verified:
        out.parent.mkdir(mode=0o700, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w",dir=out.parent,delete=False) as f:
            json.dump(verified,f)
        os.replace(f.name,out)
    print(f"{len(items)} required assets verified", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action", choices=["record","check"])
    check(ap.parse_args().action=="record")
