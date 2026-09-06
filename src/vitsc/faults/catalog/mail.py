from random import Random

from vitsc.env.base import Action, Query
from vitsc.faults.base import FaultBase, PLACEHOLDER, Placement, ResolutionPath, UserSymptoms
from vitsc.faults.registry import register
from vitsc.world.models import Mailbox, MailRule, World

_FORWARD_RULE_NAME = "AutoForward"
_EXTERNAL_DOMAIN = "external-mail.example.com"


def _mailbox_owners(world: World) -> list[Placement]:
    return [Placement(kind="user", key=sam) for sam in world.org.users]


def _mailbox(world: World, at: Placement) -> Mailbox:
    """The placement's mailbox, or a loud failure.

    `placements()` only ever returns users, and `seed.py` derives one mailbox
    per user, so `None` here means the world was built wrong. An `assert`
    would say the same thing but vanish under `python -O`, taking the check
    with it — and `is_present()` is the pass/fail gate, so it must not
    silently read `False` because a mailbox went missing.
    """
    mailbox = world.mailbox_for(at.key)
    if mailbox is None:
        raise KeyError(f"no mailbox for {at.key}")
    return mailbox


def _is_external(world: World, address: str | None) -> bool:
    return bool(address) and not address.lower().endswith(f"@{world.org.domain.lower()}")


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
    kb_articles = ["mail-cannot-send-or-receive"]

    def placements(self, world: World) -> list[Placement]:
        return _mailbox_owners(world)

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        mailbox = _mailbox(world, at)
        mailbox.used_mb = mailbox.quota_mb + rng.uniform(50, 500)

    def is_present(self, world: World, at: Placement) -> bool:
        mailbox = _mailbox(world, at)
        return mailbox.used_mb >= mailbox.quota_mb

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
    kb_articles = ["mail-cannot-send-or-receive"]
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
        mailbox = _mailbox(world, at)
        outside_address = f"{at.key}@{_EXTERNAL_DOMAIN}"
        mailbox.rules.append(
            MailRule(name=_FORWARD_RULE_NAME, forward_to=outside_address, created_by=at.key)
        )
        mailbox.forwarding_smtp = outside_address

    def is_present(self, world: World, at: Placement) -> bool:
        # Both halves, not just the rule. `apply()` sets the mailbox-level
        # forwarding address too, and no action in `env/simulated.py` clears
        # it — so a rules-only gate reads "fixed" the moment `mail.remove_rule`
        # runs, on a mailbox that is still redirecting every message out of
        # the company. The gate is what "was it fixed" means; it has to mean
        # the mail stopped leaving.
        mailbox = _mailbox(world, at)
        return any(
            _is_external(world, rule.forward_to) for rule in mailbox.rules
        ) or _is_external(world, mailbox.forwarding_smtp)

    def symptoms(self, world: World, at: Placement) -> UserSymptoms:
        return UserSymptoms(
            opening="Customers keep replying to messages I never sent them.",
            onset="It's been happening for the past couple of days.",
            scope="Several different customers, not just one person.",
            error_text=None,
        )

    def diagnostic_path(self, at: Placement) -> list[Query]:
        # Both reads, because the fault has two halves and `mail.rules` only
        # shows one of them.
        return [
            Query(kind="mail.rules", target=PLACEHOLDER),
            Query(kind="mail.mailbox", target=PLACEHOLDER),
        ]

    def canonical_resolutions(self) -> list[ResolutionPath]:
        # Empty, and honestly so: with the gate covering `forwarding_smtp`,
        # no sequence of existing actions clears this fault. That is the same
        # escalate-correct-plus-no-technician-fix encoding `endpoint.
        # failing_disk` uses, and `tests/test_catalog.py` already has the
        # branch for it. A technician who removes the visible rule finds the
        # fault still present — which is the lesson this fault exists to teach.
        return []


register(MailboxFull())
register(ExternalForwardingRule())
