from random import Random

from vitsc.env.base import Action, Query
from vitsc.faults.base import (
    PLACEHOLDER,
    PLACEHOLDER_MACHINE,
    PLACEHOLDER_PRINTER,
    Placement,
    ResolutionPath,
    UserSymptoms,
)
from vitsc.faults.registry import register
from vitsc.world.models import ServiceState, World

GENERIC_DRIVER = "Generic / Text Only"


def _workstations_with_printers(world: World) -> list[Placement]:
    return [
        Placement(kind="machine", key=m.hostname)
        for m in world.machines.values()
        if m.assigned_to is not None and m.installed_printers
    ]


class SpoolerStopped:
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


class WrongDriver:
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


register(SpoolerStopped())
register(WrongDriver())
