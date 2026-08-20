"""The fallback YAML parser must agree with PyYAML on the files we actually ship.

`asdlc` claims zero dependencies, which means on most machines the fallback
parser IS the parser — and it is the least-exercised code in the repo, because
every dev box has PyYAML installed. This test is the only thing standing between
that claim and a client's CI.

    python3 -m pytest tests/test_policy_parser.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from asdlc.yamlish import _mini_yaml  # noqa: E402

yaml = pytest.importorskip("yaml", reason="parity test needs PyYAML as the oracle")

SHIPPED = [
    Path(__file__).parents[1] / "src/asdlc/gates/policy.yaml",
    *sorted((Path(__file__).parents[1] / "src/asdlc/gates/presets").glob("*.yaml")),
    Path(__file__).parents[1] / "src/asdlc/assets/agents/roles.yaml",
]


@pytest.mark.parametrize("path", SHIPPED, ids=lambda p: p.name)
def test_fallback_matches_pyyaml_on_shipped_files(path: Path):
    text = path.read_text()
    assert _mini_yaml(text) == yaml.safe_load(text)


@pytest.mark.parametrize(
    "src",
    [
        "a: 1\nb: two\nc: true\nd: false\ne:\n",
        "list:\n  - one\n  - two\n",
        "nested:\n  inner:\n    - a\n    - b\n  scalar: 3\n",
        "flow: {enabled: true, mode: warn}\n",
        "flowlist: [a, b, c]\n",
        "quoted:\n  - \"src/**\"\n  - '*.py'\n",
        "empty_map:\ntrailing: 1\n",
        "comment: 1  # ignored\n# whole line\nafter: 2\n",
    ],
)
def test_fallback_matches_pyyaml_on_the_subset_we_use(src: str):
    assert _mini_yaml(src) == yaml.safe_load(src)


def test_capabilities_round_trip():
    src = 'capabilities:\n  billing:\n    - "src/billing/**"\n  auth:\n    - "src/auth/**"\n'
    assert _mini_yaml(src) == {
        "capabilities": {"billing": ["src/billing/**"], "auth": ["src/auth/**"]}
    }
