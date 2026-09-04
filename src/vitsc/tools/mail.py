from vitsc.tools.base import DispatchTool


class MailConsole(DispatchTool):
    name = "mail"
    TARGET_PARAM = "sam"
    READS = {
        "get-mailbox": "mail.mailbox",
        "get-rules": "mail.rules",
        "get-queue": "mail.queue",
    }
    WRITES = {
        "set-quota": "mail.set_quota",
        "archive": "mail.archive",
        "remove-rule": "mail.remove_rule",
        "restart-transport": "mail.restart_transport",
    }

    def target_key(self, command: str, args: dict[str, str]) -> str:
        if command.lower() in ("get-queue", "restart-transport"):
            return args.get("host", "")
        return args.get("sam", "")
