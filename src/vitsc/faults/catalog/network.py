from random import Random

from vitsc.env.base import Action, Query
from vitsc.faults.base import FaultBase, PLACEHOLDER, Placement, ResolutionPath, UserSymptoms
from vitsc.faults.registry import register
from vitsc.world.models import EventEntry, World


# Narrow enough that the site's servers and the site's router both fall outside
# what the machine computes as its own subnet. A /24 estate with servers on .5
# to .8 and workstations on .41 upwards: a /28 or /29 boundary separates them.
NARROW_MASKS = ["255.255.255.240", "255.255.255.248"]

DECOMMISSIONED_PROXY = "10.20.10.9:8080"


def _lowest_hostname(world: World) -> str:
    return sorted(
        m.hostname for m in world.machines.values() if m.assigned_to is not None
    )[0]


def _partner_of(world: World, hostname: str) -> str:
    """Whose address this machine ends up holding.

    Deterministic rather than random: the fault has to name the same partner in
    `apply()`, in `reporters()` and for anyone re-deriving it later, and an
    `rng` is not in scope for the last two.
    """
    others = sorted(
        m.hostname
        for m in world.machines.values()
        if m.assigned_to is not None and m.hostname != hostname
    )
    return others[0]


def _workstations(world: World) -> list[Placement]:
    return [
        Placement(kind="machine", key=m.hostname)
        for m in world.machines.values()
        if m.assigned_to is not None
    ]


class StaticDnsMisconfig(FaultBase):
    id = "net.static_dns_misconfig"
    domain = "network"
    difficulty = 2
    canonical_title = "Workstation pinned to a stale static DNS server"
    supported_backends = frozenset({"simulated", "winrm"})
    leak_terms = ["dns", "resolver", "name resolution", "static"]
    escalation_is_correct = False
    kb_articles = ["network-no-internet"]

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


class NoDhcpLease(FaultBase):
    id = "net.no_dhcp_lease"
    domain = "network"
    difficulty = 2
    canonical_title = "Workstation failed to obtain a DHCP lease and fell back to APIPA"
    supported_backends = frozenset({"simulated", "winrm"})
    leak_terms = ["dhcp", "apipa", "lease", "169.254"]
    escalation_is_correct = False
    kb_articles = ["network-no-internet"]

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


class WrongSubnetMask(FaultBase):
    """A mask narrow enough that the machine believes the servers are on some
    other network, and its own router is too. Nothing is unplugged and nothing
    is down: the machine's idea of "local" is simply wrong, so it never asks the
    gateway for anything."""

    id = "net.wrong_subnet_mask"
    domain = "network"
    difficulty = 3
    canonical_title = "Static subnet mask too narrow to reach the site's servers"
    supported_backends = frozenset({"simulated", "winrm"})
    leak_terms = ["mask", "prefix", "route", "routing"]
    escalation_is_correct = False
    kb_articles = ["network-no-internet", "network-address-settings"]

    def placements(self, world: World) -> list[Placement]:
        return _workstations(world)

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        world.machines[at.key].subnet_mask = rng.choice(NARROW_MASKS)

    def is_present(self, world: World, at: Placement) -> bool:
        return world.machines[at.key].subnet_mask != world.network.netmask

    def symptoms(self, world: World, at: Placement) -> UserSymptoms:
        return UserSymptoms(
            opening="Nothing on the network works from this desk — no shared "
            "folders, no web, nothing.",
            onset="Since somebody came to look at it yesterday afternoon.",
            scope="Just this machine. The one beside it is completely fine.",
            error_text=None,
        )

    def diagnostic_path(self, at: Placement) -> list[Query]:
        return [
            Query(kind="net.ipconfig", target=at.key, args={"from": at.key}),
            Query(kind="net.ping", target="10.20.10.6", args={"from": at.key}),
        ]

    def canonical_resolutions(self) -> list[ResolutionPath]:
        return [
            ResolutionPath(
                label="Renew the lease, which carries the correct mask",
                actions=[Action(kind="machine.renew_dhcp", target=PLACEHOLDER)],
            ),
            ResolutionPath(
                label="Set the mask back by hand",
                actions=[
                    Action(
                        kind="machine.set_subnet_mask",
                        target=PLACEHOLDER,
                        args={"mask": "255.255.255.0"},
                    ),
                ],
            ),
        ]


class GatewayMisconfigured(FaultBase):
    """The differential against every DNS fault: names still resolve and
    everything inside the building answers, because the resolver and the file
    server are on the same subnet. Only what has to leave the site fails."""

    id = "net.gateway_misconfigured"
    domain = "network"
    difficulty = 2
    canonical_title = "Default gateway pointing at an address no router answers on"
    supported_backends = frozenset({"simulated", "winrm"})
    leak_terms = ["gateway", "router", "default route", "hop"]
    escalation_is_correct = False
    kb_articles = ["network-no-internet", "network-address-settings"]

    def placements(self, world: World) -> list[Placement]:
        return _workstations(world)

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        world.machines[at.key].gateway = f"10.20.10.{rng.choice([2, 250, 254])}"

    def is_present(self, world: World, at: Placement) -> bool:
        return world.machines[at.key].gateway != world.network.gateway

    def symptoms(self, world: World, at: Placement) -> UserSymptoms:
        return UserSymptoms(
            opening="I can open our own systems but nothing on the outside world "
            "loads at all.",
            onset="Since first thing this morning.",
            scope="Only me. My colleague was looking at the carrier's site a "
            "minute ago.",
            error_text="Hmmm, we can't reach this page.",
        )

    def diagnostic_path(self, at: Placement) -> list[Query]:
        return [
            Query(kind="net.ipconfig", target=at.key, args={"from": at.key}),
            Query(kind="net.ping", target="8.8.8.8", args={"from": at.key}),
            Query(kind="net.ping", target="MER-FS-01", args={"from": at.key}),
        ]

    def canonical_resolutions(self) -> list[ResolutionPath]:
        return [
            ResolutionPath(
                label="Renew the lease, which carries the correct router",
                actions=[Action(kind="machine.renew_dhcp", target=PLACEHOLDER)],
            ),
        ]


