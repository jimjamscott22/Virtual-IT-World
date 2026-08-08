from vitsc.tools.base import DispatchTool


class NetworkTools(DispatchTool):
    name = "net"
    READS = {"ping": "net.ping", "nslookup": "net.nslookup", "ipconfig": "net.ipconfig"}
    WRITES = {"renew": "machine.renew_dhcp", "set-dns": "machine.set_dns"}

    def target_key(self, command: str, args: dict[str, str]) -> str:
        # ping and nslookup act *on* a remote name; everything else acts on
        # the machine the technician is sitting at.
        if command.lower() in {"ping", "nslookup"}:
            return args.get("host", "")
        return args.get("from", "")
