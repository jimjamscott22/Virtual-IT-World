from datetime import timedelta
from random import Random

from vitsc.env.base import Action, Query
from vitsc.faults.base import (
    FaultBase,
    PLACEHOLDER,
    PLACEHOLDER_GROUP,
    PLACEHOLDER_MACHINE,
    Placement,
    ResolutionPath,
    UserSymptoms,
)
from vitsc.faults.registry import register
from vitsc.world.models import ServiceState, World


def _staff_with_machines(world: World) -> list[Placement]:
    """Users who make plausible victims: ordinary staff with a workstation."""
    return [
        Placement(kind="user", key=m.assigned_to)
        for m in world.machines.values()
        if m.assigned_to is not None
    ]


def _workstations(world: World) -> list[Placement]:
    return [
        Placement(kind="machine", key=m.hostname)
        for m in world.machines.values()
        if m.assigned_to is not None
    ]


class AccountLocked(FaultBase):
    id = "ad.account_locked"
    domain = "identity"
    difficulty = 1
    canonical_title = "AD account locked out after repeated bad password attempts"
    supported_backends = frozenset({"simulated", "winrm"})
    leak_terms = ["locked", "lockout", "active directory", "ad ", "unlock"]
    escalation_is_correct = False
    kb_articles = ["identity-cannot-sign-in"]

    def placements(self, world: World) -> list[Placement]:
        return _staff_with_machines(world)

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        user = world.org.users[at.key]
        user.locked_out = True
        user.bad_pwd_count = rng.randint(6, 14)

    def is_present(self, world: World, at: Placement) -> bool:
        return world.org.users[at.key].locked_out

    def symptoms(self, world: World, at: Placement) -> UserSymptoms:
        return UserSymptoms(
            opening="I can't sign in to my computer this morning.",
            onset="It worked fine when I left on Friday.",
            scope="Just me as far as I know, the person next to me is fine.",
            error_text=(
                "It says it can't sign me in and that I should contact my "
                "system administrator."
            ),
        )

    def diagnostic_path(self, at: Placement) -> list[Query]:
        return [Query(kind="ad.user", target=at.key)]

    def canonical_resolutions(self) -> list[ResolutionPath]:
        return [
            ResolutionPath(
                label="Unlock the account",
                actions=[Action(kind="ad.unlock", target=PLACEHOLDER)],
            ),
            ResolutionPath(
                label="Reset the password",
                actions=[Action(kind="ad.reset_password", target=PLACEHOLDER)],
            ),
        ]


class PasswordExpired(FaultBase):
    id = "ad.password_expired"
    domain = "identity"
    difficulty = 2
    canonical_title = "Domain password expired; user never saw the change prompt"
    supported_backends = frozenset({"simulated", "winrm"})
    leak_terms = ["expired", "password policy", "reset"]
    escalation_is_correct = False
    kb_articles = ["identity-cannot-sign-in"]

    def placements(self, world: World) -> list[Placement]:
        return _staff_with_machines(world)

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        user = world.org.users[at.key]
        user.pwd_last_set = world.clock - timedelta(days=91)
        user.pwd_expires = world.clock - timedelta(days=rng.randint(1, 3))

    def is_present(self, world: World, at: Placement) -> bool:
        return world.clock > world.org.users[at.key].pwd_expires

    def symptoms(self, world: World, at: Placement) -> UserSymptoms:
        return UserSymptoms(
            opening="It won't let me log in and I know I'm typing the right thing.",
            onset="Since this morning. Friday was fine.",
            scope="Only me, my desk neighbour got in okay.",
            error_text="You must change your password before signing in.",
        )

    def diagnostic_path(self, at: Placement) -> list[Query]:
        return [Query(kind="ad.user", target=at.key)]

    def canonical_resolutions(self) -> list[ResolutionPath]:
        return [
            ResolutionPath(
                label="Reset the password and set a new expiry",
                actions=[Action(kind="ad.reset_password", target=PLACEHOLDER)],
            ),
        ]


class OffboardedReactivation(FaultBase):
    """Escalate-correct: reactivating a departed employee's account needs
    HR/manager authorisation. A technician who just clicks Enable is wrong,
    even though the symptom clears."""

    id = "ad.offboarded_reactivation"
    domain = "identity"
    difficulty = 3
    canonical_title = "Disabled account of an offboarded employee; requires HR authorisation"
    supported_backends = frozenset({"simulated", "winrm"})
    leak_terms = ["disabled", "offboard", "terminated", "hr approval"]
    escalation_is_correct = True
    kb_articles = ["identity-cannot-sign-in"]
    escalation_reason = (
        "Reactivating a departed employee's account needs HR or manager "
        "authorisation before it happens, not just a technician's say-so."
    )

    def placements(self, world: World) -> list[Placement]:
        return [Placement(kind="user", key="h.reyes")]

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        world.org.users[at.key].enabled = False

    def is_present(self, world: World, at: Placement) -> bool:
        return not world.org.users[at.key].enabled

    def symptoms(self, world: World, at: Placement) -> UserSymptoms:
        return UserSymptoms(
            opening="Hector is back on nights from this week and his login doesn't work at all.",
            onset="He left in June and started again yesterday.",
            scope="Just his account. Everyone else on the night shift is fine.",
            error_text=(
                "Your account has been turned off. "
                "Please contact your system administrator."
            ),
        )

    def diagnostic_path(self, at: Placement) -> list[Query]:
        return [Query(kind="ad.user", target=at.key)]

    def canonical_resolutions(self) -> list[ResolutionPath]:
        # Present so the conformance harness can verify the fault is *technically*
        # clearable. Grading still marks a fix as wrong: escalation_is_correct.
        return [
            ResolutionPath(
                label="Re-enable after HR authorisation",
                actions=[Action(kind="ad.enable", target=PLACEHOLDER)],
            ),
        ]


