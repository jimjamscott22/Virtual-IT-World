"""The knowledge-base lookup tool.

Unlike every other tool, this one has no `Query` to issue — it reads
`vitsc.kb`'s article catalog, not the simulated environment, so it is a plain
`Tool` rather than a `DispatchTool`. It still records a `ToolCall` on every
call (`mutating=False` always), because the log is what grading reads.
"""

from vitsc.env.base import Environment
from vitsc.kb.loader import get_article, search_articles
from vitsc.tools.base import MISSING, UNKNOWN, ToolCall, ToolLog

NOT_FOUND = "No article found with id '{article_id}'."
NO_HITS = "No matching articles."


class KnowledgeBase:
    name = "kb"

    def commands(self) -> list[str]:
        return ["read", "search"]

    def invoke(
        self, env: Environment, log: ToolLog, command: str, args: dict[str, str]
    ) -> ToolCall:
        del env
        if command == "search":
            return self._search(log, args)
        if command == "read":
            return self._read(log, args)
        return log.record(
            ToolCall(
                tool=self.name, command=command, args=args,
                ok=False, mutating=False, rendered=UNKNOWN.format(cmd=command),
            )
        )

    def _search(self, log: ToolLog, args: dict[str, str]) -> ToolCall:
        text = args.get("text", "")
        if not text:
            return log.record(
                ToolCall(
                    tool=self.name, command="search", args=args,
                    ok=False, mutating=False, rendered=MISSING.format(param="Text"),
                )
            )
        hits = search_articles(text)
        rendered = "\n".join(f"{a.id}: {a.title}" for a in hits) if hits else NO_HITS
        return log.record(
            ToolCall(
                tool=self.name, command="search", args=args,
                ok=True, mutating=False, rendered=rendered,
            )
        )

    def _read(self, log: ToolLog, args: dict[str, str]) -> ToolCall:
        article_id = args.get("id", "")
        if not article_id:
            return log.record(
                ToolCall(
                    tool=self.name, command="read", args=args,
                    ok=False, mutating=False, rendered=MISSING.format(param="Id"),
                )
            )
        article = get_article(article_id)
        if article is None:
            return log.record(
                ToolCall(
                    tool=self.name, command="read", args=args,
                    ok=False, mutating=False, rendered=NOT_FOUND.format(article_id=article_id),
                )
            )
        rendered = f"{article.title}\n\n{article.body}"
        return log.record(
            ToolCall(
                tool=self.name, command="read", args=args,
                ok=True, mutating=False, rendered=rendered,
            )
        )
