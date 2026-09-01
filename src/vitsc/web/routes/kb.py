from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from vitsc.kb.loader import get_article, load_articles, search_articles

router = APIRouter()


@router.get("/kb", response_class=HTMLResponse)
def kb_index(request: Request, q: str = ""):
    from vitsc.web.app import templates
    articles = search_articles(q) if q else sorted(load_articles().values(), key=lambda a: a.id)
    return templates.TemplateResponse(
        request, "_kb.html", {"query": q, "articles": articles, "article": None},
    )


@router.get("/kb/{article_id}", response_class=HTMLResponse)
def kb_article(request: Request, article_id: str):
    from vitsc.web.app import templates
    article = get_article(article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="No such article")
    return templates.TemplateResponse(
        request, "_kb.html", {"query": "", "articles": [], "article": article},
    )
