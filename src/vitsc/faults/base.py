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

    def placements(self, world: World) -> list[Placement]: ...
    def apply(self, world: World, at: Placement, rng: Random) -> None: ...
    def is_present(self, world: World, at: Placement) -> bool: ...
    def symptoms(self, world: World, at: Placement) -> UserSymptoms: ...
    def diagnostic_path(self, at: Placement) -> list[Query]: ...
    def canonical_resolutions(self) -> list[ResolutionPath]: ...


def bind(resolution: ResolutionPath, at: Placement) -> ResolutionPath:
    """Replace the `{placement}` sentinel with the concrete target key.

    `canonical_resolutions()` cannot know its placement, so callers bind it.
    """
    return ResolutionPath(
        label=resolution.label,
        actions=[
            a.model_copy(
                update={
                    "target": at.key if a.target == PLACEHOLDER else a.target,
                    "args": {
                        k: (at.key if v == PLACEHOLDER else v) for k, v in a.args.items()
                    },
                }
            )
            for a in resolution.actions
        ],
    )
