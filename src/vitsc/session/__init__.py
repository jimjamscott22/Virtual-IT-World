"""Session layer: tickets, the queue, grading, and the after-action report.

This is the first layer that knows a *fault id* — but only as an opaque string
on a `Ticket`. It still never reads fault state to decide anything the player
can see; `is_present()` remains the gate, checked by grading against the world.
"""
