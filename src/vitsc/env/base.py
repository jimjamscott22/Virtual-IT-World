"""The swap point.

Everything above this boundary — tools, faults, session, web — is written
once against these four types and never changes when the backend does. A
future `WinRMEnvironment` translating queries into PowerShell over WinRM
satisfies the same protocol, and existing faults and validators keep working.
"""

from typing import Any, Protocol

from pydantic import BaseModel, Field


class Query(BaseModel):
    """A read against the environment. Never mutates."""

    kind: str
    target: str
    args: dict[str, str] = Field(default_factory=dict)


class Observation(BaseModel):
    ok: bool
    data: dict[str, Any] = Field(default_factory=dict)
    rendered: str


class Action(BaseModel):
    """A write against the environment."""

    kind: str
    target: str
    args: dict[str, str] = Field(default_factory=dict)


class ActionResult(BaseModel):
    ok: bool
    rendered: str


class Environment(Protocol):
    def read(self, query: Query) -> Observation: ...
    def execute(self, action: Action) -> ActionResult: ...
    def snapshot(self) -> str: ...
    def restore(self, snapshot_id: str) -> None: ...
