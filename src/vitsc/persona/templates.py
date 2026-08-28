"""The model-free persona.

Used whenever LM Studio is unavailable, and by every test in the suite — the
suite must never need a model loaded (Global Constraints). Every sentence it
emits is either a `UserSymptoms` field verbatim or fixed connective text, so
it cannot leak a cause it was never told.
"""

from vitsc.faults.base import UserSymptoms
from vitsc.persona.models import ChatTurn, PersonaCard

DEFLECTION = "I'm not sure, sorry — I don't really know the computer stuff."
NO_ERROR = "No, there's no message, it just doesn't work."

ONSET_WORDS = {"when", "last", "start", "began", "since", "long"}
SCOPE_WORDS = {"anyone", "else", "others", "team", "only", "just you", "colleague"}
ERROR_WORDS = {"error", "message", "say", "screen", "shows", "text", "popup"}


def _quoted_error(error_text: str) -> str:
    """Report the on-screen text without stacking two 'It says' prefixes.

    Most faults put a literal error string in `error_text`; a few phrase it as
    the user would already say it. Both forms have to survive intact, since the
    quoted text is the technician's evidence.
    """
    if error_text.lower().startswith(("it says", "there's a message", "it just says")):
        return error_text
    return f'It says "{error_text}".'


class TemplatePersona:
    """Symptom-derived responses, matched on keywords in the question."""

    def for_fault(self, leak_terms: list[str]) -> "TemplatePersona":
        """Itself. Every sentence is a symptom field or fixed connective text,
        so there is no generated vocabulary for leak terms to filter."""
        return self

    def initial_report(self, card: PersonaCard, symptoms: UserSymptoms) -> str:
        lines = [symptoms.opening]
        if symptoms.error_text:
            lines.append(_quoted_error(symptoms.error_text))
        if card.mood == "rushed":
            lines.append(f"I'm {card.activity} so I need this quickly.")
        return " ".join(lines)

    def reply(
        self,
        card: PersonaCard,
        symptoms: UserSymptoms,
        history: list[ChatTurn],
        question: str,
    ) -> str:
        """Answer only from the symptom fields; deflect everything else.

        `history` is accepted so the signature matches the model-backed persona
        in Task 11, which does condition on it. The template deliberately does
        not: repeating an answer is realistic, and a stateless reply keeps this
        fallback trivially predictable for the grading tests.
        """
        q = question.lower()
        if any(w in q for w in ONSET_WORDS):
            return symptoms.onset
        if any(w in q for w in SCOPE_WORDS):
            return symptoms.scope
        if any(w in q for w in ERROR_WORDS):
            return _quoted_error(symptoms.error_text) if symptoms.error_text else NO_ERROR
        return DEFLECTION
