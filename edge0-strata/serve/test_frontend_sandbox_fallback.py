"""serve must start when the bundled Python's jinja2 lacks the sandbox submodule (#217).

The Windows standalone bundle ships a jinja2 without jinja2.sandbox, so `serve` crashed at startup on
`from jinja2.sandbox import ImmutableSandboxedEnvironment`. The fallback renders the model's own (hash-verified)
chat template with a plain Environment, which is what Hugging Face does for the same templates, so the prompt must
come out byte-identical. The child process blocks the submodule the way the truncated bundle does; no reload tricks
in this process, so other test modules are untouched.
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

from serve.frontend import ChatTemplate

TEMPLATE = Path(__file__).with_name("chat_template.jinja")
MESSAGES = [{"role": "user", "content": "haz un ls"}]

_RENDER = """
import json
import sys
sys.modules["jinja2.sandbox"] = None  # the truncated bundle: jinja2 imports, its sandbox does not
from pathlib import Path
from serve.frontend import ChatTemplate
print(ChatTemplate(Path(sys.argv[1])).render(json.loads(sys.argv[2])))
"""


class SandboxMissing(unittest.TestCase):
    def test_render_without_sandbox_matches(self):
        expected = ChatTemplate(TEMPLATE).render(MESSAGES)
        proc = subprocess.run(
            [sys.executable, "-c", _RENDER, str(TEMPLATE), json.dumps(MESSAGES)],
            capture_output=True, text=True, cwd=Path(__file__).parent.parent)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), expected.strip())
