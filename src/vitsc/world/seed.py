from datetime import timedelta
from importlib.resources import files
from pathlib import Path

import yaml

from vitsc.world.models import (
    ADGroup,
    ADUser,
    Machine,
    Mailbox,
    MailSystem,
    Network,
    Organization,
    Printer,
    ServiceState,
    Share,
    World,
)

WORKSTATION_SERVICES = {
    "Spooler": ServiceState.RUNNING,
    "Dhcp": ServiceState.RUNNING,
    "Dnscache": ServiceState.RUNNING,
    "WSearch": ServiceState.RUNNING,
}


def load_world(path: Path | None = None) -> World:
    """Build a healthy `World` from `company.yaml`.

    The world returned is always at rest: no account locked, no service
    stopped, no disk full. Faults are what make it interesting.
    """
    raw = yaml.safe_load(
        path.read_text()
        if path
        else files("vitsc.data").joinpath("company.yaml").read_text()
    )
    clock = raw["clock"]
    net = raw["network"]

    users: dict[str, ADUser] = {}
    for u in raw["users"]:
        users[u["sam"]] = ADUser(
            sam=u["sam"],
            display_name=u["display_name"],
            upn=f"{u['sam']}@{raw['domain']}",
            department=u["department"],
            title=u["title"],
            ou=u["ou"],
            pwd_last_set=clock - timedelta(days=30),
            pwd_expires=clock + timedelta(days=60),
            home_drive="S:",
        )

    groups = {
        name: ADGroup(name=name, members=list(members))
        for name, members in raw["groups"].items()
    }

    machines: dict[str, Machine] = {}
    for s in raw["servers"]:
        machines[s["hostname"]] = Machine(
            hostname=s["hostname"],
            ip=s["ip"],
            dhcp_reserved_ip=s["ip"],
            dhcp_enabled=False,
            gateway=net["gateway"],
            dns_servers=list(net["dns_servers"]),
            services=dict(WORKSTATION_SERVICES),
            disk_free_gb=400.0,
            disk_total_gb=1024.0,
        )
    for w in raw["workstations"]:
        machines[w["hostname"]] = Machine(
            hostname=w["hostname"],
            assigned_to=w["assigned_to"],
            ip=w["ip"],
            dhcp_reserved_ip=w["ip"],
            gateway=net["gateway"],
            dns_servers=list(net["dns_servers"]),
            services=dict(WORKSTATION_SERVICES),
            installed_printers=list(w["printers"]),
        )

    printers = {p["name"]: Printer(**p) for p in raw["printers"]}
    shares = {s["unc"]: Share(**s) for s in raw["shares"]}

    for w in raw["workstations"]:
        machine = machines[w["hostname"]]
        for name in machine.installed_printers:
            machine.printer_drivers[name] = printers[name].correct_driver
        dept_group = next(
            (g for g in groups.values() if w["assigned_to"] in g.members), None
        )
        if dept_group:
            share = next(
                (s for s in shares.values() if s.required_group == dept_group.name),
                None,
            )
            if share:
                machine.mapped_drives[share.drive_letter] = share.unc

    mail_cfg = raw["mail"]
    mail = MailSystem(
        server=mail_cfg["server"],
        mailboxes={
            sam: Mailbox(
                owner_sam=sam,
                primary_smtp=user.upn,
                server=mail_cfg["server"],
                quota_mb=float(mail_cfg["quota_mb"]),
            )
            for sam, user in users.items()
        },
    )

    return World(
        org=Organization(domain=raw["domain"], users=users, groups=groups),
        machines=machines,
        printers=printers,
        shares=shares,
        network=Network(**net),
        mail=mail,
        clock=clock,
    )
