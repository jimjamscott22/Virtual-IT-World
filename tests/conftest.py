"""Suite-wide guards.

`AppSession.build` reads the environment to pick a persona backend (Task 2),
so without this a developer with `VITSC_PERSONA=lmstudio` exported in their
shell would point the entire suite at a local model. The Global Constraint is
that the suite passes with nothing running on localhost, and that has to hold
regardless of who runs it — so it is enforced here rather than left to habit.

Tests that want the model-backed path set these variables themselves; an
autouse fixture runs before the test body, so `monkeypatch.setenv` inside a
test still wins.
"""

import pytest

VITSC_ENV_VARS = ("VITSC_PERSONA", "VITSC_BASE_URL", "VITSC_MODEL")


@pytest.fixture(autouse=True)
def isolate_vitsc_env(monkeypatch):
    for name in VITSC_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