class StaleProxy(FaultBase):
    """Left behind by a project that ended: the proxy it points at was
    decommissioned. Everything that does not go through a browser keeps
    working, which is what makes this feel like "the internet is broken" to the
    person reporting it and like nothing at all to `ping`."""

    id = "net.stale_proxy"
    domain = "network"
    difficulty = 1
    canonical_title = "Workstation still pointed at a decommissioned web proxy"
    supported_backends = frozenset({"simulated", "winrm"})
    leak_terms = ["proxy", "winhttp", "bypass"]
    escalation_is_correct = False
    kb_articles = ["network-no-internet", "network-address-settings"]

    def placements(self, world: World) -> list[Placement]:
        return _workstations(world)

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        world.machines[at.key].proxy_server = DECOMMISSIONED_PROXY

    def is_present(self, world: World, at: Placement) -> bool:
        return world.machines[at.key].proxy_server is not None

    def symptoms(self, world: World, at: Placement) -> UserSymptoms:
        return UserSymptoms(
            opening="Web pages won't load in my browser, but my email is coming "
            "in fine and the shared folder opens.",
            onset="It started after I came back from leave.",
            scope="Only my machine as far as I know.",
            error_text="No connection could be made because the target machine "
            "actively refused it.",
        )

    def diagnostic_path(self, at: Placement) -> list[Query]:
        return [
            Query(kind="net.proxy", target=at.key, args={"from": at.key}),
            Query(kind="net.ping", target="MER-FS-01", args={"from": at.key}),
        ]

    def canonical_resolutions(self) -> list[ResolutionPath]:
        return [
            ResolutionPath(
                label="Clear the proxy setting",
                actions=[Action(kind="machine.clear_proxy", target=PLACEHOLDER)],
            ),
        ]


class DuplicateStaticIp(FaultBase):
    """A cascade in the network domain: one wrong address, two people affected.

    Somebody set a static address on this machine that another machine already
    holds. Both users report intermittent trouble, and neither of them is the
    cause on their own — which is the lesson. The placement is the machine that
    was given the static address, and the fix is to put it back on DHCP.
    """

    id = "net.duplicate_static_ip"
    domain = "network"
    difficulty = 3
    canonical_title = "Static address configured on a workstation that already belongs to another"
    supported_backends = frozenset({"simulated", "winrm"})
    leak_terms = ["duplicate", "conflict", "static", "address in use"]
    escalation_is_correct = False
    kb_articles = ["network-address-settings", "general-triage-first-questions"]

    def placements(self, world: World) -> list[Placement]:
        # Every workstation except the one with the lowest hostname, which is
        # the partner `_partner_of` hands back — a machine cannot collide
        # with itself.
        return [p for p in _workstations(world) if p.key != _lowest_hostname(world)]

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        partner = world.machines[_partner_of(world, at.key)]
        machine = world.machines[at.key]
        machine.ip = partner.ip
        machine.dhcp_enabled = False
        # The conflict is intermittent by nature, so no single read catches it
        # in the act. What a real stack leaves behind is this event, and
        # without it `diagnostic_path`'s event-log step would be decoration.
        machine.event_log.append(
            EventEntry(
                log="System",
                source="Tcpip",
                event_id=4199,
                level="Error",
                at=world.clock,
                message=f"The system detected an address conflict for IP address "
                f"{partner.ip} with the system having network hardware address "
                "00-15-5D-2A-0C-7B.",
            )
        )

    def is_present(self, world: World, at: Placement) -> bool:
        machine = world.machines[at.key]
        if machine.ip is None:
            return False
        return any(
            other.hostname != machine.hostname and other.ip == machine.ip
            for other in world.machines.values()
        )

    def symptoms(self, world: World, at: Placement) -> UserSymptoms:
        return UserSymptoms(
            opening="My connection keeps dropping out for a minute and then "
            "coming back on its own.",
            onset="On and off since yesterday.",
            scope="Someone in the next office said theirs is doing it too.",
            error_text="Windows has detected a problem with this connection.",
        )

    def diagnostic_path(self, at: Placement) -> list[Query]:
        return [
            Query(kind="net.ipconfig", target=at.key, args={"from": at.key}),
            Query(kind="machine.eventlog", target=at.key, args={"log": "System"}),
        ]

    def canonical_resolutions(self) -> list[ResolutionPath]:
        return [
            ResolutionPath(
                label="Put the machine back on DHCP and take a fresh lease",
                actions=[
                    Action(kind="machine.enable_dhcp", target=PLACEHOLDER),
                    Action(kind="machine.renew_dhcp", target=PLACEHOLDER),
                ],
            ),
        ]

    def reporters(self, world: World, at: Placement) -> list[str] | None:
        partner = world.machines[_partner_of(world, at.key)]
        here = world.machines[at.key]
        return sorted(
            sam for sam in (here.assigned_to, partner.assigned_to) if sam is not None
        )


register(WrongSubnetMask())
register(GatewayMisconfigured())
register(StaleProxy())
register(DuplicateStaticIp())
