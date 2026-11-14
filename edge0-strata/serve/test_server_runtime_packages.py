"""serve's startup dependency preflight (see require_runtime_packages in server.py).

#217: the Windows standalone shipped a Python whose jinja2 lacks the sandbox submodule, so `serve`
died at import with a bare ModuleNotFoundError. The preflight must catch exactly that shape — a jinja2
package that imports fine but has no `jinja2.sandbox` — and say which package is missing and how to repair it.
"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run_server_help(env_extra):
    env = dict(os.environ)
    env.update(env_extra)
    return subprocess.run([sys.executable, "-m", "serve.server", "--help"],
                          cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)


class ServerRuntimePackages(unittest.TestCase):
    def test_missing_jinja2_sandbox_fails_with_repair_message(self):
        # A jinja2 package with no sandbox submodule, as the broken bundle shipped it: `import jinja2`
        # succeeds, `from jinja2.sandbox import ...` fails. The preflight must fail first, naming the
        # missing submodule, the pinned package and the requirements file — not a bare traceback.
        with tempfile.TemporaryDirectory() as tmp:
            pkg = Path(tmp) / "jinja2"
            pkg.mkdir()
            (pkg / "__init__.py").write_text('__version__ = "3.1.6"\n', encoding="utf-8")
            env = {"PYTHONPATH": tmp + os.pathsep + os.environ.get("PYTHONPATH", "")}
            proc = _run_server_help(env)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("jinja2.sandbox", proc.stderr)
        self.assertIn("jinja2==3.1.6", proc.stderr)
        self.assertIn("requirements.txt", proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)

    def test_healthy_python_starts_help(self):
        # With the pinned requirements installed the preflight passes through and --help works as before.
        proc = _run_server_help({})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("usage", proc.stdout.lower() + proc.stderr.lower())


if __name__ == "__main__":
    unittest.main()
