from vitsc.faults.registry import all_faults
from vitsc.kb.loader import get_article, load_articles, search_articles


def test_articles_load_with_complete_frontmatter():
    articles = load_articles()
    assert len(articles) >= 8
    for a in articles.values():
        assert a.id and a.title and a.keywords and a.body
        assert a.domain in {"identity", "network", "printing", "mail", "endpoint", "general"}


def test_search_finds_by_keyword_and_title():
    assert any(a.id == "printing-nothing-prints" for a in search_articles("printer"))
    assert search_articles("zzzzz") == []


def test_no_article_is_an_answer_key():
    """A KB that maps symptoms to causes deletes the drill."""
    articles = load_articles()
    for fault in all_faults():
        for a in articles.values():
            text = f"{a.title} {a.body}".lower()
            assert fault.id.lower() not in text, f"{a.id} names {fault.id}"
            assert fault.canonical_title.lower() not in text, f"{a.id} names {fault.id}'s cause"


def test_every_fault_kb_link_resolves():
    for fault in all_faults():
        for article_id in fault.kb_articles:
            assert get_article(article_id) is not None, f"{fault.id} links missing {article_id}"


def test_no_orphans_in_either_direction():
    """Phase 2b's Definition of Done, as a test rather than a promise.

    An article no fault links is one the after-action never offers, so nobody
    reads it; a fault with no article has nothing to suggest after a ticket the
    technician got wrong. Both are easy to create by accident and invisible
    without this — `mail-cannot-send-or-receive` shipped inert for a whole phase.
    """
    articles = set(load_articles())
    linked = {article_id for fault in all_faults() for article_id in fault.kb_articles}
    assert articles - linked == set(), "articles no fault links"
    assert [f.id for f in all_faults() if not f.kb_articles] == []


def test_articles_are_procedural():
    """Each article tells you how to check something, not what the answer is."""
    for a in load_articles().values():
        assert "## Check" in a.body or "## Steps" in a.body
