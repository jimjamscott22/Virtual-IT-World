"""Specifics for the mail domain's two reference faults.

The conformance harness (`tests/test_catalog.py`) already proves both faults
are placeable, discoverable, jargon-free and — where they declare one —
clearable by every canonical path. What is left here is the part that is
particular to these two: that `mail.mailbox_full` really has two independent
honest answers, and that `mail.external_forwarding_rule` is escalate-correct
for a reason no other fault in the catalog uses.
"""

from random import Random

import pytest

from vitsc.env.base import Action
from vitsc.env.simulated import SimulatedEnvironment
from vitsc.faults.base import bind
from vitsc.faults.registry import get_fault
from vitsc.session.ticket import WORK_STOPPING
from vitsc.world.seed import load_world


def broken(fault_id):
    """A world with the fault applied, plus its placement and an environment."""
    fault = get_fault(fault_id)
    world = load_world()
    at = fault.placements(world)[0]
    fault.apply(world, at, Random(0))
    return fault, world, at, SimulatedEnvironment(world)


# --- mail.mailbox_full ------------------------------------------------------


def test_mailbox_full_has_two_honest_fix_paths():
    """Raise the quota or reduce the usage — both are real answers."""
    fault = get_fault("mail.mailbox_full")
    assert len(fault.canonical_resolutions()) == 2
    labels = {r.label.lower() for r in fault.canonical_resolutions()}
    assert any("quota" in label for label in labels)
    assert any("archive" in label for label in labels)


@pytest.mark.parametrize("index", [0, 1])
def test_either_mailbox_full_path_clears_it_on_its_own(index):
    """Neither path is the 'real' one — the gate is world state, not a button."""
    fault, world, at, env = broken("mail.mailbox_full")
    for action in bind(fault.canonical_resolutions()[index], at, world).actions:
        assert env.execute(action).ok
    assert fault.is_present(world, at) is False


def test_a_quota_raised_below_current_usage_does_not_clear_it():
    """The gate reads the world, so a fix that does not actually help fails."""
    fault, world, at, env = broken("mail.mailbox_full")
    used = world.mail.mailboxes[at.key].used_mb
    env.execute(Action(kind="mail.set_quota", target=at.key,
                       args={"quota_mb": str(used - 1)}))
    assert fault.is_present(world, at) is True


def test_mail_faults_are_priced_into_triage():
    assert "mail.mailbox_full" in WORK_STOPPING


# --- mail.external_forwarding_rule -----------------------------------------


def test_forwarding_rule_is_escalate_correct_and_says_why():
    fault = get_fault("mail.external_forwarding_rule")
    assert fault.escalation_is_correct is True
    assert fault.escalation_reason
    assert "security" in fault.escalation_reason.lower()


def test_forwarding_symptoms_describe_what_a_person_would_notice():
    fault, world, at, _ = broken("mail.external_forwarding_rule")
    symptoms = fault.symptoms(world, at)
    for term in ("rule", "forward", "mailbox", "exfil"):
        assert term not in symptoms.opening.lower()


def test_the_forwarding_target_is_actually_outside_the_organisation():
    """A rule pointing at a colleague is a business need, not an incident."""
    _, world, at, _ = broken("mail.external_forwarding_rule")
    mailbox = world.mail.mailboxes[at.key]
    external = [r for r in mailbox.rules if r.forward_to]
    assert external
    for rule in external:
        assert not rule.forward_to.endswith(f"@{world.org.domain}")
    assert mailbox.forwarding_smtp is not None
    assert not mailbox.forwarding_smtp.endswith(f"@{world.org.domain}")


def test_removing_the_rule_alone_does_not_clear_the_fault():
    """The teaching mechanic: tidying up the visible half leaves the mailbox
    still redirecting, which is why this one was never the technician's to
    close in the first place."""
    fault, world, at, env = broken("mail.external_forwarding_rule")
    name = world.mail.mailboxes[at.key].rules[0].name
    assert env.execute(Action(kind="mail.remove_rule", target=at.key,
                              args={"name": name})).ok
    assert world.mail.mailboxes[at.key].rules == []
    assert fault.is_present(world, at) is True


def test_the_forwarding_fault_declares_no_technician_fix():
    """Same encoding `endpoint.failing_disk` uses: escalate-correct plus an
    empty resolution list means there is no correct thing to press."""
    fault = get_fault("mail.external_forwarding_rule")
    assert fault.canonical_resolutions() == []


def test_tier2_wants_the_rules_finding_in_the_note():
    fault = get_fault("mail.external_forwarding_rule")
    assert [q.kind for q in fault.escalation_evidence] == ["mail.rules"]


# --- both -------------------------------------------------------------------


@pytest.mark.parametrize(
    "fault_id", ["mail.mailbox_full", "mail.external_forwarding_rule"]
)
def test_both_mail_faults_link_the_mail_article(fault_id):
    assert get_fault(fault_id).kb_articles == ["mail-cannot-send-or-receive"]


@pytest.mark.parametrize(
    "fault_id", ["mail.mailbox_full", "mail.external_forwarding_rule"]
)
def test_both_mail_faults_are_in_the_mail_domain(fault_id):
    assert get_fault(fault_id).domain == "mail"
