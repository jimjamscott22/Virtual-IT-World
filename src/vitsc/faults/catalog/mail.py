from random import Random

from vitsc.env.base import Action, Query
from vitsc.faults.base import (
    FaultBase,
    PLACEHOLDER,
    PLACEHOLDER_MAIL_SERVER,
    Placement,
    ResolutionPath,
    UserSymptoms,
)
from vitsc.faults.registry import register
from vitsc.world.models import Mailbox, MailRule, ServiceState, World

_FORWARD_RULE_NAME = "AutoForward"
_EXTERNAL_DOMAIN = "external-mail.example.com"

# Somebody who left. Deliberately not in `company.yaml`: the point of
# `mail.stale_delegate` is that the account is gone and only the permission
# remains, so the name has to resolve to nothing in the directory.
DEPARTED_DELEGATE = "r.tolliver"

# A host that does not exist in the estate. `is_present` asks the world whether
# the endpoint resolves rather than comparing against this string, so a
# technician who points it at some *other* wrong host has not fixed it either.
MISSING_AUTODISCOVER_HOST = "MER-CAS-02"

# Who a list falls to when its manager leaves: a department head, not whoever
# happens to be nearest. One canonical path, and the gate is that the list has
# a manager who exists — so any real person clears it.
_FALLBACK_LIST_OWNER = "s.whitfield"


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


class TransportStalled(FaultBase):
    """The mail domain's cascade, and the one fault in the catalog placed on a
    server with no user of its own. Everybody's mail stops at once, so the tells
    are in the *scope* of the complaints rather than in any one of them —
    `mail.mailbox_full` says the same thing from one person's mouth."""

    id = "mail.transport_stalled"
    domain = "mail"
    difficulty = 2
    canonical_title = "Mail transport service stopped on the mail server; queue backing up"
    supported_backends = frozenset({"simulated", "winrm"})
    leak_terms = ["transport", "queue", "service", "spool"]
    escalation_is_correct = False
    kb_articles = [
        "mail-cannot-send-or-receive",
        "general-triage-first-questions",
        "general-meridian-estate",
    ]

    def placements(self, world: World) -> list[Placement]:
        return [Placement(kind="machine", key=world.mail.server)]

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        world.mail.transport_state = ServiceState.STOPPED
        world.mail.queue_depth = rng.randint(180, 900)

    def is_present(self, world: World, at: Placement) -> bool:
        return world.mail.transport_state is not ServiceState.RUNNING

    def symptoms(self, world: World, at: Placement) -> UserSymptoms:
        return UserSymptoms(
            opening="Nothing I send is arriving and I've had nothing in since "
            "about ten either.",
            onset="Some time this morning — my last reply went out fine at nine.",
            scope="The whole office is asking each other about it.",
            error_text=None,
        )

    def diagnostic_path(self, at: Placement) -> list[Query]:
        return [Query(kind="mail.queue", target=PLACEHOLDER)]

    def canonical_resolutions(self) -> list[ResolutionPath]:
        return [
            ResolutionPath(
                label="Restart the transport service and drain the queue",
                actions=[Action(kind="mail.restart_transport", target=PLACEHOLDER)],
            ),
        ]

    def reporters(self, world: World, at: Placement) -> list[str] | None:
        # Everyone with a machine of their own, so the ticket count lands at
        # CASCADE_MAX and the scope of the complaints is the real evidence.
        return sorted(
            m.assigned_to for m in world.machines.values() if m.assigned_to is not None
        )


class StaleDelegate(FaultBase):
    """Somebody who left still has full access to a mailbox. Their account is
    gone, so nothing about the person shows up in the directory — only the
    permission they were granted, still sitting there. The reported symptom is
    not "access" at all: it is mail being read and answered by nobody."""

    id = "mail.stale_delegate"
    domain = "mail"
    difficulty = 3
    canonical_title = "Departed employee's delegate access left on a mailbox"
    supported_backends = frozenset({"simulated", "winrm"})
    leak_terms = ["delegate", "permission", "full access", "departed"]
    escalation_is_correct = False
    kb_articles = ["mail-delegates-and-lists", "general-escalation-and-ownership"]

    def placements(self, world: World) -> list[Placement]:
        return _mailbox_owners(world)

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        mailbox = _mailbox(world, at)
        if DEPARTED_DELEGATE not in mailbox.delegates:
            mailbox.delegates.append(DEPARTED_DELEGATE)

    def is_present(self, world: World, at: Placement) -> bool:
        mailbox = _mailbox(world, at)
        return any(sam not in world.org.users for sam in mailbox.delegates)

    def symptoms(self, world: World, at: Placement) -> UserSymptoms:
        return UserSymptoms(
            opening="Messages in my inbox are being marked as read before I get "
            "to them, and a customer said somebody replied to them already.",
            onset="I noticed it late last week.",
            scope="Just my mail, as far as I can tell.",
            error_text=None,
        )

    def diagnostic_path(self, at: Placement) -> list[Query]:
        return [
            Query(kind="mail.delegates", target=PLACEHOLDER),
            Query(kind="mail.rules", target=PLACEHOLDER),
        ]

    def canonical_resolutions(self) -> list[ResolutionPath]:
        return [
            ResolutionPath(
                label="Remove the departed account's access",
                actions=[
                    Action(
                        kind="mail.remove_delegate",
                        target=PLACEHOLDER,
                        args={"delegate": DEPARTED_DELEGATE},
                    ),
                ],
            ),
        ]


