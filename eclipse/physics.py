"""Thick-walled pressure vessel physics (Lamé equations).

This module contains the closed-form stress and geometry expressions used by
the optimizer. All functions are written so they accept either Python scalars
or NumPy arrays of any shape; the vectorized form is what makes the 256,000-
point design-grid sweep run in a fraction of a second.

Reference: MECH 315 Spring 2026 final report, Section 4.
"""

from __future__ import annotations

from typing import Tuple

import numpy as np

from .data import P_ATM, R_BAR, T_GAS


# ---------------------------------------------------------------------------
# Maximum allowable internal pressure (Lamé + Von Mises at the inner wall)
# ---------------------------------------------------------------------------

def p_max_thick_walled(
    r_outer: np.ndarray | float,
    r_inner: np.ndarray | float,
    yield_strength: float,
    p_external: float = P_ATM,
) -> np.ndarray | float:
    """Maximum internal pressure before yield, from the Lamé/Von Mises derivation.

    Derived in the report:

        sigma_VM = sqrt(3) * r0^2 * (Pi - P0) / (r0^2 - ri^2) = Sy
        =>  P_max = Sy * (r0^2 - ri^2) / (sqrt(3) * r0^2) + P0

    The thin-walled limit (t << r) recovers P_max ≈ 2*Sy*t / (sqrt(3)*r0).

    Parameters
    ----------
    r_outer : outer radius [m]
    r_inner : inner radius [m]
    yield_strength : Sy [Pa]
    p_external : external pressure [Pa] (default 1 atm)
    """
    r0 = np.asarray(r_outer, dtype=float)
    ri = np.asarray(r_inner, dtype=float)
    return yield_strength * (r0**2 - ri**2) / (np.sqrt(3.0) * r0**2) + p_external


# ---------------------------------------------------------------------------
# Lamé stress components at an arbitrary radial position r
# ---------------------------------------------------------------------------

def lame_stresses(
    r: np.ndarray | float,
    r_outer: float,
    r_inner: float,
    p_internal: float,
    p_external: float = P_ATM,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Hoop, radial, and axial stresses through the wall of a closed-end vessel.

    Returns
    -------
    (sigma_hoop, sigma_radial, sigma_axial) : tuple of arrays in [Pa]
    """
    r = np.asarray(r, dtype=float)
    common = (p_internal * r_inner**2 - p_external * r_outer**2) / (r_outer**2 - r_inner**2)
    var_term = (r_inner * r_outer) ** 2 * (p_internal - p_external) / (r**2 * (r_outer**2 - r_inner**2))

    sigma_hoop = common + var_term
    sigma_radial = common - var_term
    sigma_axial = np.full_like(sigma_hoop, common)
    return sigma_hoop, sigma_radial, sigma_axial


def von_mises(sigma_hoop, sigma_radial, sigma_axial):
    """Three-component Von Mises stress."""
    sh = np.asarray(sigma_hoop, dtype=float)
    sr = np.asarray(sigma_radial, dtype=float)
    sa = np.asarray(sigma_axial, dtype=float)
    return np.sqrt(0.5 * ((sh - sa) ** 2 + (sa - sr) ** 2 + (sr - sh) ** 2))


def stresses_at_inner_wall(
    r_outer: float,
    r_inner: float,
    p_internal: float,
    p_external: float = P_ATM,
) -> Tuple[float, float, float, float]:
    """Convenience wrapper: stresses + Von Mises at r = r_inner."""
    sh, sr, sa = lame_stresses(r_inner, r_outer, r_inner, p_internal, p_external)
    svm = von_mises(sh, sr, sa)
    return float(sh), float(sr), float(sa), float(svm)


# ---------------------------------------------------------------------------
# Vessel geometry (cylinder + 2 hemispherical caps = sphere)
# ---------------------------------------------------------------------------

def cyl_section_length(L_total, r_outer):
    """Length of the cylindrical section: L_total - 2*r0."""
    return L_total - 2.0 * r_outer


def metal_shell_volume(r_outer, r_inner, L_total):
    """Metal volume = cylindrical annulus + spherical shell (two hemispheres)."""
    L_cyl = cyl_section_length(L_total, r_outer)
    return np.pi * (r_outer**2 - r_inner**2) * L_cyl + (4.0 / 3.0) * np.pi * (r_outer**3 - r_inner**3)


def interior_volume(r_inner, r_outer, L_total):
    """Gas-storage volume = inner cylinder + inner sphere."""
    L_cyl = cyl_section_length(L_total, r_outer)
    return np.pi * r_inner**2 * L_cyl + (4.0 / 3.0) * np.pi * r_inner**3


# ---------------------------------------------------------------------------
# Gas content (ideal gas)
# ---------------------------------------------------------------------------

def moles_stored(p_internal, volume, temperature: float = T_GAS):
    """n = P V / (R T)."""
    return p_internal * volume / (R_BAR * temperature)


def gas_mass(n_moles, molar_mass):
    return n_moles * molar_mass


def stored_energy(n_moles, energy_density):
    return n_moles * energy_density
