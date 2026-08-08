from vitsc.tools.base import DispatchTool


class ADConsole(DispatchTool):
    name = "ad"
    TARGET_PARAM = "identity"
    READS = {"get-user": "ad.user", "get-group": "ad.group"}
    WRITES = {
        "unlock": "ad.unlock",
        "reset-password": "ad.reset_password",
        "enable": "ad.enable",
        "disable": "ad.disable",
        "add-member": "ad.add_member",
        "remove-member": "ad.remove_member",
    }

    def target_key(self, command: str, args: dict[str, str]) -> str:
        if command.lower() in {"get-group", "add-member", "remove-member"}:
            return args.get("group", "")
        return args.get("sam", "")
