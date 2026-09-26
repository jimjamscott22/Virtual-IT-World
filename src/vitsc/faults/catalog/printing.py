from random import Random

from vitsc.env.base import Action, Query
from vitsc.faults.base import (
    FaultBase,
    PLACEHOLDER,
    PLACEHOLDER_MACHINE,
    PLACEHOLDER_PRINTER,
    Placement,
    ResolutionPath,
    UserSymptoms,
)
from vitsc.faults.registry import register
from vitsc.world.models import EventEntry, JobStatus, PrintJob, ServiceState, World

GENERIC_DRIVER = "Generic / Text Only"
# Any printer hosted on the print server works as the diagnostic target —
# `printer.state`'s `SpoolerState` reads the *server's* service, not the
# printer's own — so a literal name is fine, the same way `net.ping`'s
# diagnostic already hardcodes `MER-FS-01`. A fault cannot resolve one from
# `World` itself: `diagnostic_path()` receives only a `Placement`.
_SERVER_DIAGNOSTIC_PRINTER = "PRT-ACC-01"


# What the replacement device is. A different manufacturer on purpose: a driver
# that is merely a later revision of the same model usually still prints, and
# the ticket has to be visible from the first page that comes out.
REPLACEMENT_MODEL = "Brother HL-L6400DW"
REPLACEMENT_DRIVER = "Brother HL-L6400DW series"


def _installed_printers(world: World) -> list[Placement]:
    """Printers somebody actually has, named on their own.

    Distinct from `print.wrong_driver`'s `HOST/PRINTER` placements: these faults
    are about the device, so the placement is the device.
    """
    installed = {
        name
        for m in world.machines.values()
        if m.assigned_to is not None
        for name in m.installed_printers
    }
    return [Placement(kind="printer", key=name) for name in sorted(installed)]


def _users_of(world: World, printer_name: str) -> list[str]:
    return sorted(
        m.assigned_to
        for m in world.machines.values()
        if m.assigned_to is not None and printer_name in m.installed_printers
    )


def _first_user_of(world: World, printer_name: str) -> str:
    return _users_of(world, printer_name)[0]


def _workstations_with_printers(world: World) -> list[Placement]:
    return [
        Placement(kind="machine", key=m.hostname)
        for m in world.machines.values()
        if m.assigned_to is not None and m.installed_printers
    ]


class SpoolerStopped(FaultBase):
    id = "print.spooler_stopped"
    domain = "printing"
    difficulty = 1
    canonical_title = "Print spooler service stopped on the workstation"
    supported_backends = frozenset({"simulated", "winrm"})
    leak_terms = ["spooler", "service", "print queue"]
    escalation_is_correct = False
    kb_articles = ["printing-nothing-prints"]

    def placements(self, world: World) -> list[Placement]:
        return _workstations_with_printers(world)

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        world.machines[at.key].services["Spooler"] = ServiceState.STOPPED

    def is_present(self, world: World, at: Placement) -> bool:
        return world.machines[at.key].services.get("Spooler") is not ServiceState.RUNNING

    def symptoms(self, world: World, at: Placement) -> UserSymptoms:
        return UserSymptoms(
            opening="Nothing comes out when I print. It doesn't even say anything, "
            "the job just disappears.",
            onset="First noticed it after lunch.",
            scope="Just my computer, my coworker printed fine a minute ago.",
            error_text=None,
        )

    def diagnostic_path(self, at: Placement) -> list[Query]:
        return [Query(kind="machine.services", target=at.key, args={"service": "Spooler"})]

    def canonical_resolutions(self) -> list[ResolutionPath]:
        return [
            ResolutionPath(
                label="Restart the spooler service",
                actions=[
                    Action(
                        kind="machine.restart_service",
                        target=PLACEHOLDER,
                        args={"service": "Spooler"},
                    ),
                ],
            ),
        ]


class WrongDriver(FaultBase):
    id = "print.wrong_driver"
    domain = "printing"
    difficulty = 3
    canonical_title = "Wrong printer driver installed on the workstation"
    supported_backends = frozenset({"simulated", "winrm"})
    leak_terms = ["driver", "pcl", "postscript", "generic"]
    escalation_is_correct = False
    kb_articles = ["printing-nothing-prints"]

    def placements(self, world: World) -> list[Placement]:
        return [
            Placement(kind="printer", key=f"{m.hostname}/{printer}")
            for m in world.machines.values()
            if m.assigned_to is not None
            for printer in m.installed_printers
        ]

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        hostname, printer = at.key.split("/", 1)
        world.machines[hostname].printer_drivers[printer] = GENERIC_DRIVER

    def is_present(self, world: World, at: Placement) -> bool:
        hostname, printer = at.key.split("/", 1)
        installed = world.machines[hostname].printer_drivers.get(printer)
        return installed != world.printers[printer].correct_driver

    def symptoms(self, world: World, at: Placement) -> UserSymptoms:
        return UserSymptoms(
            opening="It prints but it's pages and pages of gibberish characters "
            "instead of my invoice.",
            onset="The first time was this morning's print run.",
            scope="Only from my machine, I checked with the desk next to me.",
            error_text=None,
        )

    def diagnostic_path(self, at: Placement) -> list[Query]:
        return [
            Query(
                kind="printer.state",
                target=PLACEHOLDER_PRINTER,
                args={"from": PLACEHOLDER_MACHINE},
            ),
        ]

    def canonical_resolutions(self) -> list[ResolutionPath]:
        return [
            ResolutionPath(
                label="Reinstall the correct driver",
                actions=[
                    Action(
                        kind="printer.reinstall_driver",
                        target=PLACEHOLDER_PRINTER,
                        args={"from": PLACEHOLDER_MACHINE},
                    ),
                ],
            ),
        ]


