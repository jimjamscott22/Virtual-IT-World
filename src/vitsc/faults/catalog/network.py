from random import Random

from vitsc.env.base import Action, Query
from vitsc.faults.base import PLACEHOLDER, Placement, ResolutionPath, UserSymptoms
from vitsc.faults.registry import register
from vitsc.world.models import World


def _workstations(world: World) -> list[Placement]:
    return [
        Placement(kind="machine", key=m.hostname)
        for m in world.machines.values()
        if m.assigned_to is not None
    ]


class StaticDnsMisconfig:
    id = "net.static_dns_misconfig"
    domain = "network"
    difficulty = 2
    canonical_title = "Workstation pinned to a stale static DNS server"
    supported_backends = frozenset({"simulated", "winrm"})
    leak_terms = ["dns", "resolver", "name resolution", "static"]
    escalation_is_correct = False

    def placements(self, world: World) -> list[Placement]:
        return _workstations(world)

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        world.machines[at.key].dns_servers = [f"10.20.10.{rng.choice([98, 99, 200])}"]

    def is_present(self, world: World, at: Placement) -> bool:
        machine = world.machines[at.key]
        return not set(machine.dns_servers) & set(world.network.dns_servers)

    def symptoms(self, world: World, at: Placement) -> UserSymptoms:
        return UserSymptoms(
            opening="The internet's down on my machine and I can't get to any of our systems.",
            onset="Started after I restarted this morning.",
            scope="Only mine. Everyone else in the office is working.",
            error_text="Hmmm, we can't reach this page.",
        )

    def diagnostic_path(self, at: Placement) -> list[Query]:
        return [
            Query(kind="net.ipconfig", target=at.key, args={"from": at.key}),
            Query(kind="net.ping", target="MER-FS-01", args={"from": at.key}),
        ]

    def canonical_resolutions(self) -> list[ResolutionPath]:
        return [
            ResolutionPath(
                label="Point DNS back at the domain controller",
                actions=[
                    Action(
                        kind="machine.set_dns",
                        target=PLACEHOLDER,
                        args={"servers": "10.20.10.5"},
                    ),
                ],
            ),
        ]


class NoDhcpLease:
    id = "net.no_dhcp_lease"
    domain = "network"
    difficulty = 2
    canonical_title = "Workstation failed to obtain a DHCP lease and fell back to APIPA"
    supported_backends = frozenset({"simulated", "winrm"})
    leak_terms = ["dhcp", "apipa", "lease", "169.254"]
    escalation_is_correct = False

    def placements(self, world: World) -> list[Placement]:
        return _workstations(world)

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        machine = world.machines[at.key]
        machine.ip = None
        machine.dhcp_enabled = True

    def is_present(self, world: World, at: Placement) -> bool:
        return world.machines[at.key].ip is None

    def symptoms(self, world: World, at: Placement) -> UserSymptoms:
        return UserSymptoms(
            opening="Nothing loads at all on this computer, not even the intranet.",
            onset="Since I plugged it back in after the weekend.",
            scope="Just this one machine.",
            error_text="No internet, secured.",
        )

    def diagnostic_path(self, at: Placement) -> list[Query]:
        return [Query(kind="net.ipconfig", target=at.key, args={"from": at.key})]

    def canonical_resolutions(self) -> list[ResolutionPath]:
        return [
            ResolutionPath(
                label="Renew the DHCP lease",
                actions=[Action(kind="machine.renew_dhcp", target=PLACEHOLDER)],
            ),
        ]


register(StaticDnsMisconfig())
register(NoDhcpLease())
