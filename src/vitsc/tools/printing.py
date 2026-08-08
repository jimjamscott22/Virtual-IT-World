from vitsc.tools.base import DispatchTool


class PrintManagement(DispatchTool):
    name = "print"
    TARGET_PARAM = "printer"
    READS = {"get-printer": "printer.state"}
    WRITES = {
        "restart-spooler": "machine.restart_service",
        "reinstall-driver": "printer.reinstall_driver",
    }

    def target_key(self, command: str, args: dict[str, str]) -> str:
        if command.lower() == "restart-spooler":
            return args.get("from", "")
        return args.get("printer", "")

    def query_args(self, command: str, args: dict[str, str]) -> dict[str, str]:
        if command.lower() == "restart-spooler":
            return {**args, "service": "Spooler"}
        return args
