"""A *defined* command set, not a parser.

A free-form shell cannot be honestly simulated in v1, and pretending
otherwise would teach the wrong lesson. Anything outside this set returns the
same `CommandNotFoundException` the real shell would.
"""

from vitsc.tools.base import DispatchTool

# Most cmdlets act on the machine the session is running against, named by
# `-host`. These are the ones whose target is something else.
_TARGET_PARAMS = {
    "get-aduser": "sam",
    "get-printer": "printer",
    "get-psdrive": "name",
    "test-netconnection": "target",
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
        "Get-Process": "machine.processes",
    }
    WRITES = {
        "Restart-Service": "machine.restart_service",
        "Set-Service": "machine.enable_service",
        "gpupdate": "machine.renew_dhcp",
        "w32tm": "machine.resync_time",
    }

    def target_param(self, command: str) -> str:
        return _TARGET_PARAMS.get(command.lower(), self.TARGET_PARAM)

    def target_key(self, command: str, args: dict[str, str]) -> str:
        cmd = command.lower()
        if cmd == "get-psdrive":
            return args.get("name", "S:")
        if cmd == "test-netconnection":
            # `-ComputerName` is the real cmdlet's spelling, accepted as well.
            return args.get("target") or args.get("computername", "")
        return super().target_key(command, args)

    def query_args(self, command: str, args: dict[str, str]) -> dict[str, str]:
        # `-ComputerName` is the session's machine; everything downstream of
        # the environment calls that "from".
        out = {**args, "from": args.get("host", "")}
        if command.lower() in {"get-service", "restart-service", "set-service"} and (
            "name" in args
        ):
            out["service"] = args["name"]
        return out
