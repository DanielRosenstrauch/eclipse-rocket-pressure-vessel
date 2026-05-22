"""Trajectory and drag-work calculation along the prescribed velocity profile.

The MATLAB report pre-computed the drag work once (``DragWork.m``) and
hard-coded the result as ``W_drag = 1.11e6 J``. Here we re-derive it with
SciPy's adaptive quadrature so the user can see how it depends on the
nose-cone diameter, drag coefficient, and target altitude.

Velocity profile (from the project specification, Section 3.3):

    v(h) = 2e-10 * [ -( (h - h_max)*h + (h - h_max)*h^2 ) ]   [ft/s, h in ft]

ISA troposphere density (with linear lapse rate L = 0.0065 K/m):

    T(h)   = T0 - L*h
    rho(h) = P0 * (1 - L*h/T0)^(g/(R_air*L)) / (R_air * T(h))
"""

from __future__ import annotations

import math

import numpy as np
from scipy.integrate import quad

from .data import FT_TO_M, G_ACCEL


# ISA troposphere constants
_T0_K: float = 288.15           # Sea level standard temperature [K]
_P0_PA: float = 101_325.0       # Sea level standard pressure [Pa]
_L_LAPSE: float = 0.0065        # Tropospheric lapse rate [K/m]
_R_AIR: float = 287.058         # Specific gas constant for air [J/(kg*K)]
_FT_LBF_TO_J: float = 1.35582   # ft*lbf to Joule


def isa_density(altitude_m: float | np.ndarray) -> float | np.ndarray:
    """ISA troposphere air density [kg/m^3] from altitude in meters."""
    h = np.asarray(altitude_m, dtype=float)
    T = _T0_K - _L_LAPSE * h
    exponent = G_ACCEL / (_R_AIR * _L_LAPSE)
    return _P0_PA * (1.0 - _L_LAPSE * h / _T0_K) ** exponent / (_R_AIR * T)


def velocity_ft_per_s(h_ft: float | np.ndarray, h_max_ft: float) -> float | np.ndarray:
    """Spec-defined velocity profile, returned in ft/s."""
    h = np.asarray(h_ft, dtype=float)
    return 2.0e-10 * (-((h - h_max_ft) * h + (h - h_max_ft) * h**2))


def drag_work(
    h_target_ft: float = 30_000.0,
    cd: float = 0.75,
    nose_cone_d_in: float = 6.0,
) -> float:
    """Integrate drag force over altitude to get total drag work in Joules.

    The integral is performed in mixed units (force in lbf, height in ft)
    to match the MATLAB derivation exactly, then converted to Joules at the
    end.  At default parameters this returns approximately 1.11e6 J.
    """
    # Cross-section area uses nose-cone diameter, ft^2
    d_ft = nose_cone_d_in / 12.0
    area_ft2 = math.pi * (d_ft / 2.0) ** 2

    # ISA density in slug/ft^3 (kg/m^3 -> slug/ft^3)
    kg_per_m3_to_slug_per_ft3 = 0.00194032

    def integrand(h_ft):
        h_m = h_ft * FT_TO_M
        rho = isa_density(h_m) * kg_per_m3_to_slug_per_ft3
        v = velocity_ft_per_s(h_ft, h_target_ft)
        # F = 0.5 rho Cd A v^2  -> in lbf when rho is in slug/ft^3, v in ft/s, A in ft^2
        return 0.5 * rho * cd * area_ft2 * v**2

    work_ft_lbf, _ = quad(integrand, 0.0, h_target_ft, limit=200)
    return work_ft_lbf * _FT_LBF_TO_J


def energy_needed(
    m_total_kg: float | np.ndarray,
    h_target_ft: float,
    drag_work_J: float,
) -> float | np.ndarray:
    """Energy required to reach apogee: m g h + W_drag (kinetic term vanishes)."""
    h_m = h_target_ft * FT_TO_M
    return m_total_kg * G_ACCEL * h_m + drag_work_J
