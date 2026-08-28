"""Fault declarations.

`is_present()` is the single source of truth for both "is this broken" and
"did the technician fix it". `canonical_resolutions()` is documentation and
test fixture, never the pass/fail gate — the gate is `is_present()` going
false with invariants intact, so any path there counts.
"""

from random import Random
from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel

from vitsc.env.base import Action, Query
from vitsc.world.models import World

Domain = Literal["identity", "network", "printing", "mail", "endpoint"]
Backend = Literal["simulated", "winrm"]

PLACEHOLDER = "{placement}"
PLACEHOLDER_MACHINE = "{machine}"
PLACEHOLDER_GROUP = "{group}"
PLACEHOLDER_PRINTER = "{printer}"


class Placement(BaseModel):
    """A world entity a fault is attached to."""

    kind: Literal["user", "machine", "printer", "share"]
    key: str


class UserSymptoms(BaseModel):
    """Only what a non-technical person can perceive. The sole persona input."""

    opening: str
    onset: str
    scope: str
    error_text: str | None = None


class ResolutionPath(BaseModel):
    label: str
    actions: list[Action]


@runtime_checkable
class Fault(Protocol):
    id: str
    domain: Domain
    difficulty: int
    canonical_title: str
    supported_backends: frozenset[str]
    leak_terms: list[str]
    escalation_is_correct: bool
    kb_articles: list[str]
    escalation_reason: str
    escalation_evidence: list[Query]

    def placements(self, world: World) -> list[Placement]: ...
    def apply(self, world: World, at: Placement, rng: Random) -> None: ...
    def is_present(self, world: World, at: Placement) -> bool: ...
    def symptoms(self, world: World, at: Placement) -> UserSymptoms: ...
    def diagnostic_path(self, at: Placement) -> list[Query]: ...
    def canonical_resolutions(self) -> list[ResolutionPath]: ...
    def reporters(self, world: World, at: Placement) -> list[str] | None: ...


class FaultBase:
    """Defaults for every optional `Fault` member.

    The protocol grew in Phase 2a. Ten faults predate it, so the defaults live
    here and the catalog inherits them — one mechanical change instead of ten
    copy-pasted stubs, and a 2b fault that overrides nothing still conforms.
    """

    kb_articles: list[str] = []
    escalation_reason: str = ""
    escalation_evidence: list[Query] = []

    def reporters(self, world: World, at: Placement) -> list[str] | None:
        """Who phones this in.

        `None` means "whoever the placement points at" — the session layer
        owns that resolution because it depends on `assigned_to`, which is
        queue logic rather than fault data. A list makes the fault a cascade.
        """
        return None


def _sentinels(at: Placement, world: World) -> dict[str, str]:
    return {
        PLACEHOLDER: at.key,
        PLACEHOLDER_MACHINE: _machine_key(world, at),
        PLACEHOLDER_GROUP: _share_group(world, at) or "",
        PLACEHOLDER_PRINTER: _printer_key(at),
    }


def _machine_key(world: World, at: Placement) -> str:
    if at.kind == "machine":
        return at.key
    if at.kind == "printer":
        return at.key.split("/", 1)[0]
    machine = world.machine_for(at.key) if at.kind == "user" else None
    return machine.hostname if machine else ""


def _printer_key(at: Placement) -> str:
    if at.kind != "printer":
        return ""
    return at.key.split("/", 1)[1]


def _share_group(world: World, at: Placement) -> str | None:
    machine = world.machine_for(at.key) if at.kind == "user" else None
    if machine is None or "S:" not in machine.mapped_drives:
        return None
    return world.shares[machine.mapped_drives["S:"]].required_group


def bind(resolution: ResolutionPath, at: Placement, world: World) -> ResolutionPath:
    """Replace placement sentinels (`{placement}`, `{machine}`, `{group}`,
    `{printer}`) with concrete world keys.

    `canonical_resolutions()` cannot know its placement, so callers bind it.
    """
    subs = _sentinels(at, world)
    return ResolutionPath(
        label=resolution.label,
        actions=[
            a.model_copy(
                update={
                    "target": subs.get(a.target, a.target),
                    "args": {k: subs.get(v, v) for k, v in a.args.items()},
                }
            )
            for a in resolution.actions
        ],
    )


def bind_query(query: Query, at: Placement, world: World) -> Query:
    """Replace placement sentinels in a diagnostic query the same way `bind` does."""
    subs = _sentinels(at, world)
    return query.model_copy(
        update={
            "target": subs.get(query.target, query.target),
            "args": {k: subs.get(v, v) for k, v in query.args.items()},
        }
    )
