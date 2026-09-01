import pytest
from fastapi.testclient import TestClient

from vitsc.web.app import create_app
from vitsc.web.deps import AppSession


@pytest.fixture
def client(tmp_path):
    session = AppSession.build(db_path=tmp_path / "t.sqlite3", seed=1)
    return TestClient(create_app(session)), session


def test_kb_index_lists_every_article(client):
    c, _ = client
    body = c.get("/kb").text
    assert "Before you touch anything" in body
    assert '<a href="/kb/general-triage-first-questions">' in body


def test_kb_search_narrows_the_listing(client):
    c, _ = client
    body = c.get("/kb", params={"q": "printer"}).text
    assert "Nothing prints" in body
    assert "Before you touch anything" not in body


def test_kb_search_with_no_hits_says_so(client):
    c, _ = client
    body = c.get("/kb", params={"q": "zzzzzz"}).text
    assert "No matching articles." in body


def test_kb_article_page_renders_the_body(client):
    c, _ = client
    body = c.get("/kb/general-triage-first-questions").text
    assert "Before you touch anything" in body
    assert "## Check" in body


def test_unknown_article_404s(client):
    c, _ = client
    assert c.get("/kb/nope").status_code == 404
