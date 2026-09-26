from datetime import timedelta
from random import Random

from vitsc.env.base import Action, Query
from vitsc.faults.base import (
    FaultBase,
    PLACEHOLDER,
    PLACEHOLDER_GROUP,
    PLACEHOLDER_MACHINE,
    PLACEHOLDER_SUB_GROUP,
    Placement,
    ResolutionPath,
    UserSymptoms,
    sub_group_name,
)
from vitsc.faults.registry import register
from vitsc.world.models import ADGroup, ServiceState, World

# The surname the name-change fault leaves behind on the sign-in name. A fixed
# value, not a generated one: the point of the fault is that two records
# disagree, not which name won.
_MAIDEN_SURNAME = "whitcombe"


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


class PasswordChangeNotCached(FaultBase):
    """The password changed while the machine was away from the network, so the
    machine is still checking against the one it last cached. The tell is that
    the *old* password works and the new one does not — which is the opposite
    of every other sign-in fault in the catalog.

    Named for the mechanism rather than for "cached credentials", because
    `ad.cached_credentials_expired` is a different fault about the same
    relationship: there the machine's channel to the domain is down and the
    person is signed in but cut off from their resources, while here the channel
    is fine and the credential it holds is simply older than the password. Two
    ids both reading `cached_credentials_*` would be indistinguishable in an
    after-action.
    """

    id = "ad.password_change_not_cached"
    domain = "identity"
    difficulty = 2
    canonical_title = "Workstation still holding the pre-change cached credential"
    supported_backends = frozenset({"simulated", "winrm"})
    leak_terms = ["cache", "cached", "secure channel", "machine account"]
    escalation_is_correct = False
    kb_articles = ["identity-cannot-sign-in"]

    def placements(self, world: World) -> list[Placement]:
        return _staff_with_machines(world)

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        machine = world.machine_for(at.key)
        if machine is None:  # pragma: no cover - placements guarantee a machine
            raise KeyError(f"{at.key} has no workstation")
        user = world.org.users[at.key]
        user.pwd_last_set = world.clock - timedelta(hours=rng.randint(2, 20))
        user.pwd_expires = world.clock + timedelta(days=60)
        machine.last_domain_sync = user.pwd_last_set - timedelta(days=rng.randint(3, 21))

    def is_present(self, world: World, at: Placement) -> bool:
        machine = world.machine_for(at.key)
        if machine is None or machine.last_domain_sync is None:
            return False
        return machine.last_domain_sync < world.org.users[at.key].pwd_last_set

    def symptoms(self, world: World, at: Placement) -> UserSymptoms:
        return UserSymptoms(
            opening="My new sign-in doesn't work on this machine, but the old one "
            "still lets me in.",
            onset="I changed it yesterday afternoon when it asked me to.",
            scope="It works fine on the terminal downstairs, just not here.",
            error_text="The user name or password is incorrect. Try again.",
        )

    def diagnostic_path(self, at: Placement) -> list[Query]:
        return [
            Query(kind="machine.state", target=PLACEHOLDER_MACHINE),
            Query(kind="ad.user", target=at.key),
        ]

    def canonical_resolutions(self) -> list[ResolutionPath]:
        return [
            ResolutionPath(
                label="Re-authenticate the machine against the domain",
                actions=[
                    Action(kind="machine.refresh_credentials", target=PLACEHOLDER_MACHINE),
                ],
            ),
        ]


