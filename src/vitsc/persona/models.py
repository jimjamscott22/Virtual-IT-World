from datetime import UTC, datetime
from typing import Literal, Protocol

from pydantic import BaseModel, Field

from vitsc.faults.base import UserSymptoms


class PersonaCard(BaseModel):
    """Who is on the other end of the ticket. Derived from AD, never from the fault."""

    name: str
    role: str
    department: str
    literacy: int  # 1 = avoids all jargon, 3 = knows some terms
    mood: str  # "calm", "rushed", "frustrated"
    activity: str  # what they were doing when it broke


class ChatTurn(BaseModel):
    speaker: Literal["tech", "user"]
    text: str
    # Wall clock, matching `ToolCall.at`, because this exists to order chat
    # against tool calls ("did you ask before you touched"). SLA timing is the
    # separate, simulated `world.clock` — do not mix the two here.
    at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Persona(Protocol):
    """The swap point for how the user speaks.

    Note what is *absent* from these signatures: no `World`, no `Fault`. A
    persona can only ever repeat what `UserSymptoms` already declares
    perceivable, so no implementation — template or model-backed — can leak
    the cause it doesn't have.
    """

    def initial_report(self, card: PersonaCard, symptoms: UserSymptoms) -> str: ...

    def reply(
        self,
        card: PersonaCard,
        symptoms: UserSymptoms,
        history: list[ChatTurn],
        question: str,
    ) -> str: ...
