"""The mail domain's two reference faults.

They are deliberately opposites. `mail.mailbox_full` is the catalog's
clearest demonstration that the pass/fail gate is world state and not a
chosen button — two unrelated actions both clear it, and neither is "the"
answer. `mail.external_forwarding_rule` is the third escalate-correct fault
and is escalate-correct for a third distinct reason: `ad.offboarded_
reactivation` needs authorisation and `endpoint.failing_disk` needs
hardware, but here *acting at all* is the mistake.
"""

from random import Random

from vitsc.env.base import Action, Query
from vitsc.faults.base import FaultBase, PLACEHOLDER, Placement, ResolutionPath, UserSymptoms
from vitsc.faults.registry import register
from vitsc.world.models import MailRule, World

# Enough headroom that the quota path clears the fault for any overage
# `MailboxFull.apply` can produce, without being an absurd grant.
RAISED_QUOTA_MB = "76800"


def _staff_with_mailboxes(world: World) -> list[Placement]:
    """Users who make plausible reporters: ordinary staff who still work here."""
    return [
        Placement(kind="user", key=m.assigned_to)
        for m in world.machines.values()
        if m.assigned_to is not None and m.assigned_to in world.mail.mailboxes
    ]


def _is_external(world: World, address: str | None) -> bool:
    return bool(address) and not address.lower().endswith(f"@{world.org.domain.lower()}")


class MailboxFull(FaultBase):
    id = "mail.mailbox_full"
    domain = "mail"
    difficulty = 2
    canonical_title = "Mailbox at its send quota, so outbound mail stopped"
    supported_backends = frozenset({"simulated", "winrm"})
    leak_terms = ["quota", "mailbox", "full", "limit", "archive"]
    escalation_is_correct = False
    kb_articles = ["mail-cannot-send-or-receive"]

    def placements(self, world: World) -> list[Placement]:
        return _staff_with_mailboxes(world)

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        mailbox = world.mail.mailboxes[at.key]
        mailbox.used_mb = mailbox.quota_mb + rng.uniform(1.0, 200.0)

    def is_present(self, world: World, at: Placement) -> bool:
        mailbox = world.mail.mailboxes[at.key]
        return mailbox.used_mb >= mailbox.quota_mb

    def symptoms(self, world: World, at: Placement) -> UserSymptoms:
        return UserSymptoms(
            opening="My emails are all sitting in the outbox and nothing is going out.",
            onset="Since yesterday afternoon. The morning was fine.",
            scope="Just me — the person opposite sent one while I was watching.",
            error_text=(
                "Your message did not reach some or all of the intended recipients."
            ),
        )

    def diagnostic_path(self, at: Placement) -> list[Query]:
        return [Query(kind="mail.mailbox", target=at.key)]

    def canonical_resolutions(self) -> list[ResolutionPath]:
        # Two paths on purpose. Grading asks `is_present()` against the world,
        # so a technician who picks either one — or does something else that
        # gets usage back under the limit — is right.
        return [
            ResolutionPath(
                label="Raise the send quota to give the mailbox headroom",
                actions=[
                    Action(
                        kind="mail.set_quota",
                        target=PLACEHOLDER,
                        args={"quota_mb": RAISED_QUOTA_MB},
                    )
                ],
            ),
            ResolutionPath(
                label="Archive old mail to bring usage back down",
                actions=[Action(kind="mail.archive", target=PLACEHOLDER)],
            ),
        ]


class ExternalForwardingRule(FaultBase):
    """Escalate-correct: mail is being redirected out of the company, which
    is a security incident rather than a misconfiguration. Deleting the rule
    destroys the record of when it appeared and who created it, and the
    response has to include a credential reset and a review of what was
    already sent — none of which is a technician's call.

    Encoded the same way `endpoint.failing_disk` is: `escalation_is_correct`
    plus an empty `canonical_resolutions()`. There genuinely is no correct
    thing to press. A technician who removes the visible rule anyway finds
    the fault still present, because the mailbox-level forwarding the
    attacker also set is still redirecting — which is the lesson.
    """

    id = "mail.external_forwarding_rule"
    domain = "mail"
    difficulty = 4
    canonical_title = "Mailbox redirecting mail to an outside address"
    supported_backends = frozenset({"simulated", "winrm"})
    leak_terms = ["forward", "rule", "compromis", "phish", "hack"]
    escalation_is_correct = True
    kb_articles = ["mail-cannot-send-or-receive"]
    escalation_reason = (
        "Mail is being redirected outside the company, which makes this a "
        "security incident and not a cleanup job — deleting what you can see "
        "destroys the evidence of when it started and who set it, and the "
        "response still needs a credential reset and a review of what left."
    )
    escalation_evidence = [Query(kind="mail.rules", target=PLACEHOLDER)]

    def placements(self, world: World) -> list[Placement]:
        return _staff_with_mailboxes(world)

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        mailbox = world.mail.mailboxes[at.key]
        address = f"svc.backup{rng.randint(100, 999)}@mailrelay-secure.example"
        mailbox.rules.append(
            MailRule(
                # Innocuous-looking on purpose: a name nobody questions is
                # the whole point of where an attacker hides one.
                name="RSS Subscriptions",
                forward_to=address,
                delete_after=True,
                created_by=at.key,
            )
        )
        mailbox.forwarding_smtp = address

    def is_present(self, world: World, at: Placement) -> bool:
        mailbox = world.mail.mailboxes[at.key]
        return any(
            _is_external(world, rule.forward_to) for rule in mailbox.rules
        ) or _is_external(world, mailbox.forwarding_smtp)

    def symptoms(self, world: World, at: Placement) -> UserSymptoms:
        return UserSymptoms(
            opening="Customers keep replying to messages I never sent them.",
            onset="The first one came in on Tuesday and there have been three since.",
            scope="It seems to be my own contacts. Nobody else has mentioned it.",
            error_text=None,
        )

    def diagnostic_path(self, at: Placement) -> list[Query]:
        return [
            Query(kind="mail.rules", target=at.key),
            Query(kind="mail.mailbox", target=at.key),
        ]

    def canonical_resolutions(self) -> list[ResolutionPath]:
        return []


register(MailboxFull())
register(ExternalForwardingRule())
