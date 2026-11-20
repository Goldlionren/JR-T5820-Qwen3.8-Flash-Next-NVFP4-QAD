"""Render an install for a single-card, single-socket T5820. Existing settings and keys are preserved."""
import argparse
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import stat
import subprocess

root = Path(__file__).resolve().parents[1]


def placement():
    groups = {}
    for cpu in sorted(os.sched_getaffinity(0)):
        topo = Path(f"/sys/devices/system/cpu/cpu{cpu}/topology")
        identity = tuple(int((topo/key).read_text()) for key in ("physical_package_id","core_id"))
        groups.setdefault(identity, []).append(cpu)
    pairs = sorted([pair for pair in groups.values() if len(pair)==2])
    if len(pairs)<14 or len({k[0] for k in groups})!=1:
        raise SystemExit("This CPU preset requires a single socket and at least 14 complete SMT pairs")
    chosen = pairs[-10:]
    host = min(chosen[0])
    workers = sorted(cpu for pair in chosen[1:] for cpu in pair)
    return host, workers, sorted(cpu for pair in chosen for cpu in pair)


def keyfile():
    path = root/"secrets/api.key"
    path.parent.mkdir(mode=0o700, exist_ok=True)
    if not path.exists():
        with path.open("x") as f:
            f.write(secrets.token_urlsafe(48)+"\n")
    if not stat.S_ISREG(path.lstat().st_mode) or path.stat().st_mode & 0o077:
        raise SystemExit("secrets/api.key must be a private regular file (chmod 600)")
    value=path.read_text().strip()
    if len(value)<32 or re.search(r"[,\s]",value):
        raise SystemExit("Use one key with at least 32 characters and no whitespace or comma")


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--host", type=ipaddress.IPv4Address,default=ipaddress.IPv4Address("127.0.0.1"))
    ap.add_argument("--gpu",help="exact local GPU UUID from nvidia-smi -L; defaults to the sole RTX 5060 Ti")
    args=ap.parse_args()
    if args.host.is_unspecified or args.host.is_multicast:
        ap.error("Specify loopback or one assigned IPv4 address")
    if not re.fullmatch(r"/[A-Za-z0-9_./ -]+",str(root)):
        ap.error("Choose an install path with letters, digits, spaces, dots, hyphens and underscores")
    files = [root/"strata.json",root/"strata-fp4-local.service"]
    if any(p.exists() for p in files):
        ap.error("Configuration already exists; back it up and edit it, or render in a fresh clone")
    records = subprocess.check_output(["nvidia-smi","--query-gpu=uuid,name,memory.total","--format=csv,noheader,nounits"],text=True)
    cards = [row.split(',')[0].strip() for row in records.splitlines()
             if "RTX 5060 Ti" in row and int(row.split(',')[-1])>=15000]
    gpu = args.gpu or (cards[0] if len(cards)==1 else None)
    if gpu not in cards:
        ap.error("A 16 GB RTX 5060 Ti must be selected")
    host, workers, cpus = placement()
    os.umask(0o077)
    keyfile()
    (root/"runtime").mkdir(mode=0o700,exist_ok=True)
    cfg=json.loads((root/"config/strata.template.json").read_text().replace("@ROOT@",str(root)))
    cfg["env"]["CUDA_VISIBLE_DEVICES"]=gpu
    cfg["host"]=str(args.host)
    flags=cfg["args"]
    flags[flags.index("--pool-cores")+1]=",".join(map(str,workers))
    # 'first' uses the lowest CPU in the service affinity, verified by placement().
    assert host==min(cpus)
    unit=(root/"config/service.in").read_text().replace("@ROOT@",str(root)).replace("@CPUS@"," ".join(map(str,cpus)))
    files[0].write_text(json.dumps(cfg,indent=2)+"\n")
    files[1].write_text(unit)
    print("Rendered",files[0], "and user unit. Host core:",host,"Workers:",workers)


if __name__=="__main__":
    main()