class AutodiscoverBroken(FaultBase):
    """A server-side setting, reported by one person, that will be reported by
    everyone who restarts their client next. Existing sessions keep working,
    which is why the first ticket says "only me" and is wrong about it."""

    id = "mail.autodiscover_broken"
    domain = "mail"
    difficulty = 3
    canonical_title = "Autodiscover endpoint pointing at a host that does not exist"
    supported_backends = frozenset({"simulated", "winrm"})
    leak_terms = ["autodiscover", "endpoint", "client access", "record"]
    escalation_is_correct = False
    kb_articles = ["mail-cannot-send-or-receive", "mail-delegates-and-lists"]

    def placements(self, world: World) -> list[Placement]:
        return [Placement(kind="machine", key=world.mail.server)]

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        world.mail.autodiscover_host = MISSING_AUTODISCOVER_HOST

    def is_present(self, world: World, at: Placement) -> bool:
        host = world.mail.autodiscover_host
        return host is None or host.upper() not in world.machines

    def symptoms(self, world: World, at: Placement) -> UserSymptoms:
        return UserSymptoms(
            opening="My email asked me to set itself up again this morning and "
            "then couldn't find my account.",
            onset="After I restarted the machine.",
            scope="Mine's the only one I know of — everybody else's is still open "
            "from yesterday.",
            error_text="An encrypted connection to your mail server is not "
            "available.",
        )

    def diagnostic_path(self, at: Placement) -> list[Query]:
        return [
            Query(kind="mail.autodiscover", target=PLACEHOLDER),
            Query(kind="mail.queue", target=PLACEHOLDER),
        ]

    def canonical_resolutions(self) -> list[ResolutionPath]:
        return [
            ResolutionPath(
                label="Point the endpoint back at the mail server",
                actions=[
                    Action(
                        kind="mail.set_autodiscover",
                        target=PLACEHOLDER,
                        args={"autodiscover_host": PLACEHOLDER},
                    ),
                ],
            ),
        ]

    def reporters(self, world: World, at: Placement) -> list[str] | None:
        # Placed on the mail server, which has no `assigned_to`, so without this
        # `resolved_reporters` comes back empty and nobody gets the ticket. One
        # reporter, not a cascade: only the person who restarted their client
        # has noticed yet, which is what makes their "only me" wrong.
        return [
            sorted(
                m.assigned_to
                for m in world.machines.values()
                if m.assigned_to is not None
            )[0]
        ]


class OwnerlessDistributionList(FaultBase):
    """The person who managed a distribution list left, so nobody can change who
    is on it — and the list carries on delivering to whoever was on it that day.
    The symptom is organisational rather than technical, which is the point: not
    every ticket is a thing that is broken."""

    id = "mail.ownerless_distribution_list"
    domain = "mail"
    difficulty = 2
    canonical_title = "Distribution list left with no owner after its manager departed"
    supported_backends = frozenset({"simulated", "winrm"})
    leak_terms = ["owner", "managedby", "distribution", "unmanaged"]
    escalation_is_correct = False
    kb_articles = ["mail-delegates-and-lists"]

    def placements(self, world: World) -> list[Placement]:
        return [
            Placement(kind="list", key=name)
            for name in sorted(world.mail.distribution_lists)
        ]

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        world.mail.distribution_lists[at.key].owner_sam = None

    def is_present(self, world: World, at: Placement) -> bool:
        owner = world.mail.distribution_lists[at.key].owner_sam
        return owner is None or owner not in world.org.users

    def symptoms(self, world: World, at: Placement) -> UserSymptoms:
        return UserSymptoms(
            opening="We need somebody taken off one of the group addresses and "
            "nobody can find who's able to do it.",
            onset="It's come up twice now, since the person who used to look "
            "after it left.",
            scope="It affects everyone who gets mail to that address.",
            error_text="You don't have permission to modify this group.",
        )

    def diagnostic_path(self, at: Placement) -> list[Query]:
        return [Query(kind="mail.lists", target=PLACEHOLDER_MAIL_SERVER)]

    def canonical_resolutions(self) -> list[ResolutionPath]:
        return [
            ResolutionPath(
                label="Assign the list to a manager",
                actions=[
                    Action(
                        kind="mail.set_list_owner",
                        target=PLACEHOLDER,
                        args={"owner": _FALLBACK_LIST_OWNER},
                    ),
                ],
            ),
        ]

    def reporters(self, world: World, at: Placement) -> list[str] | None:
        # Whoever is asking is the list's own members' problem, so the person who
        # reports it is a member — deterministically the first one, since
        # `reporters()` has no `rng`.
        members = [
            sam
            for sam in world.mail.distribution_lists[at.key].members
            if world.machine_for(sam) is not None
        ]
        return [sorted(members)[0]] if members else None


register(TransportStalled())
register(StaleDelegate())
register(AutodiscoverBroken())
register(OwnerlessDistributionList())
