from datetime import timedelta
from random import Random

from vitsc.env.base import Action, Query
from vitsc.faults.base import (
    PLACEHOLDER,
    PLACEHOLDER_GROUP,
    PLACEHOLDER_MACHINE,
    Placement,
    ResolutionPath,
    UserSymptoms,
)
from vitsc.faults.registry import register
from vitsc.world.models import World


def _staff_with_machines(world: World) -> list[Placement]:
    """Users who make plausible victims: ordinary staff with a workstation."""
    return [
        Placement(kind="user", key=m.assigned_to)
        for m in world.machines.values()
        if m.assigned_to is not None
    ]


class AccountLocked:
    id = "ad.account_locked"
    domain = "identity"
    difficulty = 1
    canonical_title = "AD account locked out after repeated bad password attempts"
    supported_backends = frozenset({"simulated", "winrm"})
    leak_terms = ["locked", "lockout", "active directory", "ad ", "unlock"]
    escalation_is_correct = False

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


class PasswordExpired:
    id = "ad.password_expired"
    domain = "identity"
    difficulty = 2
    canonical_title = "Domain password expired; user never saw the change prompt"
    supported_backends = frozenset({"simulated", "winrm"})
    leak_terms = ["expired", "password policy", "reset"]
    escalation_is_correct = False

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


class OffboardedReactivation:
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


class ShareGroupRemoved:
    id = "share.group_membership_removed"
    domain = "identity"
    difficulty = 3
    canonical_title = "User removed from the department share security group"
    supported_backends = frozenset({"simulated", "winrm"})
    leak_terms = ["group", "membership", "permission", "security group", "acl"]
    escalation_is_correct = False

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


register(AccountLocked())
register(PasswordExpired())
register(OffboardedReactivation())
register(ShareGroupRemoved())
