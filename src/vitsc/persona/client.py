"""Model-backed persona against an OpenAI-compatible local endpoint (LM Studio).

Leak prevention, per spec §7:
  1. structural — this class is handed a card and `UserSymptoms`, never a
     `World` or a `Fault`, so the cause is not in its input at all;
  2. prompted   — `build_system_prompt` forbids guessing a cause;
  3. filtered   — `scrub()` checks the generated text against the fault's
     `leak_terms`, retries once with a nudge, then deflects.

A model that is down, slow, or absent is not an error state: every failure
path returns `TemplatePersona` output and flips `degraded`, so the drill is
fully playable with nothing running on localhost.
"""

import re
from functools import lru_cache

from vitsc.faults.base import UserSymptoms
from vitsc.persona.models import ChatTurn, PersonaCard
from vitsc.persona.prompts import build_system_prompt
from vitsc.persona.templates import DEFLECTION, TemplatePersona

DEFAULT_BASE_URL = "http://localhost:1234/v1"
RETRY_NUDGE = (
    "That reply used a technical term you would not know. Say the same thing "
    "again in plain words, without naming any cause."
)


@lru_cache(maxsize=64)
def _leak_pattern(terms: tuple[str, ...]) -> re.Pattern[str] | None:
    """Compile leak terms into one word-start-anchored alternation.

    Anchoring matters more than it looks. Plain substring matching would find
    the DHCP term "lease" inside "please" and the identity term "ad " inside
    "bad", "had" and "read" — a polite, plain-English reply would be thrown
    away as a leak. Anchoring only the *start* keeps inflections caught
    ("lease" still matches "leases", "lock" still matches "locking").

    A term written with trailing whitespace (`"ad "`) is read as the author
    asking for a whole word, so it gets a closing boundary too and stops
    matching "address" or "adding".
    """
    parts = [
        re.escape(term.strip()) + (r"\b" if term != term.rstrip() else "")
        for term in terms
        if term.strip()
    ]
    if not parts:
        return None
    return re.compile(r"\b(?:" + "|".join(parts) + ")", re.IGNORECASE)


def scrub(text: str, leak_terms: list[str]) -> str | None:
    """Return the text if clean, or None if it leaks a forbidden term."""
    pattern = _leak_pattern(tuple(leak_terms))
    if pattern is None or not pattern.search(text):
        return text
    return None


def make_client(base_url: str = DEFAULT_BASE_URL):
    """Build a real LM Studio client. Imported lazily so the suite never needs openai."""
    from openai import OpenAI

    return OpenAI(base_url=base_url, api_key="lm-studio")


class LMStudioPersona:
    def __init__(self, client, model: str, leak_terms: list[str], fallback=None) -> None:
        self._client = client
        self._model = model
        self._leak_terms = leak_terms
        self._fallback = fallback or TemplatePersona()
        self.degraded = False

    def initial_report(self, card: PersonaCard, symptoms: UserSymptoms) -> str:
        return self._ask(
            card,
            symptoms,
            [],
            "Write your first message to the helpdesk describing the problem.",
            lambda: self._fallback.initial_report(card, symptoms),
        )

    def reply(
        self,
        card: PersonaCard,
        symptoms: UserSymptoms,
        history: list[ChatTurn],
        question: str,
    ) -> str:
        return self._ask(
            card,
            symptoms,
            history,
            question,
            lambda: self._fallback.reply(card, symptoms, history, question),
        )

    def _ask(self, card, symptoms, history, user_text, fallback) -> str:
        messages = [{"role": "system", "content": build_system_prompt(card, symptoms)}]
        for turn in history:
            messages.append(
                {
                    # The technician is the *user* of the model; the persona is
                    # the assistant. The chat roles are inverted relative to the
                    # ticket's own speaker labels.
                    "role": "user" if turn.speaker == "tech" else "assistant",
                    "content": turn.text,
                }
            )
        messages.append({"role": "user", "content": user_text})

        try:
            first = self._complete(messages)
        except Exception:
            self.degraded = True
            return fallback()

        clean = scrub(first, self._leak_terms)
        if clean is not None:
            return clean

        messages.extend(
            [
                {"role": "assistant", "content": first},
                {"role": "user", "content": RETRY_NUDGE},
            ]
        )
        try:
            second = self._complete(messages)
        except Exception:
            self.degraded = True
            return fallback()
        return scrub(second, self._leak_terms) or DEFLECTION

    def _complete(self, messages) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=0.7,
            max_tokens=120,
        )
        return response.choices[0].message.content.strip()
