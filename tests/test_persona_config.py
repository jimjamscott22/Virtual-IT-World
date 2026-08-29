from fastapi.testclient import TestClient

from vitsc.persona.config import PersonaSettings, build_persona
from vitsc.persona.client import LMStudioPersona
from vitsc.persona.templates import TemplatePersona
from vitsc.web.app import create_app
from vitsc.web.deps import AppSession
from vitsc.web.routes.events import build_payload


def test_defaults_to_the_template_persona():
    assert isinstance(build_persona(PersonaSettings.from_env()), TemplatePersona)


def test_env_selects_the_model_persona(monkeypatch):
    monkeypatch.setenv("VITSC_PERSONA", "lmstudio")
    monkeypatch.setenv("VITSC_MODEL", "qwen2.5-7b-instruct")
    settings = PersonaSettings.from_env()
    assert settings.backend == "lmstudio"
    assert settings.model == "qwen2.5-7b-instruct"


def test_unknown_backend_falls_back_to_the_template(monkeypatch):
    """A typo in the environment must not take the drill down."""
    monkeypatch.setenv("VITSC_PERSONA", "lmstduio")
    assert PersonaSettings.from_env().backend == "template"


def test_an_unreachable_endpoint_does_not_break_the_session(monkeypatch, tmp_path):
    """The whole drill must survive nothing running on localhost."""
    monkeypatch.setenv("VITSC_PERSONA", "lmstudio")
    monkeypatch.setenv("VITSC_BASE_URL", "http://127.0.0.1:9/v1")
    session = AppSession.build(db_path=tmp_path / "t.sqlite3", seed=1)
    assert isinstance(session.queue.persona, LMStudioPersona)

    ticket = session.queue.open_one()
    assert ticket.report_text          # fell back, did not raise
    assert session.degraded is True


def test_app_session_still_accepts_an_explicit_persona(tmp_path):
    session = AppSession.build(
        db_path=tmp_path / "t.sqlite3", seed=1, persona=TemplatePersona()
    )
    assert isinstance(session.queue.persona, TemplatePersona)


def test_a_healthy_session_reports_no_degradation(tmp_path):
    session = AppSession.build(db_path=tmp_path / "t.sqlite3", seed=1)
    assert session.degraded is False


class StubDegraded(TemplatePersona):
    """Template output, but reporting itself as degraded."""

    degraded = True


def test_the_banner_is_hidden_until_the_model_fails(tmp_path):
    session = AppSession.build(db_path=tmp_path / "t.sqlite3", seed=1)
    body = TestClient(create_app(session)).get("/").text
    assert 'data-degraded="false"' in body


def test_the_banner_shows_when_the_persona_is_degraded(tmp_path):
    session = AppSession.build(
        db_path=tmp_path / "t.sqlite3", seed=1, persona=StubDegraded()
    )
    body = TestClient(create_app(session)).get("/").text
    assert 'data-degraded="true"' in body


def test_the_event_payload_carries_the_degraded_flag(tmp_path):
    """Degradation happens mid-session, long after the page was rendered, so
    the SSE payload has to carry it or the banner never appears.

    Asserted against `build_payload` rather than the live endpoint, matching
    `tests/test_web_events.py`: the stream loop never terminates, so driving
    it through TestClient hangs instead of failing.
    """
    session = AppSession.build(
        db_path=tmp_path / "t.sqlite3", seed=1, persona=StubDegraded()
    )
    payload = build_payload(session, session.env.world.clock, [])
    assert payload["degraded"] is True


def test_the_event_payload_is_clean_for_a_healthy_persona(tmp_path):
    session = AppSession.build(db_path=tmp_path / "t.sqlite3", seed=1)
    payload = build_payload(session, session.env.world.clock, [])
    assert payload["degraded"] is False
