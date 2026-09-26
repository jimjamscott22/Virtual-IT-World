"""The distractor catalog.

Eleven honest anomalies (spec §4): each is real, visible through a query a clean
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
from vitsc.world.models import (
    ADGroup,
    CLOCK_SKEW_TOLERANCE_MINUTES,
    EventEntry,
    JobStatus,
    MailRule,
    PrintJob,
    Process,
    ServiceState,
    World,
)

# Well above `endpoint.disk_full`'s 2.0 GB threshold, against a 120 GB norm —
# visibly odd, never enough to trip that fault.
LOW_DISK_MIN_GB = 8.0
LOW_DISK_MAX_GB = 15.0

STALE_MAPPING_UNC = "\\\\MER-FS-01\\OldPayroll"

# Comfortably inside `CLOCK_SKEW_TOLERANCE_MINUTES`, so `endpoint.time_skew`
# cannot be tripped by this and a share access attempt is never refused for it.
MINOR_DRIFT_MAX_MINUTES = CLOCK_SKEW_TOLERANCE_MINUTES - 2

LEGACY_GROUP_NAME = "OLD-Payroll-RW"


def _delegate_for(world: World, owner_sam: str) -> str:
    """A current employee to stand in as the assistant.

    The next person in the owner's own department where there is one, so the
    grant looks like something somebody would actually have set up. Whoever it
    is, they exist — which is what separates this from `mail.stale_delegate`.
    """
    department = world.org.users[owner_sam].department
    colleagues = sorted(
        sam
        for sam, user in world.org.users.items()
        if user.department == department and sam != owner_sam
    )
    return colleagues[0] if colleagues else owner_sam


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


# --- Phase 2b: the noise floor scales with the catalog ----------------------
#
# Five anomalies against thirteen faults read as noise. Five against thirty-one
# start to read as a tell, because the same handful keeps turning up and a
# technician learns to skip them. These six are aimed at the reads Phase 2b
# added, so the new tools have honest noise in them from the first ticket
# rather than being surfaces where anything unusual is always the answer.


class IdleHelperProcess:
    id = "process.idle_helper"
    note = (
        "A helper process from a line-of-business application is running on a "
        "workstation, using almost nothing. It is meant to be there."
    )

    def placements(self, world: World) -> list[Placement]:
        return _workstations(world)

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        world.machines[at.key].processes.append(
            Process(
                name="FreightSyncMonitor.exe",
                pid=rng.randint(2600, 3100),
                # Well below the runaway gate, and in the same range as the
                # ordinary processes `world/seed.py` seeds.
                cpu_percent=rng.uniform(2.0, 7.0),
                memory_mb=rng.uniform(70.0, 180.0),
            )
        )

    def visible_through(self, at: Placement) -> list[Query]:
        return [Query(kind="machine.processes", target=at.key)]


class MinorClockDrift:
    id = "clock.minor_drift"
    note = (
        "A workstation's clock is a couple of minutes out. Well inside what the "
        "domain tolerates, and it will correct itself."
    )

    def placements(self, world: World) -> list[Placement]:
        return _workstations(world)

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        world.machines[at.key].clock_offset_minutes = rng.choice([-1, 1]) * rng.randint(
            1, MINOR_DRIFT_MAX_MINUTES
        )

    def visible_through(self, at: Placement) -> list[Query]:
        return [Query(kind="machine.state", target=at.key)]


class HarmlessInboxRule:
    id = "mail.harmless_inbox_rule"
    note = (
        "A mailbox has an inbox rule filing supplier newsletters into a folder. "
        "It forwards nowhere and deletes nothing."
    )

    def placements(self, world: World) -> list[Placement]:
        return [Placement(kind="user", key=sam) for sam in sorted(world.org.users)]

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        mailbox = world.mailbox_for(at.key)
        if mailbox is None:  # pragma: no cover - seed gives every user one
            return
        mailbox.rules.append(MailRule(name="Newsletters", created_by=at.key))

    def visible_through(self, at: Placement) -> list[Query]:
        return [Query(kind="mail.rules", target=at.key)]


class CurrentEmployeeDelegate:
    id = "mail.current_employee_delegate"
    note = (
        "A manager's assistant has access to their mailbox. They still work here "
        "and they are supposed to have it."
    )

    def placements(self, world: World) -> list[Placement]:
        # Somebody other than the owner has to exist to be the delegate, and the
        # delegate must be a *current* employee — that is the entire point.
        return [
            Placement(kind="user", key=sam)
            for sam in sorted(world.org.users)
            if sam != _delegate_for(world, sam)
        ]

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        mailbox = world.mailbox_for(at.key)
        if mailbox is None:  # pragma: no cover - seed gives every user one
            return
        delegate = _delegate_for(world, at.key)
        if delegate not in mailbox.delegates:
            mailbox.delegates.append(delegate)

    def visible_through(self, at: Placement) -> list[Query]:
        return [Query(kind="mail.delegates", target=at.key)]


class PrinterQueueBacklog:
    id = "printer.queue_backlog"
    note = (
        "A printer has a few jobs waiting in its queue. They are moving — the "
        "queue is simply busy."
    )

    def placements(self, world: World) -> list[Placement]:
        installed = {
            name
            for m in world.machines.values()
            if m.assigned_to is not None
            for name in m.installed_printers
        }
        return [Placement(kind="printer", key=name) for name in sorted(installed)]

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        printer = world.printers[at.key]
        owner = sorted(
            m.assigned_to
            for m in world.machines.values()
            if m.assigned_to is not None and at.key in m.installed_printers
        )[0]
        printer.jobs.extend(
            PrintJob(
                job_id=rng.randint(200, 260) + i,
                owner_sam=owner,
                document="Consignment label",
                pages=1,
                # Queued, never Error: an errored job at the head is a fault.
                status=JobStatus.QUEUED,
            )
            for i in range(2)
        )

    def visible_through(self, at: Placement) -> list[Query]:
        return [Query(kind="printer.jobs", target=at.key)]


class EmptyLegacyGroup:
    id = "group.empty_legacy_group"
    note = (
        "An access group from a system that was retired is still in the "
        "directory with nobody in it. It grants nothing."
    )

    def placements(self, world: World) -> list[Placement]:
        return [Placement(kind="group", key=LEGACY_GROUP_NAME)]

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        world.org.groups.setdefault(at.key, ADGroup(name=at.key))

    def visible_through(self, at: Placement) -> list[Query]:
        return [Query(kind="ad.group", target=at.key)]


register_distractor(IdleHelperProcess())
register_distractor(MinorClockDrift())
register_distractor(HarmlessInboxRule())
register_distractor(CurrentEmployeeDelegate())
register_distractor(PrinterQueueBacklog())
register_distractor(EmptyLegacyGroup())