def _print_servers(world: World) -> list[Placement]:
    hosted = {p.host for p in world.printers.values()}
    return [
        Placement(kind="machine", key=m.hostname)
        for m in world.machines.values()
        if m.assigned_to is None and m.hostname in hosted
    ]


class ServerSpoolerStopped(FaultBase):
    """The reference cascade fault: one outage, several tickets.

    The pair with `SpoolerStopped` above is deliberate, in the same spirit as
    `account_locked`/`password_expired`: one person versus several is the
    differential, and `scope` is the honest tell that it's a cascade.
    """

    id = "print.server_spooler_stopped"
    domain = "printing"
    difficulty = 2
    canonical_title = "Print spooler service stopped on the print server"
    supported_backends = frozenset({"simulated", "winrm"})
    leak_terms = ["spool", "service", "server", "queue"]
    escalation_is_correct = False
    # The estate article is what tells you every printer in the building queues
    # through one server, which is the whole reason several people report at once.
    kb_articles = ["printing-nothing-prints", "general-meridian-estate"]

    def placements(self, world: World) -> list[Placement]:
        return _print_servers(world)

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        machine = world.machines[at.key]
        machine.services["Spooler"] = ServiceState.STOPPED
        machine.event_log.append(
            EventEntry(
                log="System",
                source="Service Control Manager",
                event_id=7031,
                level="Error",
                at=world.clock,
                message="The Print Spooler service terminated unexpectedly.",
            )
        )

    def is_present(self, world: World, at: Placement) -> bool:
        return world.machines[at.key].services.get("Spooler") is not ServiceState.RUNNING

    def symptoms(self, world: World, at: Placement) -> UserSymptoms:
        return UserSymptoms(
            opening="Nothing comes out of the printer. I sent it four times.",
            onset="Since about an hour ago.",
            scope="A couple of people near me said the same.",
            error_text=None,
        )

    def diagnostic_path(self, at: Placement) -> list[Query]:
        return [
            Query(kind="machine.services", target=PLACEHOLDER, args={"service": "Spooler"}),
            Query(
                kind="printer.state",
                target=_SERVER_DIAGNOSTIC_PRINTER,
                args={"from": PLACEHOLDER},
            ),
        ]

    def canonical_resolutions(self) -> list[ResolutionPath]:
        return [
            ResolutionPath(
                label="Restart the spooler service on the print server",
                actions=[
                    Action(
                        kind="machine.restart_service",
                        target=PLACEHOLDER,
                        args={"service": "Spooler"},
                    ),
                ],
            ),
        ]

    def reporters(self, world: World, at: Placement) -> list[str] | None:
        printers_here = {p.name for p in world.printers.values() if p.host == at.key}
        return sorted(
            m.assigned_to
            for m in world.machines.values()
            if m.assigned_to is not None
            and any(printer in printers_here for printer in m.installed_printers)
        )


register(SpoolerStopped())
register(WrongDriver())
register(ServerSpoolerStopped())


class PrinterOffline(FaultBase):
    """The device itself, not the queue and not the workstation.

    The cheapest ticket in the catalog and worth having: jobs queue up and stay
    queued, which is visibly different from `print.spooler_stopped`, where they
    vanish without a trace.
    """

    id = "print.printer_offline"
    domain = "printing"
    difficulty = 1
    canonical_title = "Printer reporting offline at the device"
    supported_backends = frozenset({"simulated", "winrm"})
    leak_terms = ["offline", "power", "device", "reset"]
    escalation_is_correct = False
    kb_articles = ["printing-nothing-prints", "printing-queue-and-device"]

    def placements(self, world: World) -> list[Placement]:
        return _installed_printers(world)

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        printer = world.printers[at.key]
        printer.online = False
        printer.jobs.append(
            PrintJob(
                job_id=rng.randint(40, 90),
                owner_sam=_first_user_of(world, at.key),
                document="Delivery note",
                pages=2,
            )
        )

    def is_present(self, world: World, at: Placement) -> bool:
        return not world.printers[at.key].online

    def symptoms(self, world: World, at: Placement) -> UserSymptoms:
        return UserSymptoms(
            opening="My printing is all sitting there waiting and none of it comes out.",
            onset="Since I got in this morning.",
            scope="I think anyone using that one has the same problem.",
            error_text=None,
        )

    def diagnostic_path(self, at: Placement) -> list[Query]:
        return [
            Query(kind="printer.jobs", target=PLACEHOLDER),
            Query(kind="printer.state", target=PLACEHOLDER),
        ]

    def canonical_resolutions(self) -> list[ResolutionPath]:
        return [
            ResolutionPath(
                label="Power-cycle the device and bring it back online",
                actions=[Action(kind="printer.reset", target=PLACEHOLDER)],
            ),
        ]


