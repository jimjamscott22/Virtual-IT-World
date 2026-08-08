"""The v1 backend: an in-memory world model.

Handlers read and write `self.world` and nothing else. No handler knows that
faults exist, which is what permits multiple valid fix paths and honest
distractors (spec §3).
"""

import uuid
from datetime import timedelta

from vitsc.env.base import Action, ActionResult, Observation, Query
from vitsc.world.models import ProfileState, ServiceState, World

NOT_FOUND = "The term is not recognised, or the object cannot be found."
APIPA_PREFIX = "169.254"


class SimulatedEnvironment:
    def __init__(self, world: World) -> None:
        self.world = world
        self._snapshots: dict[str, World] = {}

    # --- Environment protocol -------------------------------------------
    def read(self, query: Query) -> Observation:
        handler = getattr(self, f"_read_{query.kind.replace('.', '_')}", None)
        if handler is None:
            return Observation(ok=False, rendered=NOT_FOUND)
        return handler(query)

    def execute(self, action: Action) -> ActionResult:
        handler = getattr(self, f"_do_{action.kind.replace('.', '_')}", None)
        if handler is None:
            return ActionResult(ok=False, rendered=NOT_FOUND)
        return handler(action)

    def snapshot(self) -> str:
        snapshot_id = uuid.uuid4().hex
        self._snapshots[snapshot_id] = self.world.model_copy(deep=True)
        return snapshot_id

    def restore(self, snapshot_id: str) -> None:
        self.world = self._snapshots[snapshot_id].model_copy(deep=True)

    # --- helpers ---------------------------------------------------------
    def _resolve(self, name: str, from_host: str) -> str | None:
        """DNS resolution, honouring the querying machine's own resolvers."""
        if name and name[0].isdigit():
            return name
        source = self.world.machines.get(from_host)
        if source is None:
            return None
        if not set(source.dns_servers) & set(self.world.network.dns_servers):
            return None
        target = self.world.machines.get(name.upper())
        return target.ip if target else None

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
        data = {"Name": group.name, "Members": members}
        rendered = "\n".join([f"{group.name} ({len(members)} members)", *members])
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
            "SubnetMask": machine.subnet_mask if leased else "255.255.0.0",
            "DefaultGateway": machine.gateway if leased else "",
            "DNSServers": list(machine.dns_servers),
            "DhcpEnabled": machine.dhcp_enabled,
            "Autoconfigured": not leased,
        }
        lines = [
            "Windows IP Configuration",
            "",
            "Ethernet adapter Ethernet:",
            "",
            f"   Connection-specific DNS Suffix  . : {self.world.org.domain}",
            f"   DHCP Enabled. . . . . . . . . . . : {'Yes' if machine.dhcp_enabled else 'No'}",
            f"   {'Autoconfiguration IPv4 Address' if not leased else 'IPv4 Address. . . . . . . . . '}"
            f". : {ip}{' (Preferred)' if leased else ''}",
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
        share = self.world.shares[machine.mapped_drives[q.target]]
        if self._resolve(share.host, machine.hostname) is None:
            return Observation(
                ok=False,
                data={"reason": "dns"},
                rendered=f"{share.unc} is not accessible. "
                "The network path was not found.",
            )
        member = machine.assigned_to in self.world.org.groups[share.required_group].members
        if not member:
            return Observation(
                ok=False,
                data={"reason": "permissions"},
                rendered=f"{share.unc} is not accessible. Access is denied.",
            )
        return Observation(
            ok=True, data={"unc": share.unc}, rendered=f"{q.target} -> {share.unc}"
        )

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
        return ActionResult(
            ok=True, rendered=f"{machine.hostname} renewed its lease: {lease}"
        )

    def _do_machine_clear_disk(self, a: Action) -> ActionResult:
        machine = self.world.machines.get(a.target.upper())
        if machine is None:
            return ActionResult(ok=False, rendered=f"{a.target}: {NOT_FOUND}")
        try:
            freed = float(a.args.get("gb", "0"))
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
