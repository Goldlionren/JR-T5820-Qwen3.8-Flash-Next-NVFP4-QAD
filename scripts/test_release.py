"""Small, offline tests of installation-specific protections."""
import contextlib
import io
import importlib.machinery
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import configure
import native

class InstallTests(unittest.TestCase):
    def test_existing_secret_survives_render(self):
        with tempfile.TemporaryDirectory() as d, patch.object(configure,"root",Path(d)):
            p=Path(d)/"secrets/api.key"
            p.parent.mkdir(mode=0o700)
            p.write_text("x"*40)
            p.chmod(0o600)
            configure.keyfile()
            self.assertEqual(p.read_text(),"x"*40)
            p.chmod(0o644)
            with self.assertRaises(SystemExit):
                configure.keyfile()

    def test_preload_handles_a_lazy_api_and_checks_ready(self):
        states=[{"loaded":False},{},{"loaded":True}]
        with patch.object(native,"api",side_effect=states) as api,contextlib.redirect_stdout(io.StringIO()):
            native.preload()
            self.assertEqual([call.args[0] for call in api.call_args_list],["/health","/load","/health"])
        with patch.object(native,"api",side_effect=[{"loaded":False},{},{"loaded":False}]):
            with self.assertRaises(SystemExit):
                native.preload()

    def test_vector_switch_and_failed_reload_rollback(self):
        script=Path(__file__).with_name("strata-cvec")
        loader=importlib.machinery.SourceFileLoader("public_cvec",str(script))
        spec=importlib.util.spec_from_loader(loader.name,loader)
        module=importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)
            (folder/"config").mkdir()
            (folder/"runtime").mkdir()
            template=(script.parents[1]/"config/strata.template.json").read_bytes()
            (folder/"config/strata.template.json").write_bytes(template)
            cfg=folder/"strata.json"
            cfg.write_text(template.decode().replace("@ROOT@",str(folder)))
            def state(cvec):
                return dict(loaded=True,cvec=cvec,state="idle",queued=0,in_flight=0)
            with patch.object(module,"root",folder), patch.object(module,"config",side_effect=lambda:json.loads(cfg.read_text())), \
                 patch.object(module.subprocess,"check_output",return_value=str(folder)), \
                 patch.object(module.subprocess,"run") as ctl, contextlib.redirect_stdout(io.StringIO()):
                with patch.object(module,"view",return_value=state("project:4-44")):
                    module.main("on")
                    ctl.assert_not_called()
                with patch.object(module,"view",side_effect=[state("project:4-44"),state("0")]):
                    module.main("off")
                    self.assertNotIn("--control-vector-scaled",json.loads(cfg.read_text())["args"])
                previous=cfg.read_bytes()
                with patch.object(module,"view",side_effect=[state("0"),state("0"),state("0")]):
                    with self.assertRaisesRegex(RuntimeError,"New mode"):
                        module.main("on")
                self.assertEqual(previous,cfg.read_bytes())

    def test_service_settings(self):
        root=Path(__file__).resolve().parents[1]
        cfg=json.loads((root/"config/strata.template.json").read_text())
        flags=cfg["args"]
        for key,val in {"--pool-workers":"18","--max-context":"262144","--kv":"bf16",
                        "--spec":"4","--spec-min-p":"0.65","--conversation-cache-mib":"5120"}.items():
            self.assertEqual(flags[flags.index(key)+1],val)
        self.assertEqual(cfg["host"],"127.0.0.1")
        unit=(root/"config/service.in").read_text().splitlines()
        for line in ["MemoryMax=85G","MemorySwapMax=0","Environment=STRATA_PF_GROUP_SCRATCH=1",
                     "LoadCredential=api.key:@ROOT@/secrets/api.key"]:
            self.assertIn(line,unit)

if __name__=="__main__":
    unittest.main()
