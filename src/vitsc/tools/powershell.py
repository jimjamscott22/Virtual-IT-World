"""A *defined* command set, not a parser.

A free-form shell cannot be honestly simulated in v1, and pretending
otherwise would teach the wrong lesson. Anything outside this set returns the
same `CommandNotFoundException` the real shell would.
"""

from vitsc.tools.base import DispatchTool

# Cmdlets whose target is the machine the session is running against.
_MACHINE_SCOPED = {
    "get-service",
    "restart-service",
    "get-eventlog",
    "gpupdate",
}


class PowerShellConsole(DispatchTool):
    name = "ps"
    READS = {
        "Get-Service": "machine.services",
        "Get-ADUser": "ad.user",
        "Get-Printer": "printer.state",
        "Get-PSDrive": "share.access",
        "Test-NetConnection": "net.ping",
        "Get-EventLog": "machine.eventlog",
    }
    WRITES = {
        "Restart-Service": "machine.restart_service",
        "gpupdate": "machine.renew_dhcp",
    }

    def target_key(self, command: str, args: dict[str, str]) -> str:
        cmd = command.lower()
        if cmd in _MACHINE_SCOPED:
            return args.get("host", "")
        if cmd == "get-aduser":
            return args.get("sam", "")
        if cmd == "get-printer":
            return args.get("printer", "")
        if cmd == "get-psdrive":
            return args.get("name", "S:")
        if cmd == "test-netconnection":
            return args.get("target") or args.get("computername", "")
        return args.get("host", "")

    def query_args(self, command: str, args: dict[str, str]) -> dict[str, str]:
        # `-ComputerName` is the session's machine; everything downstream of
        # the environment calls that "from".
        out = {**args, "from": args.get("host", "")}
        if command.lower() in {"get-service", "restart-service"} and "name" in args:
            out["service"] = args["name"]
        return out
