import random

from vitsc.persona.models import PersonaCard
from vitsc.world.models import ADUser

# How much technical vocabulary the person is likely to have. This is a
# property of the *job*, not of the fault — the same clerk sounds the same
# whether their account is locked or their printer is offline.
LITERACY_BY_DEPARTMENT = {
    "Accounting": 1,
    "HR": 1,
    "Warehouse": 1,
    "Sales": 2,
    "Operations": 2,
}
MOODS = ["calm", "rushed", "frustrated"]
ACTIVITIES = [
    "trying to get a report out",
    "about to join a call",
    "starting the morning shift",
    "in the middle of a customer order",
]


def card_for(user: ADUser, rng: random.Random | None = None) -> PersonaCard:
    """Build the persona card for an AD user.

    Seeded off `user.sam` by default, so the same person has the same
    temperament every time they appear — the drill is meant to be a stable
    workplace, not a new cast each session.
    """
    rng = rng or random.Random(user.sam)
    return PersonaCard(
        name=user.display_name,
        role=user.title,
        department=user.department,
        literacy=LITERACY_BY_DEPARTMENT.get(user.department, 2),
        mood=rng.choice(MOODS),
        activity=rng.choice(ACTIVITIES),
    )
