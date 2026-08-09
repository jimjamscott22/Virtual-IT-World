from vitsc.faults.base import UserSymptoms
from vitsc.persona.client import LMStudioPersona, scrub
from vitsc.persona.models import ChatTurn, PersonaCard
from vitsc.persona.prompts import build_system_prompt

CARD = PersonaCard(
    name="Maria Alvarez",
    role="Accounting Clerk",
    department="Accounting",
    literacy=1,
    mood="rushed",
    activity="trying to get a report out",
)
SYMPTOMS = UserSymptoms(
    opening="I can't sign in.",
    onset="Worked Friday.",
    scope="Just me.",
    error_text="The referenced account is currently disabled.",
)


class StubClient:
    """Mimics the surface of openai.OpenAI that LMStudioPersona uses."""

    def __init__(self, replies):
        self._replies = list(replies)
        self.calls = []

    @property
    def chat(self):
        return self

    @property
    def completions(self):
        return self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        text = self._replies.pop(0)
        return type(
            "R",
            (),
            {"choices": [type("C", (), {"message": type("M", (), {"content": text})()})()]},
        )()


class DeadClient:
    @property
    def chat(self):
        return self

    @property
    def completions(self):
        return self

    def create(self, **kwargs):
        raise ConnectionError("refused")


def test_system_prompt_carries_symptoms_but_no_cause():
    prompt = build_system_prompt(CARD, SYMPTOMS)
    assert "Maria Alvarez" in prompt
    assert SYMPTOMS.opening in prompt
    assert "locked" not in prompt.lower()


def test_literacy_one_forbids_jargon_in_the_prompt():
    assert "do not use technical terms" in build_system_prompt(CARD, SYMPTOMS).lower()


def test_missing_error_text_is_described_not_left_blank():
    silent = SYMPTOMS.model_copy(update={"error_text": None})
    assert "no message" in build_system_prompt(CARD, silent)


def test_scrub_passes_clean_text():
    assert scrub("I can't get in.", ["locked", "unlock"]) == "I can't get in."


def test_scrub_rejects_leaking_text():
    assert scrub("My account is locked out.", ["locked"]) is None


def test_scrub_is_case_insensitive():
    assert scrub("ACCOUNT LOCKED", ["locked"]) is None


def test_scrub_catches_inflections_of_a_leak_term():
    assert scrub("It keeps locking me out.", ["lock"]) is None


def test_scrub_does_not_fire_on_words_that_merely_contain_a_term():
    """Plain substring matching would read "please" as the DHCP term "lease"."""
    assert scrub("Please could you take a look?", ["lease", "dhcp"]) is not None


def test_a_term_written_as_a_whole_word_stays_a_whole_word():
    """`"ad "` — trailing space — must not fire on "bad" or "address"."""
    terms = ["ad "]
    assert scrub("It was working fine, then it went bad.", terms) is not None
    assert scrub("I typed the address in and nothing happened.", terms) is not None
    assert scrub("Someone in AD changed something.", terms) is None


def test_client_retries_once_then_deflects():
    stub = StubClient(["my account is locked", "still locked I think"])
    persona = LMStudioPersona(client=stub, model="local", leak_terms=["locked"])
    reply = persona.reply(CARD, SYMPTOMS, [], "what happens when you try?")
    assert "locked" not in reply.lower()
    assert len(stub.calls) == 2


def test_client_accepts_a_clean_retry():
    stub = StubClient(["it says locked", "it just won't let me in"])
    persona = LMStudioPersona(client=stub, model="local", leak_terms=["locked"])
    assert persona.reply(CARD, SYMPTOMS, [], "what happens?") == "it just won't let me in"


def test_a_clean_first_reply_costs_only_one_call():
    stub = StubClient(["it just won't let me in"])
    persona = LMStudioPersona(client=stub, model="local", leak_terms=["locked"])
    assert persona.reply(CARD, SYMPTOMS, [], "what happens?") == "it just won't let me in"
    assert len(stub.calls) == 1
    assert persona.degraded is False


def test_history_is_sent_with_inverted_chat_roles():
    """The technician is the model's 'user'; the persona is the 'assistant'."""
    stub = StubClient(["yes, same thing"])
    persona = LMStudioPersona(client=stub, model="local", leak_terms=[])
    history = [
        ChatTurn(speaker="tech", text="have you tried again?"),
        ChatTurn(speaker="user", text="I did, twice."),
    ]
    persona.reply(CARD, SYMPTOMS, history, "still failing?")
    messages = stub.calls[0]["messages"]
    assert messages[0]["role"] == "system"
    assert messages[1] == {"role": "user", "content": "have you tried again?"}
    assert messages[2] == {"role": "assistant", "content": "I did, twice."}
    assert messages[-1] == {"role": "user", "content": "still failing?"}


def test_unreachable_model_falls_back_to_template():
    persona = LMStudioPersona(client=DeadClient(), model="local", leak_terms=["locked"])
    report = persona.initial_report(CARD, SYMPTOMS)
    assert SYMPTOMS.opening in report
    assert persona.degraded is True


def test_model_dying_on_the_retry_also_falls_back():
    class DiesOnRetry(StubClient):
        def create(self, **kwargs):
            if self.calls:
                raise ConnectionError("refused")
            return super().create(**kwargs)

    persona = LMStudioPersona(
        client=DiesOnRetry(["my account is locked"]), model="local", leak_terms=["locked"]
    )
    reply = persona.reply(CARD, SYMPTOMS, [], "when did it start?")
    assert reply == SYMPTOMS.onset
    assert persona.degraded is True
