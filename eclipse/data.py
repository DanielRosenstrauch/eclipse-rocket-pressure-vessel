"""Material and fuel libraries for the Eclipse Rocket pressure-vessel design.

All values match the MATLAB report (MECH 315, Spring 2026). SI units throughout.
"""

from dataclasses import dataclass
from typing import List


# ---------------------------------------------------------------------------
# Universal constants
# ---------------------------------------------------------------------------

R_BAR: float = 8.314           # Universal gas constant [J/(mol*K)]
T_GAS: float = 300.0           # Storage temperature [K]
G_ACCEL: float = 9.81          # Gravitational acceleration [m/s^2]
P_ATM: float = 101_325.0       # Atmospheric pressure [Pa]

# Unit conversion
INCH_TO_M: float = 0.0254
FT_TO_M: float = 0.3048
PSI_TO_PA: float = 6_894.76


# ---------------------------------------------------------------------------
# Mission parameters (defaults; the app exposes these)
# ---------------------------------------------------------------------------

M_REST_DEFAULT: float = 85.0                       # Rest-of-rocket mass [kg]
H_TARGET_FT_DEFAULT: float = 30_000.0              # Target altitude [ft]
R0_MAX_IN_DEFAULT: float = 5.75 / 2.0              # Max outer radius [in]
L_MAX_IN_DEFAULT: float = 60.0                     # Max total length [in]
NOSE_CONE_D_IN_DEFAULT: float = 6.0                # Nose cone diameter [in]
CD_DEFAULT: float = 0.75                           # Drag coefficient


# ---------------------------------------------------------------------------
# Material and fuel records
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Material:
    """Pressure-vessel material properties."""

    name: str
    density: float        # [kg/m^3]
    yield_strength: float # Sy [Pa]
    cost: float           # [$/kg]
    notes: str = ""


@dataclass(frozen=True)
class Fuel:
    """Gaseous propellant properties (ideal-gas treatment)."""

    name: str
    energy_density: float # Ed [J/mol]
    molar_mass: float     # M [kg/mol]
    cost: float           # [$/kg]
    notes: str = ""


MATERIALS: List[Material] = [
    Material(
        name="Aluminum 6061-T6",
        density=2700.0,
        yield_strength=275e6,
        cost=2.00,
        notes="Primary baseline.",
    ),
    Material(
        name="Steel (Structural)",
        density=7850.0,
        yield_strength=250e6,
        cost=1.50,
        notes="Dense, low specific strength.",
    ),
    Material(
        name="Titanium Ti-6Al-4V",
        density=4430.0,
        yield_strength=880e6,
        cost=35.00,
        notes="Best strength-to-density ratio.",
    ),
    Material(
        name="Duralumin 2024-T3",
        density=2787.0,
        yield_strength=345e6,
        cost=4.50,
        notes="Strong, lightweight alternative.",
    ),
]


FUELS: List[Fuel] = [
    Fuel(
        name="Hydrogen (H2)",
        energy_density=216e3,
        molar_mass=2.01588e-3,
        cost=28.40,
        notes="Very light, cheap energy per mole.",
    ),
    Fuel(
        name="Lunar Gas Compound 1",
        energy_density=249e3,
        molar_mass=31.998e-3,
        cost=16.00,
        notes="Heavy molecule, cheapest fuel.",
    ),
    Fuel(
        name="Lunar Gas Compound 2",
        energy_density=285e3,
        molar_mass=8.619e-3,
        cost=105.00,
        notes="Highest energy per mole; expensive.",
    ),
]


def material_by_name(name: str) -> Material:
    """Lookup a Material by its display name."""
    for m in MATERIALS:
        if m.name == name:
            return m
    raise KeyError(f"Unknown material: {name!r}")


def fuel_by_name(name: str) -> Fuel:
    """Lookup a Fuel by its display name."""
    for f in FUELS:
        if f.name == name:
            return f
    raise KeyError(f"Unknown fuel: {name!r}")
