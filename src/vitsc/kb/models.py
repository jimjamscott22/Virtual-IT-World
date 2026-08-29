from typing import Literal

from pydantic import BaseModel

Domain = Literal["identity", "network", "printing", "mail", "endpoint", "general"]


class Article(BaseModel):
    """A single knowledge-base page: procedure, not an answer key."""

    id: str
    title: str
    domain: Domain
    keywords: list[str]
    body: str
