from vitsc.tools.base import DispatchTool

# Commands that act on the mail server rather than on somebody's mailbox.
_SERVER_TARGETED = {
    "get-queue",
    "restart-transport",
    "get-lists",
    "get-autodiscover",
    "set-autodiscover",
}
# ...and the one that acts on a distribution group.
_LIST_TARGETED = {"set-list-owner"}


class MailConsole(DispatchTool):
    name = "mail"
    TARGET_PARAM = "sam"
    READS = {
        "get-mailbox": "mail.mailbox",
        "get-rules": "mail.rules",
        "get-queue": "mail.queue",
        "get-delegates": "mail.delegates",
        "get-lists": "mail.lists",
        "get-autodiscover": "mail.autodiscover",
    }
    WRITES = {
        "set-quota": "mail.set_quota",
        "archive": "mail.archive",
        "remove-rule": "mail.remove_rule",
        "restart-transport": "mail.restart_transport",
        "remove-delegate": "mail.remove_delegate",
        "set-autodiscover": "mail.set_autodiscover",
        "set-list-owner": "mail.set_list_owner",
        "remove-mailbox": "mail.remove_mailbox",
    }

    def target_key(self, command: str, args: dict[str, str]) -> str:
        if command.lower() in _SERVER_TARGETED:
            return args.get("host", "")
        if command.lower() in _LIST_TARGETED:
            return args.get("list", "")
        return args.get("sam", "")
