"""Where the persona backend is chosen.

The drill must be fully playable with nothing running on localhost, so the
default is always `TemplatePersona` and selecting the model-backed one is an
explicit opt-in through the environment. Anything unrecognised falls back to
the template rather than raising: a typo in a shell variable should not take
the session down.
"""

import os
from typing import Literal

from pydantic import BaseModel

from vitsc.persona.client import DEFAULT_BASE_URL, LMStudioPersona, make_client
from vitsc.persona.models import Persona
from vitsc.persona.templates import TemplatePersona

Backend = Literal["template", "lmstudio"]
BACKENDS: tuple[Backend, ...] = ("template", "lmstudio")


class PersonaSettings(BaseModel):
    backend: Backend = "template"
    base_url: str = DEFAULT_BASE_URL
    model: str = "local-model"

    @classmethod
    def from_env(cls) -> "PersonaSettings":
        backend = os.environ.get("VITSC_PERSONA", "template").strip().lower()
        return cls(
            # An unknown value is not an error. LM Studio being misconfigured
            # should cost you the model persona, not the drill.
            backend=backend if backend in BACKENDS else "template",
            base_url=os.environ.get("VITSC_BASE_URL", DEFAULT_BASE_URL),
            model=os.environ.get("VITSC_MODEL", "local-model"),
        )


def build_persona(settings: PersonaSettings) -> Persona:
    """The persona for a whole session.

    Built with no leak terms: since Task 1 they arrive per ticket through
    `for_fault()`, because one session runs many faults in turn.
    """
    if settings.backend == "lmstudio":
        return LMStudioPersona(
            make_client(settings.base_url), settings.model, leak_terms=[]
        )
    return TemplatePersona()
