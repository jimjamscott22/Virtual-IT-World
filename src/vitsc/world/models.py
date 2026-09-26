from datetime import datetime, timedelta
from enum import Enum
from ipaddress import ip_network

from pydantic import BaseModel, Field

# How far a workstation's clock may drift before domain authentication stops
# trusting it. Both `endpoint.time_skew` (which decides "is it broken") and
# `SimulatedEnvironment` (which decides what a share access attempt says) need
# the same number, so it lives with the world rather than in either of them.
CLOCK_SKEW_TOLERANCE_MINUTES = 5


class ServiceState(str, Enum):
    RUNNING = "Running"
    STOPPED = "Stopped"
    # Distinct from STOPPED on purpose: a stopped service starts again, a
    # disabled one refuses until its startup type is changed back. That
    # differential is the whole lesson of `endpoint.service_disabled`.
    DISABLED = "Disabled"


class SmartStatus(str, Enum):
    OK = "OK"
    PRED_FAIL = "Pred Fail"


class ProfileState(str, Enum):
    NORMAL = "Normal"
    TEMPORARY = "Temporary"
    CORRUPT = "Corrupt"


class JobStatus(str, Enum):
    QUEUED = "Queued"
    PRINTING = "Printing"
    ERROR = "Error"


class PrintJob(BaseModel):
    job_id: int
    owner_sam: str
    document: str
    pages: int = 1
    status: JobStatus = JobStatus.QUEUED


class Process(BaseModel):
    name: str
    pid: int
    cpu_percent: float = 0.0
    memory_mb: float = 64.0


class EventEntry(BaseModel):
    log: str
    source: str
    event_id: int
    level: str
    at: datetime
    message: str


class ADUser(BaseModel):
    sam: str
    display_name: str
    upn: str
    department: str
    title: str
    enabled: bool = True
    locked_out: bool = False
    bad_pwd_count: int = 0
    pwd_last_set: datetime
    pwd_expires: datetime
    ou: str
    home_drive: str | None = None


class ADGroup(BaseModel):
    name: str
    members: list[str] = Field(default_factory=list)
    # Groups nested *inside* this one. Empty across the seeded estate, so
    # effective membership equals direct membership until a fault nests
    # something — which is what `ad.nested_group_membership` does.
    member_groups: list[str] = Field(default_factory=list)


class Organization(BaseModel):
    domain: str
    users: dict[str, ADUser]
    groups: dict[str, ADGroup]


class Machine(BaseModel):
    hostname: str
    assigned_to: str | None = None
    ip: str | None = None
    # The server-side lease record. Unlike `ip`, a fault never clears this —
    # it's what a DHCP renewal restores.
    dhcp_reserved_ip: str | None = None
    subnet_mask: str = "255.255.255.0"
    gateway: str | None = None
    dns_servers: list[str] = Field(default_factory=list)
    dhcp_enabled: bool = True
    services: dict[str, ServiceState] = Field(default_factory=dict)
    disk_free_gb: float = 120.0
    disk_total_gb: float = 256.0
    smart_status: SmartStatus = SmartStatus.OK
    mapped_drives: dict[str, str] = Field(default_factory=dict)
    installed_printers: list[str] = Field(default_factory=list)
    printer_drivers: dict[str, str] = Field(default_factory=dict)
    profile_state: ProfileState = ProfileState.NORMAL
    proxy_server: str | None = None
    # When this machine last authenticated against the domain controller. A
    # password changed after this moment is not in the machine's cache yet.
    last_domain_sync: datetime | None = None
    clock_offset_minutes: int = 0
    processes: list[Process] = Field(default_factory=list)
    event_log: list[EventEntry] = Field(default_factory=list)

    def clock_reading(self, true_time: datetime) -> datetime:
        """What this machine believes the time is, drift included."""
        return true_time + timedelta(minutes=self.clock_offset_minutes)


class Printer(BaseModel):
    name: str
    host: str
    model: str
    correct_driver: str
    online: bool = True
    jobs: list[PrintJob] = Field(default_factory=list)


class Share(BaseModel):
    unc: str
    host: str
    required_group: str
    drive_letter: str


class Network(BaseModel):
    subnet: str
    gateway: str
    dns_servers: list[str]
    dhcp_server: str
    external_probe: str = "8.8.8.8"

    @property
    def netmask(self) -> str:
        """The mask the subnet implies, which is what DHCP hands out.

        Derived rather than stored so that a fault which rewrites a machine's
        mask can never also rewrite the value a repair restores it to — the
        same reason `Machine.dhcp_reserved_ip` exists alongside `ip`.
        """
        return str(ip_network(self.subnet).netmask)


class MailRule(BaseModel):
    name: str
    forward_to: str | None = None
    delete_after: bool = False
    created_by: str | None = None  # who set it, for an escalation's evidence


class Mailbox(BaseModel):
    owner_sam: str
    primary_smtp: str
    server: str
    quota_mb: float = 51200.0
    used_mb: float = 4096.0
    rules: list[MailRule] = Field(default_factory=list)
    forwarding_smtp: str | None = None
    litigation_hold: bool = False
    # Who else can open this mailbox. A name here that no longer exists in
    # `Organization.users` is someone who left with their access intact.
    delegates: list[str] = Field(default_factory=list)


class DistributionList(BaseModel):
    name: str
    address: str
    owner_sam: str | None = None
    members: list[str] = Field(default_factory=list)


class MailSystem(BaseModel):
    server: str
    transport_state: ServiceState = ServiceState.RUNNING
    queue_depth: int = 0
    mailboxes: dict[str, Mailbox] = Field(default_factory=dict)
    autodiscover_host: str | None = None
    distribution_lists: dict[str, DistributionList] = Field(default_factory=dict)


class World(BaseModel):
    org: Organization
    machines: dict[str, Machine]
    printers: dict[str, Printer]
    shares: dict[str, Share]
    network: Network
    mail: MailSystem
    clock: datetime

    def machine_for(self, sam: str) -> Machine | None:
        for machine in self.machines.values():
            if machine.assigned_to == sam:
                return machine
        return None

    def groups_of(self, sam: str) -> list[str]:
        """Direct membership only — what `MemberOf` shows on the account.

        Deliberately not transitive: a technician reading the account has to
        notice that the group named there is not the group the share wants.
        Ask `is_member()` for the question a file server actually asks.
        """
        return [g.name for g in self.org.groups.values() if sam in g.members]

    def effective_members(self, group_name: str) -> set[str]:
        """Everyone the group grants, following nesting to the bottom."""
        members: set[str] = set()
        seen: set[str] = set()
        pending = [group_name]
        while pending:
            name = pending.pop()
            if name in seen:
                continue
            seen.add(name)
            group = self.org.groups.get(name)
            if group is None:
                continue
            members |= set(group.members)
            pending.extend(group.member_groups)
        return members

    def is_member(self, group_name: str, sam: str | None) -> bool:
        return sam is not None and sam in self.effective_members(group_name)

    def mailbox_for(self, sam: str) -> Mailbox | None:
        return self.mail.mailboxes.get(sam)
