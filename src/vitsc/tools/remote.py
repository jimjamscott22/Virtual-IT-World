from vitsc.tools.base import DispatchTool


class RemoteSession(DispatchTool):
    """Read-only machine state, plus the one repair a remote session can make."""

    name = "remote"
    READS = {"inspect": "machine.state", "services": "machine.services"}
    WRITES = {"clear-disk": "machine.clear_disk"}
