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
from vitsc.world.models import EventEntry, ServiceState, World

GENERIC_DRIVER = "Generic / Text Only"
# Any printer hosted on the print server works as the diagnostic target —
# `printer.state`'s `SpoolerState` reads the *server's* service, not the
# printer's own — so a literal name is fine, the same way `net.ping`'s
# diagnostic already hardcodes `MER-FS-01`. A fault cannot resolve one from
# `World` itself: `diagnostic_path()` receives only a `Placement`.
_SERVER_DIAGNOSTIC_PRINTER = "PRT-ACC-01"


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
    kb_articles = ["printing-nothing-prints"]

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
