"""Player-facing tool framework.

Tools are thin wrappers over `env.read()` / `env.execute()` that render output
in the format of the real utility. Nothing here — and nothing in any module
under `vitsc.tools` — may import from `vitsc.faults`. Tools read world state;
they never read the fault (spec §3).

Every call is logged, and the log is what grading reads: tool efficiency, and
whether the technician touched anything before asking the user a question.
"""

from datetime import UTC, datetime
from typing import Protocol

from pydantic import BaseModel, Field

from vitsc.env.base import Action, Environment, Query

UNKNOWN = "The term '{cmd}' is not recognized as the name of a cmdlet."
MISSING = "Missing required parameter: -{param}"


class ToolCall(BaseModel):
    tool: str
    command: str
    args: dict[str, str] = Field(default_factory=dict)
    at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    ok: bool
    mutating: bool
    rendered: str


class ToolLog(BaseModel):
    calls: list[ToolCall] = Field(default_factory=list)

    def record(self, call: ToolCall) -> ToolCall:
        # pylint does not model pydantic's default_factory: it infers
        # `calls` as a FieldInfo rather than the list built at runtime.
        self.calls.append(call)  # pylint: disable=no-member
        return call

    def first_mutating_index(self) -> int | None:
        for i, call in enumerate(self.calls):
            if call.mutating:
                return i
        return None


class Tool(Protocol):
    name: str

    def commands(self) -> list[str]: ...
    def invoke(
        self, env: Environment, log: ToolLog, command: str, args: dict[str, str]
    ) -> ToolCall: ...


class DispatchTool:
    """Shared dispatch for every tool: a read map, a write map, and a target.

    Subclasses declare `name`, `READS`, `WRITES`, and override `target_key`
    when the target is not `args["host"]`.
    """

    name: str = ""
    READS: dict[str, str] = {}
    WRITES: dict[str, str] = {}
    TARGET_PARAM = "host"

    def commands(self) -> list[str]:
        return sorted([*self.READS, *self.WRITES])

    def target_key(self, command: str, args: dict[str, str]) -> str:
        return args.get(self.TARGET_PARAM, "")

    def query_args(self, command: str, args: dict[str, str]) -> dict[str, str]:
        return args

    def _resolve_command(self, command: str) -> tuple[str, str] | None:
        """Return (kind, 'read'|'write'). Matching is case-insensitive."""
        for name, kind in self.READS.items():
            if name.lower() == command.lower():
                return kind, "read"
        for name, kind in self.WRITES.items():
            if name.lower() == command.lower():
                return kind, "write"
        return None

    def _record(
        self,
        log: ToolLog,
        command: str,
        args: dict[str, str],
        *,
        ok: bool,
        mutating: bool,
        rendered: str,
    ) -> ToolCall:
        return log.record(
            ToolCall(
                tool=self.name,
                command=command,
                args=args,
                ok=ok,
                mutating=mutating,
                rendered=rendered,
            )
        )

    def invoke(
        self, env: Environment, log: ToolLog, command: str, args: dict[str, str]
    ) -> ToolCall:
        resolved = self._resolve_command(command)
        if resolved is None:
            return self._record(
                log, command, args, ok=False, mutating=False,
                rendered=UNKNOWN.format(cmd=command),
            )
        kind, direction = resolved
        target = self.target_key(command, args)
        if not target:
            # A rejected call never reached the environment, so it is not a
            # mutation — which keeps the "did you touch anything first" grade
            # honest.
            return self._record(
                log, command, args, ok=False, mutating=False,
                rendered=MISSING.format(param=self.TARGET_PARAM.capitalize()),
            )
        call_args = self.query_args(command, args)
        if direction == "read":
            obs = env.read(Query(kind=kind, target=target, args=call_args))
            return self._record(
                log, command, args, ok=obs.ok, mutating=False, rendered=obs.rendered
            )
        result = env.execute(Action(kind=kind, target=target, args=call_args))
        return self._record(
            log, command, args, ok=result.ok, mutating=True, rendered=result.rendered
        )
