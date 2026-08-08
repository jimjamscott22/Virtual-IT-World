from random import Random

from vitsc.env.base import Action, Query
from vitsc.faults.base import PLACEHOLDER, Placement, ResolutionPath, UserSymptoms
from vitsc.faults.registry import register
from vitsc.world.models import EventEntry, ProfileState, SmartStatus, World

DISK_FULL_THRESHOLD_GB = 2.0


def _workstations(world: World) -> list[Placement]:
    return [
        Placement(kind="machine", key=m.hostname)
        for m in world.machines.values()
        if m.assigned_to is not None
    ]


class DiskFull:
    id = "endpoint.disk_full"
    domain = "endpoint"
    difficulty = 2
    canonical_title = "Workstation disk nearly full, forcing a temporary profile"
    supported_backends = frozenset({"simulated", "winrm"})
    leak_terms = ["disk", "full", "space", "profile", "temporary"]
    escalation_is_correct = False

    def placements(self, world: World) -> list[Placement]:
        return _workstations(world)

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        machine = world.machines[at.key]
        machine.disk_free_gb = rng.uniform(0.1, 0.8)
        machine.profile_state = ProfileState.TEMPORARY

    def is_present(self, world: World, at: Placement) -> bool:
        return world.machines[at.key].disk_free_gb < DISK_FULL_THRESHOLD_GB

    def symptoms(self, world: World, at: Placement) -> UserSymptoms:
        return UserSymptoms(
            opening="Outlook won't open any more and my desktop looks completely "
            "different — none of my files are there.",
            onset="It was fine yesterday, this started when I logged in today.",
            scope="Just my account on my machine.",
            error_text=None,
        )

    def diagnostic_path(self, at: Placement) -> list[Query]:
        return [Query(kind="machine.state", target=at.key)]

    def canonical_resolutions(self) -> list[ResolutionPath]:
        return [
            ResolutionPath(
                label="Free up disk space",
                actions=[
                    Action(kind="machine.clear_disk", target=PLACEHOLDER, args={"gb": "40"}),
                ],
            ),
        ]


class FailingDisk:
    """Escalate-correct: a pre-fail SMART status means the drive needs
    replacing, not clearing. There is no technician fix — the correct
    disposition is escalation, which is what `escalation_is_correct` and an
    empty `canonical_resolutions()` together encode."""

    id = "endpoint.failing_disk"
    domain = "endpoint"
    difficulty = 4
    canonical_title = "Workstation disk reporting SMART pre-fail status"
    supported_backends = frozenset({"simulated", "winrm"})
    leak_terms = ["smart", "disk", "drive failure", "hardware", "replace"]
    escalation_is_correct = True

    def placements(self, world: World) -> list[Placement]:
        return _workstations(world)

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        machine = world.machines[at.key]
        machine.smart_status = SmartStatus.PRED_FAIL
        machine.event_log.append(
            EventEntry(
                log="System",
                source="disk",
                event_id=7,
                level="Warning",
                at=world.clock,
                message="The device, \\Device\\Harddisk0\\DR0, has a bad block.",
            )
        )

    def is_present(self, world: World, at: Placement) -> bool:
        return world.machines[at.key].smart_status is not SmartStatus.OK

    def symptoms(self, world: World, at: Placement) -> UserSymptoms:
        return UserSymptoms(
            opening="It's been freezing for a few seconds at a time and making a "
            "clicking noise.",
            onset="It happened twice during a call yesterday.",
            scope="Just this one machine.",
            error_text=None,
        )

    def diagnostic_path(self, at: Placement) -> list[Query]:
        return [
            Query(kind="machine.state", target=at.key),
            Query(kind="machine.eventlog", target=at.key, args={"log": "System"}),
        ]

    def canonical_resolutions(self) -> list[ResolutionPath]:
        return []


register(DiskFull())
register(FailingDisk())
