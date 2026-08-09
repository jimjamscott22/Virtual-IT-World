"""The persona layer: how the simulated user talks to the technician.

Layer 1 of leak prevention is structural and lives here — a `Persona` is
handed a `PersonaCard` and a `UserSymptoms`, never a `Fault` or a `World`.
It is therefore incapable of naming the mechanism, whatever backs it.
"""