class StuckJobAtQueueHead(FaultBase):
    """A cascade: one document nobody can print past.

    The job at the head of a shared queue errored and everything behind it is
    waiting. Restarting the spooler does not clear it — the job comes back — so
    this is the printing fault where the reflex fix is the wrong one.
    """

    id = "print.stuck_job"
    domain = "printing"
    difficulty = 2
    canonical_title = "Errored job at the head of a shared print queue"
    supported_backends = frozenset({"simulated", "winrm"})
    leak_terms = ["stuck", "queue", "spool", "job"]
    escalation_is_correct = False
    kb_articles = ["printing-nothing-prints", "printing-queue-and-device"]

    def placements(self, world: World) -> list[Placement]:
        return _installed_printers(world)

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        printer = world.printers[at.key]
        users = _users_of(world, at.key)
        printer.jobs.append(
            PrintJob(
                job_id=101,
                owner_sam=users[0],
                document="Manifest batch",
                pages=rng.randint(40, 180),
                status=JobStatus.ERROR,
            )
        )
        printer.jobs.extend(
            PrintJob(job_id=102 + i, owner_sam=sam, document="Delivery note", pages=1)
            for i, sam in enumerate(users[1:])
        )

    def is_present(self, world: World, at: Placement) -> bool:
        return any(job.status is JobStatus.ERROR for job in world.printers[at.key].jobs)

    def symptoms(self, world: World, at: Placement) -> UserSymptoms:
        return UserSymptoms(
            opening="Everything I send just piles up behind somebody else's big "
            "document and nothing moves.",
            onset="Since about eleven.",
            scope="Everyone who uses that printer is waiting on the same thing.",
            error_text=None,
        )

    def diagnostic_path(self, at: Placement) -> list[Query]:
        return [Query(kind="printer.jobs", target=PLACEHOLDER)]

    def canonical_resolutions(self) -> list[ResolutionPath]:
        return [
            ResolutionPath(
                label="Clear the queue",
                actions=[Action(kind="printer.clear_queue", target=PLACEHOLDER)],
            ),
        ]

    def reporters(self, world: World, at: Placement) -> list[str] | None:
        return _users_of(world, at.key)


class DriverAfterModelSwap(FaultBase):
    """The hardware changed, not the computer.

    A cascade, and the mirror image of `print.wrong_driver`: there, one
    workstation was given the wrong driver. Here the *printer* was replaced with
    a different model and every workstation still holds the driver for the old
    one, so everybody prints gibberish at once. The placement is the printer,
    and the repair is published from the print server rather than repeated at
    every desk.
    """

    id = "print.driver_after_model_swap"
    domain = "printing"
    difficulty = 3
    canonical_title = "Printer replaced with a different model; workstations hold the old driver"
    supported_backends = frozenset({"simulated", "winrm"})
    leak_terms = ["driver", "model", "swap", "replace"]
    escalation_is_correct = False
    kb_articles = ["printing-nothing-prints", "printing-queue-and-device"]

    def placements(self, world: World) -> list[Placement]:
        return _installed_printers(world)

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        printer = world.printers[at.key]
        printer.model = REPLACEMENT_MODEL
        printer.correct_driver = REPLACEMENT_DRIVER

    def is_present(self, world: World, at: Placement) -> bool:
        printer = world.printers[at.key]
        return any(
            machine.printer_drivers.get(printer.name) != printer.correct_driver
            for machine in world.machines.values()
            if printer.name in machine.installed_printers
        )

    def symptoms(self, world: World, at: Placement) -> UserSymptoms:
        return UserSymptoms(
            opening="A different printer turned up yesterday and now everything "
            "that comes out of it is pages of nonsense characters.",
            onset="Since the one that was there before got taken away.",
            scope="Everyone printing to that one is getting the same rubbish.",
            error_text=None,
        )

    def diagnostic_path(self, at: Placement) -> list[Query]:
        return [
            Query(
                kind="printer.state",
                target=PLACEHOLDER,
                args={"from": PLACEHOLDER_MACHINE},
            ),
        ]

    def canonical_resolutions(self) -> list[ResolutionPath]:
        return [
            ResolutionPath(
                label="Publish the new driver from the print server",
                actions=[Action(kind="printer.push_driver", target=PLACEHOLDER)],
            ),
        ]

    def reporters(self, world: World, at: Placement) -> list[str] | None:
        return _users_of(world, at.key)


register(PrinterOffline())
register(StuckJobAtQueueHead())
register(DriverAfterModelSwap())
