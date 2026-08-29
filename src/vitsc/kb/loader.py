"""Loads the original-content knowledge base from `vitsc/data/kb/*.md`.

Each article is a markdown file with a YAML frontmatter block (`id`, `title`,
`domain`, `keywords`) followed by the body. Loading is cached — the catalog
is static for the life of the process, same as `world/seed.py`'s company data.
"""

from functools import lru_cache
from importlib.resources import files

import yaml

from vitsc.kb.models import Article


def _parse(text: str) -> Article:
    _, frontmatter, body = text.split("---", 2)
    meta = yaml.safe_load(frontmatter)
    return Article(
        id=meta["id"],
        title=meta["title"],
        domain=meta["domain"],
        keywords=list(meta["keywords"]),
        body=body.strip(),
    )


@lru_cache(maxsize=None)
def load_articles() -> dict[str, Article]:
    articles = {}
    for entry in files("vitsc.data").joinpath("kb").iterdir():
        if entry.name.endswith(".md"):
            article = _parse(entry.read_text())
            articles[article.id] = article
    return articles


def get_article(article_id: str) -> Article | None:
    return load_articles().get(article_id)


def search_articles(text: str) -> list[Article]:
    query = text.strip().lower()
    if not query:
        return []
    scored: list[tuple[int, Article]] = []
    for article in load_articles().values():
        score = 0
        if query in article.title.lower():
            score += 3
        if any(query in kw.lower() or kw.lower() in query for kw in article.keywords):
            score += 2
        if query in article.id.lower():
            score += 1
        if score:
            scored.append((score, article))
    scored.sort(key=lambda pair: (-pair[0], pair[1].id))
    return [article for _, article in scored]