class NestedGroupMembership(FaultBase):
    """The account *is* in a group whose name looks right, and the share still
    refuses it: the group it is in was never put inside the group the share
    actually requires. `MemberOf` on the account is not the question the file
    server asks — which is why `World.groups_of()` stays non-transitive and
    `is_member()` exists next to it."""

    id = "ad.nested_group_membership"
    domain = "identity"
    difficulty = 4
    canonical_title = "Access group nested one level below the group the share requires"
    supported_backends = frozenset({"simulated", "winrm"})
    leak_terms = ["nest", "group", "membership", "token", "recursive"]
    escalation_is_correct = False
    kb_articles = ["identity-missing-drive", "identity-group-and-access"]

    def placements(self, world: World) -> list[Placement]:
        return [
            Placement(kind="user", key=m.assigned_to)
            for m in world.machines.values()
            if m.assigned_to and world.groups_of(m.assigned_to)
        ]

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        # `ACC-Share-RW` becomes `ACC-Staff` — plausibly the group somebody
        # reorganising permissions would have created, and plausibly the one a
        # technician stops reading at. `sub_group_name` is shared with the
        # sentinel that names it in a resolution.
        parent_name = world.groups_of(at.key)[0]
        child_name = sub_group_name(parent_name)
        world.org.groups[parent_name].members.remove(at.key)
        world.org.groups.setdefault(child_name, ADGroup(name=child_name))
        if at.key not in world.org.groups[child_name].members:
            world.org.groups[child_name].members.append(at.key)

    def is_present(self, world: World, at: Placement) -> bool:
        machine = world.machine_for(at.key)
        if machine is None or "S:" not in machine.mapped_drives:
            return False
        share = world.shares[machine.mapped_drives["S:"]]
        return not world.is_member(share.required_group, at.key)

    def symptoms(self, world: World, at: Placement) -> UserSymptoms:
        return UserSymptoms(
            opening="I still can't open the shared folder, and someone already "
            "told me I'd been given access.",
            onset="They said it was sorted on Friday. It wasn't.",
            scope="Everyone else on my team can open it.",
            error_text="You do not have permission to access this folder.",
        )

    def diagnostic_path(self, at: Placement) -> list[Query]:
        return [
            Query(kind="share.access", target="S:", args={"from": PLACEHOLDER_MACHINE}),
            Query(kind="ad.user", target=at.key),
            Query(kind="ad.group", target=PLACEHOLDER_GROUP),
        ]

    def canonical_resolutions(self) -> list[ResolutionPath]:
        # Two honest paths, and neither is "the" answer: nest the group the
        # reorganisation created, or grant the person directly. A site with a
        # group-nesting convention would prefer the first; a site without one
        # would prefer the second. The gate is the share opening either way.
        return [
            ResolutionPath(
                label="Nest the sub-group inside the group the share requires",
                actions=[
                    Action(
                        kind="ad.nest_group",
                        target=PLACEHOLDER_GROUP,
                        args={"member_group": PLACEHOLDER_SUB_GROUP},
                    ),
                ],
            ),
            ResolutionPath(
                label="Grant the account directly",
                actions=[
                    Action(
                        kind="ad.add_member",
                        target=PLACEHOLDER_GROUP,
                        args={"member": PLACEHOLDER},
                    ),
                ],
            ),
        ]


class UpnMismatchAfterNameChange(FaultBase):
    """Escalate-correct for a fourth distinct reason: not authorisation, not
    hardware, and not "acting is the mistake" — nobody in IT *knows the right
    answer*. Which name is the legal one is a personnel record, and guessing at
    it renames a person by accident."""

    id = "ad.upn_mismatch"
    domain = "identity"
    difficulty = 3
    canonical_title = "Sign-in name and mail address disagree after a legal name change"
    supported_backends = frozenset({"simulated", "winrm"})
    leak_terms = ["upn", "principal name", "rename", "mismatch"]
    escalation_is_correct = True
    kb_articles = ["identity-cannot-sign-in", "general-escalation-and-ownership"]
    escalation_reason = (
        "Which of the two names is the current legal one is a personnel record, "
        "not something the service desk holds. Picking one renames somebody on "
        "a guess, and the wrong guess follows them through payroll and every "
        "system that trusts the directory — HR confirms the name first."
    )
    escalation_evidence = [Query(kind="ad.user", target=PLACEHOLDER)]

    def placements(self, world: World) -> list[Placement]:
        return _staff_with_machines(world)

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        user = world.org.users[at.key]
        initial = user.display_name.split()[0][0].lower()
        user.upn = f"{initial}.{_MAIDEN_SURNAME}@{world.org.domain}"

    def is_present(self, world: World, at: Placement) -> bool:
        user = world.org.users[at.key]
        return user.upn.lower() != f"{user.sam}@{world.org.domain}".lower()

    def symptoms(self, world: World, at: Placement) -> UserSymptoms:
        return UserSymptoms(
            opening="Half our systems know me by my married name and half still "
            "have the old one, and now the travel booking site won't let me in.",
            onset="I handed the paperwork in weeks ago.",
            scope="Just me. Payroll went through under one of them and my email "
            "comes from the other.",
            error_text="We couldn't find an account with that address.",
        )

    def diagnostic_path(self, at: Placement) -> list[Query]:
        return [
            Query(kind="ad.user", target=at.key),
            Query(kind="mail.mailbox", target=at.key),
        ]

    def canonical_resolutions(self) -> list[ResolutionPath]:
        # Empty and honestly so, the same encoding `endpoint.failing_disk` uses:
        # there is no action here that IT is entitled to take before HR answers,
        # so the catalog declares none rather than offering a wrong one.
        return []


register(CachedCredentialsExpired())
register(PasswordChangeNotCached())
register(NestedGroupMembership())
register(UpnMismatchAfterNameChange())
