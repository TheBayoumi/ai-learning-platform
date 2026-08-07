"""One-shot bounded repair for PR #10; deleted by its invoking workflow."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def _replace_once(path: str, old: str, new: str) -> None:
    file_path = Path(path)
    text = file_path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"expected one match in {path}, found {count}: {old!r}")
    file_path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")


def patch() -> None:
    workflow_path = Path(".github/workflows/ci.yml")
    workflow = workflow_path.read_text(encoding="utf-8")
    draft_guard = "    if: ${{ github.event.pull_request.draft == false }}\n"
    if workflow.count(draft_guard) != 4:
        raise RuntimeError("unexpected draft guard count")
    workflow = workflow.replace(draft_guard, "")

    projection_guard = (
        "    if: ${{ always() && github.event.pull_request.draft == false }}\n"
    )
    if workflow.count(projection_guard) != 1:
        raise RuntimeError("projection guard not found exactly once")
    workflow = workflow.replace(projection_guard, "    if: ${{ always() }}\n", 1)
    workflow_path.write_text(workflow, encoding="utf-8", newline="\n")

    phase_path = "apps/api/src/ai_learning_platform_api/automation/phase_gate.py"
    _replace_once(
        phase_path,
        """    if \"pull_request:\" not in text or 'branches: [main, \"automation/**\"]' not in text:\n        raise _violation(\"workflow_trigger_invalid\")\n""",
        """    trigger = re.search(\n        r\"^on:\\n(?P<body>.*?)(?=^\\S)\",\n        text,\n        re.MULTILINE | re.DOTALL,\n    )\n    expected_trigger = (\n        \"  pull_request:\\n\"\n        \"    branches: [main]\\n\"\n        \"    types: [opened, reopened, ready_for_review]\\n\\n\"\n    )\n    if trigger is None or trigger.group(\"body\") != expected_trigger:\n        raise _violation(\"workflow_trigger_invalid\")\n""",
    )
    _replace_once(
        phase_path,
        "    expected_expression = \"EXACT_HEAD_SHA: ${{ github.event.pull_request.head.sha || github.sha }}\"\n",
        "    expected_expression = \"EXACT_HEAD_SHA: ${{ github.event.pull_request.head.sha }}\"\n",
    )
    _replace_once(phase_path, '        "api": 10,\n', '        "api": 12,\n')

    test_path = "apps/api/tests/test_phase_gate.py"
    _replace_once(
        test_path,
        """        (\n            'branches: [main, \"automation/**\"]',\n            \"branches: [main]\",\n            \"workflow_trigger_invalid\",\n        ),\n""",
        """        (\n            \"branches: [main]\",\n            \"branches: [develop]\",\n            \"workflow_trigger_invalid\",\n        ),\n        (\n            \"types: [opened, reopened, ready_for_review]\",\n            \"types: [opened, reopened, synchronize, ready_for_review]\",\n            \"workflow_trigger_invalid\",\n        ),\n        (\n            \"  pull_request:\\n\",\n            \"  pull_request:\\n  push:\\n\",\n            \"workflow_trigger_invalid\",\n        ),\n""",
    )

    compatibility_path = (
        "apps/api/src/ai_learning_platform_api/transport/http/"
        "persistent_compatibility.py"
    )
    _replace_once(
        compatibility_path,
        "from typing import Annotated, TypeVar\n",
        "from typing import Annotated\n",
    )
    _replace_once(compatibility_path, 'T = TypeVar("T")\n', "")
    _replace_once(
        compatibility_path,
        "async def _run(operation: Callable[[], Awaitable[T]]) -> T:\n",
        "async def _run[T](operation: Callable[[], Awaitable[T]]) -> T:\n",
    )


def refresh_hashes() -> None:
    governed = (
        ".github/workflows/ci.yml",
        "apps/api/src/ai_learning_platform_api/automation/phase_gate.py",
        "apps/api/tests/test_phase_gate.py",
    )
    state_path = Path("plans/autonomous-loop/state.json")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    hashes = state["authoritative_file_hashes"]
    for relative in governed:
        data = Path(relative).read_bytes().replace(b"\r\n", b"\n")
        hashes[relative] = hashlib.sha256(data).hexdigest()
        print(f"{relative}={hashes[relative]}")
    state_path.write_text(
        json.dumps(state, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("patch", "refresh-hashes"))
    args = parser.parse_args()
    if args.mode == "patch":
        patch()
    else:
        refresh_hashes()


if __name__ == "__main__":
    main()
