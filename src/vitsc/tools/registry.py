from vitsc.tools.ad import ADConsole
from vitsc.tools.base import Tool
from vitsc.tools.eventlog import EventViewer
from vitsc.tools.kb import KnowledgeBase
from vitsc.tools.mail import MailConsole
from vitsc.tools.network import NetworkTools
from vitsc.tools.powershell import PowerShellConsole
from vitsc.tools.printing import PrintManagement
from vitsc.tools.remote import RemoteSession

_TOOLS: dict[str, Tool] = {
    t.name: t
    for t in [
        ADConsole(),
        NetworkTools(),
        RemoteSession(),
        EventViewer(),
        PrintManagement(),
        PowerShellConsole(),
        KnowledgeBase(),
        MailConsole(),
    ]
}


def get_tool(name: str) -> Tool:
    return _TOOLS[name]


def all_tools() -> list[Tool]:
    return sorted(_TOOLS.values(), key=lambda t: t.name)


def register_tool(tool: Tool) -> None:
    _TOOLS[tool.name] = tool
