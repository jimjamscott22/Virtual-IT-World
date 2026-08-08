from random import Random

from vitsc.env.base import Action, Query
from vitsc.faults.base import PLACEHOLDER, Placement, ResolutionPath, UserSymptoms
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


register(AccountLocked())
