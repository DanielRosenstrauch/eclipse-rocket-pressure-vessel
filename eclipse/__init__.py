"""Eclipse Rocket pressure-vessel design tool.

A Python translation of the MECH 315 (Spring 2026) thick-walled pressure
vessel optimization originally written in MATLAB. Provides:

- Thick-walled (Lamé) stress model with closed-end Von Mises criterion
- ISA-troposphere drag-work calculation along the prescribed velocity profile
- Material and fuel libraries
- Vectorized two-pass optimizer that searches a 3D (r0, t, L) design grid

Public modules:
    physics      - stress, P_max, geometry, gas mass/energy
    trajectory   - drag work, energy required to reach apogee
    data         - material and fuel libraries
    optimize     - feasibility filter and two-pass optimizer
"""

from . import data, optimize, physics, trajectory

__all__ = ["data", "optimize", "physics", "trajectory"]
__version__ = "0.1.0"
