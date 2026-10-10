from vitsc.tools.base import DispatchTool

# Commands whose subject is a group rather than an account. `nest-group` takes
# the parent as `-group` and the group being put inside it as `-member_group`.
_GROUP_TARGETED = {"get-group", "add-member", "remove-member", "nest-group"}


class ADConsole(DispatchTool):
    name = "ad"
    TARGET_PARAM = "sam"
    READS = {"get-user": "ad.user", "get-group": "ad.group"}
    WRITES = {
        "unlock": "ad.unlock",
        "reset-password": "ad.reset_password",
        "enable": "ad.enable",
        "disable": "ad.disable",
        "add-member": "ad.add_member",
        "remove-member": "ad.remove_member",
        "nest-group": "ad.nest_group",
    }

    def target_param(self, command: str) -> str:
        if command.lower() in _GROUP_TARGETED:
            return "group"
        return self.TARGET_PARAM
