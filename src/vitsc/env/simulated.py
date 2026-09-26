"""The v1 backend: an in-memory world model.

Handlers read and write `self.world` and nothing else. No handler knows that
faults exist, which is what permits multiple valid fix paths and honest
distractors (spec §3).
"""

import uuid
from datetime import timedelta
from ipaddress import ip_address, ip_network

from vitsc.env.base import Action, ActionResult, Observation, Query
from vitsc.world.models import (
    CLOCK_SKEW_TOLERANCE_MINUTES,
    Machine,
    ProfileState,
    ServiceState,
    World,
)

NOT_FOUND = "The term is not recognised, or the object cannot be found."
APIPA_PREFIX = "169.254"
APIPA_MASK = "255.255.0.0"
UNREACHABLE = "Destination host unreachable."
# What `mail.archive` reduces a mailbox to — a fixed fraction of quota, never
# a remembered pre-fault value: `SimulatedEnvironment` is constructed *after*
# `apply()`, so nothing cached at `__init__` reflects pre-fault state.
ARCHIVE_TARGET_FRACTION = 0.1


def _same_subnet(left: str, right: str, mask: str) -> bool:
    """Whether two addresses look local to each other under one mask."""
    try:
        network = ip_network(f"{left}/{mask}", strict=False)
        return ip_address(right) in network
    except ValueError:
        return False