class ShareGroupRemoved(FaultBase):
    id = "share.group_membership_removed"
    domain = "identity"
    difficulty = 3
    canonical_title = "User removed from the department share security group"
    supported_backends = frozenset({"simulated", "winrm"})
    leak_terms = ["group", "membership", "permission", "security group", "acl"]
    escalation_is_correct = False
    kb_articles = ["identity-missing-drive"]

    def placements(self, world: World) -> list[Placement]:
        return [
            Placement(kind="user", key=m.assigned_to)
            for m in world.machines.values()
            if m.assigned_to and world.groups_of(m.assigned_to)
        ]

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        group_name = world.groups_of(at.key)[0]
        world.org.groups[group_name].members.remove(at.key)

    def is_present(self, world: World, at: Placement) -> bool:
        machine = world.machine_for(at.key)
        if machine is None or "S:" not in machine.mapped_drives:
            return False
        share = world.shares[machine.mapped_drives["S:"]]
        return at.key not in world.org.groups[share.required_group].members

    def symptoms(self, world: World, at: Placement) -> UserSymptoms:
        return UserSymptoms(
            opening="My S drive is gone. There's a little red cross on it.",
            onset="It was there yesterday.",
            scope="My whole team uses that folder and they can still get in.",
            error_text="S:\\ is not accessible. Access is denied.",
        )

    def diagnostic_path(self, at: Placement) -> list[Query]:
        return [
            Query(kind="share.access", target="S:", args={"from": PLACEHOLDER_MACHINE}),
            Query(kind="ad.user", target=at.key),
        ]

    def canonical_resolutions(self) -> list[ResolutionPath]:
        return [
            ResolutionPath(
                label="Restore group membership",
                actions=[
                    Action(
                        kind="ad.add_member",
                        target=PLACEHOLDER_GROUP,
                        args={"member": PLACEHOLDER},
                    ),
                ],
            ),
        ]


class CachedCredentialsExpired(FaultBase):
    """A workstation's cached domain sign-in lets a user reach their desktop
    even when the machine's own channel to the domain is broken — which is
    what happens after an extended absence, once that channel needs to be
    re-established on return. The account itself checks out clean; the
    differential is noticing that and looking at the machine instead."""

    id = "ad.cached_credentials_expired"
    domain = "identity"
    difficulty = 2
    canonical_title = (
        "Workstation's cached domain credentials are stale after an "
        "extended absence from the corporate network"
    )
    supported_backends = frozenset({"simulated", "winrm"})
    leak_terms = ["cached", "cache", "trust relationship", "secure channel", "netlogon"]
    escalation_is_correct = False
    kb_articles = ["identity-signed-in-but-cut-off"]

    def placements(self, world: World) -> list[Placement]:
        return _workstations(world)

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        world.machines[at.key].services["Netlogon"] = ServiceState.STOPPED

    def is_present(self, world: World, at: Placement) -> bool:
        # Unlike `Spooler`, `Netlogon` has no entry in a clean machine's
        # `services` dict at all — a healthy world never mentions it, so
        # absence must read as healthy rather than as "unconfirmed running".
        return world.machines[at.key].services.get("Netlogon") is ServiceState.STOPPED

    def symptoms(self, world: World, at: Placement) -> UserSymptoms:
        return UserSymptoms(
            opening="I can log in fine, but none of my shared drives will "
            "connect, my printer's missing, and Outlook won't stay signed in.",
            onset="I've been working from home for the last few weeks and "
            "only came back into the office this morning.",
            scope="Just me — the person next to me hasn't had any problems.",
            error_text="Outlook keeps asking for my password, I type it in "
            "correctly, and it just asks again. My drives say the network "
            "path can't be found.",
        )

    def diagnostic_path(self, at: Placement) -> list[Query]:
        return [Query(kind="machine.services", target=at.key, args={"service": "Netlogon"})]

    def canonical_resolutions(self) -> list[ResolutionPath]:
        return [
            ResolutionPath(
                label="Restart the Netlogon service",
                actions=[
                    Action(
                        kind="machine.restart_service",
                        target=PLACEHOLDER,
                        args={"service": "Netlogon"},
                    ),
                ],
            ),
        ]


register(AccountLocked())
register(PasswordExpired())
register(OffboardedReactivation())
register(ShareGroupRemoved())
register(CachedCredentialsExpired())
