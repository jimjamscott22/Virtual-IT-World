"""Baseline capture and invariant checking.

This is what gives wrong fixes teeth. A technician who clears a symptom by
disabling an account or stopping a service passes the fault check and fails
here — grading reports it as collateral damage.

The baseline is captured *after* faults are applied, so repairing a fault can
never trip an invariant. Only additional damage does.

The mail pair was deferred from Phase 2a for the right reason — an invariant is
a new way for a fault to accuse itself, and there were no mail faults to test it
against. There are six now, and two of the ways a technician can "resolve"
`mail.mailbox_full` are destructive: setting the quota below what the mailbox is
using stops it sending as surely as the fault did, and deleting the mailbox
clears every symptom by throwing the mail away.
"""

from pydantic import BaseModel, Field

from vitsc.world.models import ServiceState, World


class Baseline(BaseModel):
    enabled_users: set[str] = Field(default_factory=set)
    running_services: set[tuple[str, str]] = Field(default_factory=set)
    group_members: dict[str, set[str]] = Field(default_factory=dict)
    allowed_dns: set[str] = Field(default_factory=set)
    mailboxes: set[str] = Field(default_factory=set)
    # Mailboxes that were *within* quota when the baseline was taken. Recorded
    # as a set rather than as each mailbox's numbers because the question is not
    # "did the quota change" — raising and lowering a quota are both legitimate
    # repairs for `mail.mailbox_full` — but "did a mailbox that was fine stop
    # being able to send". A mailbox already over quota when the baseline was
    # captured is the fault itself and must never be reported as damage.
    mailboxes_within_quota: set[str] = Field(default_factory=set)


def capture_baseline(world: World) -> Baseline:
    return Baseline(
        enabled_users={u.sam for u in world.org.users.values() if u.enabled},
        running_services={
            (m.hostname, name)
            for m in world.machines.values()
            for name, state in m.services.items()
            if state is ServiceState.RUNNING
        },
        group_members={g.name: set(g.members) for g in world.org.groups.values()},
        # Every other field snapshots current world state; this one must too.
        # Reading only `network.dns_servers` would break the capture-after-apply
        # guarantee for `net.static_dns_misconfig`, whose whole effect is a
        # machine pointing somewhere the network config does not list — the
        # fault would report itself as collateral damage the moment it landed.
        allowed_dns=set(world.network.dns_servers)
        | {server for m in world.machines.values() for server in m.dns_servers},
        mailboxes=set(world.mail.mailboxes),
        mailboxes_within_quota={
            sam
            for sam, mailbox in world.mail.mailboxes.items()
            if mailbox.used_mb < mailbox.quota_mb
        },
    )


def _account_violations(world: World, baseline: Baseline) -> list[str]:
    violations: list[str] = []
    for sam in sorted(baseline.enabled_users):
        user = world.org.users.get(sam)
        if user is None:
            violations.append(f"account {sam} was deleted")
        elif not user.enabled:
            violations.append(f"account {sam} was disabled")
    return violations


def _service_violations(world: World, baseline: Baseline) -> list[str]:
    violations: list[str] = []
    for hostname, service in sorted(baseline.running_services):
        machine = world.machines.get(hostname)
        if machine is None:
            continue
        if machine.services.get(service) is not ServiceState.RUNNING:
            violations.append(f"service {service} on {hostname} was stopped")
    return violations


def _group_violations(world: World, baseline: Baseline) -> list[str]:
    violations: list[str] = []
    for group_name, members in sorted(baseline.group_members.items()):
        current = world.org.groups.get(group_name)
        if current is None:
            violations.append(f"group {group_name} was deleted")
            continue
        for sam in sorted(members - set(current.members)):
            violations.append(f"{sam} was removed from {group_name}")
    return violations


def _dns_violations(world: World, baseline: Baseline) -> list[str]:
    return [
        f"{machine.hostname} points at foreign DNS {server}"
        for machine in world.machines.values()
        for server in machine.dns_servers
        if server not in baseline.allowed_dns
    ]


def _mail_violations(world: World, baseline: Baseline) -> list[str]:
    violations: list[str] = []
    for sam in sorted(baseline.mailboxes):
        if sam not in world.mail.mailboxes:
            violations.append(f"mailbox for {sam} was deleted")
    for sam in sorted(baseline.mailboxes_within_quota):
        mailbox = world.mail.mailboxes.get(sam)
        if mailbox is None:
            continue  # already reported as a deletion above
        if mailbox.used_mb >= mailbox.quota_mb:
            # No possessive apostrophe, matching every other message here.
            # These strings are rendered into HTML, where an apostrophe becomes
            # an entity and any test comparing the raw text silently stops
            # matching.
            violations.append(
                f"mailbox quota for {sam} was set below its current usage"
            )
    return violations


# One checker per family, in the order a report reads them. Adding a family
# means adding a function and an entry here, which keeps `check_invariants`
# from growing a branch per invariant — it was already over pylint's branch
# limit with the mail pair in line.
_CHECKERS = (
    _account_violations,
    _service_violations,
    _group_violations,
    _dns_violations,
    _mail_violations,
)


def check_invariants(world: World, baseline: Baseline) -> list[str]:
    return [
        violation
        for checker in _CHECKERS
        for violation in checker(world, baseline)
    ]
