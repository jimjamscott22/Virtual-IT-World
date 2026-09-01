from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ServiceState(str, Enum):
    RUNNING = "Running"
    STOPPED = "Stopped"


class SmartStatus(str, Enum):
    OK = "OK"
    PRED_FAIL = "Pred Fail"


class ProfileState(str, Enum):
    NORMAL = "Normal"
    TEMPORARY = "Temporary"
    CORRUPT = "Corrupt"


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
    event_log: list[EventEntry] = Field(default_factory=list)


class Printer(BaseModel):
    name: str
    host: str
    model: str
    correct_driver: str
    online: bool = True


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


class MailSystem(BaseModel):
    server: str
    transport_state: ServiceState = ServiceState.RUNNING
    queue_depth: int = 0
    mailboxes: dict[str, Mailbox] = Field(default_factory=dict)


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
        return [g.name for g in self.org.groups.values() if sam in g.members]

    def mailbox_for(self, sam: str) -> Mailbox | None:
        return self.mail.mailboxes.get(sam)
