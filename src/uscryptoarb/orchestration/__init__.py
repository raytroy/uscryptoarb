"""
Orchestration layer — imperative shell wiring pure pipeline to real I/O.

This is the top layer (Section 5.1). It imports everything and is the only
layer that performs I/O scheduling, config loading, and lifecycle management.

NO pure business logic here — that lives in strategy/ and calculation/.
"""
