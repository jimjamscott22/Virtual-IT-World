from vitsc.tools.base import DispatchTool

# The one command here that acts on a *machine* rather than a printer: the
# spooler is a service on the workstation or the print server.
_MACHINE_TARGETED = {"restart-spooler"}


class PrintManagement(DispatchTool):
    name = "print"
    TARGET_PARAM = "printer"
    READS = {"get-printer": "printer.state", "get-jobs": "printer.jobs"}
    WRITES = {
        "restart-spooler": "machine.restart_service",
        "reinstall-driver": "printer.reinstall_driver",
        "clear-queue": "printer.clear_queue",
        "reset-printer": "printer.reset",
        "push-driver": "printer.push_driver",
    }

    def target_param(self, command: str) -> str:
        if command.lower() in _MACHINE_TARGETED:
            return "from"
        return self.TARGET_PARAM

    def query_args(self, command: str, args: dict[str, str]) -> dict[str, str]:
        if command.lower() in _MACHINE_TARGETED:
            return {**args, "service": "Spooler"}
        return args
