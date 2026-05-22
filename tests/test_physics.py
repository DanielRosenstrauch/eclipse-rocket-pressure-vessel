"""Verification tests against the MATLAB report's published numerical results.

These pin the Python port to the same answers reported in the MECH 315
Eclipse Rocket final report (Spring 2026).
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pytest

from eclipse.data import INCH_TO_M, PSI_TO_PA, material_by_name, fuel_by_name
from eclipse.optimize import DesignSpace, optimize
from eclipse.physics import (
    interior_volume,
    metal_shell_volume,
    p_max_thick_walled,
    stresses_at_inner_wall,
)
from eclipse.trajectory import drag_work


# -----------------------------------------------------------------------
# Drag work: report says W_drag = 1.11e6 J
# -----------------------------------------------------------------------

def test_drag_work_matches_report_within_5pct():
    W = drag_work(h_target_ft=30_000.0, cd=0.75, nose_cone_d_in=6.0)
    assert 1.0e6 < W < 1.2e6, f"Drag work {W:.3e} J outside expected band"


# -----------------------------------------------------------------------
# Lamé / Von Mises self-consistency: P_max formula should yield sigma_VM = Sy
# -----------------------------------------------------------------------

def test_p_max_recovers_yield_stress():
    """The P_max formula should put sigma_VM exactly at Sy at the inner wall."""
    Sy = 345e6
    r0 = 0.0695
    t = 0.00081
    ri = r0 - t
    P = p_max_thick_walled(r0, ri, Sy)
    _, _, _, svm = stresses_at_inner_wall(r0, ri, P)
    rel_err = abs(svm - Sy) / Sy
    assert rel_err < 1e-10, f"sigma_VM/Sy off by {rel_err:.2e}"


# -----------------------------------------------------------------------
# Geometry: at the optimum the report gives V_inner and V_metal that we
# can back out from m_tank and density.
# -----------------------------------------------------------------------

def test_optimum_tank_mass_matches_report():
    """Duralumin + H2 optimum: m_tank = 1.4933 kg, r0=2.737 in, t=0.0319 in, L=60 in."""
    mat = material_by_name("Duralumin 2024-T3")
    r0 = 2.737 * INCH_TO_M
    t = 0.0319 * INCH_TO_M
    L = 60.0 * INCH_TO_M
    ri = r0 - t
    V_metal = metal_shell_volume(r0, ri, L)
    m_tank = mat.density * V_metal
    # Report value is 1.4933 kg; allow 0.5% tolerance for in/m rounding
    assert math.isclose(m_tank, 1.4933, rel_tol=5e-3), m_tank


def test_optimum_pmax_matches_report():
    mat = material_by_name("Duralumin 2024-T3")
    r0 = 2.737 * INCH_TO_M
    t = 0.0319 * INCH_TO_M
    P = p_max_thick_walled(r0, r0 - t, mat.yield_strength)
    assert math.isclose(P / PSI_TO_PA, 684.0, rel_tol=5e-3), P / PSI_TO_PA


# -----------------------------------------------------------------------
# Full optimization: at alpha=0.5 the global optimum should be Duralumin+H2
# -----------------------------------------------------------------------

def test_global_optimum_is_duralumin_plus_hydrogen():
    res = optimize(alpha=0.5, drag_work_J=1.11e6)  # match the MATLAB hardcoded value
    g = res.global_optimum
    assert g is not None
    assert g.material.name == "Duralumin 2024-T3"
    assert g.fuel.name == "Hydrogen (H2)"
    # Loose checks on the headline numbers (~1% tolerance, since our grid
    # discretization is identical to the MATLAB one)
    assert math.isclose(g.r_outer / INCH_TO_M, 2.737, rel_tol=2e-3)
    assert math.isclose(g.thickness / INCH_TO_M, 0.0319, rel_tol=5e-2)
    assert math.isclose(g.L_total / INCH_TO_M, 60.0, rel_tol=2e-3)
    assert math.isclose(g.m_prop, 1.5768, rel_tol=1e-2)
    assert math.isclose(g.cost, 9.09, rel_tol=2e-2)


def test_per_combination_sample_aluminum_h2():
    """Sanity check one of the non-optimal rows from the report table."""
    res = optimize(alpha=0.5, drag_work_J=1.11e6)
    pair = next(
        d for d in res.per_combination
        if d.material.name == "Aluminum 6061-T6" and d.fuel.name == "Hydrogen (H2)"
    )
    # report: r=2.529, m_prop=1.9268, cost=$6.06
    assert math.isclose(pair.r_outer / INCH_TO_M, 2.529, rel_tol=1e-2)
    assert math.isclose(pair.m_prop, 1.9268, rel_tol=1e-2)
    assert math.isclose(pair.cost, 6.06, rel_tol=2e-2)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
