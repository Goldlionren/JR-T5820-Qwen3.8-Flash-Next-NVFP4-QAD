"""Start, preload or inspect the upstream native API. No HTTP adapter."""
import argparse
import json
import os
from pathlib import Path
import time
from urllib.request import ProxyHandler, Request, build_opener
from urllib.error import HTTPError, URLError

root = Path(__file__).resolve().parents[1]
opener = build_opener(ProxyHandler({}))


def config():
    return json.loads((root/"strata.json").read_text())


def key():
    return (Path(os.getenv("CREDENTIALS_DIRECTORY",root/"secrets"))/"api.key").read_text().strip()


def api(path,body=None,timeout=10):
    req=Request(f"http://{config()['host']}:10001"+path, data=None if body is None else json.dumps(body).encode(),
                headers={"Authorization":"Bearer "+key(),"Content-Type":"application/json"})
    with opener.open(req, timeout=timeout) as response:
        return json.load(response)


def serve():
    cfg=config()
    env={**os.environ,"STRATA_API_KEY":key(),"CUDA_VISIBLE_DEVICES":cfg["env"]["CUDA_VISIBLE_DEVICES"]}
    python=str(root/".venv/bin/python")
    os.execve(python,[python,str(root/"src/serve/server.py"),"--engine","strata","--config",str(root/"strata.json"),
                      "--host",cfg["host"],"--port","10001","--lazy","--offline","--shutdown-timeout","120"],env)


def preload():
    deadline=time.monotonic()+45
    while True:
        try:
            health=api("/health",timeout=3)
            break
        except HTTPError:
            raise
        except (URLError,TimeoutError):
            if time.monotonic()>=deadline:
                raise
            time.sleep(1)
    if not health["loaded"]:
        api("/load",{},timeout=590)
    if not api("/health")["loaded"]:
        raise SystemExit("API is listening but the model is not READY")
    print("Native model READY")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=["serve","preload","status","models","smoke"])
    action=parser.parse_args().action
    if action=="serve":
        serve()
    elif action=="preload":
        preload()
    elif action=="status":
        print(json.dumps(api("/health")))
    elif action=="models":
        print(json.dumps(api("/v1/models")))
    else:
        print(json.dumps(api("/v1/chat/completions",{"model":config()["aliases"][0],"reasoning_effort":"none",
            "max_tokens":32,"messages":[{"role":"user","content":"Reply OK."}]},timeout=150),ensure_ascii=False))
