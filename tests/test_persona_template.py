from random import Random

from vitsc.faults.registry import get_fault
from vitsc.persona.models import ChatTurn
from vitsc.persona.personas import card_for
from vitsc.persona.templates import TemplatePersona
from vitsc.world.seed import load_world


def _symptoms():
    world = load_world()
    fault = get_fault("ad.account_locked")
    placement = fault.placements(world)[0]
    fault.apply(world, placement, Random(0))
    return world, placement, fault.symptoms(world, placement)


def test_card_is_derived_from_the_ad_user():
    world = load_world()
    card = card_for(world.org.users["m.alvarez"])
    assert card.name == "Maria Alvarez"
    assert card.role == "Accounting Clerk"
    assert 1 <= card.literacy <= 3


def test_card_is_stable_for_the_same_person():
    world = load_world()
    first = card_for(world.org.users["t.nakamura"])
    second = card_for(load_world().org.users["t.nakamura"])
    assert first == second


def test_initial_report_contains_the_opening_complaint():
    world, placement, symptoms = _symptoms()
    card = card_for(world.org.users[placement.key])
    report = TemplatePersona().initial_report(card, symptoms)
    assert symptoms.opening in report
    assert symptoms.error_text in report


def test_reply_answers_from_symptoms_only():
    world, placement, symptoms = _symptoms()
    card = card_for(world.org.users[placement.key])
    reply = TemplatePersona().reply(card, symptoms, [], "when did it last work?")
    assert symptoms.onset in reply


def test_reply_deflects_questions_it_cannot_answer():
    world, placement, symptoms = _symptoms()
    card = card_for(world.org.users[placement.key])
    reply = TemplatePersona().reply(card, symptoms, [], "what is your DNS server set to?")
    assert "not sure" in reply.lower()


def test_history_is_accepted_but_does_not_crash():
    world, placement, symptoms = _symptoms()
    card = card_for(world.org.users[placement.key])
    history = [ChatTurn(speaker="tech", text="hello"), ChatTurn(speaker="user", text="hi")]
    assert TemplatePersona().reply(card, symptoms, history, "any error on screen?")


def test_template_replies_never_leak_the_fault_vocabulary():
    """The template can only echo symptom fields, so every fault's replies
    must stay clean of that fault's own leak terms."""
    from vitsc.faults.registry import all_faults

    persona = TemplatePersona()
    questions = [
        "when did this start?",
        "is anyone else affected?",
        "what does the error say?",
        "what is your ip address?",
    ]
    for fault in all_faults():
        world = load_world()
        placement = fault.placements(world)[0]
        fault.apply(world, placement, Random(0))
        symptoms = fault.symptoms(world, placement)
        user = world.org.users.get(placement.key)
        card = card_for(user) if user else card_for(next(iter(world.org.users.values())))
        spoken = " ".join(
            [persona.initial_report(card, symptoms)]
            + [persona.reply(card, symptoms, [], q) for q in questions]
        ).lower()
        for term in fault.leak_terms:
            assert term not in spoken, f"{fault.id} leaked {term!r}"
