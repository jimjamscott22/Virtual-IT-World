from vitsc.tools.base import DispatchTool

# Commands that act *on* a remote name rather than on the machine the
# technician is working from.
_REMOTE_TARGETED = {"ping", "nslookup"}


class NetworkTools(DispatchTool):
    name = "net"
    READS = {
        "ping": "net.ping",
        "nslookup": "net.nslookup",
        "ipconfig": "net.ipconfig",
        "get-proxy": "net.proxy",
    }
    WRITES = {
        "renew": "machine.renew_dhcp",
        "set-dns": "machine.set_dns",
        "set-mask": "machine.set_subnet_mask",
        "enable-dhcp": "machine.enable_dhcp",
        "clear-proxy": "machine.clear_proxy",
    }

    def target_param(self, command: str) -> str:
        # ping and nslookup act *on* a remote name; everything else acts on
        # the machine the technician is sitting at.
        if command.lower() in _REMOTE_TARGETED:
            return "host"
        return "from"