class SimulatedEnvironment:
    def __init__(self, world: World) -> None:
        self.world = world
        self._snapshots: dict[str, World] = {}

    # --- Environment protocol -------------------------------------------
    def read(self, query: Query) -> Observation:
        handler = getattr(self, f"_read_{query.kind.replace('.', '_')}", None)
        if handler is None:
            return Observation(ok=False, rendered=NOT_FOUND)
        return handler(query)  # pylint: disable=not-callable

    def execute(self, action: Action) -> ActionResult:
        handler = getattr(self, f"_do_{action.kind.replace('.', '_')}", None)
        if handler is None:
            return ActionResult(ok=False, rendered=NOT_FOUND)
        return handler(action)  # pylint: disable=not-callable

    def snapshot(self) -> str:
        snapshot_id = uuid.uuid4().hex
        self._snapshots[snapshot_id] = self.world.model_copy(deep=True)
        return snapshot_id

    def restore(self, snapshot_id: str) -> None:
        self.world = self._snapshots[snapshot_id].model_copy(deep=True)

    # --- helpers ---------------------------------------------------------
    def _resolve(self, name: str, from_host: str) -> str | None:
        """DNS resolution, honouring the querying machine's own resolvers.

        Three things have to hold before a name becomes an address: the machine
        has to be pointed at a resolver the domain actually runs, that resolver
        has to be *reachable* from where the machine thinks it is, and the DNS
        client service has to be running to ask it. Each is a separate fault in
        the catalog, and each has to be able to break resolution on its own.
        """
        if name and name[0].isdigit():
            return name
        source = self.world.machines.get(from_host)
        if source is None:
            return None
        if source.services.get("Dnscache") is not ServiceState.RUNNING:
            return None
        usable = set(source.dns_servers) & set(self.world.network.dns_servers)
        if not usable:
            return None
        if not any(self._reachable(source, server) for server in sorted(usable)):
            return None
        target = self.world.machines.get(name.upper())
        return target.ip if target else None

    def _effective_mask(self, machine: Machine) -> str:
        """What the adapter is actually using — APIPA brings its own mask."""
        return machine.subnet_mask if machine.ip is not None else APIPA_MASK

    def _effective_gateway(self, machine: Machine) -> str | None:
        """A machine with no lease has no default route, which is what
        `ipconfig` already renders as a blank gateway."""
        return machine.gateway if machine.ip is not None else None

    def _reachable(self, source: Machine, target_ip: str) -> bool:
        """Can this machine get a packet to that address at all?

        On-subnet traffic needs no router. Everything else needs a default
        gateway that is both inside the machine's own subnet — as the machine
        computes it, wrong mask included — and the address the site's router
        actually answers on. That is what makes a wrong mask and a wrong
        gateway two different faults with two different symptom shapes rather
        than one field nobody reads.
        """
        source_ip = self._effective_ip(source.hostname)
        mask = self._effective_mask(source)
        if _same_subnet(source_ip, target_ip, mask):
            return True
        gateway = self._effective_gateway(source)
        if not gateway:
            return False
        return _same_subnet(source_ip, gateway, mask) and gateway == self.world.network.gateway

    def _effective_ip(self, hostname: str) -> str:
        """What `ipconfig` would print — an APIPA address when the lease failed."""
        machine = self.world.machines[hostname]
        if machine.ip is not None:
            return machine.ip
        octet = sum(ord(c) for c in hostname) % 254 + 1
        return f"{APIPA_PREFIX}.{octet}.{octet}"

    # --- reads: active directory -----------------------------------------
    def _read_ad_user(self, q: Query) -> Observation:
        user = self.world.org.users.get(q.target)
        if user is None:
            return Observation(ok=False, rendered=f"Get-ADUser: {NOT_FOUND}")
        data = {
            "SamAccountName": user.sam,
            "Name": user.display_name,
            "UserPrincipalName": user.upn,
            "Enabled": user.enabled,
            "LockedOut": user.locked_out,
            "BadPwdCount": user.bad_pwd_count,
            "PasswordLastSet": user.pwd_last_set.isoformat(),
            "PasswordExpired": self.world.clock > user.pwd_expires,
            "MemberOf": self.world.groups_of(user.sam),
        }
        rendered = "\n".join(f"{k:<18}: {v}" for k, v in data.items())
        return Observation(ok=True, data=data, rendered=rendered)

    def _read_ad_group(self, q: Query) -> Observation:
        group = self.world.org.groups.get(q.target)
        if group is None:
            return Observation(ok=False, rendered=f"Get-ADGroup: {NOT_FOUND}")
        members = sorted(group.members)
        nested = sorted(group.member_groups)
        data = {"Name": group.name, "Members": members, "MemberGroups": nested}
        lines = [f"{group.name} ({len(members)} direct members)", *members]
        if nested:
            lines += ["", "Nested groups:", *nested]
        rendered = "\n".join(lines)
        return Observation(ok=True, data=data, rendered=rendered)

    # --- reads: endpoint ---------------------------------------------------
    def _read_machine_state(self, q: Query) -> Observation:
        machine = self.world.machines.get(q.target.upper())
        if machine is None:
            return Observation(ok=False, rendered=f"{q.target}: {NOT_FOUND}")
        data = {
            "Hostname": machine.hostname,
            "AssignedTo": machine.assigned_to,
            "IPv4Address": self._effective_ip(machine.hostname),
            "DiskFreeGB": round(machine.disk_free_gb, 1),
            "DiskTotalGB": round(machine.disk_total_gb, 1),
            "SmartStatus": machine.smart_status.value,
            "ProfileState": machine.profile_state.value,
            "SystemTime": machine.clock_reading(self.world.clock).isoformat(),
            "LastDomainSync": (
                machine.last_domain_sync.isoformat()
                if machine.last_domain_sync is not None
                else None
            ),
            "MappedDrives": dict(machine.mapped_drives),
            "InstalledPrinters": list(machine.installed_printers),
        }
        rendered = "\n".join(f"{k:<18}: {v}" for k, v in data.items())
        return Observation(ok=True, data=data, rendered=rendered)

    def _read_machine_services(self, q: Query) -> Observation:
        machine = self.world.machines.get(q.target.upper())
        if machine is None:
            return Observation(ok=False, rendered=f"{q.target}: {NOT_FOUND}")
        wanted = q.args.get("service")
        services = {
            name: state
            for name, state in sorted(machine.services.items())
            if wanted is None or name.lower() == wanted.lower()
        }
        if wanted and not services:
            return Observation(
                ok=False,
                rendered=f"Get-Service: Cannot find any service with service name '{wanted}'.",
            )
        lines = [f"{'Status':<10}{'Name':<12}", f"{'------':<10}{'----':<12}"]
        lines += [f"{state.value:<10}{name:<12}" for name, state in services.items()]
        return Observation(
            ok=True,
            data={"services": {n: s.value for n, s in services.items()}},
            rendered="\n".join(lines),
        )

    def _read_machine_eventlog(self, q: Query) -> Observation:
        machine = self.world.machines.get(q.target.upper())
        if machine is None:
            return Observation(ok=False, rendered=f"{q.target}: {NOT_FOUND}")
        log_name = q.args.get("log")
        try:
            count = int(q.args.get("count", "10"))
        except ValueError:
            count = 10
        entries = [
            e for e in machine.event_log if log_name is None or e.log == log_name
        ][-count:]
        data = {"entries": [e.model_dump(mode="json") for e in entries]}
        if not entries:
            return Observation(
                ok=True, data=data, rendered="No matching events were found."
            )
        rendered = "\n".join(
            f"{e.at:%Y-%m-%d %H:%M}  {e.level:<11} {e.source:<16} {e.event_id:<6} {e.message}"
            for e in entries
        )
        return Observation(ok=True, data=data, rendered=rendered)

    # --- reads: network ----------------------------------------------------
    def _read_net_ping(self, q: Query) -> Observation:
        from_host = q.args.get("from", "")
        ip = self._resolve(q.target, from_host)
        if ip is None:
            return Observation(
                ok=False,
                data={"resolved": False},
                rendered=f"Ping request could not find host {q.target}. "
                "Please check the name and try again.",
            )
        source = self.world.machines.get(from_host.upper())
        if source is not None and not self._reachable(source, ip):
            # Resolution succeeded and delivery still failed — the difference
            # between a name problem and a routing one, which is exactly the
            # distinction a technician is here to learn to make.
            return Observation(
                ok=False,
                data={"resolved": True, "ip": ip, "reachable": False},
                rendered=f"Pinging {q.target} [{ip}] with 32 bytes of data:\n"
                + "\n".join(f"Reply from {self._effective_ip(source.hostname)}: "
                             f"{UNREACHABLE}" for _ in range(4))
                + f"\n\nPing statistics for {ip}:\n"
                "    Packets: Sent = 4, Received = 0, Lost = 4 (100% loss),",
            )
        replies = "\n".join(
            f"Reply from {ip}: bytes=32 time<1ms TTL=128" for _ in range(4)
        )
        return Observation(
            ok=True,
            data={"resolved": True, "ip": ip},
            rendered=f"Pinging {q.target} [{ip}] with 32 bytes of data:\n{replies}\n\n"
            f"Ping statistics for {ip}:\n"
            "    Packets: Sent = 4, Received = 4, Lost = 0 (0% loss),",
        )

    def _read_net_nslookup(self, q: Query) -> Observation:
        from_host = q.args.get("from", "")
        source = self.world.machines.get(from_host)
        server = source.dns_servers[0] if source and source.dns_servers else "unknown"
        ip = self._resolve(q.target, from_host)
        if ip is None:
            return Observation(
                ok=False,
                data={"resolved": False, "server": server},
                rendered=f"Server:  {server}\nAddress:  {server}#53\n\n"
                f"*** Request to {server} timed-out",
            )
        return Observation(
            ok=True,
            data={"resolved": True, "ip": ip, "server": server},
            rendered=f"Server:  {server}\nAddress:  {server}#53\n\n"
            f"Name:    {q.target.lower()}.{self.world.org.domain}\nAddress:  {ip}",
        )

    def _read_net_ipconfig(self, q: Query) -> Observation:
        hostname = (q.target or q.args.get("from", "")).upper()
        machine = self.world.machines.get(hostname)
        if machine is None:
            return Observation(ok=False, rendered=f"{hostname}: {NOT_FOUND}")
        leased = machine.ip is not None
        ip = self._effective_ip(machine.hostname)
        data = {
            "IPv4Address": ip,
            "SubnetMask": self._effective_mask(machine),
            "DefaultGateway": self._effective_gateway(machine) or "",
            "DNSServers": list(machine.dns_servers),
            "DhcpEnabled": machine.dhcp_enabled,
            "Autoconfigured": not leased,
        }
        # Hoisted only to keep the line readable; the rendered dotted-leader
        # spacing is real `ipconfig` output and must stay byte-for-byte.
        ipv4_label = (
            "Autoconfiguration IPv4 Address"
            if not leased
            else "IPv4 Address. . . . . . . . . "
        )
        lines = [
            "Windows IP Configuration",
            "",
            "Ethernet adapter Ethernet:",
            "",
            f"   Connection-specific DNS Suffix  . : {self.world.org.domain}",
            f"   DHCP Enabled. . . . . . . . . . . : {'Yes' if machine.dhcp_enabled else 'No'}",
            f"   {ipv4_label}. : {ip}{' (Preferred)' if leased else ''}",
            f"   Subnet Mask . . . . . . . . . . . : {data['SubnetMask']}",
            f"   Default Gateway . . . . . . . . . : {data['DefaultGateway']}",
        ]
        lines += [
            f"   DNS Servers . . . . . . . . . . . : {s}" for s in machine.dns_servers
        ] or ["   DNS Servers . . . . . . . . . . . :"]
        return Observation(ok=True, data=data, rendered="\n".join(lines))

    # --- reads: printing and shares ----------------------------------------
    def _read_printer_state(self, q: Query) -> Observation:
        printer = self.world.printers.get(q.target)
        if printer is None:
            return Observation(ok=False, rendered=f"Get-Printer: {NOT_FOUND}")
        machine = self.world.machines.get(q.args.get("from", "").upper())
        installed = (
            machine.printer_drivers.get(printer.name) if machine is not None else None
        )
        data = {
            "Name": printer.name,
            "Host": printer.host,
            "Model": printer.model,
            "Online": printer.online,
            "CorrectDriver": printer.correct_driver,
            "InstalledDriver": installed,
            "SpoolerState": (
                machine.services.get("Spooler").value
                if machine is not None and "Spooler" in machine.services
                else None
            ),
        }
        rendered = "\n".join(
            f"{k:<18}: {v}" for k, v in data.items() if v is not None
        )
        return Observation(ok=True, data=data, rendered=rendered)

    def _read_share_access(self, q: Query) -> Observation:
        machine = self.world.machines.get(q.args.get("from", "").upper())
        if machine is None or q.target not in machine.mapped_drives:
            return Observation(ok=False, rendered=f"{q.target} is not mapped.")
        share = self.world.shares.get(machine.mapped_drives[q.target])
        if share is None:
            return Observation(
                ok=False,
                data={"reason": "stale"},
                rendered=f"{q.target} is not accessible. "
                "The network path was not found.",
            )
        if self._resolve(share.host, machine.hostname) is None:
            return Observation(
                ok=False,
                data={"reason": "dns"},
                rendered=f"{share.unc} is not accessible. "
                "The network path was not found.",
            )
        if abs(machine.clock_offset_minutes) > CLOCK_SKEW_TOLERANCE_MINUTES:
            return Observation(
                ok=False,
                data={"reason": "clock"},
                rendered=f"{share.unc} is not accessible. There is a time and/or "
                "date difference between the client and server.",
            )
        # Effective membership, so a group nested inside the required one
        # grants access exactly as the file server would.
        if not self.world.is_member(share.required_group, machine.assigned_to):
            return Observation(
                ok=False,
                data={"reason": "permissions"},
                rendered=f"{share.unc} is not accessible. Access is denied.",
            )
        return Observation(
            ok=True, data={"unc": share.unc}, rendered=f"{q.target} -> {share.unc}"
        )

    # --- reads: mail ---------------------------------------------------------
    def _read_mail_mailbox(self, q: Query) -> Observation:
        mailbox = self.world.mailbox_for(q.target)
        if mailbox is None:
            return Observation(ok=False, rendered=f"Get-Mailbox: {NOT_FOUND}")
        data = {
            "PrimarySmtpAddress": mailbox.primary_smtp,
            "TotalItemSize": f"{mailbox.used_mb:.1f} MB",
            "ProhibitSendQuota": f"{mailbox.quota_mb:.1f} MB",
            "ForwardingSmtpAddress": mailbox.forwarding_smtp,
            "LitigationHoldEnabled": mailbox.litigation_hold,
        }
        rendered = "\n".join(f"{k:<21}: {v}" for k, v in data.items())
        return Observation(ok=True, data=data, rendered=rendered)

    def _read_mail_rules(self, q: Query) -> Observation:
        mailbox = self.world.mailbox_for(q.target)
        if mailbox is None:
            return Observation(ok=False, rendered=f"Get-InboxRule: {NOT_FOUND}")
        data = {"rules": [r.model_dump() for r in mailbox.rules]}
        if not mailbox.rules:
            return Observation(ok=True, data=data, rendered="No inbox rules configured.")
        # Widths come from the content, the way `Format-Table` sizes a column,
        # rather than from a fixed literal: a forwarding address longer than
        # the column ran straight into the next one with no separating space.
        name_w = max(len("Name"), *(len(r.name) for r in mailbox.rules)) + 2
        fwd_w = max(len("ForwardTo"), *(len(r.forward_to or "") for r in mailbox.rules)) + 2
        lines = [f"{'Name':<{name_w}}{'ForwardTo':<{fwd_w}}DeleteMessage"]
        lines += [
            f"{r.name:<{name_w}}{r.forward_to or '':<{fwd_w}}{r.delete_after}"
            for r in mailbox.rules
        ]
        return Observation(ok=True, data=data, rendered="\n".join(lines))

    def _read_mail_queue(self, q: Query) -> Observation:
        if q.target.upper() != self.world.mail.server:
            return Observation(ok=False, rendered=f"Get-Queue: {NOT_FOUND}")
        data = {
            "Server": self.world.mail.server,
            "TransportState": self.world.mail.transport_state.value,
            "QueueLength": self.world.mail.queue_depth,
        }
        rendered = "\n".join(f"{k:<15}: {v}" for k, v in data.items())
        return Observation(ok=True, data=data, rendered=rendered)


    def _read_machine_processes(self, q: Query) -> Observation:
        machine = self.world.machines.get(q.target.upper())
        if machine is None:
            return Observation(ok=False, rendered=f"{q.target}: {NOT_FOUND}")
        processes = sorted(machine.processes, key=lambda pr: -pr.cpu_percent)
        data = {"processes": [pr.model_dump() for pr in processes]}
        if not processes:
            return Observation(ok=True, data=data, rendered="No processes are running.")
        # Widths from the content, per the Format-Table rule a fixed-width
        # column broke once already (see _read_mail_rules).
        name_w = max(len("Name"), *(len(pr.name) for pr in processes)) + 2
        lines = [f"{'Name':<{name_w}}{'Id':<8}{'CPU%':<8}{'WorkingSet(MB)'}"]
        lines += [
            f"{pr.name:<{name_w}}{pr.pid:<8}{pr.cpu_percent:<8.1f}{pr.memory_mb:.0f}"
            for pr in processes
        ]
        return Observation(ok=True, data=data, rendered="\n".join(lines))

    def _read_net_proxy(self, q: Query) -> Observation:
        machine = self.world.machines.get((q.target or q.args.get("from", "")).upper())
        if machine is None:
            return Observation(ok=False, rendered=f"{q.target}: {NOT_FOUND}")
        data = {"ProxyServer": machine.proxy_server}
        if machine.proxy_server is None:
            rendered = "Current WinHTTP proxy settings:\n\n    Direct access (no proxy server)."
        else:
            rendered = (
                "Current WinHTTP proxy settings:\n\n"
                f"    Proxy Server(s) :  {machine.proxy_server}\n"
                "    Bypass List     :  (none)"
            )
        return Observation(ok=True, data=data, rendered=rendered)

    def _read_printer_jobs(self, q: Query) -> Observation:
        printer = self.world.printers.get(q.target)
        if printer is None:
            return Observation(ok=False, rendered=f"Get-PrintJob: {NOT_FOUND}")
        data = {
            "Printer": printer.name,
            "Online": printer.online,
            "jobs": [j.model_dump(mode="json") for j in printer.jobs],
        }
        header = f"Printer {printer.name} ({'Online' if printer.online else 'Offline'})"
        if not printer.jobs:
            return Observation(
                ok=True, data=data, rendered=f"{header}\nThe print queue is empty."
            )
        owner_w = max(len("Owner"), *(len(j.owner_sam) for j in printer.jobs)) + 2
        doc_w = max(len("Document"), *(len(j.document) for j in printer.jobs)) + 2
        lines = [header, f"{'Id':<6}{'Owner':<{owner_w}}{'Document':<{doc_w}}{'Pages':<8}Status"]
        lines += [
            f"{j.job_id:<6}{j.owner_sam:<{owner_w}}{j.document:<{doc_w}}"
            f"{j.pages:<8}{j.status.value}"
            for j in printer.jobs
        ]
        return Observation(ok=True, data=data, rendered="\n".join(lines))

    def _read_mail_delegates(self, q: Query) -> Observation:
        mailbox = self.world.mailbox_for(q.target)
        if mailbox is None:
            return Observation(ok=False, rendered=f"Get-MailboxPermission: {NOT_FOUND}")
        data = {"delegates": list(mailbox.delegates)}
        if not mailbox.delegates:
            return Observation(
                ok=True, data=data, rendered=f"{q.target}: no delegates are assigned."
            )
        user_w = max(len("User"), *(len(d) for d in mailbox.delegates)) + 2
        lines = [f"{'User':<{user_w}}{'AccessRights':<16}AccountExists"]
        lines += [
            f"{sam:<{user_w}}{'FullAccess':<16}{sam in self.world.org.users}"
            for sam in mailbox.delegates
        ]
        return Observation(ok=True, data=data, rendered="\n".join(lines))

    def _read_mail_lists(self, q: Query) -> Observation:
        if q.target.upper() != self.world.mail.server:
            return Observation(ok=False, rendered=f"Get-DistributionGroup: {NOT_FOUND}")
        lists = [self.world.mail.distribution_lists[n]
                 for n in sorted(self.world.mail.distribution_lists)]
        data = {"lists": [dl.model_dump() for dl in lists]}
        if not lists:
            return Observation(ok=True, data=data, rendered="No distribution groups exist.")
        name_w = max(len("Name"), *(len(dl.name) for dl in lists)) + 2
        owner_w = max(len("ManagedBy"), *(len(dl.owner_sam or "<none>") for dl in lists)) + 2
        lines = [f"{'Name':<{name_w}}{'ManagedBy':<{owner_w}}{'Members':<10}OwnerExists"]
        lines += [
            f"{dl.name:<{name_w}}{(dl.owner_sam or '<none>'):<{owner_w}}"
            f"{len(dl.members):<10}{dl.owner_sam in self.world.org.users}"
            for dl in lists
        ]
        return Observation(ok=True, data=data, rendered="\n".join(lines))

    def _read_mail_autodiscover(self, q: Query) -> Observation:
        if q.target.upper() != self.world.mail.server:
            return Observation(ok=False, rendered=f"Get-ClientAccessService: {NOT_FOUND}")
        host = self.world.mail.autodiscover_host
        resolves = host is not None and host.upper() in self.world.machines
        data = {
            "AutodiscoverHost": host,
            "Resolves": resolves,
            "MailServer": self.world.mail.server,
        }
        lines = [
            f"{'AutodiscoverHost':<20}: {host}",
            f"{'Resolves':<20}: {resolves}",
            f"{'MailServer':<20}: {self.world.mail.server}",
        ]
        if not resolves:
            lines.append("")
            lines.append(
                "Outlook cannot determine its settings: the autodiscover endpoint "
                "does not answer."
            )
        return Observation(ok=True, data=data, rendered="\n".join(lines))

    # --- actions: active directory -----------------------------------------
    def _do_ad_unlock(self, a: Action) -> ActionResult:
        user = self.world.org.users.get(a.target)
        if user is None:
            return ActionResult(ok=False, rendered=f"Unlock-ADAccount: {NOT_FOUND}")
        user.locked_out = False
        user.bad_pwd_count = 0
        return ActionResult(ok=True, rendered=f"Account {user.sam} unlocked.")

    def _do_ad_reset_password(self, a: Action) -> ActionResult:
        user = self.world.org.users.get(a.target)
        if user is None:
            return ActionResult(ok=False, rendered=f"Set-ADAccountPassword: {NOT_FOUND}")
        user.pwd_last_set = self.world.clock
        user.pwd_expires = self.world.clock + timedelta(days=60)
        user.locked_out = False
        user.bad_pwd_count = 0
        return ActionResult(ok=True, rendered=f"Password reset for {user.sam}.")

    def _do_ad_enable(self, a: Action) -> ActionResult:
        user = self.world.org.users.get(a.target)
        if user is None:
            return ActionResult(ok=False, rendered=f"Enable-ADAccount: {NOT_FOUND}")
        user.enabled = True
        return ActionResult(ok=True, rendered=f"Account {user.sam} enabled.")

    def _do_ad_disable(self, a: Action) -> ActionResult:
        user = self.world.org.users.get(a.target)
        if user is None:
            return ActionResult(ok=False, rendered=f"Disable-ADAccount: {NOT_FOUND}")
        user.enabled = False
        return ActionResult(ok=True, rendered=f"Account {user.sam} disabled.")

    def _do_ad_add_member(self, a: Action) -> ActionResult:
        group = self.world.org.groups.get(a.target)
        sam = a.args.get("member", "")
        if group is None or sam not in self.world.org.users:
            return ActionResult(ok=False, rendered=f"Add-ADGroupMember: {NOT_FOUND}")
        if sam not in group.members:
            group.members.append(sam)
        return ActionResult(ok=True, rendered=f"{sam} added to {group.name}.")

    def _do_ad_remove_member(self, a: Action) -> ActionResult:
        group = self.world.org.groups.get(a.target)
        sam = a.args.get("member", "")
        if group is None or sam not in group.members:
            return ActionResult(ok=False, rendered=f"Remove-ADGroupMember: {NOT_FOUND}")
        group.members.remove(sam)
        return ActionResult(ok=True, rendered=f"{sam} removed from {group.name}.")

    # --- actions: endpoint --------------------------------------------------
    def _do_machine_restart_service(self, a: Action) -> ActionResult:
        machine = self.world.machines.get(a.target.upper())
        service = a.args.get("service", "")
        if machine is None or service not in machine.services:
            return ActionResult(
                ok=False,
                rendered=f"Restart-Service: Cannot find any service with service name '{service}'.",
            )
        if machine.services[service] is ServiceState.DISABLED:
            # The differential this fault exists for: a stopped service starts,
            # a disabled one refuses until its startup type is changed back.
            return ActionResult(
                ok=False,
                rendered=f"Restart-Service: Service '{service}' on {machine.hostname} "
                "cannot be started because it is disabled.",
            )
        machine.services[service] = ServiceState.RUNNING
        return ActionResult(
            ok=True, rendered=f"Service {service} on {machine.hostname} is running."
        )

    def _do_machine_set_dns(self, a: Action) -> ActionResult:
        machine = self.world.machines.get(a.target.upper())
        if machine is None:
            return ActionResult(ok=False, rendered=f"{a.target}: {NOT_FOUND}")
        servers = [s.strip() for s in a.args.get("servers", "").split(",") if s.strip()]
        if not servers:
            return ActionResult(
                ok=False, rendered="Set-DnsClientServerAddress: -ServerAddresses is required."
            )
        machine.dns_servers = servers
        return ActionResult(
            ok=True,
            rendered=f"DNS servers on {machine.hostname} set to {', '.join(servers)}.",
        )

    def _do_machine_renew_dhcp(self, a: Action) -> ActionResult:
        machine = self.world.machines.get(a.target.upper())
        if machine is None:
            return ActionResult(ok=False, rendered=f"{a.target}: {NOT_FOUND}")
        if not machine.dhcp_enabled:
            return ActionResult(
                ok=False,
                rendered=f"The operation failed as no adapter is in the state "
                f"permissible for this operation on {machine.hostname}.",
            )
        lease = machine.dhcp_reserved_ip
        if lease is None:
            return ActionResult(
                ok=False,
                rendered=f"DHCP server {self.world.network.dhcp_server} "
                "did not offer an address.",
            )
        machine.ip = lease
        machine.gateway = self.world.network.gateway
        # A lease carries a mask and a router, so a renewal restores all three.
        # `network.netmask` is derived from the subnet, which no fault touches.
        machine.subnet_mask = self.world.network.netmask
        return ActionResult(
            ok=True, rendered=f"{machine.hostname} renewed its lease: {lease}"
        )

    def _do_machine_clear_disk(self, a: Action) -> ActionResult:
        machine = self.world.machines.get(a.target.upper())
        if machine is None:
            return ActionResult(ok=False, rendered=f"{a.target}: {NOT_FOUND}")
        if "gb" not in a.args:
            # Defaulting to 0 logged a mutation against the technician that
            # freed nothing and still reported success. `mail.set_quota`
            # already rejected its own missing argument; this now matches, and
            # DispatchTool's "a rejected call never reached the environment"
            # rule keeps the grade honest.
            return ActionResult(ok=False, rendered="-Gb is required.")
        try:
            freed = float(a.args["gb"])
        except ValueError:
            return ActionResult(ok=False, rendered="-Gb must be a number.")
        machine.disk_free_gb = min(machine.disk_free_gb + freed, machine.disk_total_gb)
        if machine.profile_state is ProfileState.TEMPORARY:
            machine.profile_state = ProfileState.NORMAL
        return ActionResult(
            ok=True,
            rendered=f"{machine.hostname} now has "
            f"{machine.disk_free_gb:.1f} GB free of {machine.disk_total_gb:.1f} GB.",
        )

    def _do_printer_reinstall_driver(self, a: Action) -> ActionResult:
        printer = self.world.printers.get(a.target)
        machine = self.world.machines.get(a.args.get("from", "").upper())
        if printer is None or machine is None:
            return ActionResult(ok=False, rendered=f"Add-PrinterDriver: {NOT_FOUND}")
        machine.printer_drivers[printer.name] = printer.correct_driver
        return ActionResult(
            ok=True,
            rendered=f"Driver for {printer.name} on {machine.hostname} reinstalled "
            f"as '{printer.correct_driver}'.",
        )

    # --- actions: mail ---------------------------------------------------------
    def _do_mail_set_quota(self, a: Action) -> ActionResult:
        mailbox = self.world.mailbox_for(a.target)
        if mailbox is None:
            return ActionResult(ok=False, rendered=f"Set-Mailbox: {NOT_FOUND}")
        try:
            quota_mb = float(a.args.get("quota_mb", ""))
        except ValueError:
            return ActionResult(ok=False, rendered="-quota_mb must be a number.")
        mailbox.quota_mb = quota_mb
        return ActionResult(
            ok=True, rendered=f"Mailbox quota for {a.target} set to {quota_mb:.1f} MB."
        )

    def _do_mail_archive(self, a: Action) -> ActionResult:
        mailbox = self.world.mailbox_for(a.target)
        if mailbox is None:
            return ActionResult(ok=False, rendered=f"New-MailboxExportRequest: {NOT_FOUND}")
        mailbox.used_mb = min(mailbox.used_mb, mailbox.quota_mb * ARCHIVE_TARGET_FRACTION)
        return ActionResult(
            ok=True,
            rendered=f"Archived {a.target}'s mailbox; now using "
            f"{mailbox.used_mb:.1f} MB of {mailbox.quota_mb:.1f} MB.",
        )

    def _do_mail_remove_rule(self, a: Action) -> ActionResult:
        mailbox = self.world.mailbox_for(a.target)
        name = a.args.get("name", "")
        if mailbox is None or not any(r.name == name for r in mailbox.rules):
            return ActionResult(ok=False, rendered=f"Remove-InboxRule: {NOT_FOUND}")
        mailbox.rules = [r for r in mailbox.rules if r.name != name]
        return ActionResult(ok=True, rendered=f"Rule '{name}' removed from {a.target}'s mailbox.")

    def _do_mail_restart_transport(self, a: Action) -> ActionResult:
        if a.target.upper() != self.world.mail.server:
            return ActionResult(
                ok=False,
                rendered="Restart-Service: Cannot find any service with service "
                "name 'MSExchangeTransport'.",
            )
        self.world.mail.transport_state = ServiceState.RUNNING
        self.world.mail.queue_depth = 0
        return ActionResult(
            ok=True,
            rendered=f"Microsoft Exchange Transport service on {a.target} is running. "
            "Queue drained.",
        )

    def _do_machine_enable_service(self, a: Action) -> ActionResult:
        machine = self.world.machines.get(a.target.upper())
        service = a.args.get("service", "")
        if machine is None or service not in machine.services:
            return ActionResult(
                ok=False,
                rendered=f"Set-Service: Cannot find any service with service name '{service}'.",
            )
        if machine.services[service] is ServiceState.DISABLED:
            # Enabling is not starting: the service comes back as Stopped, so
            # the repair is two steps and the technician has to notice.
            machine.services[service] = ServiceState.STOPPED
        return ActionResult(
            ok=True,
            rendered=f"Service {service} on {machine.hostname} set to start "
            "automatically. Current state: "
            f"{machine.services[service].value}.",
        )

    def _do_machine_rebuild_profile(self, a: Action) -> ActionResult:
        machine = self.world.machines.get(a.target.upper())
        if machine is None:
            return ActionResult(ok=False, rendered=f"{a.target}: {NOT_FOUND}")
        machine.profile_state = ProfileState.NORMAL
        return ActionResult(
            ok=True,
            rendered=f"User profile on {machine.hostname} rebuilt from the server "
            "copy and loaded normally.",
        )

    def _do_machine_resync_time(self, a: Action) -> ActionResult:
        machine = self.world.machines.get(a.target.upper())
        if machine is None:
            return ActionResult(ok=False, rendered=f"{a.target}: {NOT_FOUND}")
        machine.clock_offset_minutes = 0
        return ActionResult(
            ok=True,
            rendered=f"Sending resync command to {machine.hostname}\n"
            "The command completed successfully.",
        )

    def _do_machine_refresh_credentials(self, a: Action) -> ActionResult:
        machine = self.world.machines.get(a.target.upper())
        if machine is None:
            return ActionResult(ok=False, rendered=f"{a.target}: {NOT_FOUND}")
        machine.last_domain_sync = self.world.clock
        return ActionResult(
            ok=True,
            rendered=f"{machine.hostname} re-authenticated against "
            f"{self.world.network.dhcp_server} and refreshed its cached credentials.",
        )

    def _do_machine_kill_process(self, a: Action) -> ActionResult:
        machine = self.world.machines.get(a.target.upper())
        name = a.args.get("name", "")
        if machine is None:
            return ActionResult(ok=False, rendered=f"{a.target}: {NOT_FOUND}")
        if not name:
            return ActionResult(ok=False, rendered="-Name is required.")
        matching = [pr for pr in machine.processes if pr.name.lower() == name.lower()]
        if not matching:
            return ActionResult(
                ok=False,
                rendered=f"Stop-Process: Cannot find a process with the name '{name}'.",
            )
        machine.processes = [
            pr for pr in machine.processes if pr.name.lower() != name.lower()
        ]
        return ActionResult(
            ok=True,
            rendered=f"Stopped {len(matching)} process(es) named {name} on "
            f"{machine.hostname}.",
        )

    def _do_machine_clear_proxy(self, a: Action) -> ActionResult:
        machine = self.world.machines.get(a.target.upper())
        if machine is None:
            return ActionResult(ok=False, rendered=f"{a.target}: {NOT_FOUND}")
        machine.proxy_server = None
        return ActionResult(
            ok=True,
            rendered=f"WinHTTP proxy settings on {machine.hostname} reset to "
            "direct access.",
        )

    def _do_machine_enable_dhcp(self, a: Action) -> ActionResult:
        machine = self.world.machines.get(a.target.upper())
        if machine is None:
            return ActionResult(ok=False, rendered=f"{a.target}: {NOT_FOUND}")
        machine.dhcp_enabled = True
        return ActionResult(
            ok=True,
            rendered=f"{machine.hostname} set to obtain an address automatically. "
            "Renew the lease to pick one up.",
        )

    def _do_machine_set_subnet_mask(self, a: Action) -> ActionResult:
        machine = self.world.machines.get(a.target.upper())
        if machine is None:
            return ActionResult(ok=False, rendered=f"{a.target}: {NOT_FOUND}")
        mask = a.args.get("mask", "")
        try:
            ip_network(f"0.0.0.0/{mask}")
        except ValueError:
            return ActionResult(ok=False, rendered="-mask must be a valid subnet mask.")
        machine.subnet_mask = mask
        return ActionResult(
            ok=True, rendered=f"Subnet mask on {machine.hostname} set to {mask}."
        )

    def _do_ad_nest_group(self, a: Action) -> ActionResult:
        parent = self.world.org.groups.get(a.target)
        child_name = a.args.get("member_group", "")
        child = self.world.org.groups.get(child_name)
        if parent is None or child is None:
            return ActionResult(ok=False, rendered=f"Add-ADGroupMember: {NOT_FOUND}")
        if child.name == parent.name:
            return ActionResult(
                ok=False, rendered="Add-ADGroupMember: a group cannot contain itself."
            )
        if child.name not in parent.member_groups:
            parent.member_groups.append(child.name)
        return ActionResult(
            ok=True, rendered=f"Group {child.name} nested inside {parent.name}."
        )

    def _do_printer_clear_queue(self, a: Action) -> ActionResult:
        printer = self.world.printers.get(a.target)
        if printer is None:
            return ActionResult(ok=False, rendered=f"Remove-PrintJob: {NOT_FOUND}")
        cleared = len(printer.jobs)
        printer.jobs = []
        return ActionResult(
            ok=True, rendered=f"Cleared {cleared} job(s) from the {printer.name} queue."
        )

    def _do_printer_reset(self, a: Action) -> ActionResult:
        printer = self.world.printers.get(a.target)
        if printer is None:
            return ActionResult(ok=False, rendered=f"Set-Printer: {NOT_FOUND}")
        printer.online = True
        return ActionResult(
            ok=True,
            rendered=f"{printer.name} power-cycled and reporting Online.",
        )

    def _do_mail_remove_delegate(self, a: Action) -> ActionResult:
        mailbox = self.world.mailbox_for(a.target)
        sam = a.args.get("delegate", "")
        if mailbox is None or sam not in mailbox.delegates:
            return ActionResult(ok=False, rendered=f"Remove-MailboxPermission: {NOT_FOUND}")
        mailbox.delegates = [d for d in mailbox.delegates if d != sam]
        return ActionResult(
            ok=True, rendered=f"Removed {sam}'s access to {a.target}'s mailbox."
        )

    def _do_mail_set_autodiscover(self, a: Action) -> ActionResult:
        if a.target.upper() != self.world.mail.server:
            return ActionResult(ok=False, rendered=f"Set-ClientAccessService: {NOT_FOUND}")
        host = a.args.get("autodiscover_host", "")
        if not host:
            return ActionResult(
                ok=False, rendered="-autodiscover_host is required."
            )
        self.world.mail.autodiscover_host = host.upper()
        return ActionResult(
            ok=True,
            rendered=f"Autodiscover endpoint for {a.target} set to {host.upper()}.",
        )

    def _do_mail_set_list_owner(self, a: Action) -> ActionResult:
        group = self.world.mail.distribution_lists.get(a.target)
        owner = a.args.get("owner", "")
        if group is None or owner not in self.world.org.users:
            return ActionResult(ok=False, rendered=f"Set-DistributionGroup: {NOT_FOUND}")
        group.owner_sam = owner
        return ActionResult(ok=True, rendered=f"{group.name} is now managed by {owner}.")

    def _do_mail_remove_mailbox(self, a: Action) -> ActionResult:
        """Destructive on purpose.

        Nothing in the catalog is fixed by deleting a mailbox, and the mail
        invariants exist to say so — but a real console would let a technician
        do it, and an invariant nobody can trip teaches nobody anything.
        """
        if a.target not in self.world.mail.mailboxes:
            return ActionResult(ok=False, rendered=f"Remove-Mailbox: {NOT_FOUND}")
        del self.world.mail.mailboxes[a.target]
        return ActionResult(ok=True, rendered=f"Mailbox for {a.target} removed.")
