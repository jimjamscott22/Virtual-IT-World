"""Baseline capture and invariant checking.

This is what gives wrong fixes teeth. A technician who clears a symptom by
disabling an account or stopping a service passes the fault check and fails
here — grading reports it as collateral damage.

The baseline is captured *after* faults are applied, so repairing a fault can
never trip an invariant. Only additional damage does.
"""

from pydantic import BaseModel, Field

from vitsc.world.models import ServiceState, World


class Baseline(BaseModel):
    enabled_users: set[str] = Field(default_factory=set)
    running_services: set[tuple[str, str]] = Field(default_factory=set)
    group_members: dict[str, set[str]] = Field(default_factory=dict)
    allowed_dns: set[str] = Field(default_factory=set)


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
    )


def check_invariants(world: World, baseline: Baseline) -> list[str]:
    violations: list[str] = []

    for sam in sorted(baseline.enabled_users):
        user = world.org.users.get(sam)
        if user is None:
            violations.append(f"account {sam} was deleted")
        elif not user.enabled:
            violations.append(f"account {sam} was disabled")

    for hostname, service in sorted(baseline.running_services):
        machine = world.machines.get(hostname)
        if machine is None:
            continue
        if machine.services.get(service) is not ServiceState.RUNNING:
            violations.append(f"service {service} on {hostname} was stopped")

    for group_name, members in sorted(baseline.group_members.items()):
        current = world.org.groups.get(group_name)
        if current is None:
            violations.append(f"group {group_name} was deleted")
            continue
        for sam in sorted(members - set(current.members)):
            violations.append(f"{sam} was removed from {group_name}")

    for machine in world.machines.values():
        for server in machine.dns_servers:
            if server not in baseline.allowed_dns:
                violations.append(
                    f"{machine.hostname} points at foreign DNS {server}"
                )

    return violations
