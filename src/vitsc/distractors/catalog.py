"""The v1 distractor catalog.

Five honest anomalies (spec §4): each is real, visible through a query a clean
world answers differently, and mechanically inert — none of them can flip any
registered fault's `is_present()`. See `distractors/base.py` for why the
contract deliberately excludes `is_present`/`symptoms`/`canonical_resolutions`.

Register *instances*, not classes, at the bottom of this module — the same
shape `faults/catalog/identity.py` uses. The conformance harness calls
`placements(world)` on whatever is registered, so a bare class fails at
collection time with a missing `self`.
"""

from datetime import timedelta
from random import Random

from vitsc.distractors.registry import register_distractor
from vitsc.env.base import Query
from vitsc.faults.base import Placement
from vitsc.world.models import EventEntry, ServiceState, World

# Well above `endpoint.disk_full`'s 2.0 GB threshold, against a 120 GB norm —
# visibly odd, never enough to trip that fault.
LOW_DISK_MIN_GB = 8.0
LOW_DISK_MAX_GB = 15.0

STALE_MAPPING_UNC = "\\\\MER-FS-01\\OldPayroll"


def _workstations(world: World) -> list[Placement]:
    return [
        Placement(kind="machine", key=m.hostname)
        for m in world.machines.values()
        if m.assigned_to is not None
    ]


class ModeratelyLowDisk:
    id = "disk.moderately_low"
    note = "A workstation is running lower on disk space than usual, but nowhere near full."

    def placements(self, world: World) -> list[Placement]:
        return _workstations(world)

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        world.machines[at.key].disk_free_gb = rng.uniform(LOW_DISK_MIN_GB, LOW_DISK_MAX_GB)

    def visible_through(self, at: Placement) -> list[Query]:
        return [Query(kind="machine.state", target=at.key)]


class StoppedSearchIndexer:
    id = "service.wsearch_stopped"
    note = "Windows Search indexing is stopped on a workstation. Cosmetic — nothing reads it."

    def placements(self, world: World) -> list[Placement]:
        return _workstations(world)

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        world.machines[at.key].services["WSearch"] = ServiceState.STOPPED

    def visible_through(self, at: Placement) -> list[Query]:
        return [Query(kind="machine.services", target=at.key, args={"service": "WSearch"})]


class OldDiskWarning:
    id = "eventlog.old_disk_warning"
    note = "A month-old disk warning sits in the event log. The drive has been fine since."

    def placements(self, world: World) -> list[Placement]:
        return _workstations(world)

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        world.machines[at.key].event_log.append(
            EventEntry(
                log="System",
                source="Disk",
                event_id=51,
                level="Warning",
                at=world.clock - timedelta(days=30),
                message="An error was detected on device \\Device\\Harddisk0\\DR0 "
                "during a paging operation.",
            )
        )

    def visible_through(self, at: Placement) -> list[Query]:
        return [Query(kind="machine.eventlog", target=at.key, args={"log": "System"})]


class OfflineUnusedPrinter:
    id = "printer.offline_unused"
    note = "A printer nobody has installed is showing offline. No one is affected."

    def placements(self, world: World) -> list[Placement]:
        installed = {
            name for m in world.machines.values() for name in m.installed_printers
        }
        return [
            Placement(kind="printer", key=name)
            for name in world.printers
            if name not in installed
        ]

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        world.printers[at.key].online = False

    def visible_through(self, at: Placement) -> list[Query]:
        return [Query(kind="printer.state", target=at.key)]


class StaleMappedDrive:
    id = "drive.stale_mapping"
    note = "A workstation still has a Z: drive mapped to a share that no longer exists."

    def placements(self, world: World) -> list[Placement]:
        return _workstations(world)

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        world.machines[at.key].mapped_drives["Z:"] = STALE_MAPPING_UNC

    def visible_through(self, at: Placement) -> list[Query]:
        return [Query(kind="machine.state", target=at.key)]


register_distractor(ModeratelyLowDisk())
register_distractor(StoppedSearchIndexer())
register_distractor(OldDiskWarning())
register_distractor(OfflineUnusedPrinter())
register_distractor(StaleMappedDrive())
