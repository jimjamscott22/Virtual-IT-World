from random import Random

from vitsc.env.base import Action, Query
from vitsc.faults.base import FaultBase, PLACEHOLDER, Placement, ResolutionPath, UserSymptoms
from vitsc.faults.registry import register
from vitsc.world.models import (
    CLOCK_SKEW_TOLERANCE_MINUTES,
    EventEntry,
    ProfileState,
    Process,
    ServiceState,
    SmartStatus,
    World,
)

DISK_FULL_THRESHOLD_GB = 2.0

# A plausible name for something nobody meant to leave running: an indexing
# helper from a line-of-business application. Not malware — a technician should
# be able to stop it without escalating, which is what makes this a
# difficulty-1 ticket.
RUNAWAY_PROCESS_NAME = "FreightSyncAgent.exe"
# Far above anything `world/seed.py` seeds (the busiest ordinary process sits at
# 2.4%), so the gate cannot be tripped by a healthy machine.
RUNAWAY_CPU_THRESHOLD = 60.0


def _workstations(world: World) -> list[Placement]:
    return [
        Placement(kind="machine", key=m.hostname)
        for m in world.machines.values()
        if m.assigned_to is not None
    ]


class DiskFull(FaultBase):
    id = "endpoint.disk_full"
    domain = "endpoint"
    difficulty = 2
    canonical_title = "Workstation disk nearly full, forcing a temporary profile"
    supported_backends = frozenset({"simulated", "winrm"})
    leak_terms = ["disk", "full", "space", "profile", "temporary"]
    escalation_is_correct = False
    kb_articles = ["endpoint-slow-or-failing"]

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


class FailingDisk(FaultBase):
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
    kb_articles = ["endpoint-slow-or-failing"]
    escalation_reason = (
        "A pre-fail SMART status means the drive needs replacing and its data "
        "migrating — a hardware swap, not a software fix."
    )

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


class CorruptProfile(FaultBase):
    """Not the same as `endpoint.disk_full`'s temporary profile, and the
    difference matters: there the profile failed to load *because* the disk was
    full, so freeing space fixes it. Here the stored profile itself is damaged
    and there is plenty of room — clearing disk space changes nothing, which is
    the trap."""

    id = "endpoint.corrupt_profile"
    domain = "endpoint"
    difficulty = 2
    canonical_title = "User profile on the workstation damaged and failing to load"
    supported_backends = frozenset({"simulated", "winrm"})
    leak_terms = ["profile", "corrupt", "ntuser", "rebuild"]
    escalation_is_correct = False
    kb_articles = ["endpoint-slow-or-failing", "endpoint-profile-and-services"]

    def placements(self, world: World) -> list[Placement]:
        return _workstations(world)

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        machine = world.machines[at.key]
        machine.profile_state = ProfileState.CORRUPT
        machine.event_log.append(
            EventEntry(
                log="Application",
                source="User Profile Service",
                event_id=1542,
                level="Error",
                at=world.clock,
                message="Windows cannot load the user's profile but has logged "
                "you on with the default profile for the system.",
            )
        )

    def is_present(self, world: World, at: Placement) -> bool:
        return world.machines[at.key].profile_state is ProfileState.CORRUPT

    def symptoms(self, world: World, at: Placement) -> UserSymptoms:
        return UserSymptoms(
            opening="When I log on my desktop is empty and all my settings are "
            "gone, like it's a brand new computer.",
            onset="This morning. Yesterday it was normal.",
            scope="Only on this machine — my things are all there when I log on "
            "downstairs.",
            error_text="We can't sign in to your account. This problem can "
            "often be corrected by signing out of your account and then signing "
            "back in.",
        )

    def diagnostic_path(self, at: Placement) -> list[Query]:
        return [
            Query(kind="machine.state", target=at.key),
            Query(kind="machine.eventlog", target=at.key, args={"log": "Application"}),
        ]

    def canonical_resolutions(self) -> list[ResolutionPath]:
        return [
            ResolutionPath(
                label="Rebuild the profile from the server copy",
                actions=[Action(kind="machine.rebuild_profile", target=PLACEHOLDER)],
            ),
        ]


class DnsClientDisabled(FaultBase):
    """A service set to Disabled rather than merely stopped, which is the
    differential against `print.spooler_stopped`: the reflex restart *fails*
    here, with the service manager saying why. Two steps, in order — change the
    startup type, then start it — and a technician who only does the first has
    enabled a service that still is not running."""

    id = "endpoint.service_disabled"
    domain = "endpoint"
    difficulty = 2
    canonical_title = "DNS Client service disabled on the workstation"
    supported_backends = frozenset({"simulated", "winrm"})
    leak_terms = ["disabled", "startup type", "service", "dns client"]
    escalation_is_correct = False
    kb_articles = ["endpoint-profile-and-services", "network-no-internet"]

    def placements(self, world: World) -> list[Placement]:
        return _workstations(world)

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        machine = world.machines[at.key]
        machine.services["Dnscache"] = ServiceState.DISABLED
        machine.event_log.append(
            EventEntry(
                log="System",
                source="Service Control Manager",
                event_id=7040,
                level="Information",
                at=world.clock,
                message="The start type of the DNS Client service was changed "
                "from auto start to disabled.",
            )
        )

    def is_present(self, world: World, at: Placement) -> bool:
        return world.machines[at.key].services.get("Dnscache") is not ServiceState.RUNNING

    def symptoms(self, world: World, at: Placement) -> UserSymptoms:
        return UserSymptoms(
            opening="Nothing I try to open will load — not our systems, not the web.",
            onset="Since I restarted at the end of last week.",
            scope="Just this machine. Everyone around me is working normally.",
            error_text="We can't connect to the server right now.",
        )

    def diagnostic_path(self, at: Placement) -> list[Query]:
        return [
            Query(kind="machine.services", target=at.key, args={"service": "Dnscache"}),
            Query(kind="net.ping", target="MER-FS-01", args={"from": at.key}),
            Query(kind="net.ipconfig", target=at.key, args={"from": at.key}),
        ]

    def canonical_resolutions(self) -> list[ResolutionPath]:
        return [
            ResolutionPath(
                label="Set the service back to start automatically, then start it",
                actions=[
                    Action(
                        kind="machine.enable_service",
                        target=PLACEHOLDER,
                        args={"service": "Dnscache"},
                    ),
                    Action(
                        kind="machine.restart_service",
                        target=PLACEHOLDER,
                        args={"service": "Dnscache"},
                    ),
                ],
            ),
        ]


