from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path

import pytest


@pytest.fixture(scope="session", autouse=True)
def agentdoctor_test_root() -> Path:
    root = Path(__file__).resolve().parents[1] / ".tmp_pytest_base" / "agentdoctor" / uuid.uuid4().hex
    root.mkdir(parents=True, exist_ok=True)
    previous = os.environ.get("AGENTDOCTOR_TEST_ROOT")
    os.environ["AGENTDOCTOR_TEST_ROOT"] = str(root)
    try:
        yield root
    finally:
        if previous is None:
            os.environ.pop("AGENTDOCTOR_TEST_ROOT", None)
        else:
            os.environ["AGENTDOCTOR_TEST_ROOT"] = previous
        shutil.rmtree(root, ignore_errors=True)
