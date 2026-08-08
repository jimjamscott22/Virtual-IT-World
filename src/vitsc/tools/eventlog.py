from vitsc.tools.base import DispatchTool


class EventViewer(DispatchTool):
    name = "events"
    READS = {"get": "machine.eventlog"}
    WRITES: dict[str, str] = {}
