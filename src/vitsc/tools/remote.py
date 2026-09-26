from vitsc.tools.base import DispatchTool


class RemoteSession(DispatchTool):
    """Read-only machine state, plus the repairs a remote session can make.

    Everything here acts on the machine named by `-host`, which is why the
    default `TARGET_PARAM` is left alone — the per-command arguments
    (`-service`, `-name`, `-gb`) ride along in `args`.
    """

    name = "remote"
    READS = {
        "inspect": "machine.state",
        "services": "machine.services",
        "processes": "machine.processes",
    }
    WRITES = {
        "clear-disk": "machine.clear_disk",
        "enable-service": "machine.enable_service",
        # The tool that shows you a service's state should let you start it.
        # Before this, the only restarts reachable through the UI were
        # `print restart-spooler` (which hardcodes Spooler) and PowerShell's
        # `Restart-Service`, so a stopped service with any other name had no
        # obvious repair from the console that reported it.
        "restart-service": "machine.restart_service",
        "rebuild-profile": "machine.rebuild_profile",
        "resync-time": "machine.resync_time",
        "refresh-credentials": "machine.refresh_credentials",
        "kill-process": "machine.kill_process",
    }
