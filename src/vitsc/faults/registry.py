from vitsc.faults.base import Fault

_REGISTRY: dict[str, Fault] = {}


def register(fault: Fault) -> Fault:
    if fault.id in _REGISTRY:
        raise ValueError(f"duplicate fault id: {fault.id}")
    _REGISTRY[fault.id] = fault
    return fault


def all_faults() -> list[Fault]:
    import vitsc.faults.catalog  # noqa: F401  — triggers registration

    return sorted(_REGISTRY.values(), key=lambda f: f.id)


def get_fault(fault_id: str) -> Fault:
    all_faults()
    return _REGISTRY[fault_id]
