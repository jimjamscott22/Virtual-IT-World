"""The v1 distractor catalog.

Deliberately empty at Task 3: the protocol, the registry and the conformance
harness land first so that every distractor written in Task 4 is proven the
moment it registers, rather than being retrofitted with tests afterwards.

Importing this module is what triggers registration, exactly as
`faults/catalog/__init__.py` does for faults — so it must exist even while
empty, or `all_distractors()` and the harness cannot import it.

Register *instances*, not classes, at the bottom of this module — the same
shape `faults/catalog/identity.py` uses:

    register_distractor(StoppedPrintSpoolerOnAnIdleMachine())

The conformance harness calls `placements(world)` on whatever is registered,
so a bare class fails at collection time with a missing `self`.
"""
