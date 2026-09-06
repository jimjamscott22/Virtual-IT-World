from random import Random

from vitsc.faults.registry import get_fault
from vitsc.world.seed import load_world


def test_mailbox_full_has_two_honest_fix_paths():
    """Raise the quota or reduce the usage — both are real answers."""
    fault = get_fault("mail.mailbox_full")
    assert len(fault.canonical_resolutions()) == 2
    labels = {r.label for r in fault.canonical_resolutions()}
    assert any("quota" in l.lower() for l in labels)
    assert any("archive" in l.lower() for l in labels)


def test_forwarding_rule_is_escalate_correct_and_says_why():
    fault = get_fault("mail.external_forwarding_rule")
    assert fault.escalation_is_correct is True
    assert fault.escalation_reason
    assert "security" in fault.escalation_reason.lower()


def test_forwarding_symptoms_describe_what_a_person_would_notice():
    world = load_world()
    fault = get_fault("mail.external_forwarding_rule")
    at = fault.placements(world)[0]
    fault.apply(world, at, Random(0))
    symptoms = fault.symptoms(world, at)
    for term in ("rule", "forward", "mailbox", "exfil"):
        assert term not in symptoms.opening.lower()


def test_mail_faults_are_priced_into_triage():
    from vitsc.session.ticket import WORK_STOPPING

    assert "mail.mailbox_full" in WORK_STOPPING