class ClockSkew(FaultBase):
    """The machine's clock has drifted far enough that the domain stops trusting
    it. Sign-in fails and shares refuse, with an error about neither — so every
    read that looks like an access problem points somewhere else, and the tell is
    a field a technician has to actually look at rather than skim."""

    id = "endpoint.time_skew"
    domain = "endpoint"
    difficulty = 3
    canonical_title = "Workstation clock drifted beyond the domain's tolerance"
    supported_backends = frozenset({"simulated", "winrm"})
    leak_terms = ["clock", "time", "skew", "kerberos", "w32tm"]
    escalation_is_correct = False
    kb_articles = ["endpoint-profile-and-services", "identity-cannot-sign-in"]

    def placements(self, world: World) -> list[Placement]:
        return _workstations(world)

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        drift = rng.choice([-1, 1]) * rng.randint(
            CLOCK_SKEW_TOLERANCE_MINUTES * 4, CLOCK_SKEW_TOLERANCE_MINUTES * 40
        )
        world.machines[at.key].clock_offset_minutes = drift

    def is_present(self, world: World, at: Placement) -> bool:
        return (
            abs(world.machines[at.key].clock_offset_minutes)
            > CLOCK_SKEW_TOLERANCE_MINUTES
        )

    def symptoms(self, world: World, at: Placement) -> UserSymptoms:
        return UserSymptoms(
            opening="It won't let me into the shared folder and it made me sign in "
            "twice to get onto the machine at all.",
            onset="Since the power went off on our floor at the weekend.",
            scope="Just this one. The desk opposite is fine.",
            error_text="There is a problem with your account. Please contact your "
            "administrator.",
        )

    def diagnostic_path(self, at: Placement) -> list[Query]:
        return [
            Query(kind="machine.state", target=at.key),
            Query(kind="share.access", target="S:", args={"from": at.key}),
        ]

    def canonical_resolutions(self) -> list[ResolutionPath]:
        return [
            ResolutionPath(
                label="Resynchronise the clock against the domain",
                actions=[Action(kind="machine.resync_time", target=PLACEHOLDER)],
            ),
        ]


class RunawayProcess(FaultBase):
    """The cheap endpoint ticket, and the one that teaches the process table.

    Nothing is misconfigured and nothing is broken: one program is eating the
    machine. The read that finds it is the one nobody runs first, and the
    haystack is the five ordinary processes every workstation is seeded with.
    """

    id = "endpoint.runaway_process"
    domain = "endpoint"
    difficulty = 1
    canonical_title = "A single process consuming the workstation's CPU"
    supported_backends = frozenset({"simulated", "winrm"})
    leak_terms = ["process", "cpu", "task manager", "runaway"]
    escalation_is_correct = False
    kb_articles = ["endpoint-slow-or-failing", "endpoint-profile-and-services"]

    def placements(self, world: World) -> list[Placement]:
        return _workstations(world)

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        world.machines[at.key].processes.append(
            Process(
                name=RUNAWAY_PROCESS_NAME,
                pid=rng.randint(4000, 9000),
                cpu_percent=rng.uniform(88.0, 99.0),
                memory_mb=rng.uniform(1400.0, 2600.0),
            )
        )

    def is_present(self, world: World, at: Placement) -> bool:
        return any(
            process.cpu_percent >= RUNAWAY_CPU_THRESHOLD
            for process in world.machines[at.key].processes
        )

    def symptoms(self, world: World, at: Placement) -> UserSymptoms:
        return UserSymptoms(
            opening="The whole machine is crawling. The fan is roaring and it takes "
            "ten seconds to open anything.",
            onset="It's been like it since yesterday afternoon.",
            scope="Only this one. It's fine on the shared terminal.",
            error_text=None,
        )

    def diagnostic_path(self, at: Placement) -> list[Query]:
        return [Query(kind="machine.processes", target=at.key)]

    def canonical_resolutions(self) -> list[ResolutionPath]:
        return [
            ResolutionPath(
                label="Stop the offending process",
                actions=[
                    Action(
                        kind="machine.kill_process",
                        target=PLACEHOLDER,
                        args={"name": RUNAWAY_PROCESS_NAME},
                    ),
                ],
            ),
        ]


register(CorruptProfile())
register(DnsClientDisabled())
register(ClockSkew())
register(RunawayProcess())
