from random import Random

from vitsc.env.base import Action, Query
from vitsc.faults.base import FaultBase, PLACEHOLDER, Placement, ResolutionPath, UserSymptoms
from vitsc.faults.registry import register
from vitsc.world.models import MailRule, World

_FORWARD_RULE_NAME = "AutoForward"
_EXTERNAL_DOMAIN = "external-mail.example.com"


def _mailbox_owners(world: World) -> list[Placement]:
    return [Placement(kind="user", key=sam) for sam in world.org.users]


class MailboxFull(FaultBase):
    """The clearest demonstration in the catalog that the gate is world state,
    not a chosen button: raising the quota and reducing usage both clear it."""

    id = "mail.mailbox_full"
    domain = "mail"
    difficulty = 2
    canonical_title = "Mailbox over quota; outbound mail queued and not sending"
    supported_backends = frozenset({"simulated", "winrm"})
    leak_terms = ["quota", "mailbox", "full", "limit", "archive"]
    escalation_is_correct = False

    def placements(self, world: World) -> list[Placement]:
        return _mailbox_owners(world)

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        mailbox = world.mailbox_for(at.key)
        assert mailbox is not None
        mailbox.used_mb = mailbox.quota_mb + rng.uniform(50, 500)

    def is_present(self, world: World, at: Placement) -> bool:
        mailbox = world.mailbox_for(at.key)
        return mailbox is not None and mailbox.used_mb >= mailbox.quota_mb

    def symptoms(self, world: World, at: Placement) -> UserSymptoms:
        return UserSymptoms(
            opening="My emails are all sitting in the outbox and nothing is going out.",
            onset="Since this morning, it was fine yesterday.",
            scope="Just me, nobody else has said anything.",
            error_text="It says my messages can't be delivered right now.",
        )

    def diagnostic_path(self, at: Placement) -> list[Query]:
        return [Query(kind="mail.mailbox", target=PLACEHOLDER)]

    def canonical_resolutions(self) -> list[ResolutionPath]:
        return [
            ResolutionPath(
                label="Raise the mailbox quota",
                actions=[
                    Action(
                        kind="mail.set_quota",
                        target=PLACEHOLDER,
                        args={"quota_mb": "999999"},
                    ),
                ],
            ),
            ResolutionPath(
                label="Archive to reduce usage below quota",
                actions=[Action(kind="mail.archive", target=PLACEHOLDER)],
            ),
        ]


class ExternalForwardingRule(FaultBase):
    """Escalate-correct because *acting* is the mistake: deleting the rule
    destroys evidence of a compromised account, so this is a security
    incident to hand off, not a routine fix."""

    id = "mail.external_forwarding_rule"
    domain = "mail"
    difficulty = 4
    canonical_title = "Inbox rule silently forwarding mail to an external address"
    supported_backends = frozenset({"simulated", "winrm"})
    leak_terms = ["forward", "rule", "compromis", "phish", "hack"]
    escalation_is_correct = True
    escalation_reason = (
        "This looks like a compromised account: deleting the forwarding rule "
        "destroys the evidence of when it was created, and the response needs "
        "a credential reset and a review of what was sent — a security "
        "incident, not a routine fix."
    )
    escalation_evidence = [Query(kind="mail.rules", target=PLACEHOLDER)]

    def placements(self, world: World) -> list[Placement]:
        return _mailbox_owners(world)

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        mailbox = world.mailbox_for(at.key)
        assert mailbox is not None
        outside_address = f"{at.key}@{_EXTERNAL_DOMAIN}"
        mailbox.rules.append(
            MailRule(name=_FORWARD_RULE_NAME, forward_to=outside_address, created_by=at.key)
        )
        mailbox.forwarding_smtp = outside_address

    def is_present(self, world: World, at: Placement) -> bool:
        mailbox = world.mailbox_for(at.key)
        if mailbox is None:
            return False
        domain_suffix = f"@{world.org.domain}"
        return any(
            rule.forward_to is not None and not rule.forward_to.endswith(domain_suffix)
            for rule in mailbox.rules
        )

    def symptoms(self, world: World, at: Placement) -> UserSymptoms:
        return UserSymptoms(
            opening="Customers keep replying to messages I never sent them.",
            onset="It's been happening for the past couple of days.",
            scope="Several different customers, not just one person.",
            error_text=None,
        )

    def diagnostic_path(self, at: Placement) -> list[Query]:
        return [Query(kind="mail.rules", target=PLACEHOLDER)]

    def canonical_resolutions(self) -> list[ResolutionPath]:
        # Present so the conformance harness can verify the fault is
        # *technically* clearable. Grading still marks a fix as wrong:
        # escalation_is_correct.
        return [
            ResolutionPath(
                label="Remove the forwarding rule",
                actions=[
                    Action(
                        kind="mail.remove_rule",
                        target=PLACEHOLDER,
                        args={"name": _FORWARD_RULE_NAME},
                    ),
                ],
            ),
        ]


register(MailboxFull())
register(ExternalForwardingRule())
